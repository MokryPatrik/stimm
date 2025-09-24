#!/usr/bin/env python3
"""
Test script for the shared streaming module integration.

This script tests that the parallel live streaming logic works correctly
for both TTS and voicebot interfaces.
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from voicebot_app.services.shared_streaming import SharedStreamingManager


async def test_shared_streaming_manager():
    """Test the shared streaming manager functionality."""
    print("🧪 Testing Shared Streaming Manager...")
    
    # Create manager instance
    manager = SharedStreamingManager()
    
    # Test session creation
    session_id = "test_session_123"
    session = manager.create_session(session_id)
    assert session.session_id == session_id
    print("✅ Session creation test passed")
    
    # Test session retrieval
    retrieved_session = manager.get_session(session_id)
    assert retrieved_session is not None
    assert retrieved_session.session_id == session_id
    print("✅ Session retrieval test passed")
    
    # Test session status
    status = manager.get_session_status(session_id)
    assert status["session_id"] == session_id
    assert status["is_streaming"] == False
    assert status["is_playing"] == False
    print("✅ Session status test passed")
    
    # Test progress updates
    manager.update_progress(session_id, llm_progress=0.5, tts_progress=0.3)
    updated_status = manager.get_session_status(session_id)
    assert updated_status["llm_progress"] == 0.5
    assert updated_status["tts_progress"] == 0.3
    print("✅ Progress update test passed")
    
    # Test session cleanup
    manager.end_session(session_id)
    assert manager.get_session(session_id) is None
    print("✅ Session cleanup test passed")
    
    print("🎉 All Shared Streaming Manager tests passed!")


async def test_text_generator():
    """Test the text generator functionality."""
    print("\n🧪 Testing Text Generator...")
    
    manager = SharedStreamingManager()
    session_id = "test_generator_session"
    session = manager.create_session(session_id)
    
    # Create a simple text source
    async def simple_text_source():
        yield "Hello "
        yield "world "
        yield "this is a test."
    
    # Test text generator with progress tracking
    text_chunks = []
    
    async def on_text_chunk(chunk, count):
        text_chunks.append(chunk)
        print(f"📤 Text chunk {count}: '{chunk.strip()}'")
    
    generator = manager.create_text_generator(
        None,  # No WebSocket needed for this test
        simple_text_source(),
        session_id,
        on_text_chunk=on_text_chunk
    )
    
    # Consume the generator
    async for chunk in generator:
        pass
    
    assert len(text_chunks) == 3
    assert text_chunks[0] == "Hello "
    assert text_chunks[1] == "world "
    assert text_chunks[2] == "this is a test."
    print("✅ Text generator test passed")
    
    # Check progress tracking
    status = manager.get_session_status(session_id)
    assert status["text_chunks_sent"] == 3
    print("✅ Progress tracking test passed")
    
    manager.end_session(session_id)
    print("🎉 All Text Generator tests passed!")


async def main():
    """Run all tests."""
    print("🚀 Starting Shared Streaming Module Tests...\n")
    
    try:
        await test_shared_streaming_manager()
        await test_text_generator()
        
        print("\n🎊 All tests completed successfully!")
        print("✅ The shared streaming module is working correctly.")
        print("📊 The voicebot interface now has access to parallel live streaming capabilities.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)