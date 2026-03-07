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

### Phase 1 — Core Research Engine (2 Weeks)

**Goal:** Working end-to-end research engine — user enters a question, gets a streamed, multi-source, cited answer.

#### Sprint 1 (Days 1-7): Backend Foundation + Source Adapters

| Task | Owner | Files | Duration | Description |
|------|-------|-------|----------|-------------|
| **1.1** Project Scaffolding | Backend Lead | `main.py`, `config.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml` | Day 1 | FastAPI app, CORS, lifespan, health endpoint, Docker setup, `.env.example` |
| **1.2** Source Adapters (×3) | Backend Engineer | `sources/base.py`, `duckduckgo.py`, `wikipedia.py`, `hackernews.py`, `registry.py` | Days 2-3 | Abstract interface, 3 adapter implementations, source registry, mocked tests |
| **1.3** Ingestion Pipeline | Backend Engineer | `ingestion/pipeline.py`, `extractors.py`, `chunker.py`, `embedder.py` | Days 3-4 | HTML extraction, text chunking (512/64), embedding generation (HF API), full pipeline |
| **1.4** ChromaDB Integration | Backend Engineer | `db/vector_store.py` | Day 4 | VectorStore class, upsert, query, metadata filtering, persistence |
| **1.5** Query Analyzer + Synthesizer | Backend Lead | `core/query_analyzer.py`, `core/synthesizer.py` | Days 4-5 | LLM decomposition, streaming synthesis with citations, Groq integration |
| **1.6** Research Orchestrator | Backend Lead | `core/orchestrator.py`, `api/routes/research.py` | Days 5-6 | Full pipeline orchestration, SSE endpoint, request/response models |

**Acceptance Criteria:**
- `docker compose up` starts backend on port 8000
- `POST /api/v1/research` streams SSE events through full pipeline
- Partial source failures don't crash the pipeline
- Complete event includes `session_id` and citations

#### Sprint 2 (Days 8-14): Docker + Testing + Documentation

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **1.8** Docker Compose Full Stack | Backend Lead | Day 11 | Production + dev docker-compose, Makefile (dev, prod, test, lint) |
| **1.9** Core Test Suite | Entire team | Days 12-13 | `conftest.py`, fixtures, 50+ tests across all modules, 70%+ coverage |
| **1.10** Documentation | Backend Lead | Day 14 | QUICKSTART.md, demo queries, verify clean-clone setup |

**Exit Criteria:**
- [ ] All 10 tasks completed and merged to `main`
- [ ] 70%+ test coverage
- [ ] Docker Compose starts cleanly from a fresh clone
- [ ] 10 demo queries produce quality answers

---

### Phase 2 — Memory, Hybrid Retrieval & Resilience (4 Weeks)

**Goal:** Production-grade system with hybrid retrieval, persistent sessions, Celery parallelism, resilience, auth, and deployment.

#### Sprint 3 (Week 3): Hybrid Retrieval + BM25

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **2.1** BM25 Implementation | Backend Engineer | 2 days | Custom BM25 from scratch, inverted index, incremental update, persistence |
| **2.2** Hybrid Retriever + RRF | Backend Engineer | 2 days | Dense retriever extraction, RRF fusion, integration into orchestrator |
| **2.3** Near-Duplicate Detection | Backend Engineer | 1 day | MinHash/LSH via `datasketch`, authority-based selection, <100ms for 100 docs |

#### Sprint 4 (Week 4): Celery + Redis Infrastructure

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **2.4** Celery Workers + Tasks | Backend Lead | 2 days | Celery config, search/process tasks, chord fan-out, Docker worker service |
| **2.5** Redis Caching Layer | Backend Engineer | 2 days | Two-tier cache, stale-while-revalidate, embedding LRU cache |
| **2.6** Circuit Breaker + Rate Limiter | Backend Engineer | 2 days | Redis-backed circuit breaker, token bucket rate limiter, retry decorator |

#### Sprint 5 (Week 5): Sessions + Additional Sources

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **2.7** PostgreSQL + Sessions | Backend Lead | 2 days | SQLAlchemy models, Alembic migrations, session CRUD endpoints, Supabase |
| **2.8** Follow-ups + Context Compression | Backend Lead | 2 days | Context manager, progressive summarization, follow-up endpoint |
| **2.9** Reddit + ArXiv Adapters | Backend Engineer | 2 days | Reddit JSON API, ArXiv Atom XML, both with rate limits |

#### Sprint 6 (Week 6): Auth, CI/CD, Deployment

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **2.10** Supabase Auth | Backend Engineer | 2 days | JWT verification, protected endpoints, anonymous mode |
| **2.11** CI/CD Pipeline | DevOps | 1 day | GitHub Actions: lint+test on PR, auto-deploy on main push |
| **2.12** Free-Tier Deployment | DevOps + Backend Lead | 2 days | Render, Supabase, Upstash, UptimeRobot, smoke tests |

