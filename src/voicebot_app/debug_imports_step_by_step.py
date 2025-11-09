#!/usr/bin/env python3
"""
Debug script to test provider imports step by step
"""

import sys
import importlib

def test_import_step_by_step():
    """Test imports step by step to identify where the issue occurs"""
    
    print("🧪 Testing Imports Step by Step")
    print(f"Python path: {sys.path}")
    print()
    
    # Test importing the base module first
    print("1. Testing base module import:")
    try:
        base_module = importlib.import_module("services.llm.providers")
        print(f"✅ Successfully imported: services.llm.providers")
        print(f"   Module attributes: {dir(base_module)}")
    except ImportError as e:
        print(f"❌ Failed to import services.llm.providers: {e}")
        return
    
    print()
    
    # Test importing the groq submodule
    print("2. Testing groq submodule import:")
    try:
        groq_module = importlib.import_module("services.llm.providers.groq")
        print(f"✅ Successfully imported: services.llm.providers.groq")
        print(f"   Module attributes: {dir(groq_module)}")
    except ImportError as e:
        print(f"❌ Failed to import services.llm.providers.groq: {e}")
        return
    
    print()
    
    # Test importing the groq_provider module
    print("3. Testing groq_provider module import:")
    try:
        groq_provider_module = importlib.import_module("services.llm.providers.groq.groq_provider")
        print(f"✅ Successfully imported: services.llm.providers.groq.groq_provider")
        print(f"   Module attributes: {dir(groq_provider_module)}")
        
        # Test getting the GroqProvider class
        if hasattr(groq_provider_module, 'GroqProvider'):
            print(f"✅ Found GroqProvider class")
            provider_class = groq_provider_module.GroqProvider
            print(f"   Class methods: {[m for m in dir(provider_class) if not m.startswith('_')]}")
        else:
            print(f"❌ GroqProvider class not found in module")
            
    except ImportError as e:
        print(f"❌ Failed to import services.llm.providers.groq.groq_provider: {e}")

if __name__ == "__main__":
    test_import_step_by_step()