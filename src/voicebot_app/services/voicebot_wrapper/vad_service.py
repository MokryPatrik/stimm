"""
Backend WebRTC VAD service for real-time voice activity detection.

This service replaces the frontend JavaScript VAD with Google's WebRTC VAD
implementation for better voice filtering and noise discrimination.
"""

import asyncio
import logging
import struct
from typing import AsyncGenerator, Dict, Any, Optional
import webrtcvad

logger = logging.getLogger(__name__)


class WebRTCVADService:
    """
    WebRTC VAD service for real-time voice activity detection.
    
    Uses Google's WebRTC VAD algorithm to distinguish voice from non-voice
    audio with high accuracy and low latency.
    """
    
    def __init__(self, aggressiveness: int = 3):
        """
        Initialize WebRTC VAD service.
        
        Args:
            aggressiveness: VAD aggressiveness level (0-3)
                0 = least aggressive about filtering out non-speech
                3 = most aggressive about filtering out non-speech
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = 16000  # WebRTC VAD requires 16kHz
        self.frame_duration = 30  # ms (10, 20, or 30ms supported)
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        
        # Validate frame size (must be 160, 320, or 480 samples for 16kHz)
        valid_frame_sizes = [160, 320, 480]  # 10ms, 20ms, 30ms at 16kHz
        if self.frame_size not in valid_frame_sizes:
            raise ValueError(f"Invalid frame size {self.frame_size}. Must be one of {valid_frame_sizes}")
        
        logger.info(f"WebRTC VAD initialized: aggressiveness={aggressiveness}, "
                   f"sample_rate={self.sample_rate}, frame_duration={self.frame_duration}ms")
    
    def is_valid_audio_frame(self, audio_data: bytes) -> bool:
        """
        Check if audio data is valid for WebRTC VAD processing.
        
        Args:
            audio_data: Raw PCM audio data
            
        Returns:
            True if valid for VAD processing
        """
        # Check if data length matches expected frame size (2 bytes per sample for 16-bit PCM)
        expected_bytes = self.frame_size * 2
        return len(audio_data) == expected_bytes
    
    def process_audio_frame(self, audio_data: bytes) -> bool:
        """
        Process a single audio frame through WebRTC VAD.
        
        Args:
            audio_data: Raw PCM audio data (16kHz, 16-bit, mono)
            
        Returns:
            True if voice detected, False otherwise
            
        Raises:
            ValueError: If audio data is invalid for VAD processing
        """
        if not self.is_valid_audio_frame(audio_data):
            raise ValueError(f"Invalid audio frame size: {len(audio_data)} bytes, "
                           f"expected {self.frame_size * 2} bytes")
        
        try:
            return self.vad.is_speech(audio_data, self.sample_rate)
        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            return False
    
    async def process_audio_stream(
        self, 
        audio_generator: AsyncGenerator[bytes, None],
        vad_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process continuous audio stream with real-time VAD.
        
        Args:
            audio_generator: Async generator yielding audio chunks
            vad_callback: Optional callback function for VAD results
            
        Yields:
            Dict with VAD results and metadata
        """
        frame_count = 0
        voice_frame_count = 0
        consecutive_voice_frames = 0
        consecutive_silence_frames = 0
        
        # VAD state tracking
        is_voice_active = False
        voice_start_time = None
        
        try:
            async for audio_chunk in audio_generator:
                frame_count += 1
                
                # Process frame through VAD
                is_voice = self.process_audio_frame(audio_chunk)
                
                # Update counters
                if is_voice:
                    voice_frame_count += 1
                    consecutive_voice_frames += 1
                    consecutive_silence_frames = 0
                else:
                    consecutive_voice_frames = 0
                    consecutive_silence_frames += 1
                
                # Voice activity state machine
                previous_voice_state = is_voice_active
                
                # Voice start: 12 consecutive voice frames (360ms) - extremely conservative
                if not is_voice_active and consecutive_voice_frames >= 12:
                    is_voice_active = True
                    voice_start_time = frame_count * self.frame_duration
                    logger.debug(f"Voice activity started at frame {frame_count}")
                
                # Voice end: 20 consecutive silence frames (600ms) - require very long silence
                elif is_voice_active and consecutive_silence_frames >= 20:
                    is_voice_active = False
                    voice_duration = (frame_count - (voice_start_time // self.frame_duration)) * self.frame_duration
                    logger.debug(f"Voice activity ended at frame {frame_count}, duration: {voice_duration}ms")
                    voice_start_time = None
                
                # Calculate voice probability (simple moving average)
                voice_probability = voice_frame_count / frame_count if frame_count > 0 else 0.0
                
                # Prepare VAD result
                vad_result = {
                    "type": "vad_result",
                    "is_voice": is_voice,
                    "is_voice_active": is_voice_active,
                    "voice_probability": voice_probability,
                    "frame_count": frame_count,
                    "consecutive_voice_frames": consecutive_voice_frames,
                    "consecutive_silence_frames": consecutive_silence_frames,
                    "timestamp": frame_count * self.frame_duration,
                    "frame_duration": self.frame_duration
                }
                
                # Call callback if provided
                if vad_callback:
                    try:
                        vad_callback(vad_result)
                    except Exception as e:
                        logger.error(f"VAD callback error: {e}")
                
                yield vad_result
                
        except asyncio.CancelledError:
            logger.info("VAD processing cancelled")
        except Exception as e:
            logger.error(f"Error in VAD stream processing: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get VAD service statistics."""
        return {
            "sample_rate": self.sample_rate,
            "frame_duration": self.frame_duration,
            "frame_size": self.frame_size,
            "aggressiveness": self.vad._mode
        }


class VADProcessor:
    """
    Higher-level VAD processor that integrates with the voicebot pipeline.
    
    This class handles the integration between WebRTC VAD and the existing
    voicebot service architecture.
    """
    
    def __init__(self, aggressiveness: int = 2):
        self.vad_service = WebRTCVADService(aggressiveness)
        self.active = False
        
    async def start_vad_processing(
        self, 
        conversation_id: str,
        audio_generator: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Start VAD processing for a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            audio_generator: Async generator yielding audio chunks
            
        Yields:
            VAD results with conversation context
        """
        self.active = True
        logger.info(f"Starting VAD processing for conversation: {conversation_id}")
        
        async for vad_result in self.vad_service.process_audio_stream(audio_generator):
            if not self.active:
                break
                
            # Add conversation context to VAD result
            vad_result["conversation_id"] = conversation_id
            yield vad_result
        
        logger.info(f"VAD processing stopped for conversation: {conversation_id}")
    
    def stop_vad_processing(self):
        """Stop VAD processing."""
        self.active = False
        logger.info("VAD processing stopped")
    
    def is_voice_active(self) -> bool:
        """Check if voice is currently active (for interruption logic)."""
        # This would track the current voice state from the last processed frame
        # For now, return False - actual state tracking would be implemented
        # in the integration with voicebot_service
        return False


# Global VAD service instance
vad_service = WebRTCVADService(aggressiveness=3)
vad_processor = VADProcessor(aggressiveness=3)