**Exit Criteria:**
- [ ] 85%+ test coverage
- [ ] Deployed at public URLs, total cost $0/month
- [ ] Circuit breakers, rate limiting, caching operational
- [ ] 5+ concurrent users without degradation
- [ ] Cache hit <300ms

---

### Phase 3 — Knowledge Graph & Intelligence (4 Weeks)

**Goal:** Persistent knowledge graph, cross-session recall, visualization, plugins, export, scheduling.

#### Sprint 7 (Week 7): Entity Extraction + KG Foundation

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **3.1** Entity Extraction | Backend Engineer | 3 days | LLM-based extraction, entity normalization, alias resolution, deduplication |
| **3.2** KG Storage (PostgreSQL) | Backend Engineer | 2 days | Entity + relationship tables, KnowledgeGraph service, graph queries |

#### Sprint 8 (Week 8): Recall + Graph Visualization

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **3.3** Cross-Session Recall | Backend Lead | 3 days | KnowledgeMemory service, recall endpoint, temporal weighting, connection paths |

#### Sprint 9 (Week 9): Plugins + Export

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **3.5** Custom Source Plugins | Backend Engineer | 2 days | Plugin spec, config.yaml schema, auto-discovery, `GET /api/v1/sources` |
| **3.6** Export System | Backend Engineer | 2 days | Markdown, JSON, Obsidian vault export. Session + full knowledge export |

#### Sprint 10 (Week 10): Scheduling + Analytics

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **3.7** Scheduled Research | Backend Engineer | 2 days | Celery Beat, ResearchSchedule model, daily briefings, schedule CRUD API |
| **3.8** Analytics Endpoint | Backend Lead | 1 day | `/api/v1/analytics` returning sessions, queries, entities, source perf, cache stats |
| **3.9** Collaborative Sessions | Backend Engineer | 2 days | `session_collaborators` table, share endpoint, role-based access |

**Exit Criteria:**
- [ ] Knowledge graph stores entities/relationships and grows per session
- [ ] Recall queries work across sessions (<2s response)
- [ ] Export to Markdown/Obsidian works
- [ ] Scheduled research runs via Celery Beat
- [ ] Analytics endpoint operational

---

### Phase 4 — Agentic Intelligence (4 Weeks)

**Goal:** Transform fixed orchestration into autonomous agent architecture with reasoning, self-evaluation, multi-agent collaboration, and proactive intelligence.

**Prerequisite:** Phase 3 complete.

#### Sprint 11 (Week 11): ReAct Agent Core

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **4.1** Agent State + ReAct Loop | Backend Lead | 3 days | AgentState model, ReAct loop (reason→act→observe), iteration budget, SSE events |
| **4.2** Agent Tool Registry | Backend Engineer | 2 days | SearchTool, RefineTool, VerifyTool, RecallTool, ExpandTool — all wrapping existing infra |
| **4.3** Self-Evaluation + Confidence | Backend Engineer | 2 days | AgentEvaluator, confidence scoring, synthesis thresholds, caveat generation |

#### Sprint 12 (Week 12): Multi-Agent Architecture

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **4.4** Specialist Agents + Coordinator | Backend Lead | 3 days | AcademicAgent, PractitionerAgent, FactCheckAgent, ResearchCoordinator, parallel dispatch |
| **4.5** Agent Trace + Transparency | Backend Engineer | 2 days | AgentTrace DB model, trace API endpoint, SSE events for agent reasoning |

#### Sprint 13 (Week 13): Proactive Intelligence

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **4.7** Proactive Research Agent | Backend Engineer | 3 days | Knowledge gap analysis, stale detection, incomplete comparisons, notifications, Celery Beat |

#### Sprint 14 (Week 14): Testing + Documentation

| Task | Owner | Duration | Description |
|------|-------|----------|-------------|
| **4.8** Agent Test Suite | Entire team | 2 days | 13+ agent tests, integration tests, performance benchmarks |
| **4.9** Agent Architecture Docs | Backend Lead | 2 days | `docs/agent-architecture.md`, `docs/adding-agent-tools.md`, demo video |

**Exit Criteria:**
- [ ] Single-agent simple query <10s
- [ ] Multi-agent complex query <30s
- [ ] Agent trace stored and visualized
- [ ] Proactive suggestions generated weekly
- [ ] 85%+ test coverage on agent code

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

*This document should be treated as the engineering specification for the backend team. Each task has clear ownership, file-level scope, acceptance criteria, and test requirements. Update this document as implementation progresses.*
