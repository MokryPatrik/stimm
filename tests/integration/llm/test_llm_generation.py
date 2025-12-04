"""
LLM Streaming Tests
"""

import pytest
import asyncio
import sys
import os

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from services.llm.llm import LLMService


@pytest.mark.requires_provider("llm")
@pytest.mark.asyncio
async def test_llm_generation():
    """Test LLM text generation"""
    llm_service = LLMService()
    prompt = "Test prompt"
    result = await llm_service.generate(prompt)

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.requires_provider("llm")
@pytest.mark.asyncio
async def test_llm_streaming():
    """Test LLM streaming generation"""
    llm_service = LLMService()
    prompt = "Test prompt"
    
    chunks = []
    async for chunk in llm_service.generate_stream(prompt):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert isinstance(full_text, str)
    assert len(full_text) > 0


@pytest.mark.requires_provider("llm")
class TestLLMGeneration:
    """Test suite for LLM generation across all providers."""
    
    @pytest.mark.asyncio
    async def test_groq_service_initialization(self, groq_config):
        """Test that LLM service initializes correctly with Groq provider."""
        if not groq_config:
            pytest.skip("GROQ_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.groq.groq_provider import GroqProvider
        
        provider = GroqProvider(groq_config)
        
        assert provider is not None
        assert provider.config["api_key"] == groq_config["api_key"]
        assert provider.config["model"] == groq_config["model"]
    
    @pytest.mark.asyncio
    async def test_mistral_service_initialization(self, mistral_config):
        """Test that LLM service initializes correctly with Mistral provider."""
        if not mistral_config:
            pytest.skip("MISTRAL_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.mistral.mistral_provider import MistralProvider
        
        provider = MistralProvider(mistral_config)
        
        assert provider is not None
        assert provider.config["api_key"] == mistral_config["api_key"]
        assert provider.config["model"] == mistral_config["model"]
    
    @pytest.mark.asyncio
    async def test_openrouter_service_initialization(self, openrouter_config):
        """Test that LLM service initializes correctly with OpenRouter provider."""
        if not openrouter_config:
            pytest.skip("OPENROUTER_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.openrouter.openrouter_provider import OpenRouterProvider
        
        provider = OpenRouterProvider(openrouter_config)
        
        assert provider is not None
        assert provider.config["api_key"] == openrouter_config["api_key"]
        assert provider.config["model"] == openrouter_config["model"]
    
    @pytest.mark.asyncio
    async def test_llama_cpp_service_initialization(self, llama_cpp_config):
        """Test that LLM service initializes correctly with Llama.cpp provider."""
        from services.llm.providers.llama_cpp.llama_cpp_provider import LlamaCppProvider
        
        provider = LlamaCppProvider(llama_cpp_config)
        
        assert provider is not None
        assert provider.config["api_url"] == llama_cpp_config["api_url"]
        assert provider.config["model"] == llama_cpp_config["model"]
    
    @pytest.mark.asyncio
    async def test_groq_generation(self, groq_config):
        """Test text generation with Groq provider."""
        if not groq_config:
            pytest.skip("GROQ_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.groq.groq_provider import GroqProvider
        
        provider = GroqProvider(groq_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            result = await provider.generate(prompt)
            
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ Groq generation succeeded: {result[:50]}...")
        
        except Exception as e:
            # If the Groq connection fails, this might be expected
            if "Connection" in str(e) or "API" in str(e) or "quota" in str(e).lower():
                pytest.skip(f"Groq connection issue: {e}")
            else:
                pytest.fail(f"Groq generation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_mistral_generation(self, mistral_config):
        """Test text generation with Mistral provider."""
        if not mistral_config:
            pytest.skip("MISTRAL_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.mistral.mistral_provider import MistralProvider
        
        provider = MistralProvider(mistral_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            result = await provider.generate(prompt)
            
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ Mistral generation succeeded: {result[:50]}...")
        
        except Exception as e:
            if "Connection" in str(e) or "API" in str(e) or "quota" in str(e).lower():
                pytest.skip(f"Mistral connection issue: {e}")
            else:
                pytest.fail(f"Mistral generation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_openrouter_generation(self, openrouter_config):
        """Test text generation with OpenRouter provider."""
        if not openrouter_config:
            pytest.skip("OPENROUTER_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.openrouter.openrouter_provider import OpenRouterProvider
        
        provider = OpenRouterProvider(openrouter_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            result = await provider.generate(prompt)
            
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ OpenRouter generation succeeded: {result[:50]}...")
        
        except Exception as e:
            if "Connection" in str(e) or "API" in str(e) or "quota" in str(e).lower():
                pytest.skip(f"OpenRouter connection issue: {e}")
            else:
                pytest.fail(f"OpenRouter generation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_llama_cpp_generation(self, llama_cpp_config):
        """Test text generation with Llama.cpp provider."""
        from services.llm.providers.llama_cpp.llama_cpp_provider import LlamaCppProvider
        
        provider = LlamaCppProvider(llama_cpp_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            result = await provider.generate(prompt)
            
            assert isinstance(result, str)
            assert len(result) > 0
            print(f"✅ Llama.cpp generation succeeded: {result[:50]}...")
        
        except Exception as e:
            if "Connection" in str(e) or "API" in str(e):
                pytest.skip(f"Llama.cpp connection issue: {e}")
            else:
                pytest.fail(f"Llama.cpp generation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_groq_streaming(self, groq_config):
        """Test streaming generation with Groq provider."""
        if not groq_config:
            pytest.skip("GROQ_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.groq.groq_provider import GroqProvider
        
        provider = GroqProvider(groq_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            
            chunks = []
            async for chunk in provider.generate_stream(prompt):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            full_text = "".join(chunks)
            assert isinstance(full_text, str)
            assert len(full_text) > 0
            print(f"✅ Groq streaming succeeded: {len(chunks)} chunks, {len(full_text)} chars")
        
        except Exception as e:
            if "Connection" in str(e) or "API" in str(e) or "quota" in str(e).lower():
                pytest.skip(f"Groq connection issue: {e}")
            else:
                pytest.fail(f"Groq streaming failed: {e}")
    
    @pytest.mark.asyncio
    async def test_mistral_streaming(self, mistral_config):
        """Test streaming generation with Mistral provider."""
        if not mistral_config:
            pytest.skip("MISTRAL_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.mistral.mistral_provider import MistralProvider
        
        provider = MistralProvider(mistral_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            
            chunks = []
            async for chunk in provider.generate_stream(prompt):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            full_text = "".join(chunks)
            assert isinstance(full_text, str)
            assert len(full_text) > 0
            print(f"✅ Mistral streaming succeeded: {len(chunks)} chunks, {len(full_text)} chars")
        
        except Exception as e:
            if "Connection" in str(e) or "API" in str(e) or "quota" in str(e).lower():
                pytest.skip(f"Mistral connection issue: {e}")
            else:
                pytest.fail(f"Mistral streaming failed: {e}")
    
    @pytest.mark.asyncio
    async def test_openrouter_streaming(self, openrouter_config):
        """Test streaming generation with OpenRouter provider."""
        if not openrouter_config:
            pytest.skip("OPENROUTER_LLM_API_KEY environment variable is required")
        
        from services.llm.providers.openrouter.openrouter_provider import OpenRouterProvider
        
        provider = OpenRouterProvider(openrouter_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            
            chunks = []
            async for chunk in provider.generate_stream(prompt):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            full_text = "".join(chunks)
            assert isinstance(full_text, str)
            assert len(full_text) > 0
            print(f"✅ OpenRouter streaming succeeded: {len(chunks)} chunks, {len(full_text)} chars")
        
        except Exception as e:
            if "Connection" in str(e) or "API" in str(e) or "quota" in str(e).lower():
                pytest.skip(f"OpenRouter connection issue: {e}")
            else:
                pytest.fail(f"OpenRouter streaming failed: {e}")
    
    @pytest.mark.asyncio
    async def test_llama_cpp_streaming(self, llama_cpp_config):
        """Test streaming generation with Llama.cpp provider."""
        from services.llm.providers.llama_cpp.llama_cpp_provider import LlamaCppProvider
        
        provider = LlamaCppProvider(llama_cpp_config)
        
        try:
            prompt = "Hello, this is a test. Please respond with a short greeting."
            
            chunks = []
            async for chunk in provider.generate_stream(prompt):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            full_text = "".join(chunks)
            assert isinstance(full_text, str)
            assert len(full_text) > 0
            print(f"✅ Llama.cpp streaming succeeded: {len(chunks)} chunks, {len(full_text)} chars")
        
        except Exception as e:
            if "Connection" in str(e) or "API" in str(e):
                pytest.skip(f"Llama.cpp connection issue: {e}")
            else:
                pytest.fail(f"Llama.cpp streaming failed: {e}")