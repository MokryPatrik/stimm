import asyncio
import logging
import time
from services.rag.chatbot_service import chatbot_service
from services.llm.llm import LLMService
from services.rag.rag_state import get_rag_state

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_basic():
    """Test basique pour voir où ça bloque"""
    logger.info("🔍 Test basique du voicebot...")
    
    try:
        # Test 1: RAG State
        logger.info("🧪 Test 1: RAG State")
        rag_state = await get_rag_state()
        logger.info(f"✅ RAG State OK: client={rag_state.client is not None}")
        
        # Test 2: LLM Service
        logger.info("🧪 Test 2: LLM Service")
        llm_service = LLMService()
        logger.info(f"✅ LLM Service OK: {llm_service.provider.__class__.__name__}")
        
        # Test 3: Chatbot Service 
        logger.info("🧪 Test 3: Chatbot Service")
        count = 0
        async for chunk in chatbot_service.process_chat_message("Bonjour", "test", rag_state):
            count += 1
            logger.info(f"📨 Chunk #{count}: {chunk.get('type')}")
            if count >= 3:
                break
        
        logger.info(f"✅ Test 3 OK: {count} chunks received")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_basic())
    logger.info(f"RESULT: {result}")
