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

### Data Flow: Audio-to-Audio Pipeline

The core of the voicebot is the real-time audio processing pipeline. Here is how data flows from the user's microphone back to their speakers:

```mermaid
sequenceDiagram
    participant User
    participant WebRTC as WebRTC/WebSocket
    participant Media as MediaHandler
    participant VAD as Silero VAD
    participant EvLoop as VoicebotEventLoop
    participant STT as STT Service
    participant RAG as RAG/LLM Service
    participant TTS as TTS Service

    User->>WebRTC: Microphone Audio Stream
    WebRTC->>Media: Incoming Audio Track
    Media->>VAD: Raw Audio Frames
    
    alt Voice Detected
        VAD->>EvLoop: Speech Start Event
        EvLoop->>STT: Start Transcribing
    end
    
    alt Voice Ended
        VAD->>EvLoop: Speech End Event
        EvLoop->>STT: Finalize Transcription
        STT->>EvLoop: Transcribed Text
        EvLoop->>RAG: User Query
        RAG->>EvLoop: LLM Response Stream
        EvLoop->>TTS: Text Stream
        TTS->>Media: Audio Stream
        Media->>WebRTC: Outgoing Audio Track
        WebRTC->>User: Voice Response
    end
```

1.  **Ingestion**: Audio is captured by the client (browser) and sent via **WebRTC** (preferred) or **WebSocket** to the backend.
2.  **Media Handling**: The `WebRTCMediaHandler` receives the incoming audio track and buffers the raw audio frames.
3.  **Voice Activity Detection (VAD)**: The `SileroVADService` analyzes the audio frames in real-time to detect speech segments. It triggers events for "speech start" and "speech end".
4.  **Orchestration**: The `VoicebotEventLoop` acts as the central brain. It receives VAD events and coordinates the other services.
5.  **Speech-to-Text (STT)**: When speech is detected, audio is buffered. On "speech end", the `STTService` (e.g., Deepgram, Whisper) transcribes the audio buffer into text.
6.  **Intelligence (RAG/LLM)**: The transcribed text is sent to the `ChatbotService`. This service may query the **Qdrant** vector database for context (RAG) before sending the prompt to the **LLM** (e.g., Groq, Mistral).
7.  **Text-to-Speech (TTS)**: The LLM's response is streamed token-by-token to the `TTSService` (e.g., Deepgram, ElevenLabs). The TTS service converts the text stream into an audio stream.
8.  **Output**: The generated audio is sent back to the `WebRTCMediaHandler`, which pushes it to the outgoing WebRTC track, playing it back to the user.

### Key Components

- **Backend (`src/`)**: FastAPI application handling API requests, WebSocket/WebRTC connections, and business logic.
  - `services/agents`: Core voicebot logic and event loop.
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

The VoiceBot platform supports **dual-mode development** with flexible deployment options.

### Option 1: Local Development (Recommended)

This approach runs the backend locally with uv virtualenv while using Docker for supporting services.

1. **Start supporting services** (PostgreSQL, Qdrant, LiveKit, Redis, Traefik):
   ```bash
   docker compose up -d postgres qdrant livekit redis traefik
   ```

2. **Setup and run backend locally**:
   ```bash
   # The virtual environment is already set up
   source .venv/bin/activate
   
   # Run the application
   python src/main.py
   ```
   Backend will be available at: http://localhost:8001

3. **Setup and run frontend locally**:
   ```bash
   cd src/front
   
   # Setup environment (first time only)
   ./scripts/setup-frontend-dev.sh
   
   # Run development server
   npm run dev
   ```
   Frontend will be available at: http://localhost:3000

**Benefits:**
- ✅ Fast development with immediate code changes
- ✅ Direct access to backend with debugging tools
- ✅ 60% faster dependency management with uv
- ✅ Environment-aware URLs (automatic localhost vs container detection)

### Option 2: Full Docker Stack

This approach runs everything in Docker containers for a consistent environment.

1. **Start all services including voicebot-app and voicebot-app-front**:
   ```bash
   docker compose up
   ```

