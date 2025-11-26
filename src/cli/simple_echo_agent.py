import asyncio
import logging
import os
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)

load_dotenv()
logger = logging.getLogger("simple-echo")
logging.basicConfig(level=logging.INFO)

async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # wait for the first participant to connect
    participant: rtc.Participant = await ctx.wait_for_participant()
    logger.info(f"starting simple echo for participant {participant.identity}")
    
    stream = rtc.AudioStream.from_participant(
        participant=participant,
        track_source=rtc.TrackSource.SOURCE_MICROPHONE,
    )

    source = rtc.AudioSource(sample_rate=48000, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("simple-echo", source)
    await ctx.room.local_participant.publish_track(
        track,
        rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE),
    )
    
    logger.info("Echo loop started - speak to hear yourself immediately")

    async for audio_event in stream:
        # Immediately capture and send back the frame
        await source.capture_frame(audio_event.frame)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
