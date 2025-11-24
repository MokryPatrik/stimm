# Voicebot Platform

A modular, real-time AI voice assistant platform built with Python (FastAPI) and Next.js. This project provides a flexible infrastructure for creating, managing, and interacting with voice agents using various LLM, TTS, and STT providers.

## 🚀 Features

- **Real-time Voice Interaction**: Low-latency voice conversations using WebRTC and WebSocket transports.
- **Modular AI Providers**:
  - **LLM**: Support for Groq, Mistral, OpenRouter, and local Llama.cpp.
  - **TTS**: Deepgram, ElevenLabs, Async.ai, and local Kokoro.
  - **STT**: Deepgram and local Whisper.
- **RAG & Knowledge Base**: Integrated Retrieval-Augmented Generation using Qdrant vector database.
- **Agent Management**: Admin interface to configure and manage multiple agents with different personalities and provider settings.
- **Modern Frontend**: Responsive web interface built with Next.js 16 and Tailwind CSS.
- **Robust Infrastructure**: Dockerized deployment with Traefik reverse proxy, PostgreSQL for data persistence, and Alembic for migrations.
- **Voice Activity Detection**: Integrated Silero VAD for accurate speech detection.

## 🏗 Architecture

The project follows a modular monolith architecture, containerized with Docker Compose.

```mermaid
graph TD
    Client[Web Client / Next.js] -->|HTTPS/WSS| Traefik[Traefik Reverse Proxy]
    Traefik -->|/api| Backend[Voicebot Backend / FastAPI]
    Traefik -->|/| Frontend[Frontend Service]
    
    Backend --> Postgres[(PostgreSQL)]
    Backend --> Qdrant[(Qdrant Vector DB)]
    
    subgraph "AI Services"
        Backend -->|External API| LLM[LLM Providers]
        Backend -->|External API| TTS[TTS Providers]
        Backend -->|External API| STT[STT Providers]
    end
```

### Key Components

- **Backend (`src/`)**: FastAPI application handling API requests, WebSocket/WebRTC connections, and business logic.
  - `services/agents`: Core voicebot logic.
  - `services/agents_admin`: Agent configuration management.
  - `services/rag`: Knowledge base and retrieval logic.
  - `services/webrtc`: WebRTC signaling and media handling.
- **Frontend (`src/front/`)**: Next.js application for the user interface.
- **Database**: PostgreSQL for storing user, agent, and session data.
- **Vector Store**: Qdrant for storing document embeddings for RAG.

## 🛠 Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic.
- **Frontend**: Next.js 16, React 19, Tailwind CSS, TypeScript.
- **AI/ML**: PyTorch, Sentence Transformers, Silero VAD.
- **Real-time**: WebRTC (aiortc), WebSockets.
- **Infrastructure**: Docker, Docker Compose, Traefik.

## 🏁 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) and Docker Compose installed on your machine.

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd voicebot
   ```

2. **Environment Configuration**:
   Create a `.env` file in the root directory. You can use the following template:

   ```env
   # Database
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=voicebot
   DATABASE_URL=postgresql://postgres:postgres@postgres:5432/voicebot

   # Security
   SECRET_KEY=your_secret_key_here

   # AI Providers (Add keys for providers you intend to use)
   OPENAI_API_KEY=sk-...
   DEEPGRAM_API_KEY=...
   ELEVENLABS_API_KEY=...
   GROQ_API_KEY=...
   MISTRAL_API_KEY=...
   OPENROUTER_API_KEY=...

   # Qdrant
   QDRANT_HOST=qdrant
   QDRANT_PORT=6333
   ```

   Also ensure `src/front/.env` exists for the frontend (or is mapped correctly in docker-compose).

3. **Build and Run**:
   ```bash
   docker-compose up --build
   ```

4. **Access the Application**:
   - **Frontend**: [http://front.localhost](http://front.localhost)
   - **API Documentation**: [http://api.localhost/docs](http://api.localhost/docs)
   - **Traefik Dashboard**: [http://localhost:8080](http://localhost:8080)

## 💻 Development

### Backend Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r src/requirements.txt
   ```

3. Run migrations:
   ```bash
   alembic upgrade head
   ```

4. Run locally (without Docker):
   ```bash
   cd src
   uvicorn main:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd src/front
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

## 📂 Project Structure

```
.
├── alembic/              # Database migrations
├── docker/               # Docker configurations for services
├── src/
│   ├── database/         # Database models and session
│   ├── front/            # Next.js Frontend application
│   ├── services/         # Microservices / Modules
│   │   ├── agents/       # Voicebot logic
│   │   ├── agents_admin/ # Agent management
│   │   ├── llm/          # LLM integrations
│   │   ├── rag/          # RAG & Knowledge base
│   │   ├── stt/          # Speech-to-Text
│   │   ├── tts/          # Text-to-Speech
│   │   ├── vad/          # Voice Activity Detection
│   │   └── webrtc/       # WebRTC handling
│   ├── main.py           # Application entry point
│   └── requirements.txt  # Python dependencies
├── docker-compose.yml    # Main Docker Compose file
└── README.md             # Project documentation
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
