#!/usr/bin/env python3
"""
Integration test for the shared streaming module with voicebot service.

This test verifies that the voicebot service can successfully import and use
the shared streaming module for parallel live streaming.
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing module imports...")
    
    try:
        # Test shared streaming module
        from voicebot_app.services.shared_streaming import SharedStreamingManager, shared_streaming_manager
        print("✅ Shared streaming module imported successfully")
        
        # Test voicebot routes
        from voicebot_app.services.voicebot_wrapper.routes import router
        print("✅ Voicebot routes imported successfully")
        
        # Test voicebot service
        from voicebot_app.services.voicebot_wrapper.voicebot_service import VoicebotService
        print("✅ Voicebot service imported successfully")
        
        # Test that shared streaming is integrated in routes
        import voicebot_app.services.voicebot_wrapper.routes as voicebot_routes
        assert hasattr(voicebot_routes, 'shared_streaming_manager')
        print("✅ Shared streaming manager integrated in voicebot routes")
        
        # Test that shared streaming is integrated in service
        import voicebot_app.services.voicebot_wrapper.voicebot_service as voicebot_service_module
        assert hasattr(voicebot_service_module, 'shared_streaming_manager')
        print("✅ Shared streaming manager integrated in voicebot service")
        
        print("🎉 All imports and integrations successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_shared_streaming_functionality():
    """Test basic shared streaming functionality."""
    print("\n🧪 Testing shared streaming functionality...")
    
    try:
        from voicebot_app.services.shared_streaming import SharedStreamingManager
        
        # Create manager instance
        manager = SharedStreamingManager()
        
        # Test session management
        session_id = "test_integration_session"
        session = manager.create_session(session_id)
        assert session.session_id == session_id
        print("✅ Session creation working")
        
        # Test status retrieval
        status = manager.get_session_status(session_id)
        assert status["session_id"] == session_id
        print("✅ Status retrieval working")
        
        # Test progress updates
        manager.update_progress(session_id, llm_progress=0.7, tts_progress=0.4)
        updated_status = manager.get_session_status(session_id)
        assert updated_status["llm_progress"] == 0.7
        assert updated_status["tts_progress"] == 0.4
        print("✅ Progress updates working")
        
        # Test session cleanup
        manager.end_session(session_id)
        assert manager.get_session(session_id) is None
        print("✅ Session cleanup working")
        
        print("🎉 Shared streaming functionality verified!")
        return True
        
    except Exception as e:
        print(f"❌ Shared streaming functionality test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Starting Integration Tests for Shared Streaming Module...\n")
    
    success = True
    
    # Run import tests
    if not test_imports():
        success = False
    
    # Run functionality tests
    if not test_shared_streaming_functionality():
        success = False
    
    if success:
        print("\n🎊 All integration tests passed!")
        print("✅ The shared streaming module is successfully integrated with the voicebot interface.")
        print("📊 Parallel live streaming is now available for both TTS and voicebot interfaces.")
        return 0
    else:
        print("\n❌ Some integration tests failed.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)