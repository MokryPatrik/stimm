"""
Main entry point for the voicebot application.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

# Import route modules
from services.llm.llm_routes import router as llm_router
from services.rag.chatbot_routes import router as chatbot_router
from services.stt.routes import router as stt_router
from services.stt.web_routes import router as stt_web_router
from services.tts.routes import router as tts_router
from services.tts.web_routes import router as tts_web_router
from services.voicebot_wrapper.routes import router as voicebot_router

app = FastAPI(title="Voicebot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for voicebot wrapper
app.mount("/static", StaticFiles(directory="services/voicebot_wrapper/static"), name="voicebot_static")

# Mount shared static files
app.mount("/shared-static", StaticFiles(directory="static"), name="shared_static")

# Include routers
app.include_router(llm_router, prefix="/api", tags=["llm"])
app.include_router(chatbot_router, prefix="/rag", tags=["chatbot"])
app.include_router(stt_router, prefix="/api", tags=["stt"])
app.include_router(stt_web_router, prefix="/stt", tags=["stt-web"])
app.include_router(tts_router, prefix="/api", tags=["tts"])
app.include_router(tts_web_router, prefix="/tts", tags=["tts-web"])
app.include_router(voicebot_router, prefix="/api", tags=["voicebot"])

# Templates for voicebot interface
templates = Jinja2Templates(directory="services/voicebot_wrapper/templates")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Voicebot API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/voicebot/interface")
async def voicebot_interface(request: Request):
    """Serve the voicebot interface."""
    return templates.TemplateResponse("voicebot.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)