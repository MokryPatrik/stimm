# Voicebot Platform

This project provides a complete, real-time voicebot platform, including Speech-to-Text (STT), Text-to-Speech (TTS), and a Large Language Model (LLM) for conversation logic. The entire platform is designed as a fully containerized architecture using Docker Compose.

## Architecture

The system is a modular, multi-service platform:

- **`riva-service`**: A GPU-accelerated service running NVIDIA Riva for high-performance STT and TTS.
- **`llm-server`**: A llama.cpp powered LLM server that streams chat completions.
- **`rag-service`**: A FastAPI microservice that performs retrieval-augmented generation (RAG), managing knowledge-base documents and short-term conversation memory.
- **`qdrant`**: A dedicated vector database used by the RAG service for low-latency semantic search.
- **`voicebot-app`**: The central application that connects the speech services with the LLM and now orchestrates RAG context.

For a detailed breakdown, see [project_architecture.md](project_architecture.md).

## Current Status

This repository now includes **real-time STT, TTS, an on-device LLM, and a retrieval-augmented knowledge base**, enabling grounded conversations with persistent context.

## Prerequisites

1.  **Windows 11 with WSL 2:** This project is designed to run within a WSL 2 (Ubuntu) environment.
2.  **NVIDIA GPU:** A Turing architecture or newer GPU is required.
3.  **NVIDIA GPU Drivers:** The latest drivers for your GPU must be installed on the Windows host.
4.  **Docker Desktop:** Must be installed with the WSL 2 backend enabled.
5.  **NVIDIA NGC Account:** You need a free account to access the Riva models.

## Setup and Deployment

All setup and deployment commands should be run from **within your WSL 2 (Ubuntu) terminal**.

### 1. Initial NGC Authentication

You must be authenticated with the NVIDIA GPU Cloud (NGC) for the Docker build process to succeed.

**a. Install NGC CLI:**
If you don't have it installed in your WSL environment, run these commands from your project root:
```bash
wget --content-disposition https://ngc.nvidia.com/downloads/ngccli_linux.zip && unzip ngccli_linux.zip
chmod u+x ngc-cli/ngc
echo 'export PATH="$PATH:'$(pwd)'/ngc-cli"' >> ~/.bashrc
source ~/.bashrc
```

**b. Configure NGC CLI:**
Configure your credentials by running:
```bash
ngc config set
```
You will be prompted for your NGC API key.

### 2. Build and Run the Platform

Once authenticated, you can build and run the entire platform with a single command from the project's root directory:

```bash
docker-compose up --build
```

The first time you run this command, it will be very slow as it downloads the large base images and the Riva speech models. Subsequent runs will be much faster.

### 3. Network Configuration (Important)

After starting the platform, you need to manually connect the Riva speech container to the Docker Compose network:

```bash
docker network connect voicebot_voicebot-network riva-speech
```

This step is necessary because the Riva speech container is started outside of Docker Compose and needs to be manually added to the network for proper communication between services.

### Troubleshooting: `401 Unauthorized` Error

If the `docker-compose up --build` command fails with a `401 Unauthorized` or `Access Denied` error, it indicates a problem with Docker's credential store. To fix this:

1.  **Force a credential reset within WSL:**
    ```bash
    rm -rf ~/.docker/config.json
    ```
2.  **Log back into Docker's `nvcr.io` registry:**
    ```bash
    docker login nvcr.io
    ```
    - **Username:** `$oauthtoken`
    - **Password:** Your NGC API Key

3.  Retry the `docker-compose up --build` command.

## Development with Hot-Reloading

To streamline development, this project is configured for hot-reloading. This means you can change the Python code for the `voicebot-app` or `web-client` services, and the changes will be applied automatically inside the running containers without needing to rebuild the Docker images.

### How It Works

-   **Volume Mounting**: The `src` directory on your local machine is mounted as a volume into the `/app` directory inside the `voicebot-app` and `web-client` containers.
-   **Auto-Reload**:
-   The `voicebot-app` service uses `uvicorn --reload` to watch for file changes and automatically restart the application.  
    It now defaults to a Bayview banking system prompt; override it by setting `LLM_SYSTEM_PROMPT` before starting Docker Compose.
    -   The `web-client` service uses `uvicorn web_client:app --reload` for the same purpose.

