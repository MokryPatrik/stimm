# AGENTS GUIDE (stimm)

Repository: Python (FastAPI + async services + RAG). Tests: pytest/pytest-asyncio. Formatting/linting: Ruff (format + check), mypy. Packaging: pyproject.toml. No Cursor or Copilot rule files present.

## Quickstart
- Create venv: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -e .` (pyproject-managed); for dev extras: `pip install -e .[dev]`
- Env files: `.env`, `docker/stimm/.env` (do not commit secrets).
- Services via Docker: `docker compose up stimm` (backend), `docker compose up livekit` (LiveKit), other services in `docker-compose.yml`.

## Build / Run
- Start API locally: `uvicorn src.main:app --reload --port 8001`
- Docker build backend: `docker compose build stimm`
- Docker run backend: `docker compose up stimm`
- Restart single service: `docker compose restart stimm`
- Logs: `docker compose logs stimm --tail=100 -f`

## Tests
- Full suite: `pytest`
- Single file: `pytest tests/path/test_file.py`
- Single test: `pytest tests/path/test_file.py -k test_name`
- Coverage (terminal): `pytest --cov=. --cov-report=term-missing`
- Async tests supported via pytest-asyncio (already configured).

## Lint / Format / Type-check
- Format: `ruff format src tests`
- Lint+fix: `ruff check --fix src tests`
- Type-check: `mypy src tests`
- Pre-commit (if configured): `pre-commit run -a`

## Dependencies
- Main: FastAPI, SQLAlchemy, Alembic, Qdrant client, transformers, onnxruntime, livekit, aiohttp, httpx, openai, deepgram-sdk, google-cloud-speech.
- Optional audio: `pip install -e .[audio]`
- Optional livekit extras: `pip install -e .[livekit]`

## Project Structure (high level)
- `src/services/rag/` – RAG chatbot, retrieval engine, preloader.
- `src/services/llm/` – LLM provider abstraction and providers (OpenAI, Groq, etc.).
- `src/services/stt/` – STT providers (Deepgram, Gladia, Google, Whisper local).
- `src/services/tools/` – Tools and product RAG sync/indexing.
- `src/database/` – SQLAlchemy models and session.
- `docker/` – Compose fragments; envs under `docker/stimm/.env`.

## Code Style (Python)
- Use type hints everywhere (mypy `disallow_untyped_defs=true`).
- Follow Ruff defaults: 200-char line len; keep imports sorted (standard, third-party, first-party `stimm`).
- Strings: prefer double quotes (Ruff format default).
- Avoid wildcard imports; prefer explicit names.
- Use pathlib over os.path when convenient; prefer f-strings.
- Logging: use module-level `logger = logging.getLogger(__name__)`; no prints in production code.
- Error handling: catch specific exceptions; log with context; re-raise or return meaningful errors. Avoid bare `except`.
- Async: use `async/await`; ensure long-running tasks are awaited or scheduled with `asyncio.create_task` and properly cancelled/closed.
- HTTP calls: prefer aiohttp/httpx async clients; close sessions (context managers or explicit close).
- Database sessions: use context managers; commit/rollback appropriately. When updating JSONB fields, call `flag_modified` so SQLAlchemy persists changes.
- Data models: SQLAlchemy models in `database/models.py`; use `to_dict()` helpers consistently.
- Pydantic/Pydantic-v2 (FastAPI): validate request/response models; avoid dynamic attrs.
- Naming: snake_case for vars/functions, PascalCase for classes, UPPER_SNAKE for constants.
- Comments: concise; no commented-out code in final patches unless user requests.
- Docstrings: include when behavior is non-trivial; brief summary line.

## RAG / LLM / STT Guidance
- Chat flow uses `ChatbotService.process_chat_message`; LLM via `LLMService.generate_stream` with full message history. Do not reintroduce `generate_stream_messages`.
- RAG context added to system prompt; product_stock tool for stock-only queries (not general recommendations).
- Product sync: incremental by `modified_after`; `last_sync_at` stored in `integration_config` (JSONB) → use `flag_modified` when updating.
- Avoid altering RAG collection names or agent IDs unless required.

## Testing and Validation Philosophy
- Prefer targeted tests near changed code; start with file-level pytest invocations.
- Run lint/format/type-check for touched areas when feasible; avoid introducing new lint/type errors.
- Do not commit env files, secrets, or large artifacts.

## Commit / PR Hygiene
- Do not create commits unless user requests.
- Do not force-push; respect existing branch protection.
- Keep changes minimal and scoped to the request.

## When Editing
- Respect existing style; reuse utilities instead of duplicating logic.
- For new configs in JSONB (SQLAlchemy), remember `flag_modified` before commit.
- Prefer dependency injection patterns already present (service classes, provider registries).
- Maintain streaming patterns (LLM/STT/TTS) without blocking operations.

## Documentation Tone
- Keep responses concise and actionable; avoid filler.

## Missing Rules
- No Cursor or Copilot instruction files detected; none to follow.

End of AGENTS guidance.
