# Sift — Quick Start Guide

Get the Sift research engine running locally in under 5 minutes.

## Prerequisites

| Tool | Minimum Version | Check |
|------|-----------------|-------|
| [Docker](https://docs.docker.com/get-docker/) | 20.10+ | `docker --version` |
| [Docker Compose](https://docs.docker.com/compose/install/) | 2.0+ (V2) | `docker compose version` |
| Git | any | `git --version` |

You also need **one** LLM API key (all have free tiers):

| Provider | Free Tier | Get a Key |
|----------|-----------|-----------|
| **Google Gemini** (default) | 60 req/min | [Google AI Studio](https://aistudio.google.com/apikey) |
| **Groq** | 30 req/min | [Groq Console](https://console.groq.com/keys) |
| **NVIDIA** | 1000 credits | [NVIDIA Build](https://build.nvidia.com/) |

---

## Step 1: Clone the repository

```bash
git clone https://github.com/your-org/sift.git
cd sift/backend
```

## Step 2: Configure environment variables

```bash
cp .env.example .env
```

Open `.env` in your editor and set your API key for the provider you chose:

```dotenv
# Pick your provider: "google", "groq", or "nvidia"
LLM_PROVIDER=google

# Set the key for your chosen provider (leave the others blank)
GOOGLE_API_KEY=your-google-api-key-here
# GROQ_API_KEY=your-groq-key-here
# NVIDIA_API_KEY=your-nvidia-key-here
```

All other settings have sensible defaults and can be left unchanged.

## Step 3: Start the backend

**Production mode** (detached):

```bash
docker compose up --build -d
```

**Development mode** (hot reload, logs in foreground):

```bash
make dev
```

Or without Make:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

The first build takes 1-2 minutes (downloading Python packages and the embedding model). Subsequent starts are nearly instant.

## Step 4: Verify it's running

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{"status": "ok", "version": "0.1.0"}
```

You can also open the interactive API docs at: **http://localhost:8000/docs**

## Step 5: Run your first research query

```bash
curl -N -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key differences between Kafka and RabbitMQ?", "depth": "standard"}'
```

You'll see a Server-Sent Event (SSE) stream with these event types:

| Event | Description |
|-------|-------------|
| `status` | Pipeline phase updates (decomposing, searching, processing, etc.) |
| `source_complete` | Per-source result counts as each finishes |
| `token` | LLM synthesis tokens streamed incrementally |
| `complete` | Final event with `session_id`, `citations`, and metadata |

---

## Available Make Commands

Run these from the `backend/` directory:

| Command | Description |
|---------|-------------|
| `make dev` | Start with hot reload (development) |
| `make prod` | Start production build (detached) |
| `make test` | Run the test suite inside a container |
| `make test-coverage` | Run tests with coverage report |
| `make lint` | Run ruff linter and format checker |
| `make logs` | Follow container logs |
| `make down` | Stop all services |
| `make clean` | Stop services, remove volumes and images |

---

## Running Without Docker

If you prefer running directly on your machine:

```bash
cd backend

# Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API key

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Project Structure

```
backend/
├── app/
│   ├── main.py               # FastAPI application factory
│   ├── config.py              # Pydantic settings (loaded from .env)
│   ├── api/routes/
│   │   ├── health.py          # GET /api/v1/health
│   │   └── research.py        # POST /api/v1/research (SSE stream)
│   ├── core/
│   │   ├── orchestrator.py    # 7-step research pipeline
│   │   ├── query_analyzer.py  # LLM-powered query decomposition
│   │   ├── synthesizer.py     # LLM streaming synthesis with citations
│   │   └── prompts.py         # All LLM prompt templates
│   ├── db/
│   │   └── vector_store.py    # ChromaDB wrapper for vector storage
│   ├── ingestion/
│   │   ├── pipeline.py        # Extract → chunk → embed pipeline
│   │   ├── chunker.py         # Token-bounded text chunking
│   │   ├── embedder.py        # HuggingFace / local embeddings
│   │   └── extractors.py      # HTML and text content extraction
│   └── sources/
│       ├── base.py            # Abstract SourceAdapter interface
│       ├── registry.py        # Source adapter registry
│       ├── duckduckgo.py      # DuckDuckGo web search adapter
│       ├── wikipedia.py       # Wikipedia API adapter
│       └── hackernews.py      # Hacker News API adapter
├── tests/                     # Full test suite (pytest)
├── Dockerfile                 # Multi-stage production image
├── docker-compose.yml         # Production compose config
├── docker-compose.dev.yml     # Development overlay (hot reload)
├── Makefile                   # Convenience commands
└── .env.example               # Environment variable template
```

---

## Troubleshooting

### Container fails to start

Check logs for the error:

```bash
docker compose logs backend
```

Common causes:
- **Missing API key**: Ensure your `.env` has a valid key for the selected `LLM_PROVIDER`.
- **Port conflict**: Another service is using port 8000. Change the port mapping in `docker-compose.yml`.

### Embedding model download is slow

The first request triggers a download of the `all-MiniLM-L6-v2` model (~80 MB). This is cached in a Docker volume after the first run.

### Health check fails during startup

The container has a 40-second startup grace period. If using a slow machine, increase `start_period` in `docker-compose.yml`.

---

## Next Steps

- Browse the [demo queries](demo_queries.md) for examples that showcase multi-source synthesis
- Read the full [backend specification](README.md) for architecture details
- Explore the interactive API docs at http://localhost:8000/docs