### Workflow

1.  **Start the services**:
    ```bash
    docker-compose up --build
    ```
2.  **Modify code**: Make changes to any Python file inside the `src` directory.
3.  **See changes live**: The corresponding service will automatically restart in its container, applying your changes instantly.

You only need to run `docker-compose up --build` again if you modify dependencies in `src/requirements.txt` or change the `Dockerfile` itself.

## Knowledge Base & RAG API

The `rag-service` exposes a small HTTP API for managing documents and recovering relevant context during a call. The `voicebot-app` transparently queries the RAG microservice before each LLM request and pushes assistant replies back so that future turns stay grounded.

- `POST /knowledge/documents` – Bulk-ingest text snippets into the knowledge base.
- `POST /rag/query` – Retrieve top-k snippets and the recent conversation history (used internally by `voicebot-app`).
- `POST /conversation/message` – Append messages manually when integrating custom clients.

The compose stack includes a `rag-ingest` helper service that seeds
`knowledge_base/bayview_horizon_banking_agent_guide.md` into the
`bayview-banking` namespace as soon as Qdrant and the RAG API report ready.
Restarting (`docker compose up --build`) automatically reapplies the seed. Edit
the markdown file and rerun `docker compose up rag-ingest` to refresh it; the
voicebot prompt instructs the LLM to answer directly using these snippets after
an initial greeting.

To push additional documents manually use the helper script so content is chunked
consistently with the automated seeding:

```bash
python scripts/ingest_documents.py knowledge_base/bayview_horizon_banking_agent_guide.md \
  --base-url http://localhost:8002 \
  --namespace bayview-banking
```

Documents are chunked and de-duplicated before ingestion. The helper script
`scripts/ingest_documents.py` splits Markdown by heading, emits ~200-word
segments with stable SHA256 IDs, and enriches them with section metadata so the
retriever can cite precise snippets. By default the RAG service runs with
`BAAI/bge-base-en-v1.5` embeddings, a hybrid dense + BM25 retriever, and a
`BAAI/bge-reranker-base` cross-encoder to boost precision. Override the models,
candidate counts, or namespace defaults through the environment variables defined
in `docker-compose.yml`.

You can sanity-check retrieval quality after modifying the knowledge base with:

```bash
python scripts/evaluate_rag.py --base-url http://localhost:8002
```

The script hits `/rag/query` using prompts stored in
`evaluation/bayview_rag_eval.jsonl` and reports whether required facts are
present in the returned contexts.

## Testing Async.ai TTS Provider

To test the Async.ai TTS provider with real WebSocket connections and generate audio files for playback testing:

```bash
docker-compose -f docker/test-machine/docker-compose.yml run --rm -v $(pwd):/output test-hume-websocket bash -c "python3 /app/tests/async/test_async_ai_standalone.py && cp /app/test-async-ai-audio.wav /output/test-async-ai-audio.wav"
```

This command:
- Runs the Async.ai provider test in isolation
- Establishes a real WebSocket connection to Async.ai API
- Generates audio from test text
- Saves the resulting WAV file to your current directory for playback

The generated audio file will be in standard WAV format (44.1kHz, 16-bit, mono) and can be played with any audio player.

## Using the ASR (Speech-to-Text) Feature

### Web Interface

1. **Access the web interface**: Open your browser to `http://localhost:8080`
2. **Start recording**: Click the "Start Recording" button to activate your microphone
3. **Speak clearly**: Your speech will be transcribed in real-time
4. **View transcription**: See the interim and final transcription results appear on the screen
5. **Stop recording**: Click "Stop Recording" when finished

### Technical Details

- **Microphone access**: The web interface uses the Web Audio API to capture microphone input
- **Real-time streaming**: Audio is sent to the server via WebSocket for real-time processing
- **Transcription**: Results are displayed with interim (partial) and final transcriptions
- **Language support**: Currently configured for English (en-US) but can be extended

### Troubleshooting

- **Microphone permission**: Ensure your browser has permission to access the microphone
- **Network issues**: Make sure all Docker containers are running and connected to the same network
- **Audio format**: The system expects 16kHz, 16-bit PCM audio for optimal ASR performance
