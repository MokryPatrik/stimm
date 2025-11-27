#!/usr/bin/env python3
"""
Simple LiveKit Echo Client - Optimized with sounddevice and ring buffer
"""

import asyncio
import logging
import os
import sounddevice as sd
import numpy as np
import threading
from dotenv import load_dotenv

from livekit import rtc
from livekit.api import AccessToken, VideoGrants

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple-echo-client")

# Audio Configuration
SAMPLE_RATE = 48000
CHANNELS = 1
DTYPE = 'int16'
# We let sounddevice decide the block size for low latency, 
# or set it to 0 to let it be adaptive
BLOCK_SIZE = 0 

async def main():
    """Connect to LiveKit and test echo"""
    logger.info("🚀 Starting simple echo client (sounddevice + ring buffer)")
    
    # Create LiveKit room
    room = rtc.Room()
    
    # Connect to LiveKit
    url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    api_key = os.getenv("LIVEKIT_API_KEY", "devkey")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")
    
    grants = VideoGrants(
        room_join=True,
        room="echo-test",
        can_publish=True,
        can_subscribe=True,
    )
    token = AccessToken(
        api_key=api_key,
        api_secret=api_secret
    ).with_identity("test-client").with_name("Test Client").with_grants(grants).to_jwt()
    
    logger.info(f"Connecting to {url}")
    
    @room.on("participant_connected")
    def on_participant_connected(participant):
        if participant.identity == "echo-bot":
            logger.info(f"🔍 Echo agent connected: {participant.identity}")
            # Subscribe to all audio tracks from echo agent
            for publication in participant.track_publications.values():
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    publication.set_subscribed(True)
                    logger.info(f"✅ Subscribed to audio track from {participant.identity}")

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        logger.info(f"🔍 Track subscribed from {participant.identity} ({track.kind})")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"🎧 Audio track from {participant.identity} - Starting playback")
            asyncio.create_task(play_audio_stream(track))

    try:
        await room.connect(url, token)
        logger.info("✅ Connected to room")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return
    
    # Log all current participants
    logger.debug(f"📊 Current participants in room:")
    for participant in room.remote_participants.values():
        logger.debug(f"   - {participant.identity} (SID: {participant.sid})")
        if participant.identity == "echo-bot":
            logger.info(f"🔍 Found existing echo agent: {participant.identity}")
            for publication in participant.track_publications.values():
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    publication.set_subscribed(True)
                    logger.info(f"✅ Subscribed to existing audio track from {participant.identity}")
    
    # Create audio source for microphone
    mic_source = rtc.AudioSource(sample_rate=SAMPLE_RATE, num_channels=CHANNELS)
    mic_track = rtc.LocalAudioTrack.create_audio_track("mic", mic_source)
    
    # Publish microphone track
    await room.local_participant.publish_track(
        mic_track,
        rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE),
    )
    logger.info("🎤 Published microphone track")
    
    # Start microphone capture
    capture_task = asyncio.create_task(capture_microphone(mic_source))
    
    logger.info(" Echo client running! Speak and you should hear yourself!")
    
    try:
        # Keep running
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        capture_task.cancel()
        await room.disconnect()
        logger.info("Client disconnected")


async def capture_microphone(source):
    """Capture microphone using sounddevice"""
    loop = asyncio.get_event_loop()
    # Use asyncio.Queue for thread-safe communication from callback
    audio_queue = asyncio.Queue()

    def callback(indata, frames, time, status):
        if status:
            pass
        loop.call_soon_threadsafe(audio_queue.put_nowait, indata.copy())

    try:
        # For capture, we prefer small blocks to reduce input latency
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=1024, # ~21ms
            callback=callback
        )
        
        logger.info(f"🎤 Microphone capture started (device: {sd.query_devices(kind='input')['name']})")
        
        with stream:
            while True:
                try:
                    indata = await audio_queue.get()
                    frame = rtc.AudioFrame.create(SAMPLE_RATE, CHANNELS, len(indata))
                    frame_data_np = np.frombuffer(frame.data, dtype=np.int16)
                    np.copyto(frame_data_np, indata.flatten())
                    await source.capture_frame(frame)
                except Exception as e:
                    logger.error(f"Error in capture loop: {e}")
                    await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Microphone setup error: {e}")


class RingBuffer:
    """Thread-safe byte ring buffer"""
    def __init__(self, size):
        self.size = size
        self.buffer = bytearray(size)
        self.read_pos = 0
        self.write_pos = 0
        self.count = 0
        self.lock = threading.Lock()

    def write(self, data):
        with self.lock:
            data_len = len(data)
            if data_len > self.size:
                # Too big, just take last part
                data = data[-self.size:]
                data_len = self.size
                self.read_pos = 0
                self.write_pos = 0
                self.count = 0

            if self.count + data_len > self.size:
                # Overflow - advance read_pos (drop oldest)
                dropped = (self.count + data_len) - self.size
                self.read_pos = (self.read_pos + dropped) % self.size
                self.count -= dropped
                # logger.warning(f"RingBuffer overflow, dropped {dropped} bytes")

            # Write data
            first_part = min(data_len, self.size - self.write_pos)
            self.buffer[self.write_pos:self.write_pos + first_part] = data[:first_part]
            if first_part < data_len:
                self.buffer[0:data_len - first_part] = data[first_part:]
            
            self.write_pos = (self.write_pos + data_len) % self.size
            self.count += data_len

    def read(self, num_bytes):
        with self.lock:
            if self.count < num_bytes:
                # Underrun - return what we have + zeros
                available = self.count
                result = bytearray(num_bytes)
                
                if available > 0:
                    first_part = min(available, self.size - self.read_pos)
                    result[:first_part] = self.buffer[self.read_pos:self.read_pos + first_part]
                    if first_part < available:
                        result[first_part:available] = self.buffer[0:available - first_part]
                    
                    self.read_pos = (self.read_pos + available) % self.size
                    self.count -= available
                
                return result
            
            result = bytearray(num_bytes)
            first_part = min(num_bytes, self.size - self.read_pos)
            result[:first_part] = self.buffer[self.read_pos:self.read_pos + first_part]
            if first_part < num_bytes:
                result[first_part:] = self.buffer[0:num_bytes - first_part]
                
            self.read_pos = (self.read_pos + num_bytes) % self.size
            self.count -= num_bytes
            return result

async def play_audio_stream(track):
    """
    Play received audio using sounddevice with a ring buffer.
    Handles mismatch between LiveKit packet size and SoundDevice block size.
    """
    # 200ms buffer
    buffer_size = int(SAMPLE_RATE * 0.2) * CHANNELS * 2 # 2 bytes per sample
    ring_buffer = RingBuffer(buffer_size)
    
    def callback(outdata, frames, time, status):
        if status:
            pass 
        
        bytes_needed = frames * CHANNELS * 2
        data = ring_buffer.read(bytes_needed)
        
        # Convert to numpy for sounddevice
        outdata[:] = np.frombuffer(data, dtype=DTYPE).reshape(frames, CHANNELS)

    logger.info("🔊 Audio playback started (sounddevice + ring buffer)")
    
    try:
        output_stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=callback
        )
        
        output_stream.start()
        
        audio_stream = rtc.AudioStream(track)
        
        async for event in audio_stream:
            if event.frame:
                # Write directly to ring buffer
                # event.frame.data is memoryview/bytes
                ring_buffer.write(event.frame.data)
                
    except Exception as e:
        logger.error(f"Playback error: {e}")
    finally:
        try:
            output_stream.stop()
            output_stream.close()
        except:
            pass
        logger.info("Playback stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass