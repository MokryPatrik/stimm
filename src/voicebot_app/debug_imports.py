#!/usr/bin/env python3
"""
Debug script to test provider imports
"""

import sys
import importlib

def test_import(module_path):
    """Test importing a module"""
    try:
        print(f"🔍 Testing import: {module_path}")
        module = importlib.import_module(module_path)
        print(f"✅ Successfully imported: {module_path}")
        return module
    except ImportError as e:
        print(f"❌ Failed to import {module_path}: {e}")
        return None

def main():
    print("🧪 Debugging Provider Imports")
    print(f"Python path: {sys.path}")
    print()
    
    # Test LLM provider imports
    print("🤖 Testing LLM Provider Imports:")
    test_import("services.llm.providers.groq.groq_provider")
    test_import("services.llm.providers.mistral.mistral_provider")
    test_import("services.llm.providers.openrouter.openrouter_provider")
    test_import("services.llm.providers.llama_cpp.llama_cpp_provider")
    
    print()
    
    # Test TTS provider imports
    print("🗣️ Testing TTS Provider Imports:")
    test_import("services.tts.providers.deepgram.deepgram_provider")
    test_import("services.tts.providers.elevenlabs.elevenlabs_provider")
    test_import("services.tts.providers.async_ai.async_ai_provider")
    test_import("services.tts.providers.kokoro_local.kokoro_local_provider")
    
    print()
    
    # Test STT provider imports
    print("🎤 Testing STT Provider Imports:")
    test_import("services.stt.providers.deepgram.deepgram_provider")
    test_import("services.stt.providers.whisper_local.whisper_local_provider")

if __name__ == "__main__":
    main()