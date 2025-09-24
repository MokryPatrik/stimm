"""
LLM API Routes
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
from .llm import LLMService

router = APIRouter()
llm_service = LLMService()

@router.post("/llm/generate")
async def generate_text(prompt: str):
    """
    Generate text using the configured LLM provider
    """
    result = await llm_service.generate(prompt)
    return {"result": result}

@router.post("/llm/generate-stream")
async def generate_text_stream(prompt: str):
    """
    Stream text generation using the configured LLM provider
    """
    async def generate():
        async for chunk in llm_service.generate_stream(prompt):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )