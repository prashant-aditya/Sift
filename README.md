# Sift — Backend Engineering Specification

> **Language:** Python 3.11+ | **Framework:** FastAPI | **Task Queue:** Celery + Redis | **Databases:** PostgreSQL (Supabase) + ChromaDB (Vector)

This document is the single source of truth for the backend team. It contains every API, data model, service, infrastructure component, design decision, and phased implementation plan needed to build Sift's backend from scratch.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack & Dependencies](#2-tech-stack--dependencies)
3. [Architecture Diagram](#3-architecture-diagram)
4. [Project Structure](#4-project-structure)
5. [Configuration & Environment](#5-configuration--environment)
6. [Data Models](#6-data-models)
7. [API Reference](#7-api-reference)
8. [Core Services](#8-core-services)
9. [Source Adapters](#9-source-adapters)
10. [Ingestion Pipeline](#10-ingestion-pipeline)
11. [Retrieval Engine](#11-retrieval-engine)
12. [Resilience Layer](#12-resilience-layer)
13. [Caching Strategy](#13-caching-strategy)
14. [Knowledge Graph & Memory](#14-knowledge-graph--memory)
15. [Agent System (Phase 4)](#15-agent-system-phase-4)
16. [Worker Infrastructure](#16-worker-infrastructure)
17. [Authentication](#17-authentication)
18. [Testing Strategy](#18-testing-strategy)
19. [Deployment & Infrastructure](#19-deployment--infrastructure)
20. [Performance Targets](#20-performance-targets)
21. [Phased Implementation Plan](#21-phased-implementation-plan)

---

## Quick Setup (5 Minutes)

> For a detailed walkthrough, see [QUICKSTART.md](QUICKSTART.md). For demo queries, see [demo_queries.md](demo_queries.md).

```bash
# 1. Clone and enter the backend directory
git clone https://github.com/your-org/sift.git
cd sift/backend

# 2. Configure your API key
cp .env.example .env
# Edit .env — set LLM_PROVIDER and the corresponding API key

# 3. Start the backend
docker compose up --build -d

# 4. Verify
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "version": "0.1.0"}
```

### Working API Examples (Phase 1)

**Health Check:**

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok", "version": "0.1.0"}
```

**Research Query (SSE Stream):**

```bash
curl -N -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the trade-offs between Kafka and RabbitMQ for event-driven microservices?",
    "depth": "standard"
  }'
```

Request body fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string (3-2000 chars) | Yes | The research question |
| `sources` | string array or null | No | Source adapter names (`"duckduckgo"`, `"wikipedia"`, `"hackernews"`). Null uses all. |
| `depth` | `"quick"` \| `"standard"` \| `"deep"` | No | Controls results per source and retrieval depth. Default: `"standard"`. |

**SSE Response Stream:**

```
event: status
data: {"phase": "decomposing", "session_id": "session_a1b2c3d4e5f6"}

event: status
data: {"phase": "decomposed", "sub_queries": ["Kafka ordering and throughput characteristics", "RabbitMQ message routing and reliability features", "Kafka vs RabbitMQ operational complexity comparison"]}

event: status
data: {"phase": "searching", "sources_active": 3, "sub_queries_count": 3}

event: source_complete
data: {"source": "duckduckgo", "results_count": 5}

event: source_complete
data: {"source": "wikipedia", "results_count": 5}

event: source_complete
data: {"source": "hackernews", "results_count": 5}

event: status
data: {"phase": "processing", "results_count": 15}

event: status
data: {"phase": "storing", "chunks_count": 42}

event: status
data: {"phase": "retrieving"}

event: status
data: {"phase": "synthesizing"}

event: token
data: {"content": "## Overview\n\n"}

event: token
data: {"content": "Kafka and RabbitMQ represent two fundamentally different approaches..."}

event: complete
data: {"session_id": "session_a1b2c3d4e5f6", "sources_used": 15, "citations": [{"id": 1, "title": "Apache Kafka - Wikipedia", "url": "https://en.wikipedia.org/wiki/Apache_Kafka", "source_name": "wikipedia", "relevance_score": 0.92}, {"id": 2, "title": "Kafka vs RabbitMQ", "url": "https://...", "source_name": "duckduckgo", "relevance_score": 0.88}]}
```

**Search specific sources only:**

```bash
curl -N -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest developments in WebAssembly outside the browser",
    "sources": ["duckduckgo", "hackernews"],
    "depth": "deep"
  }'
```

**Interactive API Docs:**

Once running, visit **http://localhost:8000/docs** for the auto-generated Swagger UI where you can test all endpoints interactively.

---

## 1. System Overview

Sift is a self-hostable AI research engine that:

1. **Decomposes** a complex query into 2-4 focused sub-queries via LLM
2. **Fan-outs** those sub-queries across 5 source adapters in parallel (Celery chord)
3. **Ingests** results: extracts text, deduplicates (MinHash/LSH), chunks (512 tokens), embeds (384-dim)
4. **Retrieves** the top-15 most relevant chunks via hybrid BM25 + dense + Reciprocal Rank Fusion
5. **Synthesizes** a streaming, cited answer via LLM (SSE)
6. **Persists** every session into a knowledge graph (entities + relationships) for cross-session recall

The backend is the engine powering all of this. The frontend is a consumer of SSE streams and REST endpoints.

---

## 2. Tech Stack & Dependencies

### Core Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.110+ | HTTP framework, SSE endpoints |
| `uvicorn[standard]` | 0.27+ | ASGI server |
| `pydantic` | 2.6+ | Data validation, settings |
| `pydantic-settings` | 2.1+ | `.env` config loading |
| `sse-starlette` | 2.0+ | Server-Sent Events support |

### Data & Storage

| Package | Version | Purpose |
|---------|---------|---------|
| `chromadb` | 0.4.22+ | Vector database (embedded, in-process) |
| `sqlalchemy[asyncio]` | 2.0.25+ | PostgreSQL ORM (async) |
| `asyncpg` | 0.29+ | Async PostgreSQL driver |
| `alembic` | 1.13+ | Database migrations |

### Task Queue & Caching

| Package | Version | Purpose |
|---------|---------|---------|
| `celery[redis]` | 5.3.6+ | Distributed task queue |
| `redis` / `aioredis` | 5.0+ | Cache, rate limiting, circuit breaker state |

### AI/ML

| Package | Version | Purpose |
|---------|---------|---------|
| `groq` | 0.4+ | LLM API client (Llama 3.1 70B) |
| `sentence-transformers` | latest | Local embedding fallback |
| `tiktoken` | latest | Token counting (cl100k_base) |

### Source Adapters

| Package | Version | Purpose |
|---------|---------|---------|
| `httpx` | 0.27+ | Async HTTP client (all adapters) |
| `duckduckgo-search` | latest | DuckDuckGo web search |
| `feedparser` | latest | ArXiv Atom XML parsing |
| `beautifulsoup4` | latest | HTML content extraction |
| `readability-lxml` | latest | Main content extraction from HTML |

### Retrieval & Deduplication

| Package | Version | Purpose |
|---------|---------|---------|
| `datasketch` | latest | MinHash/LSH near-duplicate detection |

### Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| `python-dotenv` | 1.0+ | Environment variable loading |
| `structlog` | latest | Structured logging |

### Testing & Quality

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | latest | Test framework |
| `pytest-asyncio` | latest | Async test support |
| `pytest-httpx` / `respx` | latest | HTTP mocking for adapters |
| `pytest-cov` | latest | Coverage reporting |
| `ruff` | latest | Linting + formatting |
| `mypy` | latest | Static type checking |
| `pre-commit` | latest | Git hooks |

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SIFT BACKEND ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Frontend ──▶  ┌──────────────────────────────────────────────────────┐     │
│        ◀── SSE │              FastAPI Application                     │     │
│                │                                                      │     │
│                │  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  │     │
│                │  │ /research  │  │ /knowledge  │  │  /sessions   │  │     │
│                │  │ (SSE)      │  │ (REST)      │  │  (REST)      │  │     │
│                │  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘  │     │
│                │        │                │                 │          │     │
│                │        ▼                ▼                 ▼          │     │
│                │  ┌──────────────────────────────────────────────┐    │     │
│                │  │           Research Orchestrator               │    │     │
│                │  │                                              │    │     │
│                │  │  1. Query Analysis & Decomposition           │    │     │
│                │  │  2. Source Selection & Fan-out (Celery)      │    │     │
│                │  │  3. Ingestion (Extract → Chunk → Embed)     │    │     │
│                │  │  4. Hybrid Retrieval (BM25 + Dense + RRF)   │    │     │
│                │  │  5. Streaming Synthesis (LLM via SSE)       │    │     │
│                │  │  6. Persistence (PG + ChromaDB + KG)        │    │     │
│                │  └───────────────┬──────────────────────────────┘    │     │
│                └─────────────────┬┼──────────────────────────────────┘     │
│                                  ││                                        │
│          ┌──────────────────────┘│                                         │
│          │                       │                                         │
│          ▼                       ▼                                         │
│  ┌───────────────┐    ┌──────────────────────────────────────────────┐    │
│  │  Redis         │    │              Celery Workers                  │    │
│  │  (Upstash)     │    │                                              │    │
│  │                │    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │    │
│  │  • Task Queue  │◀──▶│  │ DuckDuck │ │  Reddit  │ │  HackerNews  │ │    │
│  │  • Cache Layer │    │  │ Go Worker│ │  Worker  │ │  Worker      │ │    │
│  │  • Rate Limits │    │  └──────────┘ └──────────┘ └──────────────┘ │    │
│  │  • Circuit     │    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │    │
│  │    Breaker     │    │  │  ArXiv   │ │ Wikipedia│ │   Custom     │ │    │
│  │    State       │    │  │  Worker  │ │  Worker  │ │   Source     │ │    │
│  └───────────────┘    │  └──────────┘ └──────────┘ └──────────────┘ │    │
│                        └──────────────────┬───────────────────────────┘    │
│                                           │                                │
│                     ┌─────────────────────┼─────────────────────┐          │
│                     │                     │                     │          │
│                     ▼                     ▼                     ▼          │
│           ┌──────────────┐    ┌──────────────────┐   ┌──────────────┐     │
│           │  ChromaDB     │    │   PostgreSQL      │   │   Groq /     │     │
│           │  (Vector DB)  │    │   (Supabase)      │   │   HuggingFace│     │
│           │               │    │                    │   │   LLM API    │     │
│           │  • Embeddings │    │  • Users           │   │              │     │
│           │  • Chunks     │    │  • Sessions        │   │  • Decompose │     │
│           │  • Metadata   │    │  • Research Turns  │   │  • Synthesize│     │
│           │  • BM25 Index │    │  • Knowledge Graph │   │  • Entities  │     │
│           └──────────────┘    │  • Source Cache    │   │  • Summaries │     │
│                                └──────────────────┘   └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow: Single Research Query

```
User Query
    │
    ▼
┌─────────────────────────┐
│  1. QUERY ANALYSIS       │
│  • Intent classification │──── Cache hit? → Return cached result
│  • Complexity scoring    │
│  • Sub-query generation  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. PARALLEL SOURCE FAN-OUT (Celery chord)                   │
│                                                               │
│  Task Group:                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
│  │ DDG x3  │ │Reddit x3│ │  HN x3  │ │ArXiv x3 │ │Wiki x3│ │
│  │sub-query│ │sub-query│ │sub-query│ │sub-query│ │sub-q  │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └───┬───┘ │
│       │           │           │           │          │      │
│  Each worker has:                                           │
│  • 10s timeout with circuit breaker                         │
│  • Per-source rate limiter (token bucket in Redis)          │
│  • Retry with exponential backoff (max 2 retries)           │
│  • Partial result return on timeout                         │
└───┬───────┬───────┬───────┬───────┬─────────────────────────┘
    │       │       │       │       │
    ▼       ▼       ▼       ▼       ▼
┌─────────────────────────────────────────┐
│  3. AGGREGATION & PROCESSING             │
│  a) Collect results (Celery chord cb)   │
│  b) HTML/PDF → clean text extraction     │
│  c) Near-duplicate detection (MinHash)   │
│     Jaccard similarity > 0.8 → dedupe    │
│  d) Intelligent chunking:                │
│     512 tokens, 64 token overlap         │
│  e) Parallel embedding generation:       │
│     HuggingFace all-MiniLM-L6-v2 (384d) │
│  f) Batch upsert → ChromaDB             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  4. TWO-PHASE HYBRID RETRIEVAL           │
│  Phase 1 — BM25 sparse → top-50         │
│  Phase 2 — Dense embedding → top-50     │
│  Fusion  — RRF(d) = Σ 1/(k+rank_i(d))  │
│            k=60, returns final top-15    │
│  Post: source diversity + recency boost  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  5. STREAMING SYNTHESIS                  │
│  • Top-15 chunks → LLM context window   │
│  • Inline citations: [1], [2], [3]       │
│  • Streaming via SSE token-by-token      │
│  • Structured: Summary → Analysis →     │
│    Trade-offs → Sources & Confidence     │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  6. PERSISTENCE                          │
│  • Research session → PostgreSQL         │
│  • Chunks + embeddings → ChromaDB        │
│  • Entity extraction → knowledge graph   │
│  • Redis cache: query hash → result      │
│    (TTL: 24h, stale-while-revalidate)    │
└─────────────────────────────────────────┘
```

---

## 4. Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, middleware, CORS, lifespan
│   ├── config.py                # Settings via pydantic-settings
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── research.py      # /research endpoints (SSE streaming)
│   │   │   ├── knowledge.py     # /knowledge search & graph endpoints
│   │   │   ├── sessions.py      # /sessions CRUD
│   │   │   ├── export.py        # /export endpoints (markdown, JSON, Obsidian)
│   │   │   ├── analytics.py     # /analytics dashboard data
│   │   │   └── health.py        # /health for monitoring
│   │   └── dependencies.py      # Auth, rate limiting, DB sessions
│   │
│   ├── core/
│   │   ├── orchestrator.py      # Research pipeline orchestration
│   │   ├── query_analyzer.py    # Intent classification, sub-query generation
│   │   ├── synthesizer.py       # LLM-based answer synthesis with citations
│   │   └── context_manager.py   # Session context compression
│   │
│   ├── retrieval/
│   │   ├── hybrid_retriever.py  # BM25 + dense + RRF fusion
│   │   ├── bm25.py             # Sparse retrieval implementation
│   │   ├── dense.py            # Embedding-based retrieval
│   │   ├── reranker.py         # Cross-encoder reranking (optional)
│   │   └── deduplication.py    # MinHash/LSH near-duplicate detection
│   │
│   ├── sources/
│   │   ├── base.py             # Abstract source adapter interface
│   │   ├── duckduckgo.py       # DuckDuckGo search adapter
│   │   ├── reddit.py           # Reddit API adapter
│   │   ├── hackernews.py       # HN Algolia API adapter
│   │   ├── arxiv.py            # ArXiv API adapter
│   │   ├── wikipedia.py        # Wikipedia API adapter
│   │   └── registry.py         # Source discovery & registration
│   │
│   ├── ingestion/
│   │   ├── pipeline.py         # Document processing pipeline
│   │   ├── extractors.py       # HTML/PDF/text content extraction
│   │   ├── chunker.py          # Recursive text splitting with metadata
│   │   └── embedder.py         # Embedding generation (HF/OpenAI)
│   │
│   ├── knowledge/
│   │   ├── graph.py            # Knowledge graph operations
│   │   ├── entities.py         # Entity extraction & linking
│   │   └── memory.py           # Persistent memory / recall
│   │
│   ├── agents/                  # Phase 4
│   │   ├── base.py             # Base agent class
│   │   ├── state.py            # Agent state machine
│   │   ├── react_loop.py       # ReAct reasoning loop
│   │   ├── tools.py            # Agent tool registry
│   │   ├── evaluator.py        # Self-evaluation + confidence scoring
│   │   ├── trace.py            # Agent trace logging
│   │   ├── coordinator.py      # Multi-agent coordination
│   │   ├── proactive.py        # Proactive research agent
│   │   └── specialists/
│   │       ├── academic.py     # Academic-focused agent
│   │       ├── practitioner.py # Practitioner-focused agent
│   │       └── factcheck.py    # Fact-checking agent
│   │
│   ├── workers/
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── tasks.py            # Source search tasks, ingestion tasks
│   │   ├── callbacks.py        # Chord callbacks for aggregation
│   │   └── scheduled.py        # Celery Beat scheduled tasks
│   │
│   ├── resilience/
│   │   ├── circuit_breaker.py  # Per-source circuit breaker (Redis-backed)
│   │   ├── rate_limiter.py     # Token bucket rate limiter (Redis-backed)
│   │   └── retry.py            # Exponential backoff retry logic
│   │
│   ├── cache/
│   │   ├── redis_cache.py      # Cache operations + stale-while-revalidate
│   │   └── embedding_cache.py  # LRU cache for repeated embedding queries
│   │
│   └── db/
│       ├── models.py           # SQLAlchemy models
│       ├── vector_store.py     # ChromaDB operations
│       └── session.py          # Async DB session management
│
├── tests/
│   ├── conftest.py             # Fixtures: mock Redis, mock Celery, test DB
│   ├── test_orchestrator.py
│   ├── test_retrieval.py       # Hybrid retrieval accuracy tests
│   ├── test_sources/           # Per-source adapter tests (mocked HTTP)
│   ├── test_resilience.py      # Circuit breaker state machine tests
│   ├── test_cache.py           # Cache hit/miss/stale scenarios
│   └── test_api/               # FastAPI endpoint tests
│
├── migrations/                  # Alembic migrations
├── plugins/                     # Custom source plugins directory
├── requirements.txt
├── Dockerfile
├── pytest.ini
└── .pre-commit-config.yaml
```

---

## 5. Configuration & Environment

### Settings Class (`config.py`)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM
    groq_api_key: str
    llm_model: str = "llama-3.1-70b-versatile"

    # Embeddings
    hf_api_token: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"

    # Vector DB
    chroma_persist_dir: str = "./chroma_data"

    # PostgreSQL (Supabase)
    supabase_url: str
    supabase_key: str
    supabase_jwt_secret: str = ""
    database_url: str = ""  # async postgres connection string

    # Redis (Upstash)
    upstash_redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Research pipeline
    max_sources_per_query: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_context_tokens: int = 4096

    model_config = SettingsConfigDict(env_file=".env")
```

### Environment Variables (`.env.example`)

```bash
# Required
GROQ_API_KEY=gsk_...               # Free at console.groq.com
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Optional (defaults work for local dev)
UPSTASH_REDIS_URL=redis://...       # Falls back to local Redis
HF_API_TOKEN=hf_...                 # For HuggingFace embeddings API
CHROMA_PERSIST_DIR=./chroma_data
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
SUPABASE_JWT_SECRET=...             # For auth token verification
```

---

## 6. Data Models

### Pydantic Models (API Layer)

```python
# --- Request Models ---

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    sources: list[str] | None = None   # None = use all available
    depth: Literal["quick", "standard", "deep"] = "standard"

class FollowupRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)

# --- Domain Models ---

class SourceResult(BaseModel):
    title: str
    url: str
    snippet: str
    raw_content: str | None = None
    source_name: str
    published_date: datetime | None = None
    metadata: dict = {}

class Chunk(BaseModel):
    chunk_id: str           # UUID
    text: str
    source_url: str
    source_name: str
    source_title: str
    chunk_index: int        # Position within the source document
    total_chunks: int       # Total chunks from this document
    published_date: datetime | None
    fetched_at: datetime

class RetrievedChunk(BaseModel):
    chunk: Chunk
    score: float           # RRF fused score
    citation_id: int       # Auto-assigned: 1, 2, 3...

class Citation(BaseModel):
    id: int
    title: str
    url: str
    source_name: str
    relevance_score: float

# --- Entity / Knowledge Models ---

class Entity(BaseModel):
    name: str
    type: str              # technology, concept, organization, person, protocol, algorithm, library, service, pattern
    description: str
    aliases: list[str] = []
    first_seen: datetime
    last_seen: datetime
    mention_count: int = 1

class Relationship(BaseModel):
    source_entity: str
    target_entity: str
    type: str              # compared_with, depends_on, implements, alternative_to, part_of, used_by, supersedes, extends, conflicts_with
    context: str
    session_id: str
    confidence: float = 1.0
```

### SQLAlchemy Models (PostgreSQL)

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    sessions: Mapped[list["ResearchSession"]] = relationship(back_populates="user")

class ResearchSession(Base):
    __tablename__ = "research_sessions"
    id: Mapped[str] = mapped_column(primary_key=True)   # "session_xxx"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    query_count: Mapped[int] = mapped_column(default=1)
    sources_used: Mapped[list[str]] = mapped_column(ARRAY(String))
    status: Mapped[str] = mapped_column(default="active")   # active, archived

    user: Mapped["User"] = relationship(back_populates="sessions")
    turns: Mapped[list["ResearchTurn"]] = relationship(back_populates="session")

class ResearchTurn(Base):
    __tablename__ = "research_turns"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"), index=True)
    query: Mapped[str]
    synthesized_answer: Mapped[str]
    sources_searched: Mapped[int]
    chunks_retrieved: Mapped[int]
    latency_ms: Mapped[int]
    citations: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime]
    compressed_context: Mapped[str | None]   # For progressive summarization

    session: Mapped["ResearchSession"] = relationship(back_populates="turns")

class SourceCache(Base):
    __tablename__ = "source_cache"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_hash: Mapped[str] = mapped_column(index=True)
    source_name: Mapped[str]
    results_json: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime]
    expires_at: Mapped[datetime]

class KnowledgeEntity(Base):
    __tablename__ = "knowledge_entities"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(index=True)
    type: Mapped[str]
    description: Mapped[str]
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    mention_count: Mapped[int] = mapped_column(default=1)
    first_seen: Mapped[datetime]
    last_seen: Mapped[datetime]
    __table_args__ = (UniqueConstraint("user_id", "name"),)

class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_entities.id"))
    target_entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_entities.id"))
    type: Mapped[str]
    context: Mapped[str]
    session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"))
    confidence: Mapped[float] = mapped_column(default=1.0)
    created_at: Mapped[datetime]

class ResearchSchedule(Base):
    __tablename__ = "research_schedules"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]
    query_template: Mapped[str]       # "Latest developments in {topic}"
    topics: Mapped[list[str]]
    frequency: Mapped[str]            # "daily", "weekly"
    sources: Mapped[list[str]]
    is_active: Mapped[bool]
    last_run: Mapped[datetime | None]

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]
    type: Mapped[str]                 # proactive_research, knowledge_update, contradiction_found
    title: Mapped[str]
    body: Mapped[str]
    suggestion_query: Mapped[str | None]
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]

# Phase 4: Agent Traces
class AgentTrace(Base):
    __tablename__ = "agent_traces"
    id: Mapped[uuid.UUID]
    session_id: Mapped[str]
    turn_id: Mapped[uuid.UUID]
    agent_type: Mapped[str]           # coordinator, academic, practitioner, factcheck
    iterations: Mapped[list[dict]] = mapped_column(JSON)
    total_iterations: Mapped[int]
    total_duration_ms: Mapped[int]
    final_confidence: Mapped[float]
    tools_used: Mapped[list[str]] = mapped_column(ARRAY(String))
```

---

## 7. API Reference

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Returns `{"status": "ok", "version": "0.1.0"}` |

### Research (SSE Streaming)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/research` | Start new research query (SSE stream) |
| `POST` | `/api/v1/research/{session_id}/followup` | Follow-up within existing session (SSE stream) |

#### `POST /api/v1/research` — Request

```json
{
  "query": "Trade-offs between Kafka and RabbitMQ for event-driven microservices",
  "sources": ["ddg", "reddit", "hackernews", "arxiv", "wikipedia"],
  "session_id": null,
  "depth": "standard"
}
```

#### SSE Event Stream (Response)

```
event: status
data: {"phase": "decomposing", "message": "Breaking query into sub-queries..."}

event: status
data: {"phase": "searching", "message": "Searching 5 sources in parallel...", "sources_active": 5}

event: source_complete
data: {"source": "ddg", "results_count": 8, "latency_ms": 1200}

event: source_complete
data: {"source": "reddit", "results_count": 5, "latency_ms": 890}

event: status
data: {"phase": "synthesizing", "message": "Generating answer from 24 sources..."}

event: token
data: {"content": "Based on analysis of 24 sources...", "citations": []}

event: token
data: {"content": " Kafka excels at high-throughput ordered event streaming [1][2]", "citations": [1, 2]}

event: complete
data: {
  "session_id": "sess_abc123",
  "sources_used": 24,
  "latency_ms": 7800,
  "citations": [
    {"id": 1, "title": "Kafka vs RabbitMQ - Confluent", "url": "https://...", "relevance": 0.94},
    {"id": 2, "title": "Message Broker Comparison - r/microservices", "url": "https://...", "relevance": 0.89}
  ]
}
```

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sessions` | List user's sessions (paginated, sorted by `updated_at`) |
| `GET` | `/api/v1/sessions/{id}` | Get session with all turns |
| `PATCH` | `/api/v1/sessions/{id}` | Rename session |
| `DELETE` | `/api/v1/sessions/{id}` | Soft-delete (set `status=archived`) |
| `GET` | `/api/v1/sessions/{id}/graph` | Get knowledge graph for a session |
| `POST` | `/api/v1/sessions/{id}/share` | Generate shareable link with role |

### Knowledge

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/knowledge/search?q={query}&limit=10` | Search across persistent knowledge base |
| `GET` | `/api/v1/knowledge/recall?q={query}&limit=10&recency=on` | Cross-session recall with temporal weighting |
| `GET` | `/api/v1/knowledge/export?format=obsidian` | Export full knowledge graph (ZIP) |

### Sources

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sources` | List all available sources (built-in + plugins) |

### Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sessions/{id}/export?format=markdown` | Export session as markdown/json/obsidian |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics` | Dashboard data: sessions, queries, entities, performance |

### Schedules

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/schedules` | Create research schedule |
| `GET` | `/api/v1/schedules` | List schedules |
| `PATCH` | `/api/v1/schedules/{id}` | Update/pause schedule |
| `DELETE` | `/api/v1/schedules/{id}` | Delete schedule |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/notifications` | Get user notifications |
| `PATCH` | `/api/v1/notifications/{id}/read` | Mark notification as read |

### Suggestions (Phase 4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/suggestions` | Proactive research suggestions |
| `POST` | `/api/v1/suggestions/{id}/execute` | Execute a suggested research |

### Agent Trace (Phase 4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sessions/{id}/turns/{turn_id}/trace` | Full agent reasoning trace |

---

## 8. Core Services

### 8.1 Query Analyzer (`core/query_analyzer.py`)

Decomposes complex queries into 2-4 orthogonal sub-queries using the Groq LLM.

```python
class QueryAnalyzer:
    # Model: llama-3.1-70b-versatile via Groq
    # Temperature: 0.1 (deterministic decomposition)
    # Output: JSON array of sub-query strings
    # Fallback: split on newlines if JSON parse fails
    # Simple queries returned as single-element array
    async def decompose(self, query: str) -> list[str]: ...
```

**System prompt:**
```
You are a research query decomposer. Given a complex research question,
break it into 2-4 focused, orthogonal sub-queries that together cover
the full scope of the original question.

Rules:
- Each sub-query should target a different aspect
- Sub-queries should be specific enough for a search engine
- Return as JSON array of strings
- If the query is already simple and focused, return it as a single-element array
```

### 8.2 Synthesizer (`core/synthesizer.py`)

Streams a cited answer from retrieved chunks via the Groq LLM.

```python
class Synthesizer:
    # Model: llama-3.1-70b-versatile via Groq
    # Temperature: 0.3 (balanced factual + readable)
    # Max tokens: 2048
    # Streaming: stream=True, yield token-by-token
    async def stream(self, chunks: list[RetrievedChunk], query: str) -> AsyncGenerator[str, None]: ...
```

**System prompt:**
```
You are a research synthesis engine. Using ONLY the provided sources,
generate a comprehensive, well-structured answer.

Rules:
- Cite sources using [1], [2], [3] notation
- Only cite source IDs that are provided below
- Do NOT generate URLs or reference external information
- Structure your response with clear sections
- If sources conflict, explicitly note the disagreement
- If sources are insufficient, state what's missing

Sources:
[1] {chunk_1_text}
[2] {chunk_2_text}
...
```

**Citation architecture** (hallucination is structurally impossible):
- Citations are pre-assigned IDs in the prompt
- LLM can only reference provided IDs
- Frontend resolves IDs to verified URLs from the database

### 8.3 Research Orchestrator (`core/orchestrator.py`)

Ties the full pipeline together and emits SSE events at each stage.

```python
class ResearchOrchestrator:
    def __init__(self, query_analyzer, source_registry, ingestion_pipeline,
                 vector_store, synthesizer): ...

    async def research(self, query: str, sources: list[str] | None = None
                      ) -> AsyncGenerator[SSEEvent, None]:
        # Step 1: Analyze → sub-queries          → yield status event
        # Step 2: Fan-out → parallel search       → yield source_complete events
        # Step 3: Ingest → extract/chunk/embed    → yield status event
        # Step 4: Store → ChromaDB upsert
        # Step 5: Retrieve → hybrid BM25+dense+RRF → top-15
        # Step 6: Synthesize → streaming LLM      → yield token events
        # Step 7: Complete                         → yield complete event with citations
```

### 8.4 Context Manager (`core/context_manager.py`)

Manages session context for follow-up questions. Implements progressive summarization to prevent context window overflow.

```python
class ContextManager:
    MAX_CONTEXT_TOKENS = 4096

    async def build_context(self, session_id: str, db: AsyncSession) -> str:
        # If total turns fit in budget → return full context
        # Else → compress older turns via LLM summary, keep last 2 turns full
        # Summary preserves: key findings, citations, contradictions, preferences
```

---

## 9. Source Adapters

### Abstract Interface (`sources/base.py`)

```python
class SourceAdapter(ABC):
    name: str              # e.g., "duckduckgo"
    display_name: str      # e.g., "DuckDuckGo Web Search"
    max_results: int = 10
    timeout_seconds: int = 10

    @abstractmethod
    async def search(self, query: str, max_results: int) -> list[SourceResult]: ...

    @abstractmethod
    def is_available(self) -> bool: ...
```

### Adapter Specifications

| Adapter | API | Rate Limit | Notes |
|---------|-----|-----------|-------|
| **DuckDuckGo** | `duckduckgo-search` library | 1 req/sec, burst 5 | No API key needed |
| **Wikipedia** | REST API + search API | 5 req/sec, burst 20 | Fetch top 3 article summaries |
| **HackerNews** | Algolia API (`hn.algolia.com`) | 2 req/sec, burst 10 | Top 10 stories by relevance, top 5 with comments |
| **Reddit** | JSON API (append `.json`) | 1 req/2sec, burst 3 | Target subreddits: r/programming, r/devops, r/machinelearning, r/Python, r/ExperiencedDevs. User-Agent required |
| **ArXiv** | Atom XML API (`export.arxiv.org`) | 1 req/3sec, burst 3 | Parse via `feedparser`, use abstracts as content |

### Source Registry (`sources/registry.py`)

```python
class SourceRegistry:
    _adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter): ...
    def get(self, name: str) -> SourceAdapter: ...
    def get_all(self) -> list[SourceAdapter]: ...
    def get_available(self) -> list[SourceAdapter]: ...
```

Auto-registers all adapters on app startup via FastAPI `lifespan`.

### Custom Source Plugin Interface (Phase 3)

```python
class SourcePlugin(SourceAdapter):
    """
    Plugin structure:
    plugins/
      my_source/
        __init__.py      # Class extending SourcePlugin
        config.yaml      # Name, rate limits, auth requirements
        requirements.txt # Additional dependencies
    """
    @classmethod
    def from_config(cls, config_path: str) -> "SourcePlugin": ...
```

Plugin `config.yaml` schema:
```yaml
name: "stackoverflow"
display_name: "Stack Overflow"
description: "Search Stack Overflow questions and answers"
base_url: "https://api.stackexchange.com/2.3"
rate_limit:
  requests_per_second: 1
  burst: 5
auth:
  type: "api_key"     # or "oauth" or "none"
  env_var: "SO_API_KEY"
```

---

## 10. Ingestion Pipeline

### Pipeline Flow (`ingestion/pipeline.py`)

```python
class IngestionPipeline:
    async def process(self, source_results: list[SourceResult]) -> list[Chunk]:
        # 1. Extract clean text from each source result
        # 2. Deduplicate (MinHash, Jaccard > 0.8)
        # 3. Chunk each document (512 tokens, 64 overlap)
        # 4. Generate embeddings in batches (384-dim)
        # 5. Return chunks with embeddings attached
```

### Content Extraction (`ingestion/extractors.py`)

| Method | Input | Approach |
|--------|-------|----------|
| `extract_from_html` | HTML string | `beautifulsoup4` + `readability-lxml`, strip tags |
| `extract_from_text` | Raw text | Clean whitespace, normalize unicode |
| `extract_from_snippet` | URL + snippet | Use snippet as-is when full content unavailable |

Handles: encoding issues, UTF-8 normalize, null byte stripping.

### Text Chunking (`ingestion/chunker.py`)

- **Algorithm:** Recursive character text splitter
- **Chunk size:** 512 tokens
- **Overlap:** 64 tokens
- **Split hierarchy:** `\n\n` → `\n` → `. ` → ` ` → character
- **Token counting:** `tiktoken` (cl100k_base encoding)
- Each chunk preserves full metadata (source URL, name, title, position, date)

### Embedding Generation (`ingestion/embedder.py`)

| Priority | Provider | Model | Dimensions |
|----------|----------|-------|-----------|
| Primary | HuggingFace Inference API | `all-MiniLM-L6-v2` | 384 |
| Fallback | Local `sentence-transformers` | `all-MiniLM-L6-v2` | 384 |

- Batch embedding: up to 32 chunks per API call
- Retry: 2 retries with 1s backoff on 429/503

### Near-Duplicate Detection (`retrieval/deduplication.py`)

```python
class MinHashDeduplicator:
    # num_perm=128, threshold=0.8
    # Tokenizes into 3-grams (shingles)
    # Uses datasketch library for MinHash + LSH
    # Authority ranking for duplicate selection:
    #   ArXiv > Wikipedia > HackerNews > Reddit > DuckDuckGo
    def deduplicate(self, chunks: list[Chunk]) -> list[Chunk]: ...
```

Target: <100ms for 100 documents, 15-30% reduction in embedding API calls.

---

## 11. Retrieval Engine

### BM25 Sparse Retrieval (`retrieval/bm25.py`)

Custom implementation (no external dependency):

```python
class BM25Index:
    # k1=1.5 (term frequency saturation)
    # b=0.75 (document length normalization)
    # IDF: log((N - df + 0.5) / (df + 0.5) + 1)
    # BM25(q,d) = Σ IDF(t) * (tf * (k1+1)) / (tf + k1*(1-b+b*dl/avgdl))

    def fit(self, documents: list[str]) -> None: ...       # Build inverted index
    def query(self, query: str, top_k: int = 50) -> list[tuple[int, float]]: ...
    def add_documents(self, docs: list[str]) -> None: ...  # Incremental update
```

- Tokenizer: whitespace + lowercasing + stop word removal
- Index persistence: pickle alongside ChromaDB data

### Dense Retrieval (`retrieval/dense.py`)

```python
class DenseRetriever:
    # Wraps ChromaDB vector search
    async def query(self, query_embedding: list[float], collection: str,
                    top_k: int = 50) -> list[tuple[str, float]]: ...
```

### Hybrid Retriever with RRF (`retrieval/hybrid_retriever.py`)

```python
class HybridRetriever:
    def __init__(self, dense: DenseRetriever, bm25: BM25Index, k: int = 60): ...

    async def retrieve(self, query: str, query_embedding: list[float],
                       collection: str, top_k: int = 15) -> list[RetrievedChunk]:
        sparse_results = self.bm25.query(query, top_k=50)         # Phase 1
        dense_results = await self.dense.query(...)                # Phase 2
        fused = self._rrf_fuse(sparse_results, dense_results)     # Fusion
        return fused[:top_k]

    def _rrf_fuse(self, *result_lists) -> list[tuple[str, float]]:
        # RRF(d) = Σ 1/(k + rank_i(d))  for each ranking system i
        # k=60 (standard constant)
```

### Post-Retrieval Processing

- **Source diversity enforcement:** No more than 3 chunks from same source in top-15
- **Recency boost:** For time-sensitive queries, apply recency weighting
- **Cross-encoder reranker** (optional): Additional reranking pass for higher precision

### Retrieval Benchmarks (Natural Questions subset)

| Method | Recall@10 | MRR@10 | Latency |
|--------|-----------|--------|---------|
| BM25 only | 0.72 | 0.58 | 12ms |
| Dense only (MiniLM) | 0.78 | 0.64 | 45ms |
| **Hybrid (RRF)** | **0.86** | **0.71** | **62ms** |
| Hybrid + Reranker | 0.91 | 0.79 | 180ms |

---

## 12. Resilience Layer

### Circuit Breaker (`resilience/circuit_breaker.py`)

Per-source circuit breaker with Redis-backed state.

```
States:  CLOSED → OPEN → HALF_OPEN → CLOSED
         (normal)  (failing)  (testing)  (recovered)

Transitions:
  CLOSED → OPEN:      failure_count >= 5 within 60s window
  OPEN → HALF_OPEN:   after 30s cooldown
  HALF_OPEN → CLOSED: test request succeeds
  HALF_OPEN → OPEN:   test request fails
```

Redis keys per source:
- `cb:{source}:state` → `"closed"` | `"open"` | `"half_open"`
- `cb:{source}:failures` → int
- `cb:{source}:last_fail` → timestamp
- `cb:{source}:opened_at` → timestamp

Used as async context manager in source search tasks.

### Token Bucket Rate Limiter (`resilience/rate_limiter.py`)

Per-source rate limits stored in Redis:

| Source | Requests/sec | Bucket Size |
|--------|-------------|-------------|
| DuckDuckGo | 1 | 5 |
| Reddit | 0.5 | 3 |
| HackerNews | 2 | 10 |
| ArXiv | 0.33 | 3 |
| Wikipedia | 5 | 20 |

Redis keys: `rl:{source}:tokens`, `rl:{source}:last_refill`

### Retry with Exponential Backoff (`resilience/retry.py`)

```python
def with_retry(max_retries=2, backoff_base=1.0,
               retryable_exceptions=(TimeoutError, ConnectionError)):
    # Delay: backoff_base * 2^attempt (1s, 2s, 4s...)
    # Jitter: ±20% random to avoid thundering herd
```

### Graceful Degradation

- If a source fails, remaining sources still return results
- Synthesis pipeline works with however many sources returned
- Synthesis notes which sources were unavailable

---

## 13. Caching Strategy

### Two-Tier Research Cache (`cache/redis_cache.py`)

```python
class ResearchCache:
    # Tier 1: Query hash → full synthesized result (TTL: 24 hours)
    # Tier 2: Source + query hash → raw source results (TTL: 6 hours)

    fresh_ttl = 86400            # 24 hours
    stale_threshold = 72000      # Stale after 20 hours

    async def get_research(self, query_hash: str) -> CacheResult | None: ...
    async def set_research(self, query_hash: str, data: dict) -> None: ...
    async def get_source_results(self, source: str, query_hash: str) -> list[dict] | None: ...
    async def set_source_results(self, source: str, query_hash: str, data: list[dict]) -> None: ...

    @staticmethod
    def hash_query(query: str) -> str:
        # Normalize: lowercase, strip whitespace, remove punctuation → SHA-256
```

### Stale-While-Revalidate Pattern

```
Fresh cache hit (TTL > stale_threshold):
  → Return immediately (~200ms)

Stale cache hit (TTL <= stale_threshold):
  → Return stale result immediately (~250ms)
  → Trigger background refresh via Celery task

Cache miss:
  → Full research pipeline (~8-12s)
```

### Embedding Cache (`cache/embedding_cache.py`)

- In-memory LRU cache (max 10,000 entries)
- Key: hash of chunk text → Value: embedding vector
- Uses `cachetools.LRUCache`
- Target: 30%+ reduction in embedding API calls on related queries

---

## 14. Knowledge Graph & Memory

### Entity Extraction (`knowledge/entities.py`)

Runs on every synthesized research answer via Groq LLM.

```python
class EntityExtractor:
    ENTITY_TYPES = [
        "technology", "concept", "organization", "person",
        "protocol", "algorithm", "library", "service", "pattern"
    ]
    RELATIONSHIP_TYPES = [
        "compared_with", "depends_on", "implements", "alternative_to",
        "part_of", "used_by", "supersedes", "extends", "conflicts_with"
    ]

    async def extract(self, synthesized_answer: str, query: str) -> ExtractionResult: ...
```

Entity normalization pipeline:
- Lowercase all names
- Resolve aliases ("Apache Kafka" → "kafka", "K8s" → "kubernetes")
- Merge duplicates across sessions
- Increment `mention_count` on re-encounter

### Knowledge Graph Service (`knowledge/graph.py`)

```python
class KnowledgeGraph:
    async def add_entities(self, user_id, entities, session_id) -> list[KnowledgeEntity]: ...
    async def add_relationships(self, user_id, relationships, session_id) -> None: ...
    async def get_entity_graph(self, user_id, entity_name) -> GraphData: ...     # 1-hop
    async def get_session_graph(self, user_id, session_id) -> GraphData: ...
    async def get_full_graph(self, user_id) -> GraphData: ...
    async def search_entities(self, user_id, query, limit=20) -> list[KnowledgeEntity]: ...
```

### Cross-Session Recall (`knowledge/memory.py`)

```python
class KnowledgeMemory:
    async def recall(self, user_id: str, query: str, limit: int = 10) -> RecallResult:
        # 1. Embed recall query
        # 2. Search across ALL user's session collections in ChromaDB
        # 3. Search knowledge graph entities
        # 4. Graph-connected chunks ranked higher
        # 5. Apply temporal weighting: score *= exp(-0.01 * days_since)

    async def find_connections(self, user_id, entity_a, entity_b) -> list[ConnectionPath]:
        # Graph shortest-path between entities

    async def get_timeline(self, user_id, entity) -> list[TimelineEntry]:
        # Chronological view of research on an entity
```

### Export Service (`api/routes/export.py`)

Supported formats:
- **Markdown:** Session as structured `.md` with queries, answers, citations
- **JSON:** Raw data export
- **Obsidian Vault:** Each entity = a note, relationships = `[[wikilinks]]`, sessions = notes with backlinks. Returns as ZIP.

---

## 15. Agent System (Phase 4)

### ReAct Research Agent (`agents/react_loop.py`)

Autonomous Reason → Act → Observe loop with iteration budget.

```python
class ReActLoop:
    async def run(self, query: str, state: AgentState) -> AsyncGenerator[AgentEvent, None]:
        while not state.is_terminal and state.iteration < state.max_iterations:
            action = await self._reason(state)           # LLM decides next step
            result = await self._act(action, state)       # Execute via tool
            state = self._observe(state, action, result)  # Update state
            evaluation = await self._evaluate(state)      # Should we continue?
            state.iteration += 1
        async for token in self._synthesize(state):       # Final answer
            yield AgentEvent(type="token", data={"content": token})
```

Available agent actions: `decompose`, `search`, `refine`, `verify`, `expand`, `recall`, `synthesize`

### Agent State (`agents/state.py`)

```python
class AgentState(BaseModel):
    session_id: str
    original_query: str
    current_plan: list[AgentStep]
    completed_steps: list[CompletedStep]
    gathered_knowledge: list[Chunk]
    sub_queries_generated: list[str]
    sources_searched: dict[str, list[str]]
    verification_results: list[VerificationResult]
    iteration: int = 0
    max_iterations: int = 8
    confidence: float = 0.0
    status: Literal["thinking", "searching", "verifying", "synthesizing", "complete", "stuck"]
```

### Agent Tools (`agents/tools.py`)

| Tool | Wraps | Purpose |
|------|-------|---------|
| `SearchTool` | Source adapter fan-out | Search specific sources with specific queries |
| `RefineTool` | Source adapters | Rewrite and re-search a failed query |
| `VerifyTool` | Source adapters | Cross-check a specific claim |
| `RecallTool` | KnowledgeMemory | Check past research for context |
| `ExpandTool` | Source adapters | Research a related topic discovered in results |

### Self-Evaluation (`agents/evaluator.py`)

Confidence scoring after each iteration:
- **Increases:** Multiple sources agree, source diversity, quantitative data, past knowledge confirms
- **Decreases:** Contradictions, single source type, results don't address query, <3 unique queries
- **Thresholds:** >0.75 → synthesize, 0.4-0.75 → continue, <0.4 at max iterations → synthesize with disclaimer

### Multi-Agent Architecture (`agents/coordinator.py`)

| Agent | Focus | Preferred Sources | Emphasis |
|-------|-------|-------------------|----------|
| `AcademicAgent` | Papers, theory | ArXiv, Wikipedia | Rigor, methodology, peer-reviewed evidence |
| `PractitionerAgent` | Real-world experience | Reddit, HN, DuckDuckGo | Operational reality, war stories |
| `FactCheckAgent` | Claim verification | Any source | Primary sources, contradictions, bias |

Coordinator decides based on query complexity:
- Simple factual → single agent
- Comparison / trade-offs → multi-agent (academic + practitioner)
- Theory question → academic only
- Implementation question → practitioner only

### Proactive Research Agent (`agents/proactive.py`)

Background agent (Celery Beat, weekly) that:
1. Scans knowledge graph for isolated entities (few connections)
2. Detects stale knowledge (>30 days old technology entities)
3. Finds incomplete comparisons (researched A and B separately, never compared)
4. Generates actionable research suggestions with notifications

---

## 16. Worker Infrastructure

### Celery Configuration (`workers/celery_app.py`)

```python
celery_app = Celery("sift", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_soft_time_limit=15,
    task_time_limit=20,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.search_source": {"queue": "search"},
        "app.workers.tasks.process_results": {"queue": "ingestion"},
    },
)
```

### Task Definitions (`workers/tasks.py`)

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=2)
def search_source(self, source_name: str, sub_queries: list[str]) -> dict:
    """Search a single source, all sub-queries. Retries on transient failures."""

@celery_app.task
def process_results(search_results: list[dict], session_id: str) -> dict:
    """Chord callback: dedup → chunk → embed → upsert to ChromaDB."""
```

### Chord-Based Fan-out

```python
from celery import chord, group

search_tasks = group([
    search_source.s(adapter.name, sub_queries)
    for adapter in selected_adapters
])
result = chord(search_tasks)(process_results.s(session_id=session_id))
```

### Celery Beat (Scheduled Tasks)

```python
celery_app.conf.beat_schedule = {
    "process-research-schedules": {
        "task": "app.workers.scheduled.run_scheduled_research",
        "schedule": crontab(hour=7, minute=0),   # Daily at 7 AM UTC
    },
    "analyze-knowledge-gaps": {
        "task": "app.workers.scheduled.analyze_knowledge_gaps",
        "schedule": crontab(day_of_week=1, hour=6),  # Weekly Monday 6 AM
    },
}
```

---

## 17. Authentication

### Supabase Auth Integration

Backend verifies JWT tokens from Supabase Auth:

```python
async def get_current_user(authorization: str = Header(...)) -> User:
    token = authorization.replace("Bearer ", "")
    payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"])
    user_id = payload["sub"]
    # Get or create user in local DB
    return user
```

### Access Modes

| Mode | Research | Session Persistence | Knowledge Graph |
|------|----------|-------------------|-----------------|
| **Anonymous** | Yes | No (ephemeral, localStorage) | No |
| **Authenticated** | Yes | Yes (PostgreSQL) | Yes |

Protected endpoints: `/research`, `/sessions`, `/knowledge`, `/schedules`, `/notifications`, `/analytics`

### Collaborative Sessions

- `session_collaborators` join table: `user_id`, `session_id`, `role: "viewer" | "editor"`
- Viewers can read; editors can add follow-up queries
- Share via generated link with role

---

## 18. Testing Strategy

### Coverage Targets

| Phase | Overall | Critical Paths |
|-------|---------|---------------|
| Phase 1 | 70%+ | 90%+ (orchestrator, retrieval, synthesis) |
| Phase 2+ | 85%+ | 90%+ |

### Test Configuration (`pytest.ini`)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests requiring external services
```

### Test Matrix

| Category | Tests | Examples |
|----------|-------|---------|
| **Source Adapters** | 5 per adapter | Valid response, empty results, timeout, rate limit, malformed response |
| **Ingestion** | 18+ | Chunker size/overlap, metadata preservation, HTML extraction, embedding batching |
| **Vector Store** | 5+ | Upsert, query, metadata filter, empty collection, persistence |
| **Query Analyzer** | 4+ | Decomposition, simple passthrough, malformed LLM response, empty query |
| **Synthesizer** | 4+ | Streaming, citation format, empty chunks, max token handling |
| **Orchestrator** | 5+ | Full pipeline, partial failure, all sources fail, timeout, SSE format |
| **Retrieval** | 8+ | RRF fusion correctness, BM25 keyword match, hybrid e2e, golden dataset benchmark |
| **Resilience** | 7+ | Circuit breaker states, rate limiter blocking/refill, retry backoff timing |
| **Cache** | 5+ | Fresh hit, stale hit + refresh, miss, key normalization, embedding cache |
| **API** | 4+ | Valid request, invalid request, SSE format, concurrent requests |
| **Agent (Ph4)** | 13+ | ReAct loop iterations, multi-agent dispatch, confidence scoring, trace logging |

### Key Test Patterns

All external APIs mocked (no test depends on external services). Use `pytest-httpx` / `respx` for HTTP, mock Groq client for LLM, use Celery eager mode (`CELERY_ALWAYS_EAGER=True`), temporary ChromaDB directory (`tmp_path`).

---

## 19. Deployment & Infrastructure

### Free-Tier Stack

| Component | Service | Limits | Role |
|-----------|---------|--------|------|
| **LLM** | Groq | 30 req/min, Llama 3.1 70B | Decompose, synthesize, entity extract |
| **Embeddings** | HuggingFace Inference API | Rate-limited free tier | `all-MiniLM-L6-v2` (384-dim) |
| **Vector DB** | ChromaDB (embedded) | Unlimited (in-process) | Chunks, embeddings, metadata |
| **PostgreSQL** | Supabase | 500MB, 2 projects | Users, sessions, knowledge graph |
| **Redis** | Upstash | 10K commands/day | Celery broker, cache, rate limits |
| **Backend Host** | Render | 750 hrs/mo free | FastAPI + Celery worker |
| **CI/CD** | GitHub Actions | 2000 min/mo free | Lint, test, deploy |
| **Monitoring** | Better Stack (free) | Free tier | Uptime, logging |

### Docker Setup

**`docker-compose.yml` (Production):**

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - CHROMA_PERSIST_DIR=/data/chroma
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - chroma_data:/data/chroma
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
    depends_on: [redis, worker]

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 -Q search,ingestion
    depends_on: [redis]
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  chroma_data:
```

**`Dockerfile` (Backend):**
- Base: `python:3.11-slim`
- Multi-stage build
- `pip install -r requirements.txt`
- Run: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### CI/CD (`.github/workflows/`)

**`ci.yml` (on PR to main):**
- Lint: `ruff check`, `ruff format --check`, `mypy`
- Test: `pytest -v --cov=app --cov-fail-under=85` (with Redis service container)

**`deploy.yml` (on push to main):**
- Trigger Render deploy hook (webhook URL)

### Render Deployment Notes

- Free tier sleeps after 15 min inactivity → add UptimeRobot ping every 14 min
- Configure health check: `/api/v1/health`
- Background Worker for Celery on separate service

### Structured Logging

```python
import structlog
logger = structlog.get_logger()
logger.info("research_completed", session_id=sid, latency_ms=lat, sources=5, chunks=42)
```

---

## 20. Performance Targets

### Latency Targets (Render free tier, Groq Llama 3.1 70B)

| Metric | Target | Notes |
|--------|--------|-------|
| Time to first token | ~3.5s | Query analysis + first source + synthesis start |
| Full response | ~8-12s | All 5 sources + synthesis complete |
| Cache hit response | <300ms | Redis cached result |
| Stale-while-revalidate | <300ms | Stale result + background refresh |
| Embedding generation | ~50ms/chunk | HuggingFace all-MiniLM-L6-v2 |
| Hybrid retrieval | ~80ms | BM25 + dense + RRF on 10K chunks |
| P99 latency | ~15s | All sources slow + large synthesis |
| Concurrent users | ~20 | Free tier (single worker) |

### Source Reliability (30-day rolling)

```
DuckDuckGo:  99.2% uptime, avg 1.1s latency
Wikipedia:   99.8% uptime, avg 0.4s latency
HackerNews:  99.5% uptime, avg 0.8s latency
Reddit:      97.1% uptime, avg 1.4s latency   ← most circuit breaker trips
ArXiv:       98.9% uptime, avg 1.8s latency
```

### Scaling Path

```
Free Tier (Phase 1-2):    1 Render instance, Upstash 10K/day        → ~20 concurrent users
$25/mo (Phase 3):         Dedicated worker, Upstash Pro 100K/day    → ~200 concurrent users
$100/mo (Scale):          2 Celery workers, Managed Redis, Pinecone → ~2000 concurrent users
```

---

## 21. Phased Implementation Plan

> This section is the **detailed execution roadmap** for building the Sift backend from zero to production. Every phase is broken into weekly sprints, each sprint into numbered goals, and each goal into atomic checkpoints. Use this as your daily standup tracker.

### Overview Timeline

```
Phase 1 (2 Weeks)      Phase 2 (4 Weeks)       Phase 3 (4 Weeks)       Phase 4 (4 Weeks)
─────────────────       ─────────────────       ─────────────────       ─────────────────
Core Engine             Production Hardening    Knowledge System        Agentic Intelligence

• FastAPI + SSE         • Celery fan-out        • Entity extraction     • ReAct agent loop
• 3 source adapters     • Hybrid retrieval      • Knowledge graph       • Multi-agent arch
• Ingestion pipeline    • Circuit breakers      • Cross-session recall  • Self-evaluation
• ChromaDB retrieval    • Redis caching         • Custom source plugins • Agent tool registry
• LLM synthesis         • PostgreSQL sessions   • Export system         • Reasoning traces
• Docker Compose        • Auth (Supabase)       • Scheduled research    • Proactive research
• 70% test coverage     • CI/CD + Deploy        • Collab sessions       • 85% agent coverage
                        • 85% test coverage     • Perf dashboard

Deliverable:            Deliverable:            Deliverable:            Deliverable:
  Demo-able MVP           Production system       Knowledge OS            Autonomous research
```

**Total: 14 weeks (3.5 months) | Team: 2 backend + 1 DevOps (part-time after Phase 2)**

---
---

## PHASE 1 — Core Research Engine (Weeks 1-2)

**Phase Goal:** Working end-to-end research engine — user enters a question, gets a streamed, multi-source, cited answer via SSE.

**Phase Deliverable:** Demo-able MVP that runs with `docker compose up`.

---

### Sprint 1 — Backend Foundation + Source Adapters (Days 1-7)

#### Goal 1.1: Project Scaffolding & FastAPI Skeleton

**Owner:** Backend Lead | **Files:** `main.py`, `config.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml` | **Duration:** Day 1

- [x] **CP-1.1.1** Initialize Python 3.11+ project with `requirements.txt` and install core dependencies:
  `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `httpx`, `python-dotenv`, `sse-starlette`, `chromadb`, `groq`
- [x] **CP-1.1.2** Create `main.py` with FastAPI app instance, CORS middleware (allow `localhost:3000`), and a `lifespan` handler for startup/shutdown hooks
- [x] **CP-1.1.3** Create `config.py` using `pydantic-settings.BaseSettings` loading from `.env`:
  - Fields: `groq_api_key`, `chroma_persist_dir`, `embedding_model`, `llm_model`, `max_sources_per_query`, `chunk_size`, `chunk_overlap`
- [x] **CP-1.1.4** Create `health.py` route: `GET /api/v1/health` returning `{"status": "ok", "version": "0.1.0"}`
- [x] **CP-1.1.5** Create `Dockerfile` (Python 3.11-slim, multi-stage build)
- [x] **CP-1.1.6** Create `docker-compose.yml` with `backend` service + volume for ChromaDB persistence
- [x] **CP-1.1.7** Create `.env.example` with all required environment variables documented

**Checkpoint Review:**
- `docker compose up` starts the backend on port 8000
- `GET /api/v1/health` returns 200
- `GET /docs` shows Swagger UI

---

#### Goal 1.2: Source Adapter Interface + 3 Adapters

**Owner:** Backend Engineer | **Files:** `sources/base.py`, `sources/duckduckgo.py`, `sources/wikipedia.py`, `sources/hackernews.py`, `sources/registry.py` | **Duration:** Days 2-3

- [x] **CP-1.2.1** Define abstract base class `SourceAdapter` in `base.py` with `name`, `display_name`, `max_results`, `timeout_seconds`, abstract `search()`, and abstract `is_available()`
- [x] **CP-1.2.2** Define `SourceResult` Pydantic model: `title`, `url`, `snippet`, `raw_content`, `source_name`, `published_date`, `metadata`
- [x] **CP-1.2.3** Implement `DuckDuckGoAdapter`:
  - Use `duckduckgo-search` library
  - Parse results into `list[SourceResult]`
  - Handle rate limiting with 1s delay, 10s hard timeout
- [x] **CP-1.2.4** Implement `WikipediaAdapter`:
  - Wikipedia search API → top 3 article summaries via REST API
  - Extract `extract` field as raw_content
- [x] **CP-1.2.5** Implement `HackerNewsAdapter`:
  - Algolia HN API for top 10 stories by relevance
  - Fetch comments for top 5 stories, sort by points
- [x] **CP-1.2.6** Implement `SourceRegistry` in `registry.py` with `register()`, `get()`, `get_all()`, `get_available()` methods
- [x] **CP-1.2.7** Auto-register all adapters on app startup via FastAPI `lifespan`
- [x] **CP-1.2.8** Write tests per adapter with mocked HTTP (via `respx`/`pytest-httpx`):
  valid response, empty results, timeout, malformed response

**Checkpoint Review:**
- Each adapter returns a `list[SourceResult]` for any query
- Each adapter handles timeouts and errors gracefully (empty list, no crash)
- All adapter tests pass with mocked HTTP

---

#### Goal 1.3: Document Ingestion Pipeline

**Owner:** Backend Engineer | **Files:** `ingestion/pipeline.py`, `ingestion/extractors.py`, `ingestion/chunker.py`, `ingestion/embedder.py` | **Duration:** Days 3-4

- [x] **CP-1.3.1** Implement `ContentExtractor` in `extractors.py`:
  - `extract_from_html()` via `beautifulsoup4` + `readability-lxml`
  - `extract_from_text()` — clean whitespace, normalize unicode
  - `extract_from_snippet()` — use snippet as-is when full content unavailable
  - Handle encoding issues (UTF-8 normalize, strip null bytes)
- [x] **CP-1.3.2** Implement `TextChunker` in `chunker.py`:
  - Recursive character text splitter (512 tokens, 64 overlap)
  - Split hierarchy: `\n\n` → `\n` → `. ` → ` ` → character
  - Token counting via `tiktoken` (cl100k_base)
  - Preserve metadata per chunk: `chunk_id`, `source_url`, `source_name`, `source_title`, `chunk_index`, `total_chunks`, `published_date`, `fetched_at`
- [x] **CP-1.3.3** Implement `EmbeddingGenerator` in `embedder.py`:
  - Primary: HuggingFace Inference API (`all-MiniLM-L6-v2`, 384 dimensions)
  - Batch embedding: up to 32 chunks per API call
  - Fallback: local `sentence-transformers`
  - Retry: 2 retries with 1s backoff on 429/503
- [x] **CP-1.3.4** Implement `IngestionPipeline` in `pipeline.py`:
  `process(list[SourceResult]) → list[Chunk]` — extract → chunk → embed → return
- [x] **CP-1.3.5** Write tests: chunker sizes/overlaps, metadata preservation, HTML extraction, embedder batching, full pipeline e2e with mock data

**Checkpoint Review:**
- Pipeline converts `list[SourceResult]` → `list[Chunk]` with embeddings
- Chunks respect size limits (+-10% tolerance)
- Metadata is preserved through the pipeline

---

#### Goal 1.4: ChromaDB Vector Store Integration

**Owner:** Backend Engineer | **Files:** `db/vector_store.py` | **Duration:** Day 4

- [x] **CP-1.4.1** Implement `VectorStore` class wrapping `chromadb.PersistentClient`:
  - `get_or_create_collection()`, `upsert_chunks()`, `query()`, `delete_collection()`, `get_collection_stats()`
- [x] **CP-1.4.2** Define `RetrievedChunk` Pydantic model: `chunk`, `score`, `citation_id`
- [x] **CP-1.4.3** Collection naming convention: `session_{session_id}` for session-scoped, `global` for persistent
- [x] **CP-1.4.4** Persist directory configurable via `CHROMA_PERSIST_DIR` env var
- [x] **CP-1.4.5** Write tests: upsert + query, metadata filtering, empty collection, persistence across restarts

**Checkpoint Review:**
- Chunks can be stored and retrieved by semantic similarity
- Metadata filtering works (e.g., filter by `source_name`)
- Data persists across application restarts (Docker volume)

---

#### Goal 1.5: Query Analyzer + LLM Synthesis

**Owner:** Backend Lead | **Files:** `core/query_analyzer.py`, `core/synthesizer.py` | **Duration:** Days 4-5

- [x] **CP-1.5.1** Implement `QueryAnalyzer`:
  - Groq API integration with `llama-3.1-70b-versatile`
  - System prompt for decomposing complex queries into 2-4 focused sub-queries
  - Temperature: 0.1 (deterministic decomposition)
  - Parse JSON array response with fallback (split on newlines if JSON fails)
  - Simple queries returned as single-element array
- [x] **CP-1.5.2** Implement `Synthesizer`:
  - Takes `list[RetrievedChunk]` + original `query` → streams cited answer
  - System prompt enforces `[1]`, `[2]`, `[3]` citation format referencing only provided source IDs
  - Streaming: `stream=True`, yield token-by-token from Groq
  - Temperature: 0.3, max tokens: 2048
- [x] **CP-1.5.3** Write tests:
  - Decomposition produces valid JSON arrays
  - Simple query passthrough
  - Synthesis includes citation markers
  - Synthesis handles empty chunk list
  - Mock Groq API for deterministic results

**Checkpoint Review:**
- Complex queries decomposed into 2-4 focused sub-queries
- Synthesis produces structured, cited answers with streaming
- Hallucination structurally impossible (only pre-assigned IDs)

---

#### Goal 1.6: Research Orchestrator + SSE Endpoint

**Owner:** Backend Lead | **Files:** `core/orchestrator.py`, `api/routes/research.py` | **Duration:** Days 5-6

- [x] **CP-1.6.1** Implement `ResearchOrchestrator` with 7-step pipeline:
  1. Analyze query → sub-queries → yield `status` event
  2. Fan-out searches via `asyncio.gather` → yield `source_complete` events
  3. Ingest results → yield `status` event
  4. Store chunks in ChromaDB
  5. Retrieve top-15 via vector similarity
  6. Stream synthesis via LLM → yield `token` events
  7. Complete → yield `complete` event with `session_id` + citations
- [x] **CP-1.6.2** Implement SSE endpoint `POST /api/v1/research` using `EventSourceResponse`
- [x] **CP-1.6.3** Define request model `ResearchRequest` with `query`, `sources`, `depth` fields
- [x] **CP-1.6.4** Wrap each source search in try/except — log failures, continue with remaining sources
- [x] **CP-1.6.5** Write tests:
  - Full pipeline e2e with mocked sources and mocked LLM
  - Partial source failure (1 of 3 fails → still returns results)
  - Empty results handling
  - SSE event format validation

**Checkpoint Review:**
- `POST /api/v1/research` streams SSE events from decomposition through synthesis
- Partial source failures don't crash the pipeline
- Complete event includes `session_id` and citations array

---

### Sprint 1 Milestone Checkpoint

| Criteria | Target | Verification |
|----------|--------|-------------|
| Backend starts | Port 8000 | `docker compose up` |
| Health endpoint | 200 OK | `curl /api/v1/health` |
| SSE streaming | Full pipeline | `POST /api/v1/research` with test query |
| Source adapters | 3 working | DDG + Wikipedia + HackerNews |
| Error resilience | Partial failure | Kill one source mid-query |

---

### Sprint 2 — Docker, Testing & Documentation (Days 8-14)

#### Goal 1.7: Docker Compose Full Stack

**Owner:** Backend Lead | **Files:** `docker-compose.yml`, `docker-compose.dev.yml`, `Makefile` | **Duration:** Day 8

- [x] **CP-1.7.1** Create production `docker-compose.yml`:
  - `backend` service with health check, env vars, chroma volume
- [x] **CP-1.7.2** Create `docker-compose.dev.yml` with volume mounts for hot reload (`uvicorn --reload`)
- [x] **CP-1.7.3** Create `Makefile` with targets: `dev`, `prod`, `test`, `test-coverage`, `lint`, `logs`, `down`, `clean`

**Checkpoint Review:**
- `make dev` starts full stack with hot reload
- `make prod` starts production build
- `make test` runs backend tests inside container

---

#### Goal 1.8: Core Test Suite

**Owner:** Entire team | **Files:** `tests/**` | **Duration:** Days 9-12

- [x] **CP-1.8.1** Create `conftest.py` with shared fixtures:
  - `mock_groq_client`, `sample_source_results`, `temp_chroma_dir`, `vector_store`
- [x] **CP-1.8.2** Source adapter tests (5 per adapter — 15 total):
  valid response, empty results, timeout, rate limit, malformed response
- [x] **CP-1.8.3** Ingestion tests (18+):
  chunker sizes/overlaps, metadata preservation, HTML extraction, embedding batching, full pipeline
- [x] **CP-1.8.4** Vector store tests (5+):
  upsert, query, metadata filter, empty collection, persistence
- [x] **CP-1.8.5** Core tests (13+):
  - Query analyzer: decomposition, passthrough, malformed LLM response, empty query
  - Synthesizer: streaming, citation format, empty chunks, max token handling
  - Orchestrator: full pipeline, partial failure, all fail, timeout, SSE format
- [x] **CP-1.8.6** API endpoint tests (4+):
  valid request, invalid request, SSE format, concurrent requests
- [x] **CP-1.8.7** Configure `pytest.ini` with `asyncio_mode = auto`, markers for `slow` and `integration`
- [x] **CP-1.8.8** Achieve **70%+ overall coverage**, **90%+ on critical paths** (orchestrator, retrieval, synthesis)

**Checkpoint Review:**
- `pytest` passes with 0 failures
- Coverage report shows 70%+ overall
- No test depends on external APIs (all mocked)

---

#### Goal 1.9: Documentation + Demo Script

**Owner:** Backend Lead | **Duration:** Days 13-14

- [x] **CP-1.9.1** Write `QUICKSTART.md` with 5-minute setup guide
- [x] **CP-1.9.2** Create `demo_queries.md` with 10 demo queries that showcase multi-source synthesis
- [x] **CP-1.9.3** Verify Docker setup works from a clean clone on a fresh machine
- [x] **CP-1.9.4** Update README with actual API examples and setup instructions

**Checkpoint Review:**
- New developer can clone repo and have it running in under 5 minutes
- Demo queries produce impressive, well-cited answers

---

### PHASE 1 EXIT GATE

| # | Criteria | Status |
|---|----------|--------|
| 1 | All 9 goals completed and merged to `main` | [x] |
| 2 | 70%+ test coverage (90%+ on critical paths) | [x] |
| 3 | Docker Compose starts cleanly from fresh clone | [x] |
| 4 | 10 demo queries produce quality cited answers | [x] |
| 5 | No critical bugs in the happy path | [x] |
| 6 | SSE stream format verified (status → source_complete → token → complete) | [x] |

**Phase 1 Deliverable:** Enter a question → get a cited, multi-source answer streamed in real-time. Dockerized, tested, documented.

---
---

## PHASE 2 — Memory, Hybrid Retrieval & Resilience (Weeks 3-6)

**Phase Goal:** Production-grade system with hybrid retrieval, persistent sessions, Celery-based parallelism, resilience patterns, authentication, and free-tier deployment.

**Phase Deliverable:** Deployed production system at $0/month with 5+ concurrent user support.

---

### Sprint 3 — Hybrid Retrieval + BM25 (Week 3)

#### Goal 2.1: BM25 Sparse Retrieval Implementation

**Owner:** Backend Engineer | **Files:** `retrieval/bm25.py` | **Duration:** 2 days

- [x] **CP-2.1.1** Implement `BM25Index` class from scratch (no external dependency):
  - Parameters: `k1=1.5` (term frequency saturation), `b=0.75` (document length normalization)
  - IDF formula: `log((N - df + 0.5) / (df + 0.5) + 1)`
  - BM25 scoring: `Σ IDF(t) * (tf * (k1+1)) / (tf + k1*(1-b+b*dl/avgdl))`
- [x] **CP-2.1.2** Implement `fit()` — build inverted index: term → `list[(doc_idx, term_freq)]`, compute doc lengths + avg doc length
- [x] **CP-2.1.3** Implement `query()` — tokenize query, score each document, return `top_k` ranked results
- [x] **CP-2.1.4** Tokenizer: whitespace + lowercasing + stop word removal (hardcoded English list)
- [x] **CP-2.1.5** Implement `add_documents()` for incremental index updates without full refit
- [x] **CP-2.1.6** Index persistence: pickle the fitted index alongside ChromaDB data
- [x] **CP-2.1.7** Write tests: keyword match ranking, empty query, single-doc corpus, index save/load

**Checkpoint Review:**
- BM25 index builds over chunk corpus
- Queries return ranked results by BM25 score
- Index can be incrementally updated and persisted

---

#### Goal 2.2: Hybrid Retriever with Reciprocal Rank Fusion

**Owner:** Backend Engineer | **Files:** `retrieval/hybrid_retriever.py`, `retrieval/dense.py` | **Duration:** 2 days

- [x] **CP-2.2.1** Extract dense retrieval into `DenseRetriever` class wrapping ChromaDB vector search
- [x] **CP-2.2.2** Implement `HybridRetriever` with RRF fusion:
  - BM25 top-50 → Dense top-50 → `RRF(d) = Σ 1/(k + rank_i(d))` with k=60
  - Return fused top-15
- [x] **CP-2.2.3** Integrate `HybridRetriever` into orchestrator — replace direct ChromaDB query
- [x] **CP-2.2.4** Implement source diversity enforcement: max 3 chunks from same source in top-15
- [x] **CP-2.2.5** Write tests: RRF boosts docs in both rankings, non-overlapping sets, single list degradation, hybrid e2e
- [x] **CP-2.2.6** Benchmark on small golden dataset (10 queries with known relevant docs)

**Checkpoint Review:**
- Hybrid retrieval produces better results than dense-only or sparse-only
- RRF fusion verified by unit tests on known inputs
- Orchestrator uses hybrid retrieval by default

---

#### Goal 2.3: Near-Duplicate Detection

**Owner:** Backend Engineer | **Files:** `retrieval/deduplication.py` | **Duration:** 1 day

- [x] **CP-2.3.1** Implement `MinHashDeduplicator` using `datasketch`:
  - 128 permutations, threshold 0.8 Jaccard similarity
  - Tokenize into 3-grams (shingles)
- [x] **CP-2.3.2** Authority-based duplicate selection: ArXiv > Wikipedia > HackerNews > Reddit > DuckDuckGo
- [x] **CP-2.3.3** Integrate into `IngestionPipeline`: deduplicate after extraction, before embedding
- [x] **CP-2.3.4** Write tests: identical docs detected, rephrased docs detected, different docs not flagged, authority selection

**Checkpoint Review:**
- Deduplication runs in <100ms for 100 documents
- Reduces embedding API calls by 15-30% on typical queries

---

### Sprint 3 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Hybrid retrieval integrated | Orchestrator uses BM25 + Dense + RRF |
| Retrieval quality measured | Benchmark results logged |
| Deduplication active | 15-30% embedding call reduction |

---

### Sprint 4 — Celery + Redis Infrastructure (Week 4)

#### Goal 2.4: Celery Workers + Task Definitions

**Owner:** Backend Lead | **Files:** `workers/celery_app.py`, `workers/tasks.py`, `workers/callbacks.py` | **Duration:** 2 days

- [x] **CP-2.4.1** Add dependencies: `celery[redis]`, `redis`
- [x] **CP-2.4.2** Configure Celery in `celery_app.py`:
  - JSON serialization, UTC timezone
  - Soft time limit: 15s, hard time limit: 20s
  - Late ack, prefetch multiplier 1
  - Task routes: `search_source` → `search` queue, `process_results` → `ingestion` queue
- [x] **CP-2.4.3** Implement `search_source` task: search a single source with all sub-queries, max 2 retries
- [x] **CP-2.4.4** Implement `process_results` chord callback: dedup → chunk → embed → ChromaDB upsert
- [x] **CP-2.4.5** Replace `asyncio.gather` in orchestrator with Celery `chord(group(...))(callback)`
- [x] **CP-2.4.6** Add `worker` + `redis` services to `docker-compose.yml`
- [x] **CP-2.4.7** Write tests in eager mode (`CELERY_ALWAYS_EAGER=True`): task execution, chord completion, retry, timeout

**Checkpoint Review:**
- Source searches execute as Celery tasks on worker processes
- Chord callback aggregates all source results
- Worker is a separate Docker service
- Tasks respect timeout and retry limits

---

#### Goal 2.5: Redis Caching Layer

**Owner:** Backend Engineer | **Files:** `backend/app/cache/redis_cache.py`, `backend/app/cache/embedding_cache.py` | **Duration:** 2 days

- [x] **CP-2.5.1** Implement `ResearchCache` with two-tier caching:
  - Tier 1: query hash → full synthesized result (TTL: 24h)
  - Tier 2: source + query hash → raw source results (TTL: 6h)
- [x] **CP-2.5.2** Implement stale-while-revalidate logic:
  - Fresh hit (TTL > 20h) → return immediately
  - Stale hit (TTL ≤ 20h) → return stale + trigger background Celery refresh
  - Cache miss → full pipeline
- [x] **CP-2.5.3** Implement `hash_query()`: normalize (lowercase, strip, remove punctuation) → SHA-256
- [x] **CP-2.5.4** Implement `EmbeddingCache`: in-memory LRU (max 10K entries) via `cachetools.LRUCache`
- [x] **CP-2.5.5** Integrate caching into orchestrator: check cache before pipeline, store after completion
- [x] **CP-2.5.6** Write tests: fresh hit, stale hit + refresh trigger, miss, key normalization, embedding cache hit rate

**Checkpoint Review:**
- Repeat queries return in <300ms (cache hit)
- Stale results served immediately while background refresh runs
- Embedding cache reduces API calls by 30%+ on related queries

---

#### Goal 2.6: Circuit Breaker + Rate Limiter + Retry

**Owner:** Backend Engineer | **Files:** `resilience/circuit_breaker.py`, `resilience/rate_limiter.py`, `resilience/retry.py` | **Duration:** 2 days

- [x] **CP-2.6.1** Implement `CircuitBreaker` (Redis-backed state machine):
  - States: CLOSED → OPEN (5 failures in 60s) → HALF_OPEN (after 30s cooldown) → CLOSED (test succeeds)
  - Redis keys: `cb:{source}:state`, `cb:{source}:failures`, `cb:{source}:last_fail`, `cb:{source}:opened_at`
  - Async context manager (`async with circuit_breaker:`)
- [x] **CP-2.6.2** Implement `TokenBucketRateLimiter` (Redis-backed):
  - Per-source limits: DDG 1/sec burst 5, Reddit 0.5/sec burst 3, HN 2/sec burst 10, ArXiv 0.33/sec burst 3, Wikipedia 5/sec burst 20
  - `acquire()` method with timeout
- [x] **CP-2.6.3** Implement `with_retry` decorator:
  - Exponential backoff: `backoff_base * 2^attempt` (1s, 2s, 4s...)
  - Jitter: +-20% to avoid thundering herd
  - Max 2 retries by default
- [x] **CP-2.6.4** Integrate all three into Celery source search tasks: `async with circuit_breaker: await rate_limiter.acquire(); adapter.search()`
- [x] **CP-2.6.5** Write tests: CB opens after N failures, CB half-open transition, CB recovery, rate limiter blocking/refill, retry backoff timing, retry gives up

**Checkpoint Review:**
- One source failing does not affect other sources
- Circuit breaker prevents hammering a down source
- Rate limiter respects per-source limits
- All state in Redis (shared across workers)

---

### Sprint 4 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Celery fan-out working | 5 parallel source workers |
| Cache hit latency | <300ms |
| Circuit breaker tested | Open/half-open/closed transitions |
| Rate limiting enforced | Per-source token bucket |

---

### Sprint 5 — Sessions + Additional Sources (Week 5)

#### Goal 2.7: PostgreSQL Schema + Session Persistence

**Owner:** Backend Lead | **Files:** `db/models.py`, `db/session.py`, `api/routes/sessions.py` | **Duration:** 2 days

- [x] **CP-2.7.1** Add dependencies: `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
- [x] **CP-2.7.2** Define SQLAlchemy models: `User`, `ResearchSession`, `ResearchTurn`, `SourceCache`
  - All models include `created_at` and `updated_at` timestamps
  - UUIDs for user-facing IDs
  - Foreign keys and proper indexes
- [x] **CP-2.7.3** Set up Alembic: `alembic init migrations`, configure async engine, generate initial migration
- [x] **CP-2.7.4** Implement async session management: `get_db()` dependency with `async_sessionmaker`
- [x] **CP-2.7.5** Implement session CRUD endpoints:
  - `GET /api/v1/sessions` — list (paginated, sorted by `updated_at`)
  - `GET /api/v1/sessions/{id}` — get with all turns
  - `PATCH /api/v1/sessions/{id}` — rename
  - `DELETE /api/v1/sessions/{id}` — soft-delete (status=archived)
- [x] **CP-2.7.6** Update orchestrator to persist: create `ResearchSession` on first query, create `ResearchTurn` per query
- [x] **CP-2.7.7** Write tests: session create/retrieve/list/archive, turn creation and ordering, pagination

**Checkpoint Review:**
- Research sessions persisted to PostgreSQL (Supabase)
- Sessions listed, viewed, and archived via API
- Each turn stores query, answer, citations, and performance metrics

---

#### Goal 2.8: Follow-up Questions + Context Compression

**Owner:** Backend Lead | **Files:** `core/context_manager.py`, `api/routes/research.py` (update) | **Duration:** 2 days

- [x] **CP-2.8.1** Implement `ContextManager`:
  - `build_context(session_id)` — load all turns for a session
  - If total turns fit in 4096 token budget → return full context
  - Else → compress older turns via LLM summary, keep last 2 turns full
  - Summary preserves: key findings, citations, contradictions, preferences
  - Cache compressed context in the turn record
- [x] **CP-2.8.2** Implement follow-up endpoint: `POST /api/v1/research/{session_id}/followup`
  - Augment follow-up query with session context
  - Store new chunks in same session's ChromaDB collection
  - Retrieve from session's full chunk corpus
- [x] **CP-2.8.3** Write tests: context building with 1/5/10 turns, compression triggers, follow-up retrieves from full corpus

**Checkpoint Review:**
- Users can ask follow-up questions within a session
- Context maintained across follow-ups
- Long sessions don't overflow the LLM context window

---

#### Goal 2.9: Reddit + ArXiv Source Adapters

**Owner:** Backend Engineer | **Files:** `sources/reddit.py`, `sources/arxiv.py` | **Duration:** 2 days

- [x] **CP-2.9.1** Implement `RedditAdapter`:
  - Reddit JSON API (append `.json`), User-Agent header required
  - Target subreddits: r/programming, r/devops, r/machinelearning, r/Python, r/ExperiencedDevs
  - Extract: post title, selftext, top 5 comments by score
  - Rate limit: 1 request per 2 seconds
- [x] **CP-2.9.2** Implement `ArXivAdapter`:
  - ArXiv API via `feedparser` for Atom XML parsing
  - Extract: title, authors, abstract, published date, PDF URL
  - Abstract as raw_content (full paper text is Phase 3+)
  - Rate limit: 1 request per 3 seconds
- [x] **CP-2.9.3** Register both in `SourceRegistry`
- [x] **CP-2.9.4** Write tests per adapter: valid response, empty results, timeout, rate limit, malformed response

**Checkpoint Review:**
- Reddit and ArXiv searchable as sources
- Both respect rate limits
- Research queries now search 5 sources in parallel

---

### Sprint 5 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Sessions persisted | PostgreSQL via Supabase |
| Follow-up working | Context-aware within session |
| 5 source adapters | DDG + Wikipedia + HN + Reddit + ArXiv |
| Alembic migrations | Running against Supabase |

---

### Sprint 6 — Auth, CI/CD, Deployment (Week 6)

#### Goal 2.10: Supabase Authentication

**Owner:** Backend Engineer | **Files:** `api/dependencies.py` | **Duration:** 2 days

- [ ] **CP-2.10.1** Implement JWT verification dependency `get_current_user()`:
  - Verify Supabase JWT token from `Authorization: Bearer` header
  - Decode with `settings.supabase_jwt_secret`, algorithm HS256
  - Get or create user in local DB from `sub` claim
- [ ] **CP-2.10.2** Protect endpoints: `/research`, `/sessions`, `/knowledge` require auth
- [ ] **CP-2.10.3** Implement anonymous mode: allow unauthenticated research with ephemeral sessions (no persistence)
- [ ] **CP-2.10.4** Write tests: valid/invalid/expired token handling

**Checkpoint Review:**
- Authenticated users have persistent sessions
- Anonymous users can still research (ephemeral)

---

#### Goal 2.11: CI/CD Pipeline

**Owner:** DevOps | **Files:** `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `.pre-commit-config.yaml` | **Duration:** 1 day

- [ ] **CP-2.11.1** Create `ci.yml` (on PR to `main`):
  - Lint: `ruff check`, `ruff format --check`, `mypy`
  - Test: `pytest -v --cov=app --cov-fail-under=85` (with Redis service container)
- [ ] **CP-2.11.2** Create `deploy.yml` (on push to `main`):
  - Trigger Render deploy hook (webhook URL)
- [ ] **CP-2.11.3** Add pre-commit config: ruff + mypy + fast pytest
- [ ] **CP-2.11.4** Branch protection on `main`: require CI pass + 1 review

**Checkpoint Review:**
- PRs blocked if tests fail or coverage drops below 85%
- Merges to `main` auto-deploy

---

#### Goal 2.12: Free-Tier Deployment

**Owner:** DevOps + Backend Lead | **Duration:** 2 days

- [ ] **CP-2.12.1** **Render:** Web Service for backend (Docker, free tier) + Background Worker for Celery
  - Set env vars: `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `UPSTASH_REDIS_URL`
  - Health check: `/api/v1/health`
  - UptimeRobot ping every 14 min (free tier sleeps after 15 min)
- [ ] **CP-2.12.2** **Supabase:** Create project, run Alembic migration, enable email auth + GitHub OAuth
- [ ] **CP-2.12.3** **Upstash:** Create Redis database (free tier: 10K commands/day), verify Celery broker connection
- [ ] **CP-2.12.4** **Monitoring:** Better Stack or UptimeRobot for uptime, structured logging with `structlog`
- [ ] **CP-2.12.5** **Smoke test checklist:**
  - [ ] Backend health endpoint responds from Render URL
  - [ ] Full research query works end-to-end in production
  - [ ] Auth flow works (sign up, sign in, session persistence)
  - [ ] Follow-up question works within a session
  - [ ] Sessions list shows after auth

**Checkpoint Review:**
- Full stack accessible at public URLs
- End-to-end research works in production
- Total monthly cost: $0.00

---

### PHASE 2 EXIT GATE

| # | Criteria | Status |
|---|----------|--------|
| 1 | All 12 goals completed and merged to `main` | [ ] |
| 2 | 85%+ test coverage | [ ] |
| 3 | Deployed at public URLs, total cost $0/month | [ ] |
| 4 | Circuit breakers, rate limiting, caching operational | [ ] |
| 5 | 5+ concurrent users without degradation | [ ] |
| 6 | Stale-while-revalidate cache hit <300ms | [ ] |
| 7 | Hybrid retrieval (BM25 + Dense + RRF) active | [ ] |
| 8 | 5 source adapters all functional | [ ] |
| 9 | Follow-up questions with context compression | [ ] |

**Phase 2 Deliverable:** Production-grade research engine with hybrid retrieval, Celery parallelism, resilience patterns, persistent sessions, auth, and deployed to free-tier infrastructure.

---
---

## PHASE 3 — Knowledge Graph & Intelligence (Weeks 7-10)

**Phase Goal:** Persistent knowledge graph with entity extraction, cross-session intelligence, custom source plugins, export, scheduling, and collaboration.

**Phase Deliverable:** Full knowledge operating system — research, remember, connect, share, export, schedule.

---

### Sprint 7 — Entity Extraction + KG Foundation (Week 7)

#### Goal 3.1: LLM-Based Entity Extraction

**Owner:** Backend Engineer | **Files:** `knowledge/entities.py` | **Duration:** 3 days

- [ ] **CP-3.1.1** Implement `EntityExtractor` using Groq LLM:
  - Entity types: technology, concept, organization, person, protocol, algorithm, library, service, pattern
  - Relationship types: compared_with, depends_on, implements, alternative_to, part_of, used_by, supersedes, extends, conflicts_with
  - Output: JSON with `entities[]` and `relationships[]` arrays
- [ ] **CP-3.1.2** Define `Entity` and `Relationship` Pydantic models with all fields
- [ ] **CP-3.1.3** Entity normalization pipeline:
  - Lowercase all names
  - Resolve aliases ("Apache Kafka" → "kafka", "K8s" → "kubernetes")
  - Merge duplicates across sessions
  - Increment `mention_count` on re-encounter
- [ ] **CP-3.1.4** Integrate into orchestrator: run entity extraction on every synthesized answer
- [ ] **CP-3.1.5** Write tests: extraction from sample answer, alias resolution, deduplication, malformed LLM JSON

**Checkpoint Review:**
- Entities and relationships extracted from every research synthesis
- Entity normalization prevents duplicates
- Extraction adds <500ms to the research pipeline

---

#### Goal 3.2: Knowledge Graph Storage (PostgreSQL)

**Owner:** Backend Engineer | **Files:** `knowledge/graph.py`, `db/models.py` (extend) | **Duration:** 2 days

- [ ] **CP-3.2.1** Add SQLAlchemy models: `KnowledgeEntity` (with unique constraint on user_id + name), `KnowledgeRelationship`
- [ ] **CP-3.2.2** Generate Alembic migration for new tables
- [ ] **CP-3.2.3** Implement `KnowledgeGraph` service:
  - `add_entities()` — upsert (create or increment mention_count + update last_seen)
  - `add_relationships()` — resolve entity names to IDs, insert
  - `get_entity_graph()` — entity + 1-hop connections
  - `get_session_graph()` — all entities/relationships from a session
  - `get_full_graph()` — user's complete knowledge graph
  - `search_entities()` — full-text search on names, aliases, descriptions
- [ ] **CP-3.2.4** Integrate graph updates into orchestrator post-synthesis
- [ ] **CP-3.2.5** Write tests: CRUD operations, deduplication, graph traversal queries

**Checkpoint Review:**
- Entities and relationships stored in PostgreSQL
- Graph queries return connected entities within <200ms
- Knowledge graph grows with each research session

---

### Sprint 7 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Entity extraction active | Running after every synthesis |
| KG persisted | Entities + relationships in PostgreSQL |
| Normalization working | Aliases resolved, duplicates merged |

---

### Sprint 8 — Knowledge Recall + Graph Endpoints (Week 8)

#### Goal 3.3: Cross-Session Knowledge Recall

**Owner:** Backend Lead | **Files:** `knowledge/memory.py`, `api/routes/knowledge.py` | **Duration:** 3 days

- [ ] **CP-3.3.1** Implement `KnowledgeMemory` service:
  - `recall(user_id, query)` — embed query → search ALL user's session collections in ChromaDB → search KG entities → combine with graph-connected chunk boost → apply temporal weighting
  - `find_connections(user_id, entity_a, entity_b)` — graph shortest-path between entities
  - `get_timeline(user_id, entity)` — chronological view of research on an entity
- [ ] **CP-3.3.2** Implement temporal weighting: `score *= exp(-0.01 * days_since_research)`, override with `?recency=off`
- [ ] **CP-3.3.3** Implement API endpoints:
  - `GET /api/v1/knowledge/search?q={query}&limit=10` — search persistent knowledge base
  - `GET /api/v1/knowledge/recall?q={query}&limit=10&recency=on` — cross-session recall
  - `GET /api/v1/sessions/{id}/graph` — knowledge graph for a session
- [ ] **CP-3.3.4** Write tests: recall finds past session chunks, temporal weighting boosts recent, connection path finding

**Checkpoint Review:**
- "What did I research about X?" returns relevant findings from past sessions
- Cross-session connections discoverable
- Recall queries respond in <2 seconds

---

#### Goal 3.4: Graph Data API Endpoints

**Owner:** Backend Engineer | **Duration:** 2 days

- [ ] **CP-3.4.1** `GET /api/v1/sessions/{id}/graph` — session knowledge graph (nodes + edges)
- [ ] **CP-3.4.2** `GET /api/v1/knowledge/graph` — full user knowledge graph
- [ ] **CP-3.4.3** `GET /api/v1/knowledge/entities/{name}` — entity detail + neighborhood

**Checkpoint Review:**
- Graph endpoints return properly structured node/edge JSON
- Responses under 500ms for graphs with up to 200 entities

---

### Sprint 8 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Recall working | Cross-session search <2s |
| Graph API | Session + full graph endpoints |
| Temporal weighting | Recent research ranked higher |

---

### Sprint 9 — Plugins + Export (Week 9)

#### Goal 3.5: Custom Source Plugin Interface

**Owner:** Backend Engineer | **Files:** `sources/base.py` (extend), `sources/registry.py` (extend) | **Duration:** 2 days

- [ ] **CP-3.5.1** Define `SourcePlugin` class extending `SourceAdapter` with `from_config()` factory
- [ ] **CP-3.5.2** Define plugin `config.yaml` schema: name, display_name, description, base_url, rate_limit, auth
- [ ] **CP-3.5.3** Implement plugin auto-discovery: scan `plugins/` directory on startup, register valid plugins
- [ ] **CP-3.5.4** API endpoint: `GET /api/v1/sources` lists all available sources (built-in + plugins)
- [ ] **CP-3.5.5** Write documentation: "Creating a Custom Source Plugin" guide with Stack Overflow example

**Checkpoint Review:**
- New sources added by dropping a plugin folder — no core code changes
- Plugins auto-discovered and registered on startup

---

#### Goal 3.6: Export System

**Owner:** Backend Engineer | **Files:** `api/routes/export.py` | **Duration:** 2 days

- [ ] **CP-3.6.1** Implement Markdown export: session as structured `.md` with queries, answers, citations
- [ ] **CP-3.6.2** Implement JSON export: raw data export of session + turns + citations
- [ ] **CP-3.6.3** Implement Obsidian vault export:
  - Each entity = a note (`.md`), relationships = `[[wikilinks]]`, sessions = notes with backlinks
  - Return as ZIP file
- [ ] **CP-3.6.4** API endpoints:
  - `GET /api/v1/sessions/{id}/export?format=markdown`
  - `GET /api/v1/knowledge/export?format=obsidian` (ZIP)
- [ ] **CP-3.6.5** Write tests: each format produces valid output, Obsidian vault opens correctly

**Checkpoint Review:**
- Sessions exportable as Markdown, JSON, and Obsidian format
- Full knowledge graph exportable as Obsidian vault (ZIP)

---

### Sprint 9 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Plugin system working | Auto-discovery + registration |
| Export working | Markdown + JSON + Obsidian |
| Sources API | Lists built-in + plugin sources |

---

### Sprint 10 — Scheduling + Analytics + Collaboration (Week 10)

#### Goal 3.7: Scheduled Research (Daily Briefings)

**Owner:** Backend Engineer | **Files:** `workers/scheduled.py`, `db/models.py` (extend) | **Duration:** 2 days

- [ ] **CP-3.7.1** Add `ResearchSchedule` model: `query_template`, `topics`, `frequency` (daily/weekly), `sources`, `is_active`, `last_run`
- [ ] **CP-3.7.2** Implement Celery Beat schedule: `run_scheduled_research` at 7 AM UTC daily
- [ ] **CP-3.7.3** Scheduled task: for each active schedule, run research pipeline, store as tagged session, compare with previous run
- [ ] **CP-3.7.4** API endpoints: `POST /api/v1/schedules`, `GET /api/v1/schedules`, `PATCH /api/v1/schedules/{id}`, `DELETE /api/v1/schedules/{id}`
- [ ] **CP-3.7.5** Write tests: schedule creation, Celery Beat trigger, result storage

**Checkpoint Review:**
- Users can create daily/weekly research schedules
- Celery Beat triggers at configured times
- Results stored as viewable research sessions

---

#### Goal 3.8: Analytics Endpoint

**Owner:** Backend Lead | **Files:** `api/routes/analytics.py` | **Duration:** 1 day

- [ ] **CP-3.8.1** Implement `GET /api/v1/analytics` returning:
  - `total_sessions`, `total_queries`, `total_entities`
  - `knowledge_graph_stats`: nodes, edges
  - `source_performance`: avg latency, success rate per source
  - `cache_stats`: hit rate, avg hit/miss latency
  - `research_by_week`: query counts over time
  - `top_entities`: most-mentioned entities
- [ ] **CP-3.8.2** Write tests: analytics response structure validation

**Checkpoint Review:**
- Analytics endpoint returns meaningful data within <2s

---

#### Goal 3.9: Collaborative Sessions

**Owner:** Backend Engineer | **Duration:** 2 days

- [ ] **CP-3.9.1** Add `session_collaborators` join table: `user_id`, `session_id`, `role` ("viewer" | "editor")
- [ ] **CP-3.9.2** `POST /api/v1/sessions/{id}/share` — generate shareable link with role
- [ ] **CP-3.9.3** Shared sessions: viewers can read, editors can add follow-up queries
- [ ] **CP-3.9.4** Write tests: share creation, viewer access, editor access, unauthorized access blocked

**Checkpoint Review:**
- Users can share research sessions via link
- Role-based access (viewer/editor) enforced

---

### PHASE 3 EXIT GATE

| # | Criteria | Status |
|---|----------|--------|
| 1 | All 9 goals completed and merged to `main` | [ ] |
| 2 | Knowledge graph stores entities/relationships, grows per session | [ ] |
| 3 | Recall queries work across sessions (<2s response) | [ ] |
| 4 | Export to Markdown/JSON/Obsidian works | [ ] |
| 5 | Scheduled research runs via Celery Beat | [ ] |
| 6 | Analytics endpoint operational | [ ] |
| 7 | Collaborative sessions with role-based access | [ ] |
| 8 | Plugin system auto-discovers custom sources | [ ] |

**Phase 3 Deliverable:** Full knowledge operating system — research, remember, connect, share, export, schedule.

---
---

## PHASE 4 — Agentic Intelligence (Weeks 11-14)

**Phase Goal:** Transform fixed orchestration into autonomous agent architecture with reasoning, self-evaluation, multi-agent collaboration, and proactive intelligence.

**Phase Deliverable:** Autonomous, multi-agent research system with self-evaluation, dynamic tool use, reasoning transparency, and proactive intelligence.

**Prerequisite:** Phase 3 complete. Agent architecture builds on knowledge graph, entity extraction, and full source/retrieval/resilience stack.

---

### Sprint 11 — ReAct Agent Core (Week 11)

#### Goal 4.1: Agent State Machine + ReAct Loop

**Owner:** Backend Lead | **Files:** `agents/base.py`, `agents/state.py`, `agents/react_loop.py` | **Duration:** 3 days

- [ ] **CP-4.1.1** Define `AgentState` model:
  - Fields: `session_id`, `original_query`, `current_plan`, `completed_steps`, `gathered_knowledge`, `sub_queries_generated`, `sources_searched`, `verification_results`, `iteration`, `max_iterations` (default 8), `confidence`, `status`
  - Status enum: thinking, searching, verifying, synthesizing, complete, stuck
- [ ] **CP-4.1.2** Define `AgentStep` and `CompletedStep` models
- [ ] **CP-4.1.3** Implement `ReActLoop` — Reason → Act → Observe → Evaluate loop:
  - Each iteration: LLM reasons about current state → selects next action → executes → evaluates
  - Yields `AgentEvent`s (thinking, action_complete, token) for SSE streaming
  - Available actions: decompose, search, refine, verify, expand, recall, synthesize
- [ ] **CP-4.1.4** Agent reasoning prompt: includes available actions, current state summary, iteration budget
- [ ] **CP-4.1.5** Iteration budget: agent MUST synthesize by `max_iterations` even if confidence is low (graceful degradation)
- [ ] **CP-4.1.6** Write tests: simple query in 2-3 iterations, refine on poor results, max_iterations respected, state serialization

**Checkpoint Review:**
- Agent autonomously decides research strategy
- Agent terminates within iteration budget
- Each action uses real existing infrastructure

---

#### Goal 4.2: Agent Tool Registry

**Owner:** Backend Engineer | **Files:** `agents/tools.py` | **Duration:** 2 days

- [ ] **CP-4.2.1** Implement `AgentToolRegistry`: register, get, get_tool_descriptions
- [ ] **CP-4.2.2** Implement `SearchTool`: wraps source adapter fan-out, agent specifies sources + queries
- [ ] **CP-4.2.3** Implement `RefineTool`: agent rewrites failed query, runs against same sources
- [ ] **CP-4.2.4** Implement `VerifyTool`: cross-checks specific claim against primary sources
- [ ] **CP-4.2.5** Implement `RecallTool`: queries KnowledgeMemory for past research context
- [ ] **CP-4.2.6** Implement `ExpandTool`: researches related topic discovered in results, tags as "agent-expanded"
- [ ] **CP-4.2.7** Every tool execution logged with params, duration, result summary (auditable)
- [ ] **CP-4.2.8** Write tests: each tool with mocked dependencies

**Checkpoint Review:**
- Agent actions map to real tool executions
- Every tool execution is logged and auditable
- Tools reuse existing source/retrieval/knowledge infrastructure

---

#### Goal 4.3: Self-Evaluation + Confidence Scoring

**Owner:** Backend Engineer | **Files:** `agents/evaluator.py` | **Duration:** 2 days

- [ ] **CP-4.3.1** Implement `AgentEvaluator`:
  - **Confidence increases:** multiple sources agree, source diversity, quantitative data, past knowledge confirms
  - **Confidence decreases:** contradictions, single source type, results don't address query, <3 unique queries
- [ ] **CP-4.3.2** Evaluation via lightweight LLM call (low temperature) assessing knowledge quality
- [ ] **CP-4.3.3** Thresholds: >0.75 → synthesize, 0.4-0.75 → continue, <0.4 at max iterations → synthesize with "insufficient research" disclaimer
- [ ] **CP-4.3.4** Write tests: high confidence when sources agree, low confidence on contradictions, confidence increases across iterations

**Checkpoint Review:**
- Agent self-evaluates after each iteration
- Confidence scoring drives continue/synthesize decision
- Low-confidence synthesis includes honest disclaimers

---

### Sprint 11 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| ReAct loop functional | Autonomous multi-step research |
| Tool registry | 5 tools wrapping existing infra |
| Self-evaluation | Confidence scoring drives decisions |
| Simple query | Completes in <10s, ≤3 iterations |

---

### Sprint 12 — Multi-Agent Architecture (Week 12)

#### Goal 4.4: Specialist Agents + Coordinator

**Owner:** Backend Lead | **Files:** `agents/specialists/academic.py`, `agents/specialists/practitioner.py`, `agents/specialists/factcheck.py`, `agents/coordinator.py` | **Duration:** 3 days

- [ ] **CP-4.4.1** Implement `AcademicAgent`:
  - Preferred sources: ArXiv, Wikipedia
  - Emphasis: rigor, methodology, peer-reviewed evidence
  - Extracts: methodology, quantitative results, theoretical frameworks
- [ ] **CP-4.4.2** Implement `PractitionerAgent`:
  - Preferred sources: Reddit, HN, DuckDuckGo
  - Emphasis: practical experience, operational reality, war stories
  - Extracts: real-world pain points, scale context, production lessons
- [ ] **CP-4.4.3** Implement `FactCheckAgent`:
  - Any source allowed
  - Emphasis: verification, primary sources, bias identification
  - Cross-references claims from other agents
- [ ] **CP-4.4.4** Implement `ResearchCoordinator`:
  - Analyze query complexity → decide single-agent vs multi-agent
  - Decision criteria: comparison queries → multi-agent, simple factual → single, theory → academic only, implementation → practitioner only
  - Parallel specialist dispatch via Celery tasks
  - Collect results, run fact-check, synthesize with multi-perspective awareness
- [ ] **CP-4.4.5** Define `AgentFindings` structured output model: `key_claims`, `confidence`, `sources_used`, `contradictions_found`, `gaps_identified`
- [ ] **CP-4.4.6** Write tests: coordinator dispatches correct agents, multi-agent merge, timeout handling, graceful degradation

**Checkpoint Review:**
- Complex queries dispatch multiple specialist agents in parallel
- Fact-check agent verifies claims from other agents
- Simple queries still use fast single-agent path
- Final synthesis attributes findings to specific agent perspectives

---

#### Goal 4.5: Agent Trace + Reasoning Transparency

**Owner:** Backend Engineer | **Files:** `agents/trace.py` | **Duration:** 2 days

- [ ] **CP-4.5.1** Define `AgentTrace` SQLAlchemy model:
  - Fields: `session_id`, `turn_id`, `agent_type`, `iterations` (JSON array of reasoning/action/result per iteration), `total_iterations`, `total_duration_ms`, `final_confidence`, `tools_used`
- [ ] **CP-4.5.2** Generate Alembic migration for `agent_traces` table
- [ ] **CP-4.5.3** Store trace for every agent execution
- [ ] **CP-4.5.4** API endpoint: `GET /api/v1/sessions/{id}/turns/{turn_id}/trace`
- [ ] **CP-4.5.5** SSE events during agent execution: `agent_thinking`, `agent_action`, `agent_action_complete`, `agent_evaluation`
- [ ] **CP-4.5.6** Write tests: trace captures all iterations, trace retrievable via API

**Checkpoint Review:**
- Every agent decision logged with reasoning
- Traces stored in PostgreSQL and queryable via API
- SSE events show agent thought process in real-time

---

### Sprint 12 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Multi-agent working | Academic + Practitioner + FactCheck |
| Coordinator routing | Correct agent selection by query type |
| Agent trace stored | All reasoning steps persisted |
| Complex query | Completes in <30s |

---

### Sprint 13 — Proactive Intelligence (Week 13)

#### Goal 4.6: Proactive Research Agent

**Owner:** Backend Engineer | **Files:** `agents/proactive.py`, `workers/scheduled.py` (extend) | **Duration:** 3 days

- [ ] **CP-4.6.1** Implement `ProactiveResearchAgent` with `analyze_knowledge_gaps()`:
  - **Knowledge gaps:** entities with few connections → suggest exploration queries
  - **Stale knowledge:** technology entities researched >30 days ago → suggest update queries
  - **Incomplete comparisons:** researched A and B separately, never compared → suggest comparison
  - **Trending related:** HN/Reddit trending topics related to user's interests
- [ ] **CP-4.6.2** Add `Notification` model: `type` (proactive_research, knowledge_update, contradiction_found), `title`, `body`, `suggestion_query`, `is_read`
- [ ] **CP-4.6.3** API endpoints:
  - `GET /api/v1/suggestions` — proactive research suggestions
  - `POST /api/v1/suggestions/{id}/execute` — run suggested research
  - `GET /api/v1/notifications` — user notifications
  - `PATCH /api/v1/notifications/{id}/read` — mark as read
- [ ] **CP-4.6.4** Celery Beat schedule: `analyze_knowledge_gaps` weekly for each active user
- [ ] **CP-4.6.5** Write tests: gap detection, stale detection, incomplete comparison detection

**Checkpoint Review:**
- System proactively identifies knowledge gaps and stale research
- Suggestions actionable with one click
- Background analysis doesn't impact real-time performance

---

#### Goal 4.7: Agent Suggestion Endpoints

**Owner:** Backend Engineer | **Duration:** 2 days

- [ ] **CP-4.7.1** `GET /api/v1/suggestions` — proactive suggestions with reasoning
- [ ] **CP-4.7.2** `POST /api/v1/suggestions/{id}/execute` — run suggested research, tag session as "proactive"
- [ ] **CP-4.7.3** Notification integration — notify user of new suggestions and completed proactive research

**Checkpoint Review:**
- Suggestions endpoint returns actionable items with reasoning
- Executed suggestions create tagged research sessions

---

### Sprint 13 Milestone Checkpoint

| Criteria | Target |
|----------|--------|
| Proactive analysis | Weekly gap/stale/comparison detection |
| Notifications | Created and retrievable |
| Suggestion execution | One-click research from suggestion |

---

### Sprint 14 — Testing + Documentation (Week 14)

#### Goal 4.8: Comprehensive Agent Test Suite

**Owner:** Entire team | **Duration:** 2 days

- [ ] **CP-4.8.1** Agent-specific tests (13+ minimum):
  | Test | Validates |
  |------|----------|
  | `test_react_loop_simple_query` | Completes in ≤3 iterations |
  | `test_react_loop_complex_query` | Uses 4-6 iterations, multiple sources |
  | `test_react_loop_refines_on_poor_results` | Rewrites query on low-quality results |
  | `test_react_loop_max_iterations` | Synthesizes at budget even if unsatisfied |
  | `test_coordinator_dispatches_multi_agent` | Comparison queries → academic + practitioner |
  | `test_coordinator_simple_single_agent` | Simple queries use single-agent (faster) |
  | `test_factcheck_catches_contradiction` | Conflicting claims detected and verified |
  | `test_evaluator_confidence_increases` | Confidence grows with diverse agreeing sources |
  | `test_evaluator_low_confidence_disclaimer` | Low-confidence synthesis includes caveats |
  | `test_proactive_finds_gaps` | Isolated entities generate suggestions |
  | `test_proactive_finds_stale` | Old technology entities trigger update suggestions |
  | `test_trace_records_all_iterations` | Trace captures every reasoning + action step |
  | `test_agent_reuses_infrastructure` | All tools route through existing components |
- [ ] **CP-4.8.2** Integration tests (mocked LLM, real Celery/Redis/ChromaDB): full multi-agent e2e, trace stored and retrievable
- [ ] **CP-4.8.3** Performance benchmarks:
  - Single-agent simple query: <10s
  - Multi-agent complex query: <30s
  - Proactive analysis for 100 entities: <60s
- [ ] **CP-4.8.4** Achieve 85%+ coverage on agent code

**Checkpoint Review:**
- All agent tests pass
- Performance within benchmark targets

---

#### Goal 4.9: Agent Architecture Documentation

**Owner:** Backend Lead | **Duration:** 2 days

- [ ] **CP-4.9.1** Write `docs/agent-architecture.md`:
  - Design philosophy (why agents over fixed orchestration)
  - ReAct loop explanation with diagrams
  - Multi-agent coordination protocol
  - Tool registry and extension guide
  - Confidence scoring algorithm
  - Proactive intelligence design
- [ ] **CP-4.9.2** Write `docs/adding-agent-tools.md`: step-by-step guide with example (code execution tool)
- [ ] **CP-4.9.3** Update main README with Phase 4 architecture diagram and demo instructions

**Checkpoint Review:**
- Architecture documented for new team member onboarding
- Extension guide enables tool development without core knowledge

---

### PHASE 4 EXIT GATE

| # | Criteria | Status |
|---|----------|--------|
| 1 | All 9 goals completed and merged to `main` | [ ] |
| 2 | Single-agent simple query <10s | [ ] |
| 3 | Multi-agent complex query <30s | [ ] |
| 4 | Agent trace stored, retrievable, and API-accessible | [ ] |
| 5 | Proactive suggestions generated weekly | [ ] |
| 6 | Agent reasoning visible via SSE events | [ ] |
| 7 | 85%+ test coverage on agent code | [ ] |
| 8 | Architecture documentation complete | [ ] |

**Phase 4 Deliverable:** Autonomous, multi-agent research system with self-evaluation, dynamic tool use, reasoning transparency, and proactive intelligence.

---
---

## Quick Reference: All Checkpoints by Phase

### Summary Statistics

| Phase | Duration | Sprints | Goals | Checkpoints | Test Coverage Target |
|-------|----------|---------|-------|-------------|---------------------|
| Phase 1 | 2 weeks | 2 | 9 | ~45 | 70% |
| Phase 2 | 4 weeks | 4 | 12 | ~60 | 85% |
| Phase 3 | 4 weeks | 4 | 9 | ~40 | 85% |
| Phase 4 | 4 weeks | 4 | 9 | ~45 | 85% (agent code) |
| **Total** | **14 weeks** | **14** | **39** | **~190** | **85%+** |

### Critical Path Dependencies

```
Phase 1 (Core)
  └─→ Phase 2 (Production)
       ├─→ Sprint 3 depends on: Phase 1 orchestrator + vector store
       ├─→ Sprint 4 depends on: Sprint 3 retrieval + Phase 1 source adapters
       ├─→ Sprint 5 depends on: Sprint 4 Redis/Celery infrastructure
       └─→ Sprint 6 depends on: Sprint 5 sessions
            └─→ Phase 3 (Knowledge)
                 ├─→ Sprint 7 depends on: Phase 2 sessions + synthesis pipeline
                 ├─→ Sprint 8 depends on: Sprint 7 entity extraction + KG storage
                 ├─→ Sprint 9 depends on: Sprint 7 KG foundation
                 └─→ Sprint 10 depends on: Sprint 8 recall + Sprint 9 export
                      └─→ Phase 4 (Agents)
                           ├─→ Sprint 11 depends on: Phase 3 knowledge graph + recall
                           ├─→ Sprint 12 depends on: Sprint 11 ReAct loop + tools
                           ├─→ Sprint 13 depends on: Sprint 12 multi-agent + Phase 3 KG
                           └─→ Sprint 14 depends on: All Sprint 11-13 components
```

---

## Design Decisions Reference

| Decision | Choice | Why |
|----------|--------|-----|
| **Fan-out** | Celery chord (not `asyncio.gather`) | Worker pool isolation, independent failure domains, doesn't block API event loop |
| **Retrieval** | Hybrid BM25 + Dense + RRF (not just cosine) | Catches exact keyword matches (BM25) AND semantic similarity (dense). Production-grade approach |
| **Caching** | Stale-while-revalidate (not TTL-only) | 10x better P99 latency by serving slightly stale data. Same pattern as CDNs (Cloudflare, Fastly) |
| **Circuit breaker** | Redis-backed per-source (not in-memory) | Shared state across multiple Celery workers. Prevents cascading failures |
| **Context** | Progressive summarization (not truncation) | Preserves key findings while staying within token limits. Avoids "lost in the middle" problem |
| **Citations** | Structurally verified (not LLM-generated) | Pre-assigned IDs in prompt → impossible to hallucinate URLs. Frontend resolves IDs to verified URLs |
| **Vector DB** | ChromaDB embedded (not Pinecone) | $0 cost, runs in-process, no network latency. Scales to ~100K chunks easily |
| **LLM** | Groq free tier (not OpenAI) | 30 req/min free, Llama 3.1 70B. Pluggable to OpenAI/Ollama if needed |
| **BM25** | Custom implementation (not library) | Interview talking point, full understanding, no dependency |
| **Dedup** | MinHash/LSH (not exact hash) | Catches near-duplicates (rephrased content), not just exact copies |

---

*This document is the engineering specification for the Sift backend team. Each goal has clear ownership, file-level scope, numbered checkpoints, and exit criteria. Use the checkpoint IDs (CP-X.Y.Z) in commit messages and PR descriptions to track progress. Update this document as implementation progresses.*