2. **Access the application**:
   - **Frontend**: [http://front.localhost](http://front.localhost)
   - **API Documentation**: [http://api.localhost/docs](http://api.localhost/docs)

**Features:**
- Automatic code reloading for both backend and frontend
- Consistent environment across all developers
- Persistent database and vector storage
- Complete service orchestration

### Option 3: Frontend-Only Development

For UI/UX development without backend changes:

1. **Setup frontend environment**:
   ```bash
   cd src/front
   ./scripts/setup-frontend-dev.sh
   ```

2. **Start frontend** (connects to localhost:8001):
   ```bash
   npm run dev
   ```

3. **Ensure backend is running** (from Option 1 or 2)

### Environment Detection

The platform automatically detects the development environment:

- **Backend**: Uses container names when in Docker, localhost when running locally
- **Frontend SSR**: Uses environment-aware URLs for API calls
- **Frontend Client**: Always uses localhost URLs for browser consistency

### Development Tools

- **Backend debugging**: Use standard Python debugging tools with local execution
- **Frontend debugging**: Use browser DevTools and Next.js debugging features
- **Database access**: PostgreSQL available at `localhost:5432`
- **Vector database**: Qdrant available at `localhost:6333`

Choose the development approach that best fits your workflow!

## 📂 Project Structure

```
.
├── alembic/              # Database migrations
├── docker/               # Docker configurations for services
├── src/
│   ├── cli/              # Command-line interface tools
│   │   ├── agent_runner.py    # Agent runner for LiveKit
│   │   ├── echo_client.py     # Audio pipeline test client
│   │   ├── echo_server.py     # Audio pipeline test server
│   │   ├── main.py            # CLI entry point
│   │   ├── test_livekit_microphone.py  # Microphone testing
│   │   └── test_mic.py        # Basic microphone testing
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
├── pyproject.toml        # CLI dependencies (UV)
└── README.md             # Project documentation
```

## 🖥️ CLI Tool

The VoiceBot platform includes a powerful CLI tool for testing agents directly from the command line, without using the web interface.

### Usage

#### List Available Agents

```bash
# From Docker container
docker exec -it voicebot-app python -m cli.main --list-agents

# From local development
python -m src.cli.main --list-agents
```

#### Text Mode (Recommended for quick testing)

```bash
# Basic text conversation
python -m src.cli.main --agent-name "Etienne" --mode text

# With RAG enabled (default)
python -m src.cli.main --agent-name "Etienne" --mode text --use-rag

# With verbose logging
python -m src.cli.main --agent-name "Etienne" --mode text --verbose
```

#### Full Audio Mode (LiveKit WebRTC)

```bash
# Audio conversation via LiveKit
python -m src.cli.main --agent-name "Etienne" --mode full

# With custom room name
python -m src.cli.main --agent-name "Etienne" --mode full --room-name "test-conversation"
```

#### Audio Pipeline Testing

```bash
# Test complete audio pipeline with echo server and client
python -m src.cli.main --test-echo --verbose

# Test microphone recording
python -m src.cli.main --test-mic 5

# Test LiveKit microphone capture
python -m src.cli.main --test-livekit-mic 5
```

### Features

- **Text Mode**: Interactive text conversation with the agent
- **Full Audio Mode**: Real-time audio conversation via LiveKit WebRTC
- **Audio Testing**: Complete pipeline testing with echo tools
- **RAG Integration**: Retrieval-Augmented Generation with knowledge base context
- **Agent Configuration**: Uses the specific LLM/TTS/STT configuration of each agent
- **LiveKit Integration**: WebRTC audio streaming for low-latency conversations

### Examples

```bash
# List all available agents
python -m src.cli.main --list-agents

# Test agent in text mode
python -m src.cli.main --agent-name "Etienne" --mode text

# Test with audio via LiveKit
python -m src.cli.main --agent-name "Etienne" --mode full --verbose

# Test audio pipeline
python -m src.cli.main --test-echo
```

## 🔧 Audio Pipeline Testing Tools

The VoiceBot platform includes specialized tools for testing and debugging the real-time audio pipeline without requiring the full voicebot application. These tools are essential for diagnosing audio issues, VAD problems, or LiveKit connectivity.

### 🎯 Audio Test Tools

#### Single Command Echo Test (`--test-echo`)
**Purpose**: Complete audio pipeline test that automatically launches both echo server and client.

**Use Case**: Quick verification of LiveKit connectivity and full audio pipeline.

```bash
# Test complete audio pipeline with one command
python -m src.cli.main --test-echo --verbose

# Test with standard logging
python -m src.cli.main --test-echo
```

**Features**:
- ✅ Automatic launch of echo server and client
- ✅ Real-time logging from both processes
- ✅ Clean shutdown with Ctrl+C
- ✅ Stable audio playback with auto-restart

#### Echo Server (`src/cli/echo_server.py`)
**Purpose**: Server-side echo agent that joins a LiveKit room and immediately echoes back any received audio.

**Use Case**: Verify LiveKit connectivity and test full audio pipeline.

```bash
# Run echo server locally
python src/cli/echo_server.py

# Run in background
python src/cli/echo_server.py &
```

**Features**:
- ✅ Stable audio frame handling with error recovery
- ✅ Uses SOURCE_UNKNOWN to avoid audio processing interference
- ✅ Automatic source reset on errors
- ✅ Real-time statistics logging

#### Echo Client (`src/cli/echo_client.py`)
**Purpose**: Full audio pipeline test client that captures microphone input and plays back received audio.

**Use Case**: End-to-end audio testing - microphone to speaker loopback.

```bash
# Run echo client locally
python src/cli/echo_client.py
```

**Features**:
- ✅ Real-time microphone capture via ffmpeg/PulseAudio (48kHz)
- ✅ LiveKit WebRTC connection and audio streaming
- ✅ Stable audio playback via ffplay with auto-restart
- ✅ Complete pipeline verification

### 🔬 Debugging Audio Issues

#### Quick Audio Pipeline Test
```bash
# Single command test (recommended)
python -m src.cli.main --test-echo --verbose

# Manual test (if needed)
# Terminal 1: python src/cli/echo_server.py
# Terminal 2: python src/cli/echo_client.py
```

**Expected Behavior**:
- You should hear your own voice echoed back after a short delay
- Console shows connection success and audio processing statistics
- No connection errors or `InvalidState` exceptions

#### Microphone Only Test
```bash
# Test microphone capture and save to file
python -m src.cli.main --test-livekit-mic 5

# Test basic PulseAudio capture
python src/cli/test_mic.py
```

### 🛠️ Environment Setup

All audio test tools require:
```bash
# Activate Python virtual environment
source .venv/bin/activate

# Set Python path for local imports
export PYTHONPATH=/home/etienne/repos/voicebot/src:$PYTHONPATH

# Ensure LiveKit server is running
docker-compose ps livekit
```

### 📊 Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| **No microphone access** | "pulse: default: No such device" | Check microphone permissions and WSL2 audio setup |
| **InvalidState errors** | "failed to capture frame" | Use fixed `echo_server.py` with error handling |
| **No audio playback** | ffplay fails to start | Check speakers and PulseAudio configuration |
| **Connection failures** | Cannot connect to LiveKit | Verify `docker-compose up livekit` is running |

### 🎵 Audio Pipeline Architecture

```
[Microphone] → [ffmpeg capture] → [LiveKit Client] → [LiveKit Server]
     ↓              ↓                    ↓               ↓
[48kHz mono] → [Raw PCM] → [WebRTC Stream] → [Room Broadcasting]
     ↓              ↓                    ↓               ↓
[Echo Server] ← [Audio Stream] ← [LiveKit Server] ← [WebRTC Stream]
     ↓              ↓                    ↓               ↓
[Audio Loop] → [ffplay output] → [Speakers] → [User hears echo]
```

### 🚀 Ready for Main Agent Debugging

These test tools confirm that:
- ✅ **Network Layer**: LiveKit WebRTC connectivity is stable
- ✅ **Audio Pipeline**: Microphone → Server → Playback works correctly
- ✅ **Environment**: WSL2 audio is properly configured

**Any remaining issues** in the main voicebot are isolated to application logic (VAD thresholds, audio processing), not infrastructure problems.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
