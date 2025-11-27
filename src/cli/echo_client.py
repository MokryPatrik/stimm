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
    logger.info("🚀 Starting optimized echo client (sounddevice)")
    
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
        logger.info(f"Participant connected: {participant.identity}")
        if participant.identity == "echo-bot":
             # Subscribe to all audio tracks from echo agent
            for publication in participant.track_publications.values():
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    publication.set_subscribed(True)
                    logger.info(f"✅ Subscribed to audio track from {participant.identity}")

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"🎧 Audio track from {participant.identity}")
            asyncio.create_task(play_audio_stream(track))

    try:
        await room.connect(url, token)
        logger.info("✅ Connected to room")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return

    # Check for existing participants
    for participant in room.remote_participants.values():
        if participant.identity == "echo-bot":
            logger.info(f"🔍 Found existing echo agent: {participant.identity}")
            for publication in participant.track_publications.values():
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    publication.set_subscribed(True)
                    logger.info(f"✅ Subscribed to existing audio track")
    
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
        # Keep running until interrupted
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
                # indata is numpy array (int16)
                frame = rtc.AudioFrame.create(SAMPLE_RATE, CHANNELS, len(indata))
                
                # Copy data to frame
                # frame.data is memoryview, we can copy into it
                # We need to ensure types match. indata is int16.
                
                # Direct copy using numpy if available or buffer protocol
                # Note: LiveKit AudioFrame data needs to be populated
                frame_data_np = np.frombuffer(frame.data, dtype=np.int16)
                np.copyto(frame_data_np, indata.flatten())
                
                await source.capture_frame(frame)
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                await asyncio.sleep(0.1)


async def play_audio_stream(track):
    """Play received audio using sounddevice"""
    loop = asyncio.get_event_loop()
    stream_queue = asyncio.Queue(maxsize=50) # Buffer some frames
    
    # We need a callback that pulls from the queue
    # Since callback is sync and runs in a separate thread, we need a thread-safe way to get data
    # But queue.get() is async.
    # So we use a sync queue or a simpler approach:
    # We can write to a sounddevice OutputStream using write() method in a loop, 
    # but we need to match the rate.
    
    # Better approach for async playback: 
    # Use a RawOutputStream and write to it.
    
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
                # Convert frame data to numpy array
                data = np.frombuffer(event.frame.data, dtype=np.int16)
                
                # Write to sounddevice stream
                # This is blocking if buffer is full, which is what we want for sync
                # But we are in async function, so blocking here blocks the event loop!
                # We must run write in executor or use non-blocking approach.
                
                # sd.OutputStream.write takes a numpy array.
                # It writes to the ring buffer. If full, it blocks.
                await loop.run_in_executor(None, output_stream.write, data)
                
    except Exception as e:
        logger.error(f"Playback error: {e}")
    finally:
        output_stream.stop()
        output_stream.close()
        logger.info("Playback stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass