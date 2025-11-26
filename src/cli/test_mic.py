"""
Test script for PulseAudio recording using ffmpeg
"""
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def test_pulseaudio_recording(duration=5, output_file="test_recording.wav"):
    """
    Test recording from PulseAudio using ffmpeg
    """
    logger.info(f"🎙️ Testing PulseAudio recording for {duration}s...")
    
    try:
        # First, check if we can list PulseAudio sources
        result = subprocess.run(
            ["pactl", "list", "short", "sources"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("🔍 PulseAudio sources:")
        logger.info(result.stdout)
        
        # Record using ffmpeg with PulseAudio
        cmd = [
            "ffmpeg",
            "-f", "pulse",
            "-i", "default",
            "-t", str(duration),
            "-y",  # Overwrite output file
            output_file
        ]
        
        logger.info(f"📹 Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        logger.info(f"✅ Recording saved to {output_file}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error running command: {e}")
        logger.error(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError as e:
        logger.error(f"❌ Command not found: {e}")
        return False

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    success = test_pulseaudio_recording(duration)
    
    if success:
        print(f"✅ PulseAudio test successful! Recording saved to test_recording.wav")
    else:
        print("❌ PulseAudio test failed")
        sys.exit(1)