#!/usr/bin/env python3
"""
Simple LiveKit Echo Client - Optimized with sounddevice for low latency
"""

import asyncio
import logging
import os
import sounddevice as sd
import numpy as np
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
# Lower latency blocksize (e.g., 20ms)
BLOCK_SIZE = int(SAMPLE_RATE * 0.02) 

async def main():
    """Connect to LiveKit and test echo"""
    logger.info("🚀 Starting simple echo client (sounddevice)")
    
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
    queue = asyncio.Queue()

    def callback(indata, frames, time, status):
        if status:
            logger.warning(f"Microphone status: {status}")
        loop.call_soon_threadsafe(queue.put_nowait, indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=callback
        )
        
        logger.info(f"🎤 Microphone capture started (device: {sd.query_devices(kind='input')['name']})")
        
        with stream:
            while True:
                try:
                    indata = await queue.get()
                    
                    # Create audio frame
                    frame = rtc.AudioFrame.create(SAMPLE_RATE, CHANNELS, len(indata))
                    
                    # Copy data to frame
                    frame_data_np = np.frombuffer(frame.data, dtype=np.int16)
                    np.copyto(frame_data_np, indata.flatten())
                    
                    await source.capture_frame(frame)
                    
                except Exception as e:
                    logger.error(f"Error in capture loop: {e}")
                    await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Microphone setup error: {e}")


async def play_audio_stream(track):
    """Play received audio using sounddevice"""
    loop = asyncio.get_event_loop()
    
    logger.info("🔊 Audio playback started (sounddevice)")
    
    try:
        # Open output stream
        output_stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE
        )
        
        output_stream.start()
        
        audio_stream = rtc.AudioStream(track)
        
        async for event in audio_stream:
            if event.frame:
                data = np.frombuffer(event.frame.data, dtype=np.int16)
                await loop.run_in_executor(None, output_stream.write, data)
                
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