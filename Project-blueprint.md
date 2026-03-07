<div align="center">

# 🔍 Sift

### Open-Source AI Deep Research Engine with Persistent Memory

*Research anything. Remember everything. Own your knowledge.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-00a393.svg)](https://fastapi.tiangolo.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Live Demo](https://sift-research.onrender.com) · [API Docs](https://sift-research.onrender.com/docs) · [Discord](https://discord.gg/sift) · [Blog](https://sift-research.dev/blog)

---

**Sift** is a self-hostable AI research engine that searches across multiple sources in parallel, synthesizes comprehensive cited answers in real-time, and builds a persistent knowledge graph across all your research sessions. Think **Perplexity** — but with memory, privacy, and full control.

</div>

---

## The Problem

Every day, millions of developers, students, researchers, and analysts perform the same painful ritual:

1. **Open Google.** Search. Open 8 tabs. Half are SEO spam.
2. **Open ArXiv.** Search the same thing differently. Open 4 more tabs. Papers are dense, no summaries.
3. **Open Reddit/HN.** Hope someone discussed it. Open 6 more tabs. Buried in 300-comment threads.
4. **Read fragments** from 18 tabs. Try to mentally synthesize. Miss contradictions between sources.
5. **Forget 90%** within a week. Repeat the exact same search next month.

This isn't a minor annoyance. Research shows knowledge workers spend **1.8 hours per day** searching for and consolidating information ([McKinsey](https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights/the-social-economy)). That's **9 hours per week** — an entire workday — lost to a broken process.

And yet, every existing tool designed to fix this fails in fundamental, architectural ways.

---

## Where Every Existing Solution Fails (And Why)

### Perplexity AI — The Closest, But Fundamentally Broken for Serious Research

Perplexity is the best AI search product on the market today. It's fast, well-designed, and useful for quick factual lookups. But the moment you use it for **real research** — the kind where you spend days exploring a topic, building understanding across sessions, and connecting ideas — it falls apart.

**Failure 1: Zero Memory Across Sessions**

This is Perplexity's most devastating architectural gap. Every query starts from absolute zero. You research "Kafka vs RabbitMQ" on Monday, explore "event-driven architectures" on Wednesday, and investigate "distributed message ordering guarantees" on Friday — three deeply related research sessions. But Perplexity treats them as completely isolated events. On Friday, it has no idea you spent Monday and Wednesday building context on the same topic.

```
Monday:    "Kafka vs RabbitMQ trade-offs"           → Great answer. Context built.
Wednesday: "Event-driven architecture patterns"      → Starts from zero. No link to Monday.
Friday:    "What did I learn about message brokers?" → ❌ "I don't have access to previous conversations."
```

The human brain builds knowledge cumulatively. Perplexity doesn't. Every closed tab is a lobotomy.

> **How Sift solves this:** Every research session is persisted into a personal knowledge graph. Chunks, embeddings, entities, and relationships are stored permanently. When you ask "What did I research about message brokers?", Sift retrieves across ALL your past sessions — with citations back to the original sources and timestamps. Your knowledge compounds instead of evaporating.

**Failure 2: Opaque Source Selection — You Can't Control What It Searches**

Perplexity decides which sources to search. You can't tell it "search Reddit and HackerNews for practitioner opinions, not just corporate blog posts." You can't tell it "skip Medium articles, they're usually shallow." You can't add your company's internal documentation as a source. The source pipeline is a black box.

For serious research, source quality and source diversity matter enormously. A question about production Kubernetes issues needs Reddit r/devops war stories, not marketing blog posts from vendor websites. Perplexity can't make that distinction because you can't control it.

> **How Sift solves this:** Full source transparency and control. Every query shows exactly which sources are being searched in real-time (via SSE status events). Users can toggle sources on/off per query. The plugin adapter interface lets you add ANY API as a custom source — your company wiki, internal docs, niche databases, or domain-specific APIs. You see the source, you control the source.

**Failure 3: No Knowledge Synthesis Across Documents**

Perplexity retrieves and summarizes. It doesn't truly synthesize. If Source A says "Kafka is better for ordered event processing" and Source B says "RabbitMQ handles ordering via priority queues" — Perplexity will cite both independently. It won't flag the tension, analyze the trade-off conditions, or build a structured comparison matrix.

> **How Sift solves this:** The synthesis prompt is engineered for structured analysis, not just summarization. The LLM receives retrieved chunks with explicit instructions to identify contradictions, compare claims across sources, and produce structured output (Overview → Trade-offs → Conditions → Recommendation). Source diversity enforcement in the retrieval pipeline ensures the LLM sees genuinely different perspectives, not 5 paraphrases of the same blog post.

**Failure 4: $20/Month Pro — Pricing Out Students and Developers**

The free tier gives 5 Pro queries per day. Real research burns through that in 10 minutes. Students writing theses, developers evaluating technology choices, researchers exploring new domains — the people who need deep research most are priced out.

> **How Sift solves this:** Completely free. Always. Groq's free tier provides 30 requests/minute of Llama 3.1 70B inference. HuggingFace provides free embeddings. Supabase provides free Postgres. ChromaDB runs in-process with zero cost. The entire stack is designed around the constraint of $0/month.

**Failure 5: Not Self-Hostable — Enterprise and Privacy Dead Ends**

Your research queries reveal your strategic thinking. What technologies you're evaluating. What competitors you're analyzing. What problems you're trying to solve. Perplexity stores all of this on their servers. For enterprises with compliance requirements (HIPAA, SOC 2, GDPR) or individuals who value privacy, this is a non-starter.

> **How Sift solves this:** One `docker compose up` and the entire stack runs on your infrastructure. Your queries never leave your machine. No telemetry, no analytics, no data sharing. The LLM provider is pluggable — use Groq's cloud API for convenience, or point to a local Ollama instance for complete air-gapped operation.

---

### ChatGPT Browse / Deep Research — Powerful LLM, Broken Search Architecture

ChatGPT with browsing is the most capable LLM on the planet strapped to a fundamentally broken search architecture. The LLM is incredible. The way it searches is not.

**Failure 1: Sequential, Single-Source Searching**

Watch ChatGPT browse. It searches one query at a time, reads one page at a time, decides if it needs more, searches again. This is literally how a human would browse — and that's the problem. It doesn't parallelize. A complex research question that Sift resolves in 8 seconds with parallel fan-out takes ChatGPT 45-90 seconds of sequential browsing.

```
ChatGPT Browse:
  Search 1 → wait 3s → read page → think → Search 2 → wait 3s → read page → ...
  Total: 45-90 seconds for complex queries, often hitting timeout

Sift:
  Fan-out → [DDG + Reddit + HN + ArXiv + Wiki] all simultaneously
  Total: 8-12 seconds, bounded by slowest source (not sum of all)
```

> **How Sift solves this:** Celery chord-based parallel fan-out. Five source workers execute simultaneously on independent threads. The total latency is `max(source_latencies)`, not `sum(source_latencies)`. With 10-second per-source timeouts and circuit breakers, worst-case latency is bounded and predictable.

**Failure 2: Hallucinated Citations**

ChatGPT frequently cites URLs that don't exist. It generates plausible-looking links that return 404. This isn't a minor UX issue — for research, a fabricated citation is worse than no citation. It undermines trust in every other claim the model makes.

The root cause is architectural: ChatGPT generates citations from its parametric memory (training data), not from a verified retrieval index. The browsing step gives it some grounding, but the citation generation happens in the LLM's next-token prediction, which can hallucinate URLs it "remembers" from training.

> **How Sift solves this:** Citations are structurally impossible to hallucinate. Every citation ID maps to a real chunk in the vector database with a verified source URL, fetch timestamp, and content hash. The synthesis prompt receives chunks with pre-assigned citation IDs (`[1]`, `[2]`, etc.) and is constrained to reference only those IDs. The frontend resolves citation IDs to actual URLs from the database — not from the LLM's output.

```python
# Sift's citation architecture — hallucination is structurally impossible
synthesis_prompt = f"""
Answer the query using ONLY the provided sources.
Cite sources using their IDs: [1], [2], etc.
Do NOT generate URLs. Do NOT reference sources not listed below.

Sources:
{chr(10).join(f'[{chunk.citation_id}] {chunk.text}' for chunk in retrieved_chunks)}

Query: {query}
"""

# Frontend resolves [1] → actual URL from the database
citation_map = {
    chunk.citation_id: {
        "url": chunk.source_url,        # Verified at fetch time
        "title": chunk.source_title,
        "fetched_at": chunk.timestamp,
        "content_hash": chunk.hash,      # Integrity verification
    }
    for chunk in retrieved_chunks
}
```

**Failure 3: No Persistent Knowledge Base**

Same as Perplexity. Every conversation is an island. ChatGPT's "memory" feature stores superficial preferences ("user prefers Python"), not research context ("user researched Kafka vs RabbitMQ on Monday and concluded Kafka is better for their 10K msg/sec use case").

> **How Sift solves this:** Deep persistent memory. Not just "user preferences" but full research state: retrieved chunks with embeddings, extracted entities, identified relationships, synthesized findings, and unresolved questions. The knowledge graph is queryable — both by semantic search ("What did I learn about message ordering?") and by graph traversal ("What concepts are related to my Kafka research?").

**Failure 4: Context Window Collapse on Long Research**

ChatGPT's context window is large (128K tokens) but finite. In a long research session with many follow-ups, earlier context gets pushed out or degraded by the "lost in the middle" problem (Liu et al., 2023). By turn 15 of a research session, the model has functionally forgotten turns 3-10.

> **How Sift solves this:** Progressive summarization compresses historical context while preserving critical findings. At each turn, previous context is summarized into a structured digest (key findings, contradictions, open questions) before new chunks are added. This keeps the effective context window fresh while maintaining cumulative knowledge. The full uncompressed history is always available in PostgreSQL for explicit recall.

**Failure 5: Expensive at Scale**

ChatGPT Plus is $20/month. ChatGPT Pro is $200/month. For teams of 10, that's $2,000/month for a search tool. For students in developing countries, $20/month is an entire week's food budget.

> **How Sift solves this:** $0/month. See the [Free-Tier Stack Breakdown](#free-tier-stack-breakdown) section.

---

### Google Search — The 10 Blue Links Problem

Google is still the world's most-used research tool. It's also the most frustrating for deep research.

**Failure 1: Zero Synthesis — You ARE the Search Engine**

Google returns links. You do the reading, the comparing, the synthesizing, the note-taking, and the remembering. For a simple factual lookup ("What's the capital of France?"), this is fine. For a complex research question ("What are the trade-offs between event sourcing and CQRS for a payment processing system?"), you're doing hours of manual labor that a retrieval-augmented LLM can do in seconds.

> **How Sift solves this:** Multi-source retrieval + LLM synthesis. You get a structured, cited analysis — not a list of URLs to read yourself.

**Failure 2: SEO Gaming Destroys Source Quality**

The top Google results for technical queries are increasingly dominated by:
- SEO-optimized content farms that rewrite Stack Overflow answers with worse explanations
- Vendor marketing blogs disguised as "technical comparisons" (where their product always wins)
- Outdated results that still rank high due to backlink authority
- AI-generated slop that regurgitates surface-level information

The actual best content — a specific Reddit comment from a senior engineer who ran Kafka at scale, a HackerNews discussion where database authors argue about trade-offs, a 2024 ArXiv paper with new benchmarks — is buried on page 3 or not indexed at all.

> **How Sift solves this:** Sift bypasses Google entirely and searches sources directly. Reddit API returns actual discussions ranked by community votes, not SEO authority. HackerNews Algolia API returns threads with real practitioner insights. ArXiv API returns actual peer-reviewed research. The multi-source architecture means you get the raw signal from each community, not Google's ad-influenced, SEO-gamed ranking.

**Failure 3: No Memory, No Knowledge Building**

Google search history is a flat, unsearchable log. You can't ask Google "What did I search for about Kubernetes networking last month?" and get a synthesized answer. Your bookmarks are a graveyard of links you saved with the intention of reading later (you didn't).

> **How Sift solves this:** Every research session builds your persistent knowledge base. Not just search history — actual retrieved content, embedded and indexed, with entity extraction and relationship mapping. Your knowledge graph grows with every query.

**Failure 4: Information Overload — "About 2,340,000,000 results (0.52 seconds)"**

Two billion results. You need five. Google gives you overwhelming volume with minimal signal. The cognitive load of sifting through results, evaluating source quality, and synthesizing across tabs is the core problem that wastes 1.8 hours per day for knowledge workers.

> **How Sift solves this:** Sift's entire pipeline is about reduction: 5 sources × ~10 results each → 50 raw results → deduplication → chunking → hybrid retrieval → top-15 most relevant chunks → synthesized answer with citations. You go from 50 raw results to a single, structured, cited analysis. The pipeline does the cognitive labor.

---

### Elicit / Semantic Scholar — Academic Silos

Elicit and Semantic Scholar are excellent tools for academic literature review. They fail the moment your research crosses the academic boundary.

**Failure 1: Academic Sources Only — No Practitioner Knowledge**

Real research questions blend theory and practice. "How should I implement distributed caching for my microservice?" needs both the academic research (Memcached papers, consistency model proofs) and the practitioner knowledge (Reddit threads about cache invalidation nightmares, HN discussions about Redis vs Memcached operational experience, blog posts about real-world cache stampede incidents).

Elicit can find the papers. It can't find the Reddit comment from the Netflix engineer who explains why the paper's approach doesn't work at scale.

> **How Sift solves this:** Multi-source by design. Academic (ArXiv) + practitioner (Reddit, HN) + reference (Wikipedia) + general web (DuckDuckGo) searched simultaneously. The synthesis engine is prompted to distinguish between theoretical findings and practical experience, giving you both perspectives in a single answer.

**Failure 2: Paper Abstracts, Not Deep Analysis**

Elicit surfaces paper abstracts and basic metadata. For a deep literature review, you need to understand methodology differences, compare experimental results across papers, identify research gaps, and synthesize findings. Elicit doesn't do cross-paper synthesis — it's fundamentally a search tool, not a research engine.

> **How Sift solves this:** Retrieved chunks from multiple papers (full text, not just abstracts) are fed into the synthesis pipeline. The LLM is prompted to identify methodological differences, compare quantitative results, flag contradictions, and identify gaps. This is closer to what a human literature reviewer does — but in 10 seconds instead of 10 hours.

**Failure 3: No Cross-Domain Research**

If you're researching "how RAG systems handle hallucination" — you need ArXiv papers on retrieval-augmented generation, GitHub issues on LangChain's factual grounding, Reddit discussions about production RAG systems, and HN threads where practitioners share real-world accuracy metrics. Elicit gives you only the first bucket and ignores the other three.

> **How Sift solves this:** Source-agnostic research. The query decomposer generates sub-queries that are dispatched across ALL configured sources. A question about RAG hallucination will search ArXiv for papers, Reddit for practitioner experience, HN for engineering discussions, and DuckDuckGo for documentation and blog posts — simultaneously.

---

### Khoj / Open-Source Alternatives — Good Intentions, Missing Architecture

[Khoj](https://github.com/khoj-ai/khoj) is the most notable open-source alternative. It's a personal AI assistant that can search your notes, documents, and the web. It's genuinely useful. But it's architecturally designed as a **personal assistant**, not a **research engine**, and the differences are significant.

**Failure 1: No Multi-Source Parallel Fan-out**

Khoj searches the web or your notes. It doesn't decompose a complex query into sub-queries and fan them out across 5 specialized sources simultaneously. The search architecture is single-threaded and source-sequential.

> **How Sift solves this:** Purpose-built Celery chord fan-out. Complex queries are decomposed into orthogonal sub-queries, then each sub-query is dispatched to each source adapter in parallel. 5 sources × 3 sub-queries = 15 parallel search tasks, all executing concurrently with independent timeouts and circuit breakers.

**Failure 2: No Hybrid Retrieval (BM25 + Dense)**

Khoj uses embedding-based similarity search. This misses exact keyword matches that BM25 catches. If you search for "RAFT consensus protocol" and a chunk contains the exact phrase "RAFT consensus" but is semantically about distributed systems (a broad embedding), pure dense retrieval might rank it lower than a chunk that's semantically closer but doesn't mention RAFT.

> **How Sift solves this:** Two-phase hybrid retrieval with Reciprocal Rank Fusion. BM25 catches exact keyword matches (precision). Dense retrieval catches semantic similarity (recall). RRF fuses both without needing score normalization. This is the same approach production search engines (Elasticsearch 8.x, Vespa) use.

**Failure 3: No Resilience Patterns**

When Khoj's web search fails, the whole query fails. There's no circuit breaker to fail fast on a broken source, no graceful degradation to return partial results from healthy sources, no retry with exponential backoff, no timeout isolation.

> **How Sift solves this:** Production-grade resilience stack:
> - **Circuit breakers** per source (Redis-backed state machine: CLOSED → OPEN → HALF_OPEN)
> - **Timeout isolation** — each source has a 10s hard timeout; one slow source doesn't delay others
> - **Partial result assembly** — if Reddit is down, you still get results from DDG + HN + ArXiv + Wikipedia
> - **Exponential backoff retry** — transient failures are retried twice before circuit opens
> - **Graceful degradation** — the synthesis pipeline works with however many sources returned results, clearly noting which sources were unavailable

**Failure 4: No Knowledge Graph or Cross-Session Intelligence**

Khoj stores your documents and lets you search them. It doesn't extract entities, build relationship graphs, or enable cross-session knowledge discovery. You can't ask "How does my research on caching relate to my research on database indexing?" because there's no concept-level linking between interactions.

> **How Sift solves this:** LLM-based entity extraction runs on every research session's synthesized output. Entities (technologies, concepts, people, organizations) are extracted and stored as graph nodes. Relationships between entities are stored as edges. When you research "Redis caching patterns" and later research "database indexing strategies", the knowledge graph connects them through shared entities (Redis, B-tree, cache invalidation, write-through patterns). Graph traversal enables discovery: "Show me everything connected to my Redis research."

---

### You.com / Phind — Narrow Focus, No Depth

**You.com** is a general-purpose AI search engine. **Phind** is developer-focused. Both produce decent quick answers but share critical limitations.

**Failure 1: No Persistent Memory**

Same fundamental gap as Perplexity and ChatGPT. Every query starts from zero. No session continuity, no knowledge accumulation, no recall.

**Failure 2: Not Self-Hostable, Not Customizable**

Closed-source, cloud-only, fixed source selection. You can't add private data sources, can't run it on-premise, can't customize the retrieval pipeline, can't audit what data is being sent where.

**Failure 3: Developer-Only (Phind) or Shallow (You.com)**

Phind is excellent for code-specific queries but struggles with broader technical research that spans architecture, operations, and business trade-offs. You.com is broad but shallow — good for factual lookups, weak for deep multi-source synthesis.

> **How Sift solves all three:** Persistent memory, fully self-hostable with pluggable components, and domain-agnostic deep research across any topic where multi-source synthesis adds value.

---

### Tavily / Search APIs — Building Blocks, Not Solutions

Tavily is a search API built for LLM applications. It's a tool for developers, not a product for end users. But even as a building block, it illustrates what's missing from the ecosystem.

**Failure 1: Single-Source Aggregation, Not Multi-Source Intelligence**

Tavily aggregates web search results. It doesn't search Reddit's API, HackerNews's API, ArXiv's API, or Wikipedia's API independently. You get web search results — which means you get whatever Google/Bing decides to show you, with all the SEO gaming and source quality issues described above.

**Failure 2: No Retrieval Pipeline**

Tavily returns search results. What you do with them is your problem. There's no chunking, no embedding, no hybrid retrieval, no deduplication, no relevance ranking beyond what the search engine provides. Building a production RAG pipeline on top of Tavily is exactly what Sift does — but Tavily itself is just the first step.

> **How Sift solves this:** Sift is the complete pipeline. Source fetching (multi-source, parallel, resilient) → ingestion (extract, chunk, deduplicate, embed) → retrieval (hybrid BM25 + dense + RRF) → synthesis (streaming, cited, structured) → persistence (knowledge graph, session memory). Tavily is one source adapter. Sift is the entire research engine.

---

## The Sift Thesis: What a Research Engine Actually Needs

Every existing tool fails because it's optimized for the wrong primitive:

| Tool | Optimized For | Fails At |
|------|--------------|----------|
| **Google** | Finding links | Synthesis, memory, source quality |
| **Perplexity** | Quick factual answers | Deep research, memory, privacy, customization |
| **ChatGPT** | Conversational AI | Parallel search, verified citations, cost, memory |
| **Elicit** | Academic papers | Cross-domain, practitioner knowledge, general research |
| **Khoj** | Personal assistant | Multi-source search, resilience, knowledge graph |
| **Phind** | Code questions | Broad research, memory, self-hosting |

Sift is optimized for **deep research as a process** — not a single query, but an ongoing activity where knowledge accumulates, connections emerge, and past work informs future exploration.

The five architectural pillars that make this possible:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SIFT'S FIVE PILLARS                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. MULTI-SOURCE PARALLEL INTELLIGENCE                                  │
│     Not one search engine. Five specialized source adapters,            │
│     executing in parallel with independent failure domains.             │
│                                                                         │
│  2. PRODUCTION-GRADE RETRIEVAL                                          │
│     Not naive cosine similarity. Hybrid BM25 + dense retrieval          │
│     with Reciprocal Rank Fusion, deduplication, and reranking.          │
│                                                                         │
│  3. PERSISTENT KNOWLEDGE GRAPH                                          │
│     Not session-scoped chat. Permanent entity-relationship graph        │
│     that grows across every research session, queryable by              │
│     semantic search and graph traversal.                                │
│                                                                         │
│  4. RESILIENT DISTRIBUTED ARCHITECTURE                                  │
│     Not a monolith. Celery workers with circuit breakers, rate          │
│     limiters, timeout isolation, and graceful degradation.              │
│     One failed source never breaks the whole query.                     │
│                                                                         │
│  5. RADICAL OPENNESS                                                    │
│     Not a black box. Open source, self-hostable, pluggable LLM,        │
│     pluggable sources, full data ownership, zero telemetry.             │
│     Your research is YOUR research.                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Your research knowledge shouldn't evaporate when you close a tab.**

---

## How Sift Works

```
You ask: "What are the trade-offs between Kafka and RabbitMQ for
         event-driven microservices at moderate scale (10K msgs/sec)?"
```

**Sift does this in ~8 seconds:**

```
1. DECOMPOSE  →  LLM breaks query into 3 orthogonal sub-queries:
                  • "Kafka vs RabbitMQ performance benchmarks"
                  • "Event-driven architecture message broker trade-offs"
                  • "Kafka RabbitMQ operational complexity production"

2. FAN-OUT    →  Celery dispatches 5 parallel source workers:
                  ┌→ DuckDuckGo Web Search ──→ 8 results
                  ├→ Reddit API ─────────────→ 5 discussions
                  ├→ HackerNews Algolia API ─→ 6 threads
                  ├→ ArXiv API ──────────────→ 3 papers
                  └→ Wikipedia API ──────────→ 2 articles

3. INGEST     →  Real-time document processing pipeline:
                  • HTML/PDF extraction → Intelligent chunking
                  • Near-duplicate detection (MinHash/LSH)
                  • Parallel embedding generation
                  • Upsert into vector DB

4. RETRIEVE   →  Two-phase hybrid retrieval:
                  Phase 1: BM25 sparse search (keyword precision)
                  Phase 2: Dense embedding search (semantic recall)
                  Fusion: Reciprocal Rank Fusion → Top-K chunks

5. SYNTHESIZE →  Streaming LLM synthesis with:
                  • Inline source citations [1][2][3]
                  • Confidence indicators per claim
                  • Structured sections (Overview, Trade-offs, Recommendation)

6. PERSIST    →  Session saved to your knowledge graph:
                  • Chunks stored with metadata + embeddings
                  • Entity extraction → knowledge graph nodes
                  • Linked to your past research on related topics
```

**Next month, you ask:** *"What did I research about message brokers?"*

Sift retrieves your previous research context instantly — no re-searching, no lost knowledge.

---

## Key Features

### Research Engine
- **Multi-source parallel search** — 5+ sources searched simultaneously via Celery fan-out
- **Streaming answers** — Real-time Server-Sent Events as sources return results at different speeds
- **Inline citations** — Every claim linked to its source with confidence scoring
- **Follow-up questions** — Contextual follow-ups against the same retrieved corpus
- **Query decomposition** — Complex questions automatically broken into focused sub-queries

### Persistent Memory
- **Knowledge graph** — Every research session builds your personal knowledge base
- **Cross-session recall** — Ask about past research: *"What did I learn about X?"*
- **Entity linking** — Concepts automatically connected across research sessions
- **Temporal awareness** — Recent research weighted higher unless you specify otherwise
- **Export** — Markdown, JSON, or Obsidian-compatible export of your knowledge base

### Production-Grade Architecture
- **Hybrid retrieval** — BM25 + dense embeddings fused via Reciprocal Rank Fusion (RRF)
- **Smart caching** — Redis with stale-while-revalidate for sub-second repeat queries
- **Circuit breakers** — Per-source failure isolation; one slow source doesn't block others
- **Rate limiting** — Token bucket per source with exponential backoff
- **Deduplication** — MinHash/LSH near-duplicate detection before embedding

### Privacy & Control
- **Fully self-hostable** — Docker Compose, one command to run
- **Your data stays yours** — No telemetry, no third-party data sharing
- **Pluggable LLM** — Groq, OpenAI, HuggingFace, Ollama (local), or any OpenAI-compatible API
- **Custom sources** — Add your own data sources via the adapter interface

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SIFT ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────────────────────────────────────────────────┐   │
│  │  React +  │    │                 FastAPI Backend                      │   │
│  │  Next.js  │───▶│                                                      │   │
│  │  Frontend │◀───│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  └──────────┘ SSE│  │  /research  │  │  /knowledge │  │  /sessions   │  │   │
│                   │  │  endpoint   │  │  endpoint   │  │  endpoint    │  │   │
│                   │  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘  │   │
│                   │        │                │                 │          │   │
│                   │        ▼                ▼                 ▼          │   │
│                   │  ┌──────────────────────────────────────────────┐    │   │
│                   │  │            Research Orchestrator              │    │   │
│                   │  │                                              │    │   │
│                   │  │  1. Query Analysis & Decomposition           │    │   │
│                   │  │  2. Source Selection & Fan-out                │    │   │
│                   │  │  3. Result Aggregation & Dedup               │    │   │
│                   │  │  4. Retrieval & Ranking                      │    │   │
│                   │  │  5. Synthesis & Streaming                    │    │   │
│                   │  └───────────────┬──────────────────────────────┘    │   │
│                   └─────────────────┬┼──────────────────────────────────┘   │
│                                     ││                                      │
│          ┌──────────────────────────┘│                                      │
│          │                           │                                      │
│          ▼                           ▼                                      │
│  ┌───────────────┐    ┌──────────────────────────────────────────────┐      │
│  │  Redis         │    │              Celery Workers                  │      │
│  │  (Upstash)     │    │                                              │      │
│  │                │    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │      │
│  │  • Task Queue  │◀──▶│  │ DuckDuck │ │  Reddit  │ │  HackerNews  │ │      │
│  │  • Cache Layer │    │  │ Go Worker│ │  Worker  │ │  Worker      │ │      │
│  │  • Rate Limits │    │  └──────────┘ └──────────┘ └──────────────┘ │      │
│  │  • Session     │    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │      │
│  │    State       │    │  │  ArXiv   │ │ Wikipedia│ │   Custom     │ │      │
│  └───────────────┘    │  │  Worker  │ │  Worker  │ │   Source     │ │      │
│                        │  └──────────┘ └──────────┘ └──────────────┘ │      │
│                        └──────────────────┬───────────────────────────┘      │
│                                           │                                  │
│                     ┌─────────────────────┼─────────────────────┐            │
│                     │                     │                     │            │
│                     ▼                     ▼                     ▼            │
│           ┌──────────────┐    ┌──────────────────┐   ┌──────────────┐       │
│           │  ChromaDB     │    │   PostgreSQL      │   │   Groq /     │       │
│           │  (Vector DB)  │    │   (Supabase)      │   │   HuggingFace│       │
│           │               │    │                    │   │   LLM API    │       │
│           │  • Embeddings │    │  • Users           │   │              │       │
│           │  • Chunks     │    │  • Sessions        │   │  • Query     │       │
│           │  • Metadata   │    │  • Knowledge Graph │   │    Decomp    │       │
│           │  • BM25 Index │    │  • Source Cache    │   │  • Synthesis │       │
│           └──────────────┘    └──────────────────┘   │  • Summaries │       │
│                                                       └──────────────┘       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
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
│                                          │
│  a) Collect results as they arrive       │
│     (Celery chord callback)              │
│                                          │
│  b) HTML/PDF → clean text extraction     │
│                                          │
│  c) Near-duplicate detection:            │
│     MinHash signatures → LSH buckets     │
│     Jaccard similarity > 0.8 → dedupe    │
│                                          │
│  d) Intelligent chunking:                │
│     • Recursive text splitter            │
│     • 512 tokens, 64 token overlap       │
│     • Metadata preserved per chunk       │
│       (source, date, author, URL)        │
│                                          │
│  e) Parallel embedding generation:       │
│     HuggingFace all-MiniLM-L6-v2        │
│     (384-dim, free, fast)                │
│                                          │
│  f) Batch upsert → ChromaDB             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  4. TWO-PHASE HYBRID RETRIEVAL           │
│                                          │
│  Phase 1 — Sparse (BM25):               │
│  • Keyword matching on chunk text        │
│  • Returns top-50 candidates             │
│  • Score: BM25(q, d)                     │
│                                          │
│  Phase 2 — Dense (Embedding):            │
│  • Cosine similarity on embeddings       │
│  • Returns top-50 candidates             │
│  • Score: cos(embed(q), embed(d))        │
│                                          │
│  Fusion — Reciprocal Rank Fusion:        │
│  • RRF(d) = Σ 1/(k + rank_i(d))         │
│  • k = 60 (standard constant)            │
│  • Returns final top-15 chunks           │
│                                          │
│  Post-Retrieval Re-ranking:              │
│  • Cross-encoder reranker (optional)     │
│  • Source diversity enforcement           │
│  • Recency boost for time-sensitive q's  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  5. STREAMING SYNTHESIS                  │
│                                          │
│  • Top-15 chunks → LLM context window   │
│  • System prompt with citation format    │
│  • Streaming via SSE (Server-Sent Events)│
│  • Token-by-token delivery to frontend   │
│  • Inline citations: [1], [2], [3]       │
│  • Structured output:                    │
│    - Executive Summary                   │
│    - Detailed Analysis                   │
│    - Key Trade-offs                      │
│    - Sources & Confidence                │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  6. PERSISTENCE                          │
│                                          │
│  • Research session → PostgreSQL         │
│  • Chunks + embeddings retained in       │
│    ChromaDB (tagged with session ID)     │
│  • Entity extraction → knowledge graph   │
│  • Redis cache: query hash → result      │
│    (TTL: 24h, stale-while-revalidate)    │
└─────────────────────────────────────────┘
```

---

## Free-Tier Stack Breakdown

Every component runs on free tiers. Zero cost at MVP scale.

| Component | Free-Tier Service | Limits | Role |
|-----------|-------------------|--------|------|
| **LLM Inference** | [Groq](https://groq.com) | 30 req/min, Llama 3.1 70B | Query decomposition, synthesis, entity extraction |
| **Embeddings** | [HuggingFace Inference API](https://huggingface.co/inference-api) | Rate-limited free tier | `all-MiniLM-L6-v2` (384-dim) embeddings |
| **Vector Database** | [ChromaDB](https://www.trychroma.com/) (embedded) | Unlimited (runs in-process) | Chunk storage, dense retrieval, metadata filtering |
| **PostgreSQL** | [Supabase](https://supabase.com) | 500MB, 2 projects | Users, sessions, knowledge graph, source metadata |
| **Redis** | [Upstash](https://upstash.com) | 10K commands/day | Task queue (Celery broker), caching, rate limiting |
| **Backend Hosting** | [Render](https://render.com) | 750 hrs/mo free | FastAPI + Celery worker (single dyno) |
| **Frontend Hosting** | [Vercel](https://vercel.com) | Unlimited for hobby | Next.js/React frontend |
| **Web Search** | [DuckDuckGo API](https://duckduckgo.com) | Free, no key needed | General web search source |
| **Academic Search** | [ArXiv API](https://arxiv.org/help/api) | Free, rate-limited | Academic paper search source |
| **News/Discussion** | [HN Algolia API](https://hn.algolia.com/api) + [Reddit API](https://www.reddit.com/dev/api/) | Free tiers | Community discussion sources |
| **CI/CD** | [GitHub Actions](https://github.com/features/actions) | 2000 min/mo free | Testing, linting, deployment |
| **Monitoring** | [Better Stack](https://betterstack.com) (free) | Free tier | Uptime monitoring, basic logging |

### Cost Analysis at MVP Scale

```
Daily active users:     ~100
Queries per day:        ~500
LLM calls per query:    ~3 (decompose + synthesize + entity extract)
Total LLM calls/day:    ~1,500

Groq free tier:         30 req/min = 43,200/day     ✅ Well within limits
Upstash free tier:      10K commands/day             ✅ ~5K commands/day used
Supabase free tier:     500MB storage                ✅ ~50MB for 100 users
ChromaDB:               In-process, no limits        ✅ ~200MB for 100K chunks
Render free tier:       750 hrs/mo (always-on)       ✅ Single service

Total monthly cost: $0.00
```

---

## System Design Decisions

These are the engineering trade-offs that make interviewers lean forward.

### 1. Why Celery Chord (not asyncio gather) for Source Fan-out?

```python
# What most people do (fragile):
results = await asyncio.gather(
    search_ddg(query),
    search_reddit(query),
    search_arxiv(query),
)
# Problem: One slow source blocks the response.
# Problem: No retry isolation. No per-source circuit breakers.
# Problem: Ties up the API server's event loop.

# What Sift does (production-grade):
from celery import chord

chord(
    [
        search_source.s("ddg", sub_queries),
        search_source.s("reddit", sub_queries),
        search_source.s("hackernews", sub_queries),
        search_source.s("arxiv", sub_queries),
        search_source.s("wikipedia", sub_queries),
    ],
    aggregate_and_process.s(session_id=session_id)
)()
# Celery chord: all tasks execute in parallel on worker pool,
# callback fires when ALL complete (or timeout).
# Each worker has independent timeout, retry, circuit breaker.
# API server event loop stays free for other requests.
```

**Why this matters:** In a system design interview, this demonstrates understanding of:
- Worker pool isolation vs event loop blocking
- Failure domain separation per external dependency
- The difference between concurrency (asyncio) and parallelism (Celery workers)

### 2. Why Reciprocal Rank Fusion (not just cosine similarity)?

```python
def reciprocal_rank_fusion(
    sparse_results: list[tuple[str, float]],
    dense_results: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Fuse BM25 (sparse) and embedding (dense) retrieval results.

    Pure embedding search misses exact keyword matches.
    Pure BM25 misses semantic similarity.
    RRF combines both without needing score normalization.

    RRF(d) = Σ 1/(k + rank_i(d)) for each ranking system i
    """
    fused_scores: dict[str, float] = defaultdict(float)

    for rank, (doc_id, _score) in enumerate(sparse_results):
        fused_scores[doc_id] += 1.0 / (k + rank + 1)

    for rank, (doc_id, _score) in enumerate(dense_results):
        fused_scores[doc_id] += 1.0 / (k + rank + 1)

    return sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
```

**Why this matters:** Most LLM projects use naive cosine similarity. RRF is what production search engines (Elasticsearch, Vespa) use. It shows you understand information retrieval theory, not just API calls.

### 3. Why Stale-While-Revalidate Caching?

```python
async def get_cached_or_research(query_hash: str, query: str) -> AsyncGenerator:
    cached = await redis.get(f"result:{query_hash}")
    ttl = await redis.ttl(f"result:{query_hash}")

    if cached and ttl > STALE_THRESHOLD:
        # Fresh cache hit — return immediately
        yield cached
        return

    if cached and ttl <= STALE_THRESHOLD:
        # Stale cache — return stale result immediately,
        # trigger background refresh
        yield cached
        refresh_research.delay(query_hash, query)  # Celery task
        return

    # Cache miss — full research pipeline
    async for chunk in research_pipeline(query):
        yield chunk
```

**Why this matters:** This is the same pattern CDNs (Cloudflare, Fastly) use. It demonstrates understanding of cache coherence trade-offs: serving slightly stale data for 10x better P99 latency is the right trade-off for research queries where freshness isn't critical at the minute level.

### 4. Circuit Breaker Pattern for External Sources

```python
class SourceCircuitBreaker:
    """
    Prevents cascading failures when an external source is down.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Source is down, fail fast without making requests
    - HALF_OPEN: Test with single request to check recovery

    Transitions:
    - CLOSED → OPEN: failure_count >= threshold (5 failures in 60s)
    - OPEN → HALF_OPEN: after cooldown_period (30s)
    - HALF_OPEN → CLOSED: test request succeeds
    - HALF_OPEN → OPEN: test request fails
    """

    def __init__(self, source_name: str, failure_threshold: int = 5,
                 cooldown_seconds: int = 30):
        self.source_name = source_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        # State stored in Redis for shared access across workers
```

**Why this matters:** This is the resilience pattern that Amazon and Netflix use for microservice communication. Demonstrating it in a personal project shows production-grade thinking.

### 5. Why Session-Aware Context Compression?

```
Research sessions grow. After 10 follow-up questions, you might have
200+ retrieved chunks. Naively stuffing them into the LLM context
window causes:
  1. Token limit overflow
  2. "Lost in the middle" problem (LLMs ignore middle context)
  3. Increased latency and cost

Sift's approach — Progressive Summarization:
┌─────────────────────────────────────────────┐
│  Turn 1: Full retrieved chunks (15 chunks)  │
│  Turn 2: Summary of Turn 1 + 15 new chunks │
│  Turn 3: Summary of [1+2] + 15 new chunks  │
│  ...                                         │
│  Turn N: Compressed history + fresh chunks  │
└─────────────────────────────────────────────┘

The summary preserves:
  • Key findings with source citations
  • Unresolved questions
  • Contradictions between sources
  • User's expressed preferences/focus areas
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Docker & Docker Compose (recommended)

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/yourusername/sift.git
cd sift
cp .env.example .env
# Add your Groq API key (free at console.groq.com)
docker compose up
```

Open `http://localhost:3000` — start researching.

### Option 2: Local Development

```bash
# Clone
git clone https://github.com/yourusername/sift.git
cd sift

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys

# Start services
uvicorn app.main:app --reload --port 8000 &
celery -A app.worker worker --loglevel=info --concurrency=4 &

# Frontend
cd ../frontend
npm install
npm run dev
```

### Environment Variables

```bash
# Required
GROQ_API_KEY=gsk_...               # Free at console.groq.com
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# Optional (defaults work for local dev)
UPSTASH_REDIS_URL=redis://...       # Falls back to local Redis
HF_API_TOKEN=hf_...                 # For HuggingFace embeddings
CHROMA_PERSIST_DIR=./chroma_data
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## API Reference

### Core Endpoints

#### `POST /api/v1/research`
Start a new research query with streaming response.

```bash
curl -N -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Trade-offs between Kafka and RabbitMQ for event-driven microservices",
    "sources": ["ddg", "reddit", "hackernews", "arxiv", "wikipedia"],
    "session_id": null,
    "depth": "standard"
  }'
```

**Response** (Server-Sent Events stream):
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
data: {"content": "Based on analysis of 24 sources across web, Reddit, and academic papers...", "citations": []}

event: token
data: {"content": " Kafka excels at high-throughput ordered event streaming [1][2]", "citations": [1, 2]}

...

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

#### `POST /api/v1/research/{session_id}/followup`
Ask a follow-up question within an existing research session.

```bash
curl -N -X POST http://localhost:8000/api/v1/research/sess_abc123/followup \
  -H "Content-Type: application/json" \
  -d '{"query": "What about at 100K messages per second?"}'
```

#### `GET /api/v1/knowledge/search`
Search across your persistent knowledge base.

```bash
curl "http://localhost:8000/api/v1/knowledge/search?q=message+brokers&limit=10"
```

#### `GET /api/v1/sessions`
List all research sessions with metadata.

#### `GET /api/v1/sessions/{session_id}/graph`
Get the knowledge graph for a specific session (nodes + edges).

---

## Project Structure

```
sift/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, middleware, CORS
│   │   ├── config.py                # Settings via pydantic-settings
│   │   │
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── research.py      # /research endpoints (SSE streaming)
│   │   │   │   ├── knowledge.py     # /knowledge search & graph endpoints
│   │   │   │   ├── sessions.py      # /sessions CRUD
│   │   │   │   └── health.py        # /health for monitoring
│   │   │   └── dependencies.py      # Auth, rate limiting, DB sessions
│   │   │
│   │   ├── core/
│   │   │   ├── orchestrator.py      # Research pipeline orchestration
│   │   │   ├── query_analyzer.py    # Intent classification, sub-query generation
│   │   │   ├── synthesizer.py       # LLM-based answer synthesis with citations
│   │   │   └── context_manager.py   # Session context compression
│   │   │
│   │   ├── retrieval/
│   │   │   ├── hybrid_retriever.py  # BM25 + dense + RRF fusion
│   │   │   ├── bm25.py             # Sparse retrieval implementation
│   │   │   ├── dense.py            # Embedding-based retrieval
│   │   │   ├── reranker.py         # Cross-encoder reranking (optional)
│   │   │   └── deduplication.py    # MinHash/LSH near-duplicate detection
│   │   │
│   │   ├── sources/
│   │   │   ├── base.py             # Abstract source adapter interface
│   │   │   ├── duckduckgo.py       # DuckDuckGo search adapter
│   │   │   ├── reddit.py           # Reddit API adapter
│   │   │   ├── hackernews.py       # HN Algolia API adapter
│   │   │   ├── arxiv.py            # ArXiv API adapter
│   │   │   ├── wikipedia.py        # Wikipedia API adapter
│   │   │   └── registry.py         # Source discovery & registration
│   │   │
│   │   ├── ingestion/
│   │   │   ├── pipeline.py         # Document processing pipeline
│   │   │   ├── extractors.py       # HTML/PDF/text content extraction
│   │   │   ├── chunker.py          # Recursive text splitting with metadata
│   │   │   └── embedder.py         # Embedding generation (HF/OpenAI)
│   │   │
│   │   ├── knowledge/
│   │   │   ├── graph.py            # Knowledge graph operations
│   │   │   ├── entities.py         # Entity extraction & linking
│   │   │   └── memory.py           # Persistent memory / recall
│   │   │
│   │   ├── workers/
│   │   │   ├── celery_app.py       # Celery configuration
│   │   │   ├── tasks.py            # Source search tasks, ingestion tasks
│   │   │   └── callbacks.py        # Chord callbacks for aggregation
│   │   │
│   │   ├── resilience/
│   │   │   ├── circuit_breaker.py  # Per-source circuit breaker (Redis-backed)
│   │   │   ├── rate_limiter.py     # Token bucket rate limiter (Redis-backed)
│   │   │   └── retry.py            # Exponential backoff retry logic
│   │   │
│   │   ├── cache/
│   │   │   ├── redis_cache.py      # Cache operations + stale-while-revalidate
│   │   │   └── embedding_cache.py  # LRU cache for repeated embedding queries
│   │   │
│   │   └── db/
│   │       ├── models.py           # SQLAlchemy models
│   │       ├── vector_store.py     # ChromaDB operations
│   │       └── session.py          # Async DB session management
│   │
│   ├── tests/
│   │   ├── conftest.py             # Fixtures: mock Redis, mock Celery, test DB
│   │   ├── test_orchestrator.py
│   │   ├── test_retrieval.py       # Hybrid retrieval accuracy tests
│   │   ├── test_sources/           # Per-source adapter tests (mocked HTTP)
│   │   ├── test_resilience.py      # Circuit breaker state machine tests
│   │   ├── test_cache.py           # Cache hit/miss/stale scenarios
│   │   └── test_api/               # FastAPI endpoint tests
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
│
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js app router
│   │   ├── components/
│   │   │   ├── SearchBar.tsx       # Query input with source toggles
│   │   │   ├── ResearchStream.tsx  # SSE-powered streaming results
│   │   │   ├── CitationCard.tsx    # Source citation with preview
│   │   │   ├── KnowledgeGraph.tsx  # D3.js force-directed graph
│   │   │   ├── SessionSidebar.tsx  # Research session history
│   │   │   └── SourceIndicator.tsx # Real-time source status (loading/done/error)
│   │   ├── hooks/
│   │   │   ├── useSSE.ts           # Server-Sent Events hook
│   │   │   └── useResearch.ts      # Research state management
│   │   └── lib/
│   │       └── api.ts              # API client
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml              # Full stack: backend + worker + frontend + redis
├── docker-compose.dev.yml          # Development overrides (hot reload, debug)
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint + test on PR
│       └── deploy.yml              # Auto-deploy to Render on main push
├── Makefile                        # Common commands (make dev, make test, make deploy)
└── README.md
```

---

## Testing Strategy

Sift targets **85%+ test coverage** with a focus on critical paths.

```bash
# Run all tests
make test

# Run with coverage report
make test-coverage

# Run specific test suite
pytest tests/test_retrieval.py -v
pytest tests/test_resilience.py -v
```

### Test Categories

| Category | What's Tested | Example |
|----------|--------------|---------|
| **Unit** | Individual components in isolation | `test_rrf_fusion_produces_correct_ranking` |
| **Integration** | Component interactions | `test_orchestrator_handles_partial_source_failure` |
| **Contract** | Source adapter response parsing | `test_reddit_adapter_parses_api_response` |
| **Resilience** | Failure modes | `test_circuit_breaker_opens_after_5_failures` |
| **Cache** | Caching behavior | `test_stale_while_revalidate_returns_cached_then_refreshes` |
| **E2E** | Full research pipeline | `test_research_query_returns_cited_streaming_response` |

### Key Test Patterns

```python
# Resilience testing: Verify circuit breaker state transitions
async def test_circuit_breaker_state_machine():
    breaker = SourceCircuitBreaker("reddit", failure_threshold=3)

    # CLOSED → simulate failures
    for _ in range(3):
        await breaker.record_failure()

    assert breaker.state == CircuitState.OPEN

    # OPEN → requests fail fast
    with pytest.raises(CircuitOpenError):
        async with breaker:
            await search_reddit("test")

    # Wait for cooldown → HALF_OPEN
    await asyncio.sleep(breaker.cooldown_seconds)
    assert breaker.state == CircuitState.HALF_OPEN

    # Successful test request → CLOSED
    await breaker.record_success()
    assert breaker.state == CircuitState.CLOSED


# Retrieval testing: Verify RRF fusion quality
def test_rrf_fusion_boosts_documents_appearing_in_both_rankings():
    sparse = [("doc_a", 0.9), ("doc_b", 0.7), ("doc_c", 0.5)]
    dense  = [("doc_b", 0.95), ("doc_d", 0.8), ("doc_a", 0.6)]

    fused = reciprocal_rank_fusion(sparse, dense)

    # doc_b appears in both → should be ranked #1
    assert fused[0][0] == "doc_b"
    # doc_a appears in both → should be ranked #2
    assert fused[1][0] == "doc_a"
```

---

## Development Roadmap — Implementation Specification

> This section serves as the **engineering implementation plan**. Each phase is broken into weekly sprints with specific tasks, acceptance criteria, file-level ownership, and technical specifications detailed enough for a development team to execute independently.

---

### Phase 1 — Core Research Engine

**Duration:** 2 Weeks (Sprints 1–2)
**Goal:** A working end-to-end research engine where a user enters a question and receives a streamed, multi-source, cited answer.
**Team:** 1–2 backend engineers, 1 frontend engineer

---

#### Sprint 1 (Days 1–7): Backend Foundation + Source Adapters

##### Task 1.1 — Project Scaffolding & FastAPI Skeleton

**Owner:** Backend Lead
**Files:** `backend/app/main.py`, `backend/app/config.py`, `backend/requirements.txt`, `Dockerfile`, `docker-compose.yml`
**Duration:** Day 1

- [ ] Initialize Python 3.11+ project with `pyproject.toml` or `requirements.txt`
- [ ] Dependencies to install:
  ```
  fastapi==0.110.0
  uvicorn[standard]==0.27.0
  pydantic==2.6.0
  pydantic-settings==2.1.0
  httpx==0.27.0
  python-dotenv==1.0.0
  sse-starlette==2.0.0
  chromadb==0.4.22
  groq==0.4.2
  ```
- [ ] Create `main.py` with FastAPI app, CORS middleware (allow `localhost:3000`), lifespan handler
- [ ] Create `config.py` using `pydantic-settings.BaseSettings` loading from `.env`:
  ```python
  class Settings(BaseSettings):
      groq_api_key: str
      chroma_persist_dir: str = "./chroma_data"
      embedding_model: str = "all-MiniLM-L6-v2"
      llm_model: str = "llama-3.1-70b-versatile"
      max_sources_per_query: int = 5
      chunk_size: int = 512
      chunk_overlap: int = 64
      model_config = SettingsConfigDict(env_file=".env")
  ```
- [ ] Create `health.py` route: `GET /api/v1/health` returning `{"status": "ok", "version": "0.1.0"}`
- [ ] Create `Dockerfile` (Python 3.11-slim, multi-stage build)
- [ ] Create `docker-compose.yml` with `backend` service + volume for ChromaDB persistence
- [ ] Create `.env.example` with all required environment variables documented

**Acceptance Criteria:**
- `docker compose up` starts the backend on port 8000
- `GET /api/v1/health` returns 200
- `GET /docs` shows Swagger UI

---

##### Task 1.2 — Source Adapter Interface + 3 Adapters

**Owner:** Backend Engineer
**Files:** `backend/app/sources/base.py`, `backend/app/sources/duckduckgo.py`, `backend/app/sources/wikipedia.py`, `backend/app/sources/hackernews.py`, `backend/app/sources/registry.py`
**Duration:** Days 2–3

- [ ] Define abstract base class in `base.py`:
  ```python
  class SourceAdapter(ABC):
      name: str              # e.g., "duckduckgo"
      display_name: str      # e.g., "DuckDuckGo Web Search"
      max_results: int = 10
      timeout_seconds: int = 10

      @abstractmethod
      async def search(self, query: str, max_results: int) -> list[SourceResult]:
          """Execute search and return structured results."""

      @abstractmethod
      def is_available(self) -> bool:
          """Health check for this source."""
  ```
- [ ] Define `SourceResult` Pydantic model:
  ```python
  class SourceResult(BaseModel):
      title: str
      url: str
      snippet: str
      raw_content: str | None = None
      source_name: str
      published_date: datetime | None = None
      metadata: dict = {}
  ```
- [ ] Implement `DuckDuckGoAdapter`:
  - Use `duckduckgo-search` library (pip install `duckduckgo-search`)
  - Call `DDGS().text(query, max_results=max_results)`
  - Parse results into `SourceResult` list
  - Handle rate limiting with 1s delay between requests
  - Timeout: 10 seconds hard limit via `httpx` timeout
- [ ] Implement `WikipediaAdapter`:
  - Use Wikipedia REST API: `https://en.wikipedia.org/api/rest_v1/page/summary/{title}`
  - First search via `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}`
  - Fetch top 3 article summaries
  - Extract `extract` field as raw_content
  - No API key needed
- [ ] Implement `HackerNewsAdapter`:
  - Use Algolia HN API: `http://hn.algolia.com/api/v1/search?query={query}&tags=story`
  - Fetch top 10 stories by relevance
  - For top 5 stories, also fetch comments via `http://hn.algolia.com/api/v1/items/{id}`
  - Extract story text + top-level comment text as raw_content
  - Sort by points (proxy for community quality signal)
- [ ] Implement `SourceRegistry` in `registry.py`:
  ```python
  class SourceRegistry:
      _adapters: dict[str, SourceAdapter] = {}

      def register(self, adapter: SourceAdapter): ...
      def get(self, name: str) -> SourceAdapter: ...
      def get_all(self) -> list[SourceAdapter]: ...
      def get_available(self) -> list[SourceAdapter]: ...
  ```
  - Auto-register all adapters on app startup via `lifespan`
- [ ] Write tests for each adapter with mocked HTTP responses using `respx` or `pytest-httpx`
  - Test: valid response parsing
  - Test: empty results handling
  - Test: timeout handling
  - Test: malformed response handling

**Acceptance Criteria:**
- Each adapter returns a `list[SourceResult]` for any query
- Each adapter handles timeouts and errors gracefully (returns empty list, doesn't crash)
- All adapter tests pass with mocked HTTP

---

##### Task 1.3 — Document Ingestion Pipeline

**Owner:** Backend Engineer
**Files:** `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/extractors.py`, `backend/app/ingestion/chunker.py`, `backend/app/ingestion/embedder.py`
**Duration:** Days 3–4

- [ ] Implement `ContentExtractor` in `extractors.py`:
  - `extract_from_html(html: str) -> str` — strip tags, extract main content using `beautifulsoup4` + `readability-lxml`
  - `extract_from_text(text: str) -> str` — clean whitespace, normalize unicode
  - `extract_from_snippet(snippet: str, url: str) -> str` — use snippet as-is when full content unavailable
  - Handle encoding issues (UTF-8 normalize, strip null bytes)
- [ ] Implement `TextChunker` in `chunker.py`:
  - Recursive character text splitter (inspired by LangChain's, but no LangChain dependency yet)
  - Parameters: `chunk_size=512` tokens, `chunk_overlap=64` tokens
  - Split hierarchy: `\n\n` → `\n` → `. ` → ` ` → character
  - Each chunk preserves metadata:
    ```python
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
    ```
  - Token counting via `tiktoken` (cl100k_base encoding)
- [ ] Implement `EmbeddingGenerator` in `embedder.py`:
  - Primary: HuggingFace Inference API (`all-MiniLM-L6-v2`, 384 dimensions)
    ```
    POST https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2
    Headers: Authorization: Bearer {HF_API_TOKEN}
    Body: {"inputs": ["chunk text 1", "chunk text 2", ...]}
    ```
  - Batch embedding: send up to 32 chunks per API call
  - Fallback: local `sentence-transformers` if HF API is unavailable (add to requirements)
  - Retry: 2 retries with 1s backoff on 429/503
  - Return: `list[list[float]]` (list of 384-dim vectors)
- [ ] Implement `IngestionPipeline` in `pipeline.py`:
  ```python
  class IngestionPipeline:
      async def process(self, source_results: list[SourceResult]) -> list[Chunk]:
          # 1. Extract clean text from each source result
          # 2. Chunk each document
          # 3. Generate embeddings in batches
          # 4. Return chunks with embeddings attached
  ```
- [ ] Write tests:
  - Test chunker produces correct sizes and overlaps
  - Test chunker preserves metadata
  - Test extractor handles malformed HTML
  - Test embedder batching logic
  - Test full pipeline end-to-end with mock data

**Acceptance Criteria:**
- Pipeline converts `list[SourceResult]` → `list[Chunk]` with embeddings
- Chunks respect size limits (±10% tolerance)
- Metadata is preserved through the pipeline

---

##### Task 1.4 — ChromaDB Vector Store Integration

**Owner:** Backend Engineer
**Files:** `backend/app/db/vector_store.py`
**Duration:** Day 4

- [ ] Implement `VectorStore` class wrapping ChromaDB:
  ```python
  class VectorStore:
      def __init__(self, persist_dir: str):
          self.client = chromadb.PersistentClient(path=persist_dir)

      def get_or_create_collection(self, name: str) -> Collection: ...

      async def upsert_chunks(self, collection_name: str, chunks: list[Chunk],
                               embeddings: list[list[float]]) -> None:
          # Batch upsert: ids, documents, embeddings, metadatas

      async def query(self, collection_name: str, query_embedding: list[float],
                      n_results: int = 15, where: dict | None = None) -> list[RetrievedChunk]:
          # Returns chunks ranked by cosine similarity

      async def delete_collection(self, name: str) -> None: ...
      async def get_collection_stats(self, name: str) -> dict: ...
  ```
- [ ] Define `RetrievedChunk` model:
  ```python
  class RetrievedChunk(BaseModel):
      chunk: Chunk
      score: float           # Cosine similarity score
      citation_id: int       # Auto-assigned for synthesis (1, 2, 3...)
  ```
- [ ] Collection naming: `session_{session_id}` for session-scoped, `global` for persistent
- [ ] ChromaDB persistence directory: configurable via `CHROMA_PERSIST_DIR` env var
- [ ] Tests:
  - Test upsert + query returns correct results
  - Test metadata filtering works
  - Test empty collection query returns empty list

**Acceptance Criteria:**
- Chunks can be stored and retrieved by semantic similarity
- Metadata filtering works (e.g., filter by `source_name`)
- Data persists across application restarts (Docker volume)

---

##### Task 1.5 — Query Analyzer + LLM Integration

**Owner:** Backend Lead
**Files:** `backend/app/core/query_analyzer.py`, `backend/app/core/synthesizer.py`
**Duration:** Days 4–5

- [ ] Implement `QueryAnalyzer` in `query_analyzer.py`:
  - Uses Groq API to decompose complex queries into 2–4 sub-queries
  - Groq client setup:
    ```python
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    ```
  - System prompt for decomposition:
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
  - Parse response as JSON array (with fallback: split on newlines if JSON parse fails)
  - Model: `llama-3.1-70b-versatile` via Groq
  - Temperature: 0.1 (deterministic decomposition)
- [ ] Implement `Synthesizer` in `synthesizer.py`:
  - Takes `list[RetrievedChunk]` + original `query` → streams cited answer
  - System prompt:
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
  - Streaming: use Groq's `stream=True` parameter
  - Yield token-by-token as they arrive from Groq
  - Temperature: 0.3 (balanced factual + readable)
  - Max tokens: 2048
- [ ] Tests:
  - Test query decomposition produces valid JSON arrays
  - Test synthesis includes citation markers
  - Test synthesis handles empty chunk list gracefully
  - Mock Groq API responses for deterministic testing

**Acceptance Criteria:**
- Complex queries are decomposed into 2–4 focused sub-queries
- Synthesis produces structured, cited answers
- Streaming works (yields partial tokens)

---

##### Task 1.6 — Research Orchestrator

**Owner:** Backend Lead
**Files:** `backend/app/core/orchestrator.py`, `backend/app/api/routes/research.py`
**Duration:** Days 5–6

- [ ] Implement `ResearchOrchestrator` in `orchestrator.py`:
  ```python
  class ResearchOrchestrator:
      def __init__(self, query_analyzer, source_registry, ingestion_pipeline,
                   vector_store, synthesizer): ...

      async def research(self, query: str, sources: list[str] | None = None
                        ) -> AsyncGenerator[SSEEvent, None]:
          # Step 1: Analyze query → sub-queries
          yield SSEEvent(event="status", data={"phase": "decomposing"})
          sub_queries = await self.query_analyzer.decompose(query)

          # Step 2: Search all sources (asyncio.gather for Phase 1)
          yield SSEEvent(event="status", data={"phase": "searching", "sources_active": len(adapters)})
          tasks = []
          for adapter in adapters:
              for sub_query in sub_queries:
                  tasks.append(self._search_with_status(adapter, sub_query))
          all_results = await asyncio.gather(*tasks, return_exceptions=True)
          # Flatten, filter exceptions, yield source_complete events

          # Step 3: Ingest results
          yield SSEEvent(event="status", data={"phase": "processing"})
          chunks = await self.ingestion_pipeline.process(flat_results)

          # Step 4: Store in vector DB
          session_id = f"session_{uuid4().hex[:12]}"
          embeddings = [c.embedding for c in chunks]
          await self.vector_store.upsert_chunks(session_id, chunks, embeddings)

          # Step 5: Retrieve top-K
          query_embedding = await self.ingestion_pipeline.embedder.embed([query])
          relevant = await self.vector_store.query(session_id, query_embedding[0], n_results=15)

          # Step 6: Synthesize (streaming)
          yield SSEEvent(event="status", data={"phase": "synthesizing"})
          async for token in self.synthesizer.stream(relevant, query):
              yield SSEEvent(event="token", data={"content": token})

          # Step 7: Complete
          yield SSEEvent(event="complete", data={
              "session_id": session_id,
              "sources_used": len(flat_results),
              "citations": [build_citation(c) for c in relevant]
          })
  ```
- [ ] Implement SSE endpoint in `research.py`:
  ```python
  @router.post("/api/v1/research")
  async def research(request: ResearchRequest):
      orchestrator = get_orchestrator()
      return EventSourceResponse(orchestrator.research(request.query, request.sources))
  ```
- [ ] Define request/response models:
  ```python
  class ResearchRequest(BaseModel):
      query: str = Field(..., min_length=3, max_length=2000)
      sources: list[str] | None = None  # None = use all available
      depth: Literal["quick", "standard", "deep"] = "standard"

  class Citation(BaseModel):
      id: int
      title: str
      url: str
      source_name: str
      relevance_score: float
  ```
- [ ] Error handling: wrap each source search in try/except, log failures, continue with remaining sources
- [ ] Tests:
  - Test full pipeline end-to-end with mocked sources and mocked LLM
  - Test partial source failure (1 of 3 sources fails → still returns results)
  - Test empty results handling

**Acceptance Criteria:**
- `POST /api/v1/research` streams SSE events from decomposition through synthesis
- Partial source failures don't crash the pipeline
- Complete event includes session_id and citations

---

#### Sprint 2 (Days 8–14): Frontend + Docker + Testing

##### Task 1.7 — React Frontend with Streaming UI

**Owner:** Frontend Engineer
**Files:** `frontend/src/app/page.tsx`, `frontend/src/components/SearchBar.tsx`, `frontend/src/components/ResearchStream.tsx`, `frontend/src/components/CitationCard.tsx`, `frontend/src/components/SourceIndicator.tsx`, `frontend/src/hooks/useSSE.ts`
**Duration:** Days 8–10

- [ ] Initialize Next.js 14 project with TypeScript + Tailwind CSS:
  ```bash
  npx create-next-app@latest frontend --typescript --tailwind --app --src-dir
  ```
- [ ] Install dependencies: `npm install eventsource-parser`
- [ ] Implement `useSSE` hook in `hooks/useSSE.ts`:
  ```typescript
  // Custom hook that:
  // 1. Opens fetch() with ReadableStream to the SSE endpoint
  // 2. Parses SSE events using eventsource-parser
  // 3. Dispatches events to state handlers
  // 4. Handles connection errors and retries
  // 5. Returns: { status, tokens, citations, sourceStatuses, isStreaming, error }
  ```
- [ ] Implement `SearchBar` component:
  - Large centered input (similar to Perplexity's landing page)
  - Source toggles: checkboxes for DDG, Wikipedia, HackerNews (all on by default)
  - Submit button + Enter key handler
  - Disabled state while streaming
  - Query validation (min 3 chars, max 2000)
- [ ] Implement `SourceIndicator` component:
  - Shows each active source with status: `searching...` → `✓ 8 results (1.2s)` → `✗ failed`
  - Horizontal row of pills/badges
  - Updates in real-time as `source_complete` SSE events arrive
  - Color coding: gray (waiting) → blue (searching) → green (done) → red (failed)
- [ ] Implement `ResearchStream` component:
  - Renders streamed markdown tokens as they arrive
  - Uses `react-markdown` + `remark-gfm` for rendering
  - Citation references `[1]` rendered as clickable superscripts
  - Typing indicator while tokens are streaming
  - Smooth scroll-to-bottom as content grows
  - Phase indicator at top: "Decomposing query..." → "Searching 3 sources..." → "Synthesizing..."
- [ ] Implement `CitationCard` component:
  - Displayed in a sidebar or collapsible section below the answer
  - Shows: citation number, title, source name (with icon), URL (linked), relevance score bar
  - Clicking opens the source URL in new tab
  - Grouped by source type
- [ ] Main page layout:
  ```
  ┌──────────────────────────────────────┐
  │              SIFT                     │
  │     [Search bar with source toggles] │
  ├──────────────────────────────────────┤
  │  [Source indicators: DDG ✓ | Wiki ✓] │
  ├──────────────────┬───────────────────┤
  │                  │                   │
  │  [Streamed       │  [Citations       │
  │   Answer with    │   sidebar with    │
  │   markdown       │   source cards]   │
  │   rendering]     │                   │
  │                  │                   │
  └──────────────────┴───────────────────┘
  ```
- [ ] Responsive design: single-column on mobile (citations below answer), two-column on desktop
- [ ] Dark mode support via Tailwind `dark:` classes
- [ ] Loading states, error states, empty states

**Acceptance Criteria:**
- User can type a query, select sources, and submit
- Answer streams in real-time with visible markdown formatting
- Source statuses update as they complete
- Citations are displayed and clickable
- Works on mobile and desktop

---

##### Task 1.8 — Docker Compose Full Stack

**Owner:** Backend Lead
**Files:** `docker-compose.yml`, `docker-compose.dev.yml`, `frontend/Dockerfile`, `Makefile`
**Duration:** Day 11

- [ ] Create production `docker-compose.yml`:
  ```yaml
  services:
    backend:
      build: ./backend
      ports: ["8000:8000"]
      environment:
        - GROQ_API_KEY=${GROQ_API_KEY}
        - CHROMA_PERSIST_DIR=/data/chroma
      volumes:
        - chroma_data:/data/chroma
      healthcheck:
        test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]

    frontend:
      build: ./frontend
      ports: ["3000:3000"]
      environment:
        - NEXT_PUBLIC_API_URL=http://backend:8000
      depends_on:
        backend:
          condition: service_healthy

  volumes:
    chroma_data:
  ```
- [ ] Create `docker-compose.dev.yml` with:
  - Volume mounts for hot reload (`./backend/app:/app/app`)
  - `uvicorn --reload` for backend
  - `npm run dev` for frontend
- [ ] Create `Makefile`:
  ```makefile
  dev:           docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
  prod:          docker compose up --build -d
  test:          docker compose exec backend pytest -v
  test-coverage: docker compose exec backend pytest --cov=app --cov-report=html
  lint:          docker compose exec backend ruff check app/
  logs:          docker compose logs -f
  down:          docker compose down
  clean:         docker compose down -v
  ```
- [ ] Frontend `Dockerfile`:
  - Multi-stage: Node 18-alpine build stage → Node 18-alpine runtime
  - `npm ci` for deterministic installs
  - `npm run build` → `npm start`

**Acceptance Criteria:**
- `make dev` starts full stack with hot reload
- `make prod` starts production build
- `make test` runs backend tests inside container

---

##### Task 1.9 — Core Test Suite

**Owner:** Entire team
**Files:** `backend/tests/**`
**Duration:** Days 12–13

- [ ] Create `conftest.py` with shared fixtures:
  ```python
  @pytest.fixture
  def mock_groq_client():
      """Mocked Groq client that returns deterministic responses."""

  @pytest.fixture
  def sample_source_results():
      """10 sample SourceResult objects for testing."""

  @pytest.fixture
  def temp_chroma_dir(tmp_path):
      """Temporary ChromaDB directory for test isolation."""

  @pytest.fixture
  def vector_store(temp_chroma_dir):
      """VectorStore instance with temporary storage."""
  ```
- [ ] Test files and minimum test counts:
  | File | Min Tests | Key Scenarios |
  |------|-----------|--------------|
  | `test_sources/test_duckduckgo.py` | 5 | Valid response, empty results, timeout, rate limit, malformed HTML |
  | `test_sources/test_wikipedia.py` | 4 | Valid response, article not found, API error, encoding |
  | `test_sources/test_hackernews.py` | 4 | Valid response, no comments, timeout, empty results |
  | `test_ingestion/test_chunker.py` | 6 | Size limits, overlap, metadata preservation, empty input, unicode, very short text |
  | `test_ingestion/test_extractor.py` | 5 | HTML stripping, script removal, encoding, empty input, malformed HTML |
  | `test_ingestion/test_embedder.py` | 4 | Batch size, API fallback, retry on 429, dimension validation |
  | `test_ingestion/test_pipeline.py` | 3 | Full pipeline, empty input, mixed source types |
  | `test_db/test_vector_store.py` | 5 | Upsert, query, metadata filter, empty query, collection stats |
  | `test_core/test_query_analyzer.py` | 4 | Complex query decomposition, simple query passthrough, malformed LLM response, empty query |
  | `test_core/test_synthesizer.py` | 4 | Streaming output, citation format, empty chunks, max token handling |
  | `test_core/test_orchestrator.py` | 5 | Full pipeline, partial source failure, all sources fail, timeout handling, SSE event format |
  | `test_api/test_research.py` | 4 | Valid request, invalid request, SSE format, concurrent requests |

- [ ] Coverage target: **70%+ overall**, **90%+ on critical paths** (orchestrator, retrieval, synthesis)
- [ ] Set up `pytest.ini`:
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

**Acceptance Criteria:**
- `pytest` passes with 0 failures
- Coverage report shows 70%+ overall
- No test depends on external APIs (all mocked)

---

##### Task 1.10 — Documentation + Demo Script

**Owner:** Backend Lead
**Duration:** Day 14

- [ ] Update README with actual screenshots/GIF of the working product
- [ ] Write `QUICKSTART.md` with 5-minute setup guide
- [ ] Create `demo_queries.md` with 10 impressive demo queries that showcase multi-source synthesis
- [ ] Record a 60-second terminal demo (optional: use `asciinema`)
- [ ] Verify Docker setup works from a clean clone on a fresh machine

**Acceptance Criteria:**
- A new developer can clone the repo and have it running in under 5 minutes
- Demo queries produce impressive, well-cited answers

---

**Phase 1 Deliverable:** Enter a question → get a cited, multi-source answer streamed in real-time. Dockerized, tested, documented.

**Exit Criteria for Phase 1:**
- [ ] All 10 tasks completed and merged to `main`
- [ ] 70%+ test coverage
- [ ] Docker Compose starts cleanly from a fresh clone
- [ ] 10 demo queries produce quality answers
- [ ] No critical bugs in the happy path

---
---

### Phase 2 — Memory, Hybrid Retrieval & Resilience

**Duration:** 4 Weeks (Sprints 3–6)
**Goal:** Production-grade system with hybrid retrieval, persistent sessions, Celery-based parallelism, resilience patterns, and deployment to free tier.
**Team:** 2 backend engineers, 1 frontend engineer, 1 DevOps/infra

---

#### Sprint 3 (Week 3): Hybrid Retrieval + BM25

##### Task 2.1 — BM25 Sparse Retrieval Implementation

**Owner:** Backend Engineer
**Files:** `backend/app/retrieval/bm25.py`
**Duration:** 2 days

- [ ] Implement BM25 scoring from scratch (no external dependency for understanding and interview talking points):
  ```python
  class BM25Index:
      """
      Okapi BM25 implementation for sparse keyword retrieval.
      Operates over the same chunk corpus stored in ChromaDB.

      Parameters:
        k1 = 1.5  (term frequency saturation)
        b  = 0.75 (document length normalization)
      """
      def __init__(self, k1: float = 1.5, b: float = 0.75): ...
      def fit(self, documents: list[str]) -> None:
          # Build inverted index: term → list[(doc_idx, term_freq)]
          # Compute document lengths and average document length
          # Compute IDF for each term: log((N - df + 0.5) / (df + 0.5) + 1)
      def query(self, query: str, top_k: int = 50) -> list[tuple[int, float]]:
          # Tokenize query → for each term, score each document
          # BM25(q,d) = Σ IDF(t) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl/avgdl))
  ```
- [ ] Tokenizer: simple whitespace + lowercasing + stop word removal (use NLTK stop words or hardcoded English list)
- [ ] Index persistence: pickle the fitted index alongside ChromaDB data
- [ ] Incremental update: `add_documents()` method to add new docs without refitting entire index
- [ ] Tests:
  - Test exact keyword match ranks higher than semantic-only match
  - Test empty query returns empty results
  - Test single-document corpus
  - Test index persistence (save + load)

**Acceptance Criteria:**
- BM25 index builds over chunk corpus
- Queries return ranked results by BM25 score
- Index can be incrementally updated

---

##### Task 2.2 — Reciprocal Rank Fusion (RRF) + Hybrid Retriever

**Owner:** Backend Engineer
**Files:** `backend/app/retrieval/hybrid_retriever.py`, `backend/app/retrieval/dense.py`
**Duration:** 2 days

- [ ] Extract dense retrieval into `dense.py`:
  ```python
  class DenseRetriever:
      """Wraps ChromaDB vector search."""
      async def query(self, query_embedding: list[float], collection: str,
                      top_k: int = 50) -> list[tuple[str, float]]:
          # Returns (chunk_id, cosine_similarity_score) pairs
  ```
- [ ] Implement `HybridRetriever` in `hybrid_retriever.py`:
  ```python
  class HybridRetriever:
      def __init__(self, dense: DenseRetriever, bm25: BM25Index, k: int = 60):
          self.dense = dense
          self.bm25 = bm25
          self.k = k  # RRF constant

      async def retrieve(self, query: str, query_embedding: list[float],
                         collection: str, top_k: int = 15) -> list[RetrievedChunk]:
          # 1. Get top-50 from BM25
          sparse_results = self.bm25.query(query, top_k=50)

          # 2. Get top-50 from dense retrieval
          dense_results = await self.dense.query(query_embedding, collection, top_k=50)

          # 3. Reciprocal Rank Fusion
          fused = self._rrf_fuse(sparse_results, dense_results)

          # 4. Return top-K with scores
          return fused[:top_k]

      def _rrf_fuse(self, *result_lists) -> list[tuple[str, float]]:
          scores: dict[str, float] = defaultdict(float)
          for results in result_lists:
              for rank, (doc_id, _) in enumerate(results):
                  scores[doc_id] += 1.0 / (self.k + rank + 1)
          return sorted(scores.items(), key=lambda x: x[1], reverse=True)
  ```
- [ ] Integrate into `orchestrator.py`: replace direct ChromaDB query with `HybridRetriever`
- [ ] Tests:
  - Test RRF boosts documents appearing in both rankings
  - Test RRF handles non-overlapping result sets
  - Test RRF with single result list (degrades to rank-based scoring)
  - Test hybrid retriever end-to-end with mock BM25 + mock dense
  - Benchmark: measure retrieval quality on a small golden dataset (10 queries with known relevant docs)

**Acceptance Criteria:**
- Hybrid retrieval produces better results than dense-only or sparse-only (measured on test queries)
- RRF fusion is correct (verified by unit tests on known inputs)
- Orchestrator uses hybrid retrieval by default

---

##### Task 2.3 — Near-Duplicate Detection

**Owner:** Backend Engineer
**Files:** `backend/app/retrieval/deduplication.py`
**Duration:** 1 day

- [ ] Implement MinHash-based near-duplicate detection:
  ```python
  class MinHashDeduplicator:
      """
      Detects near-duplicate documents before embedding to save
      vector DB space and prevent redundant retrieval results.
      Uses MinHash signatures with LSH (Locality-Sensitive Hashing).
      """
      def __init__(self, num_perm: int = 128, threshold: float = 0.8): ...

      def compute_signature(self, text: str) -> MinHashSignature:
          # Tokenize into 3-grams (shingles)
          # Compute MinHash signature with num_perm permutations

      def find_duplicates(self, documents: list[str]) -> list[set[int]]:
          # Returns groups of duplicate document indices
          # Documents within a group have Jaccard similarity > threshold

      def deduplicate(self, chunks: list[Chunk]) -> list[Chunk]:
          # Remove duplicates, keeping the chunk from the highest-authority source
          # Authority ranking: ArXiv > Wikipedia > HackerNews > Reddit > DuckDuckGo
  ```
- [ ] Use `datasketch` library for MinHash implementation (pip install `datasketch`)
- [ ] Integrate into `IngestionPipeline`: deduplicate after extraction, before embedding
- [ ] Tests:
  - Test: identical documents detected as duplicates
  - Test: slightly rephrased documents (>80% overlap) detected
  - Test: genuinely different documents NOT flagged
  - Test: authority-based selection keeps the right document

**Acceptance Criteria:**
- Duplicate and near-duplicate content is removed before embedding
- Deduplication runs in <100ms for 100 documents
- Reduces embedding API calls by 15–30% on typical queries

---

#### Sprint 4 (Week 4): Celery + Redis Infrastructure

##### Task 2.4 — Celery Worker Setup + Task Definitions

**Owner:** Backend Lead
**Files:** `backend/app/workers/celery_app.py`, `backend/app/workers/tasks.py`, `backend/app/workers/callbacks.py`
**Duration:** 2 days

- [ ] Add dependencies: `celery[redis]==5.3.6`, `redis==5.0.1`
- [ ] Configure Celery in `celery_app.py`:
  ```python
  from celery import Celery

  celery_app = Celery(
      "sift",
      broker=settings.celery_broker_url,  # Upstash Redis URL
      backend=settings.celery_result_backend,
  )
  celery_app.conf.update(
      task_serializer="json",
      result_serializer="json",
      accept_content=["json"],
      timezone="UTC",
      task_soft_time_limit=15,   # Soft timeout: 15 seconds
      task_time_limit=20,        # Hard timeout: 20 seconds
      task_acks_late=True,       # Ack after completion (for reliability)
      worker_prefetch_multiplier=1,  # One task at a time per worker
      task_routes={
          "app.workers.tasks.search_source": {"queue": "search"},
          "app.workers.tasks.process_results": {"queue": "ingestion"},
      },
  )
  ```
- [ ] Define tasks in `tasks.py`:
  ```python
  @celery_app.task(bind=True, max_retries=2, default_retry_delay=2)
  def search_source(self, source_name: str, sub_queries: list[str]) -> dict:
      """
      Search a single source with all sub-queries.
      Returns serialized list of SourceResult dicts.
      Retries on transient failures (timeout, 429, 503).
      """

  @celery_app.task
  def process_results(search_results: list[dict], session_id: str) -> dict:
      """
      Chord callback: receives results from all source tasks.
      Runs: deduplication → chunking → embedding → vector store upsert.
      Returns: session_id + chunk count + processing stats.
      """
  ```
- [ ] Implement chord-based fan-out in orchestrator:
  ```python
  from celery import chord

  # Replace asyncio.gather with Celery chord
  search_tasks = group([
      search_source.s(adapter.name, sub_queries)
      for adapter in selected_adapters
  ])
  result = chord(search_tasks)(process_results.s(session_id=session_id))
  ```
- [ ] Update `docker-compose.yml`:
  ```yaml
  services:
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]

    worker:
      build: ./backend
      command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 -Q search,ingestion
      depends_on: [redis]
      environment:
        - CELERY_BROKER_URL=redis://redis:6379/0

    backend:
      # ... existing config ...
      depends_on: [redis, worker]
      environment:
        - CELERY_BROKER_URL=redis://redis:6379/0
  ```
- [ ] Tests:
  - Test task execution in eager mode (`CELERY_ALWAYS_EAGER=True`)
  - Test chord completion triggers callback
  - Test task retry on simulated failure
  - Test task timeout handling

**Acceptance Criteria:**
- Source searches execute as Celery tasks on worker processes
- Chord callback aggregates results from all sources
- Worker is a separate Docker service
- Tasks respect timeout and retry limits

---

##### Task 2.5 — Redis Caching Layer

**Owner:** Backend Engineer
**Files:** `backend/app/cache/redis_cache.py`, `backend/app/cache/embedding_cache.py`
**Duration:** 2 days

- [ ] Implement `ResearchCache` in `redis_cache.py`:
  ```python
  class ResearchCache:
      """
      Two-tier caching with stale-while-revalidate semantics.

      Tier 1: Query hash → full synthesized result (TTL: 24 hours)
      Tier 2: Source + query hash → raw source results (TTL: 6 hours)
      """
      def __init__(self, redis_url: str):
          self.redis = aioredis.from_url(redis_url)
          self.fresh_ttl = 3600 * 24      # 24 hours
          self.stale_threshold = 3600 * 20 # Stale after 20 hours

      async def get_research(self, query_hash: str) -> CacheResult | None:
          # Returns CacheResult with .is_fresh and .data

      async def set_research(self, query_hash: str, data: dict) -> None:
          # Store with TTL

      async def get_source_results(self, source: str, query_hash: str) -> list[dict] | None:
          # Tier 2 cache for raw source results

      async def set_source_results(self, source: str, query_hash: str, data: list[dict]) -> None:

      @staticmethod
      def hash_query(query: str) -> str:
          # Normalize: lowercase, strip whitespace, remove punctuation
          # SHA-256 hash for consistent key
  ```
- [ ] Implement stale-while-revalidate logic in orchestrator:
  ```python
  cache_result = await cache.get_research(query_hash)
  if cache_result and cache_result.is_fresh:
      yield from stream_cached_result(cache_result.data)
      return
  if cache_result and not cache_result.is_fresh:
      yield from stream_cached_result(cache_result.data)  # Return stale immediately
      refresh_research.delay(query_hash, query)  # Background refresh via Celery
      return
  # Cache miss → full pipeline
  ```
- [ ] Implement `EmbeddingCache` in `embedding_cache.py`:
  - LRU in-memory cache (max 10,000 entries) for embedding lookups
  - Key: hash of chunk text → Value: embedding vector
  - Avoids re-embedding identical chunks across queries
  - Use Python's `functools.lru_cache` or a `cachetools.LRUCache`
- [ ] Tests:
  - Test fresh cache hit returns immediately
  - Test stale cache hit returns stale + triggers background refresh
  - Test cache miss triggers full pipeline
  - Test cache key normalization (same query with different casing → same hash)
  - Test embedding cache hit rate on repeated queries

**Acceptance Criteria:**
- Repeat queries return in <300ms (cache hit)
- Stale results are served immediately while background refresh runs
- Embedding cache reduces API calls by 30%+ on related queries

---

##### Task 2.6 — Circuit Breaker + Rate Limiter

**Owner:** Backend Engineer
**Files:** `backend/app/resilience/circuit_breaker.py`, `backend/app/resilience/rate_limiter.py`, `backend/app/resilience/retry.py`
**Duration:** 2 days

- [ ] Implement `CircuitBreaker` in `circuit_breaker.py`:
  ```python
  class CircuitBreaker:
      """
      Per-source circuit breaker with Redis-backed state.
      State machine: CLOSED → OPEN → HALF_OPEN → CLOSED

      Redis keys:
        cb:{source}:state      → "closed" | "open" | "half_open"
        cb:{source}:failures   → int (failure count in window)
        cb:{source}:last_fail  → timestamp
        cb:{source}:opened_at  → timestamp
      """
      def __init__(self, source_name: str, redis: Redis,
                   failure_threshold: int = 5,
                   failure_window: int = 60,
                   cooldown: int = 30):

      async def __aenter__(self):
          state = await self._get_state()
          if state == "open":
              if await self._should_try_half_open():
                  await self._set_state("half_open")
              else:
                  raise CircuitOpenError(self.source_name, self.retry_after)
          return self

      async def __aexit__(self, exc_type, exc_val, exc_tb):
          if exc_type is None:
              await self._record_success()
          else:
              await self._record_failure()

      async def _record_failure(self): ...
      async def _record_success(self): ...
      async def _get_state(self) -> str: ...
      async def _set_state(self, state: str): ...
      async def _should_try_half_open(self) -> bool: ...
  ```
- [ ] Implement `TokenBucketRateLimiter` in `rate_limiter.py`:
  ```python
  class TokenBucketRateLimiter:
      """
      Per-source rate limiter using Redis-backed token bucket.

      Redis keys:
        rl:{source}:tokens    → float (current tokens)
        rl:{source}:last_refill → timestamp

      Refill rate and bucket size configured per source:
        DuckDuckGo: 1 req/sec, bucket 5
        Reddit:     1 req/2sec, bucket 3
        HN:         2 req/sec, bucket 10
        ArXiv:      1 req/3sec, bucket 3
        Wikipedia:  5 req/sec, bucket 20
      """
      async def acquire(self, source: str, timeout: float = 10.0) -> bool:
          # Try to consume 1 token
          # If no tokens, wait up to timeout with polling
          # Return True if acquired, False if timed out
  ```
- [ ] Implement retry decorator in `retry.py`:
  ```python
  def with_retry(max_retries: int = 2, backoff_base: float = 1.0,
                 retryable_exceptions: tuple = (TimeoutError, ConnectionError)):
      """
      Exponential backoff retry decorator.
      Delay: backoff_base * 2^attempt (1s, 2s, 4s...)
      Jitter: ±20% random to avoid thundering herd
      """
  ```
- [ ] Integrate into source search tasks:
  ```python
  @celery_app.task(bind=True, max_retries=2)
  def search_source(self, source_name, sub_queries):
      circuit_breaker = CircuitBreaker(source_name, redis)
      rate_limiter = TokenBucketRateLimiter(redis)

      async with circuit_breaker:
          await rate_limiter.acquire(source_name)
          adapter = source_registry.get(source_name)
          return await adapter.search(sub_queries)
  ```
- [ ] Tests:
  - Test circuit breaker opens after N failures
  - Test circuit breaker transitions to half-open after cooldown
  - Test circuit breaker closes on successful half-open request
  - Test rate limiter blocks when tokens exhausted
  - Test rate limiter refills over time
  - Test retry with exponential backoff timing
  - Test retry gives up after max retries

**Acceptance Criteria:**
- One source failing does not affect other sources
- Circuit breaker prevents hammering a down source
- Rate limiter respects per-source rate limits
- All state is in Redis (shared across workers)

---

#### Sprint 5 (Week 5): Persistent Sessions + Additional Sources

##### Task 2.7 — PostgreSQL Schema + Session Persistence (Supabase)

**Owner:** Backend Lead
**Files:** `backend/app/db/models.py`, `backend/app/db/session.py`, `backend/app/api/routes/sessions.py`
**Duration:** 2 days

- [ ] Add dependencies: `sqlalchemy[asyncio]==2.0.25`, `asyncpg==0.29.0`, `alembic==1.13.1`
- [ ] Define SQLAlchemy models in `models.py`:
  ```python
  class User(Base):
      __tablename__ = "users"
      id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
      email: Mapped[str] = mapped_column(unique=True, index=True)
      created_at: Mapped[datetime] = mapped_column(default=func.now())
      sessions: Mapped[list["ResearchSession"]] = relationship(back_populates="user")

  class ResearchSession(Base):
      __tablename__ = "research_sessions"
      id: Mapped[str] = mapped_column(primary_key=True)  # "session_xxx"
      user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
      title: Mapped[str]               # Auto-generated from first query
      created_at: Mapped[datetime]
      updated_at: Mapped[datetime]
      query_count: Mapped[int] = mapped_column(default=1)
      sources_used: Mapped[list[str]] = mapped_column(ARRAY(String))
      status: Mapped[str] = mapped_column(default="active")  # active, archived

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
      compressed_context: Mapped[str | None]  # For progressive summarization

      session: Mapped["ResearchSession"] = relationship(back_populates="turns")

  class SourceCache(Base):
      __tablename__ = "source_cache"
      id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
      query_hash: Mapped[str] = mapped_column(index=True)
      source_name: Mapped[str]
      results_json: Mapped[dict] = mapped_column(JSON)
      fetched_at: Mapped[datetime]
      expires_at: Mapped[datetime]
  ```
- [ ] Set up Alembic for migrations:
  - `alembic init migrations`
  - Configure `env.py` to use async engine
  - Generate initial migration: `alembic revision --autogenerate -m "initial schema"`
- [ ] Implement async session management in `session.py`:
  ```python
  async_engine = create_async_engine(settings.supabase_url)
  async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)

  async def get_db() -> AsyncGenerator[AsyncSession, None]:
      async with async_session_factory() as session:
          yield session
  ```
- [ ] Implement session CRUD endpoints in `sessions.py`:
  - `GET /api/v1/sessions` — list user's sessions (paginated, sorted by updated_at)
  - `GET /api/v1/sessions/{id}` — get session with all turns
  - `DELETE /api/v1/sessions/{id}` — soft-delete (set status="archived")
  - `PATCH /api/v1/sessions/{id}` — rename session
- [ ] Update orchestrator to persist sessions:
  - Create `ResearchSession` on first query
  - Create `ResearchTurn` for each query/followup
  - Store synthesized answer + citations in turn
- [ ] Tests:
  - Test session creation, retrieval, listing, archival
  - Test turn creation and ordering
  - Test pagination

**Acceptance Criteria:**
- Research sessions are persisted to PostgreSQL (Supabase)
- Sessions can be listed, viewed, and archived via API
- Each turn stores the query, answer, citations, and performance metrics

---

##### Task 2.8 — Follow-up Questions + Context Compression

**Owner:** Backend Lead
**Files:** `backend/app/core/context_manager.py`, `backend/app/api/routes/research.py` (update)
**Duration:** 2 days

- [ ] Implement `ContextManager` in `context_manager.py`:
  ```python
  class ContextManager:
      """
      Manages growing research session context.
      Implements progressive summarization to prevent context window overflow.
      """
      MAX_CONTEXT_TOKENS = 4096  # Budget for historical context in synthesis prompt

      async def build_context(self, session_id: str, db: AsyncSession) -> str:
          turns = await self._get_session_turns(session_id, db)

          if self._count_tokens(turns) <= self.MAX_CONTEXT_TOKENS:
              return self._format_full_context(turns)

          # Compress: summarize older turns, keep recent turns in full
          compressed = await self._compress_older_turns(turns)
          return compressed

      async def _compress_older_turns(self, turns: list[ResearchTurn]) -> str:
          # Keep last 2 turns in full
          # Summarize earlier turns using LLM:
          #   "Summarize these research findings, preserving:
          #    - Key conclusions with citation IDs
          #    - Unresolved contradictions
          #    - User's expressed preferences
          #    Keep under 500 tokens."
          # Cache the compressed context in the turn record
  ```
- [ ] Implement follow-up endpoint:
  ```python
  @router.post("/api/v1/research/{session_id}/followup")
  async def followup(session_id: str, request: FollowupRequest):
      # 1. Load session context (compressed if needed)
      context = await context_manager.build_context(session_id, db)

      # 2. Augment the follow-up query with session context
      augmented_query = f"Previous research context:\n{context}\n\nFollow-up question: {request.query}"

      # 3. Run research pipeline with augmented query
      # 4. Store new chunks in same session's ChromaDB collection
      # 5. Retrieve from session's full chunk corpus (not just new chunks)
      # 6. Synthesize with session awareness
  ```
- [ ] Update frontend to support follow-up:
  - After initial answer, show a follow-up input field
  - Follow-up queries sent to `/{session_id}/followup` endpoint
  - Streaming display appends to existing conversation view
- [ ] Tests:
  - Test context building with 1, 5, 10 turns
  - Test compression triggers when context exceeds token limit
  - Test follow-up retrieves from full session corpus
  - Test compressed context preserves key findings

**Acceptance Criteria:**
- Users can ask follow-up questions within a session
- Context is maintained across follow-ups
- Long sessions don't overflow the LLM context window

---

##### Task 2.9 — Additional Source Adapters: Reddit + ArXiv

**Owner:** Backend Engineer
**Files:** `backend/app/sources/reddit.py`, `backend/app/sources/arxiv.py`
**Duration:** 2 days

- [ ] Implement `RedditAdapter`:
  - Use Reddit JSON API (append `.json` to search URLs): `https://www.reddit.com/search.json?q={query}&sort=relevance&limit=10`
  - No OAuth needed for public search (but User-Agent header required)
  - Target subreddits for technical queries: r/programming, r/devops, r/machinelearning, r/Python, r/ExperiencedDevs
  - Extract: post title, selftext, top 5 comments (by score) as raw_content
  - Rate limit: 1 request per 2 seconds (Reddit's API rules)
  - Handle 429 responses with retry
- [ ] Implement `ArXivAdapter`:
  - Use ArXiv API: `http://export.arxiv.org/api/query?search_query=all:{query}&max_results=5`
  - Parse Atom XML response using `feedparser` library
  - Extract: title, authors, abstract, published date, PDF URL
  - Use abstract as raw_content (full paper text is Phase 3+)
  - Rate limit: 1 request per 3 seconds (ArXiv policy)
- [ ] Register both in `SourceRegistry`
- [ ] Update source indicator UI to include Reddit and ArXiv icons
- [ ] Tests for each adapter: valid response, empty results, timeout, rate limit, malformed response

**Acceptance Criteria:**
- Reddit and ArXiv are searchable sources
- Both respect rate limits
- Research queries now search 5 sources in parallel

---

#### Sprint 6 (Week 6): Auth, CI/CD, Deployment

##### Task 2.10 — User Authentication (Supabase Auth)

**Owner:** Backend Engineer
**Files:** `backend/app/api/dependencies.py`, frontend auth components
**Duration:** 2 days

- [ ] Integrate Supabase Auth:
  - Backend: verify JWT tokens from Supabase Auth in FastAPI dependency
  ```python
  async def get_current_user(authorization: str = Header(...)) -> User:
      token = authorization.replace("Bearer ", "")
      payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"])
      user_id = payload["sub"]
      # Get or create user in local DB
      return user
  ```
  - Frontend: `@supabase/supabase-js` for sign-up, sign-in, sign-out
  - Support: email/password + GitHub OAuth
- [ ] Protect endpoints: all `/research`, `/sessions`, `/knowledge` endpoints require auth
- [ ] Anonymous mode: allow unauthenticated research with session stored in localStorage (no persistence)
- [ ] Frontend auth flow:
  - Landing page: search bar works without auth
  - "Save session" prompts sign-in
  - Session sidebar only shows after sign-in
- [ ] Tests: auth middleware with valid/invalid/expired tokens

**Acceptance Criteria:**
- Users can sign up and sign in
- Authenticated users have persistent sessions
- Anonymous users can still use the research engine (but sessions are ephemeral)

---

##### Task 2.11 — CI/CD Pipeline

**Owner:** DevOps
**Files:** `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`
**Duration:** 1 day

- [ ] Create `ci.yml` (runs on every PR to `main`):
  ```yaml
  jobs:
    lint:
      - ruff check backend/app/
      - ruff format --check backend/app/
      - mypy backend/app/ --ignore-missing-imports

    test:
      services:
        redis:
          image: redis:7-alpine
      steps:
        - pip install -r backend/requirements.txt
        - pytest backend/tests/ -v --cov=app --cov-report=xml --cov-fail-under=85
        - upload coverage to Codecov (optional)

    frontend:
      - npm ci
      - npm run lint
      - npm run build  # Catch TypeScript errors
  ```
- [ ] Create `deploy.yml` (runs on push to `main`):
  ```yaml
  jobs:
    deploy-backend:
      - Trigger Render deploy hook (webhook URL)
    deploy-frontend:
      - Vercel auto-deploys from GitHub (no action needed, but verify)
  ```
- [ ] Add pre-commit config (`.pre-commit-config.yaml`):
  - ruff (lint + format)
  - mypy
  - pytest (fast tests only, exclude `@pytest.mark.slow`)
- [ ] Branch protection rules on `main`: require CI pass + 1 review

**Acceptance Criteria:**
- PRs are blocked if tests fail or coverage drops below 85%
- Merges to `main` auto-deploy to Render + Vercel
- Pre-commit hooks catch issues locally before push

---

##### Task 2.12 — Free-Tier Deployment

**Owner:** DevOps + Backend Lead
**Duration:** 2 days

- [ ] **Render setup:**
  - Create Web Service for backend (Docker, free tier)
  - Create Background Worker for Celery (free tier, 750 hrs/mo)
  - Set environment variables: `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `UPSTASH_REDIS_URL`
  - Configure health check endpoint: `/api/v1/health`
  - Note: free tier sleeps after 15 min inactivity — add UptimeRobot ping every 14 min
- [ ] **Vercel setup:**
  - Connect GitHub repo → auto-deploy `frontend/` directory
  - Set environment variable: `NEXT_PUBLIC_API_URL=https://sift-backend.onrender.com`
- [ ] **Supabase setup:**
  - Create project, run Alembic migration against Supabase Postgres
  - Enable email auth + GitHub OAuth in Supabase dashboard
  - Copy connection string + JWT secret to Render env vars
- [ ] **Upstash setup:**
  - Create Redis database (free tier: 10K commands/day)
  - Copy Redis URL to Render env vars
  - Verify Celery broker connects successfully
- [ ] **Monitoring:**
  - Set up Better Stack (free tier) or UptimeRobot for uptime monitoring
  - Add basic structured logging with `structlog`:
    ```python
    logger.info("research_completed", session_id=sid, latency_ms=lat, sources=5, chunks=42)
    ```
- [ ] **Smoke test checklist:**
  - [ ] Backend health endpoint responds from Render URL
  - [ ] Frontend loads from Vercel URL
  - [ ] Full research query works end-to-end
  - [ ] Auth flow works (sign up, sign in, session persistence)
  - [ ] Follow-up question works within a session
  - [ ] Sessions list shows in sidebar after auth

**Acceptance Criteria:**
- Full stack deployed and accessible at public URLs
- End-to-end research query works in production
- Total monthly cost: $0.00

---

**Phase 2 Deliverable:** Production-grade research engine with hybrid retrieval, Celery parallelism, resilience patterns, persistent sessions, auth, and deployed to free-tier infrastructure.

**Exit Criteria for Phase 2:**
- [ ] All 12 tasks completed and merged to `main`
- [ ] 85%+ test coverage
- [ ] Deployed and accessible at public URLs
- [ ] Circuit breakers, rate limiting, and caching operational
- [ ] 5+ concurrent users can use the system without degradation
- [ ] Stale-while-revalidate caching serves repeat queries in <300ms

---
---

### Phase 3 — Knowledge Graph & Intelligence

**Duration:** 4 Weeks (Sprints 7–10)
**Goal:** Persistent knowledge graph with entity extraction, cross-session intelligence, visualization, custom source plugins, and export capabilities.
**Team:** 2 backend engineers, 1 frontend engineer

---

#### Sprint 7 (Week 7): Entity Extraction + Knowledge Graph Foundation

##### Task 3.1 — LLM-Based Entity Extraction

**Owner:** Backend Engineer
**Files:** `backend/app/knowledge/entities.py`
**Duration:** 3 days

- [ ] Implement `EntityExtractor`:
  ```python
  class EntityExtractor:
      """
      Extracts structured entities and relationships from synthesized research answers.
      Uses Groq LLM with structured output prompting.
      """
      ENTITY_TYPES = [
          "technology", "concept", "organization", "person",
          "protocol", "algorithm", "library", "service", "pattern"
      ]

      async def extract(self, synthesized_answer: str, query: str) -> ExtractionResult:
          prompt = f"""
          Extract entities and relationships from this research text.

          Return JSON:
          {{
            "entities": [
              {{"name": "Kafka", "type": "technology", "description": "Distributed event streaming platform", "aliases": ["Apache Kafka"]}},
              ...
            ],
            "relationships": [
              {{"source": "Kafka", "target": "RabbitMQ", "type": "compared_with", "context": "Both are message brokers but differ in..."}},
              {{"source": "Kafka", "target": "ZooKeeper", "type": "depends_on", "context": "Kafka uses ZooKeeper for..."}},
              ...
            ]
          }}

          Relationship types: compared_with, depends_on, implements, alternative_to,
                              part_of, used_by, supersedes, extends, conflicts_with

          Text:
          {synthesized_answer}
          """
          # Parse JSON response with validation
          # Normalize entity names (lowercase, strip whitespace)
          # Deduplicate entities by name + aliases
  ```
- [ ] Define entity/relationship models:
  ```python
  class Entity(BaseModel):
      name: str
      type: str
      description: str
      aliases: list[str] = []
      first_seen: datetime
      last_seen: datetime
      mention_count: int = 1

  class Relationship(BaseModel):
      source_entity: str
      target_entity: str
      type: str
      context: str
      session_id: str
      confidence: float = 1.0
  ```
- [ ] Entity normalization pipeline:
  - Lowercase all names
  - Resolve aliases (e.g., "Apache Kafka" → "kafka", "K8s" → "kubernetes")
  - Merge duplicate entities across sessions (same name or overlapping aliases)
  - Increment `mention_count` on re-encounter
- [ ] Tests:
  - Test extraction from a sample research answer
  - Test alias resolution
  - Test deduplication across multiple extractions
  - Test handling of malformed LLM JSON output

**Acceptance Criteria:**
- Entities and relationships are extracted from every research synthesis
- Entity normalization prevents duplicates
- Extraction adds <500ms to the research pipeline

---

##### Task 3.2 — Knowledge Graph Storage (PostgreSQL)

**Owner:** Backend Engineer
**Files:** `backend/app/knowledge/graph.py`, `backend/app/db/models.py` (extend)
**Duration:** 2 days

- [ ] Add database models:
  ```python
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

      # Composite unique constraint: user_id + name
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
  ```
- [ ] Implement `KnowledgeGraph` service:
  ```python
  class KnowledgeGraph:
      async def add_entities(self, user_id, entities, session_id) -> list[KnowledgeEntity]:
          # Upsert entities (create or increment mention_count + update last_seen)

      async def add_relationships(self, user_id, relationships, session_id) -> None:
          # Insert relationships, resolve entity names to entity IDs

      async def get_entity_graph(self, user_id, entity_name) -> GraphData:
          # Return entity + all connected entities (1 hop) + relationships

      async def get_session_graph(self, user_id, session_id) -> GraphData:
          # Return all entities + relationships from a specific session

      async def get_full_graph(self, user_id) -> GraphData:
          # Return user's complete knowledge graph

      async def search_entities(self, user_id, query, limit=20) -> list[KnowledgeEntity]:
          # Full-text search on entity names + aliases + descriptions
  ```
- [ ] Generate Alembic migration for new tables
- [ ] Integrate into orchestrator: after synthesis, run entity extraction + graph update
- [ ] Tests: CRUD operations, deduplication, graph traversal queries

**Acceptance Criteria:**
- Entities and relationships stored in PostgreSQL
- Graph queries return connected entities within <200ms
- Knowledge graph grows with each research session

---

#### Sprint 8 (Week 8): Knowledge Recall + Graph Visualization

##### Task 3.3 — Cross-Session Knowledge Recall

**Owner:** Backend Lead
**Files:** `backend/app/knowledge/memory.py`, `backend/app/api/routes/knowledge.py`
**Duration:** 3 days

- [ ] Implement `KnowledgeMemory` service:
  ```python
  class KnowledgeMemory:
      """
      Enables recall queries: "What did I research about X?"
      Combines vector search over past chunks + knowledge graph traversal.
      """
      async def recall(self, user_id: str, query: str, limit: int = 10) -> RecallResult:
          # 1. Embed the recall query
          # 2. Search across ALL user's session collections in ChromaDB
          # 3. Search knowledge graph entities for matches
          # 4. Combine: graph-connected chunks ranked higher
          # 5. Synthesize a recall summary with session timestamps

      async def find_connections(self, user_id: str, entity_a: str, entity_b: str
                                ) -> list[ConnectionPath]:
          # Graph shortest-path between two entities
          # Shows how research topics are connected through your learning

      async def get_timeline(self, user_id: str, entity: str) -> list[TimelineEntry]:
          # Chronological view: when did user research this entity?
          # Which sessions? What were the findings?
  ```
- [ ] Implement recall endpoint:
  ```python
  @router.get("/api/v1/knowledge/recall")
  async def recall(q: str, limit: int = 10, user: User = Depends(get_current_user)):
      result = await memory.recall(user.id, q, limit)
      return result
  ```
- [ ] Implement temporal weighting:
  - Recent research weighted higher by default
  - Decay function: `score *= exp(-lambda * days_since_research)` where `lambda = 0.01`
  - User can override: `?recency=off` to treat all time periods equally
- [ ] Tests:
  - Test recall finds chunks from past sessions
  - Test temporal weighting boosts recent results
  - Test entity connection path finding

**Acceptance Criteria:**
- "What did I research about X?" returns relevant findings from past sessions
- Cross-session connections are discoverable
- Recall queries respond in <2 seconds

---

##### Task 3.4 — Knowledge Graph Visualization (Frontend)

**Owner:** Frontend Engineer
**Files:** `frontend/src/components/KnowledgeGraph.tsx`, `frontend/src/components/EntityDetail.tsx`
**Duration:** 3 days

- [ ] Implement force-directed graph using D3.js (`d3-force`):
  - Nodes: entities (sized by mention_count, colored by entity type)
  - Edges: relationships (labeled with type, weighted by confidence)
  - Layout: force simulation with collision detection
  - Interaction: drag nodes, zoom/pan, click node to show detail panel
  - Entity type color scheme:
    ```
    technology → blue
    concept → purple
    organization → green
    person → orange
    pattern → teal
    algorithm → red
    ```
- [ ] Entity detail panel (on node click):
  - Entity name, type, description
  - Mention count and first/last seen dates
  - List of sessions where this entity appears (linked)
  - Related entities (directly connected)
  - "Research more about this" button → triggers new research query
- [ ] Graph filter controls:
  - Filter by entity type (checkboxes)
  - Filter by session (dropdown)
  - Filter by date range (date picker)
  - Minimum mention count slider (hide rarely-mentioned entities)
- [ ] Graph views:
  - Full graph: all entities and relationships
  - Session graph: entities from a specific session
  - Entity neighborhood: selected entity + 1-2 hop connections
- [ ] Page: `/knowledge` route showing the graph with a sidebar for filters and detail

**Acceptance Criteria:**
- Interactive force-directed graph renders in <1 second for up to 200 entities
- Nodes are draggable, zoomable, clickable
- Filters work correctly
- Graph is visually compelling (this is what goes in the portfolio screenshot)

---

#### Sprint 9 (Week 9): Custom Source Plugins + Export

##### Task 3.5 — Custom Source Plugin Interface

**Owner:** Backend Engineer
**Files:** `backend/app/sources/base.py` (extend), `backend/app/sources/registry.py` (extend), documentation
**Duration:** 2 days

- [ ] Define plugin specification:
  ```python
  class SourcePlugin(SourceAdapter):
      """
      User-defined source adapter. Loaded from a plugin directory.

      Plugin structure:
      plugins/
        my_source/
          __init__.py      # Contains class extending SourcePlugin
          config.yaml      # Name, description, rate limits, auth requirements
          requirements.txt # Additional dependencies (optional)
      """
      @classmethod
      def from_config(cls, config_path: str) -> "SourcePlugin": ...
  ```
- [ ] Plugin config schema (`config.yaml`):
  ```yaml
  name: "stackoverflow"
  display_name: "Stack Overflow"
  description: "Search Stack Overflow questions and answers"
  base_url: "https://api.stackexchange.com/2.3"
  rate_limit:
    requests_per_second: 1
    burst: 5
  auth:
    type: "api_key"  # or "oauth" or "none"
    env_var: "SO_API_KEY"
  ```
- [ ] Plugin auto-discovery: scan `plugins/` directory on startup, register valid plugins
- [ ] API endpoint: `GET /api/v1/sources` lists all available sources (built-in + plugins)
- [ ] Documentation: write a "Creating a Custom Source Plugin" guide with example (Stack Overflow adapter)

**Acceptance Criteria:**
- New sources can be added by dropping a plugin folder — no core code changes
- Plugins are auto-discovered and registered on startup
- Plugin config validation catches errors early

---

##### Task 3.6 — Export System

**Owner:** Backend Engineer
**Files:** `backend/app/api/routes/export.py`
**Duration:** 2 days

- [ ] Implement export formats:
  ```python
  class ExportService:
      async def export_session(self, session_id: str, format: str) -> bytes | str:
          match format:
              case "markdown":    return await self._to_markdown(session_id)
              case "json":        return await self._to_json(session_id)
              case "obsidian":    return await self._to_obsidian(session_id)

      async def export_knowledge(self, user_id: str, format: str) -> bytes | str:
          match format:
              case "markdown":    return await self._knowledge_to_markdown(user_id)
              case "json":        return await self._knowledge_to_json(user_id)
              case "obsidian":    return await self._knowledge_to_obsidian_vault(user_id)
  ```
- [ ] Markdown export format:
  ```markdown
  # Research Session: Kafka vs RabbitMQ
  *Date: 2026-03-06 | Sources: 5 | Queries: 3*

  ## Query 1: "Trade-offs between Kafka and RabbitMQ..."
  [Full synthesized answer with citations]

  ### Sources
  1. [Kafka vs RabbitMQ - Confluent](https://...) (relevance: 94%)
  2. ...

  ## Query 2 (follow-up): "What about at 100K messages/sec?"
  [Answer...]
  ```
- [ ] Obsidian vault export:
  - Each entity becomes a note (`.md` file)
  - Relationships become `[[wikilinks]]` between notes
  - Sessions become notes with backlinks to entities
  - Compatible with Obsidian graph view
- [ ] API endpoints:
  - `GET /api/v1/sessions/{id}/export?format=markdown`
  - `GET /api/v1/knowledge/export?format=obsidian` (returns ZIP file)

**Acceptance Criteria:**
- Sessions exportable as Markdown, JSON, and Obsidian format
- Full knowledge graph exportable as Obsidian vault
- Exported Obsidian vault opens correctly in Obsidian and shows graph connections

---

#### Sprint 10 (Week 10): Scheduled Research + Performance + Polish

##### Task 3.7 — Scheduled Research (Daily Briefings)

**Owner:** Backend Engineer
**Files:** `backend/app/workers/scheduled.py`
**Duration:** 2 days

- [ ] Add Celery Beat for scheduled tasks:
  ```python
  celery_app.conf.beat_schedule = {
      "process-research-schedules": {
          "task": "app.workers.scheduled.run_scheduled_research",
          "schedule": crontab(hour=7, minute=0),  # Daily at 7 AM UTC
      },
  }
  ```
- [ ] Database model for research schedules:
  ```python
  class ResearchSchedule(Base):
      __tablename__ = "research_schedules"
      id: Mapped[uuid.UUID]
      user_id: Mapped[uuid.UUID]
      query_template: Mapped[str]   # "Latest developments in {topic}"
      topics: Mapped[list[str]]     # ["RAG systems", "vector databases"]
      frequency: Mapped[str]        # "daily", "weekly"
      sources: Mapped[list[str]]    # Preferred sources
      is_active: Mapped[bool]
      last_run: Mapped[datetime | None]
  ```
- [ ] Scheduled research task:
  - For each active schedule, run the research pipeline
  - Store results as a new session (tagged as "scheduled")
  - Compare with previous run: highlight what's new/changed
  - (Future: send email/webhook notification)
- [ ] API endpoints:
  - `POST /api/v1/schedules` — create schedule
  - `GET /api/v1/schedules` — list schedules
  - `PATCH /api/v1/schedules/{id}` — update/pause schedule
  - `DELETE /api/v1/schedules/{id}` — delete schedule
- [ ] Frontend: schedule management page under `/settings/schedules`

**Acceptance Criteria:**
- Users can create daily/weekly research schedules
- Celery Beat triggers scheduled research at configured times
- Results are stored as research sessions viewable in the UI

---

##### Task 3.8 — Performance Dashboard

**Owner:** Frontend Engineer
**Files:** `frontend/src/app/dashboard/page.tsx`, `backend/app/api/routes/analytics.py`
**Duration:** 2 days

- [ ] Backend analytics endpoint:
  ```python
  @router.get("/api/v1/analytics")
  async def get_analytics(user: User = Depends(get_current_user)):
      return {
          "total_sessions": count,
          "total_queries": count,
          "total_entities": count,
          "knowledge_graph_stats": { "nodes": n, "edges": e },
          "source_performance": {
              "duckduckgo": {"avg_latency_ms": 1100, "success_rate": 0.992},
              "reddit": {"avg_latency_ms": 1400, "success_rate": 0.971},
              ...
          },
          "cache_stats": {
              "hit_rate": 0.34,
              "avg_hit_latency_ms": 180,
              "avg_miss_latency_ms": 8500,
          },
          "research_by_week": [{"week": "2026-W10", "queries": 42}, ...],
          "top_entities": [{"name": "Kafka", "mentions": 12}, ...],
      }
  ```
- [ ] Frontend dashboard page:
  - Research activity chart (queries per week, line chart)
  - Source performance table (latency, success rate, circuit breaker status)
  - Cache hit rate gauge
  - Knowledge graph stats (nodes, edges, growth over time)
  - Top entities word cloud or bar chart
  - Use Chart.js or Recharts for visualization

**Acceptance Criteria:**
- Dashboard loads in <2 seconds
- Shows meaningful analytics about research usage
- Source performance is visible (useful for debugging in interviews)

---

##### Task 3.9 — Collaborative Sessions

**Owner:** Backend Engineer + Frontend Engineer
**Duration:** 2 days

- [ ] Database: add `session_collaborators` join table (user_id, session_id, role: "viewer" | "editor")
- [ ] Backend:
  - `POST /api/v1/sessions/{id}/share` — generate shareable link with role
  - Shared sessions are read-only by default, editors can add follow-up queries
  - Real-time updates via WebSocket (optional) or polling
- [ ] Frontend:
  - Share button on session view
  - Copy link modal with role selector
  - Shared session indicator (avatar pills of collaborators)

**Acceptance Criteria:**
- Users can share research sessions via link
- Shared users can view the session
- Editors can add follow-up queries to shared sessions

---

**Phase 3 Deliverable:** Full knowledge operating system — research, remember, connect, share, export, schedule.

**Exit Criteria for Phase 3:**
- [ ] All 9 tasks completed and merged to `main`
- [ ] Knowledge graph stores entities and relationships
- [ ] Visualization is interactive and visually compelling
- [ ] Recall queries work across sessions
- [ ] Export to Markdown/Obsidian works
- [ ] Scheduled research runs daily via Celery Beat
- [ ] Performance dashboard operational

---
---

### Phase 4 — Agentic Intelligence

**Duration:** 4 Weeks (Sprints 11–14)
**Goal:** Transform the fixed orchestration pipeline into an autonomous agent architecture that reasons about research strategy, self-evaluates intermediate results, dynamically selects sources, and orchestrates multi-agent collaboration.
**Team:** 2 backend engineers (strong LLM/agent experience), 1 frontend engineer

**Prerequisite:** Phase 3 must be complete. The agent architecture builds directly on top of the knowledge graph, entity extraction, and the full source/retrieval/resilience stack.

---

#### Sprint 11 (Week 11): ReAct Research Agent Core

##### Task 4.1 — Agent State Machine + ReAct Loop

**Owner:** Backend Lead
**Files:** `backend/app/agents/base.py`, `backend/app/agents/state.py`, `backend/app/agents/react_loop.py`
**Duration:** 3 days

- [ ] Define agent state model in `state.py`:
  ```python
  class AgentState(BaseModel):
      """Full state of a research agent across iterations."""
      session_id: str
      original_query: str
      current_plan: list[AgentStep]
      completed_steps: list[CompletedStep]
      gathered_knowledge: list[Chunk]
      sub_queries_generated: list[str]
      sources_searched: dict[str, list[str]]  # source → [queries searched]
      verification_results: list[VerificationResult]
      iteration: int = 0
      max_iterations: int = 8
      confidence: float = 0.0  # 0.0 to 1.0, agent's self-assessed confidence
      status: Literal["thinking", "searching", "verifying", "synthesizing", "complete", "stuck"]

  class AgentStep(BaseModel):
      step_id: str
      action_type: Literal["decompose", "search", "refine", "verify", "expand", "synthesize", "recall"]
      reasoning: str      # Agent's explanation for why this step
      parameters: dict    # Action-specific params (query, sources, etc.)

  class CompletedStep(BaseModel):
      step: AgentStep
      result: dict
      duration_ms: int
      success: bool
  ```
- [ ] Implement `ReActLoop` in `react_loop.py`:
  ```python
  class ReActLoop:
      """
      Reason → Act → Observe → Reason loop.
      Each iteration: LLM reasons about current state → selects next action → executes → evaluates.
      """
      def __init__(self, llm_client, tool_registry, max_iterations: int = 8): ...

      async def run(self, query: str, state: AgentState) -> AsyncGenerator[AgentEvent, None]:
          while not state.is_terminal and state.iteration < state.max_iterations:
              # REASON: Ask LLM what to do next
              action = await self._reason(state)
              yield AgentEvent(type="thinking", data={"reasoning": action.reasoning})

              # ACT: Execute the chosen action
              result = await self._act(action, state)
              yield AgentEvent(type="action_complete", data=result.to_dict())

              # OBSERVE: Update state with results
              state = self._observe(state, action, result)

              # EVALUATE: Should we continue, refine, or synthesize?
              evaluation = await self._evaluate(state)
              if evaluation.should_synthesize:
                  state.status = "synthesizing"

              state.iteration += 1

          # Final synthesis
          async for token in self._synthesize(state):
              yield AgentEvent(type="token", data={"content": token})
  ```
- [ ] Agent reasoning prompt:
  ```
  You are a research agent. Given the current research state, decide your next action.

  Available actions:
  - decompose: Break a query into sub-queries
  - search: Search specific sources with specific queries
  - refine: Rewrite a search query because results were poor
  - verify: Cross-check a claim that appears in retrieved results
  - expand: Research a related topic discovered in results
  - recall: Check user's past research for relevant context
  - synthesize: Generate final answer (only when confident)

  Current state:
  - Original query: {query}
  - Iteration: {iteration}/{max_iterations}
  - Knowledge gathered: {chunk_count} chunks from {source_count} sources
  - Confidence: {confidence}
  - Completed steps: {steps_summary}

  What should we do next? Return JSON:
  {
    "reasoning": "Explain your thinking...",
    "action": "search",
    "parameters": {"queries": [...], "sources": [...]}
  }
  ```
- [ ] Implement iteration budget: agent MUST synthesize by `max_iterations` even if confidence is low (graceful degradation)
- [ ] Tests:
  - Test agent completes simple query in 2–3 iterations
  - Test agent refines search when initial results are poor (mock poor results)
  - Test agent respects max_iterations limit
  - Test agent state serialization/deserialization

**Acceptance Criteria:**
- Agent autonomously decides research strategy
- Agent terminates within iteration budget
- Each action is a real operation (search, retrieve, etc.) using existing infrastructure

---

##### Task 4.2 — Agent Tool Registry

**Owner:** Backend Engineer
**Files:** `backend/app/agents/tools.py`
**Duration:** 2 days

- [ ] Implement `AgentToolRegistry`:
  ```python
  class AgentToolRegistry:
      """
      Maps agent action types to executable tools.
      Each tool wraps an existing Sift component (source adapters, retrieval, knowledge graph).
      """
      tools: dict[str, AgentTool] = {}

      def register(self, tool: AgentTool): ...
      def get(self, action_type: str) -> AgentTool: ...
      def get_tool_descriptions(self) -> str:
          # For inclusion in the agent's reasoning prompt
  ```
- [ ] Implement concrete tools:
  ```python
  class SearchTool(AgentTool):
      """Wraps source adapter fan-out. Agent specifies which sources and queries."""
      name = "search"
      async def execute(self, params: dict, state: AgentState) -> ToolResult:
          queries = params["queries"]
          sources = params.get("sources", ["ddg", "reddit", "hackernews", "arxiv", "wikipedia"])
          # Dispatch Celery tasks for each source × query combination
          # Return: list of SourceResult

  class RefineTool(AgentTool):
      """Agent rewrites a failed query. Runs the new query against the same sources."""
      name = "refine"
      async def execute(self, params: dict, state: AgentState) -> ToolResult:
          original_query = params["original_query"]
          refined_query = params["refined_query"]
          reasons = params["refinement_reasons"]
          # Search with refined query, track that this is a refinement

  class VerifyTool(AgentTool):
      """Cross-checks a specific claim against primary sources."""
      name = "verify"
      async def execute(self, params: dict, state: AgentState) -> ToolResult:
          claim = params["claim"]
          # Search for the specific claim with high-precision queries
          # Return: supporting/contradicting evidence

  class RecallTool(AgentTool):
      """Checks user's knowledge graph for relevant past research."""
      name = "recall"
      async def execute(self, params: dict, state: AgentState) -> ToolResult:
          query = params["recall_query"]
          # Use KnowledgeMemory.recall() from Phase 3
          # Return: relevant past chunks and entity connections

  class ExpandTool(AgentTool):
      """Agent discovered a related topic and wants to proactively research it."""
      name = "expand"
      async def execute(self, params: dict, state: AgentState) -> ToolResult:
          topic = params["expansion_topic"]
          reason = params["expansion_reason"]
          # Search for the expanded topic
          # Tag results as "agent-expanded" for transparency
  ```
- [ ] Each tool execution dispatches to existing Sift infrastructure (no new external APIs)
- [ ] Tool execution is auditable: every call logged with params, duration, result summary
- [ ] Tests: each tool with mocked dependencies

**Acceptance Criteria:**
- Agent actions map to real tool executions
- Every tool execution is logged and auditable
- Tools reuse existing source/retrieval/knowledge infrastructure

---

##### Task 4.3 — Agent Self-Evaluation + Confidence Scoring

**Owner:** Backend Engineer
**Files:** `backend/app/agents/evaluator.py`
**Duration:** 2 days

- [ ] Implement `AgentEvaluator`:
  ```python
  class AgentEvaluator:
      """
      Evaluates the quality of gathered knowledge after each agent iteration.
      Determines if the agent has enough to synthesize or needs more research.
      """
      async def evaluate(self, state: AgentState) -> Evaluation:
          # Factors that increase confidence:
          # - Multiple sources agree on key claims
          # - Source diversity (not all from one source type)
          # - Quantitative data present (benchmarks, metrics)
          # - Recent sources (for time-sensitive queries)
          # - Past knowledge confirms findings

          # Factors that decrease confidence:
          # - Contradictions between sources
          # - All results from a single source type
          # - Results don't directly address the query
          # - Agent has searched <3 unique queries
          # - No authoritative sources (only blog posts, no papers/docs)

          return Evaluation(
              confidence=0.82,
              should_synthesize=True,  # confidence > 0.75 AND iteration >= 3
              suggestions=[],          # If not synthesizing: what to do next
              gaps=["No benchmark data found for >50K msgs/sec"],
          )
  ```
- [ ] Evaluation uses a lightweight LLM call (Groq, low temperature) to assess knowledge quality
- [ ] Evaluation prompt includes:
  - Original query
  - Summary of gathered knowledge (not full chunks — summarized for efficiency)
  - Source diversity metrics
  - Known contradictions
- [ ] Confidence threshold configuration:
  - `confident_threshold = 0.75` → synthesize
  - `uncertain_threshold = 0.4` → synthesize with caveats ("Based on limited sources...")
  - `below 0.4 after max iterations` → synthesize with explicit "insufficient research" disclaimer
- [ ] Tests:
  - Test high confidence when sources agree and are diverse
  - Test low confidence when sources contradict
  - Test confidence increases across iterations

**Acceptance Criteria:**
- Agent self-evaluates after each iteration
- Confidence scoring drives the decision to continue or synthesize
- Insufficient results produce honest "needs more research" disclaimers

---

#### Sprint 12 (Week 12): Multi-Agent Architecture

##### Task 4.4 — Specialized Agent Roles

**Owner:** Backend Lead
**Files:** `backend/app/agents/specialists/academic.py`, `backend/app/agents/specialists/practitioner.py`, `backend/app/agents/specialists/factcheck.py`, `backend/app/agents/coordinator.py`
**Duration:** 3 days

- [ ] Implement `AcademicAgent`:
  ```python
  class AcademicAgent(BaseAgent):
      """
      Specialist: searches academic sources (ArXiv, Wikipedia).
      Extracts: methodology, quantitative results, theoretical frameworks.
      System prompt emphasizes: rigor, methodology, peer-reviewed evidence.
      Preferred sources: arxiv, wikipedia
      Evaluation criteria: statistical evidence, methodology quality, recency
      """
  ```
- [ ] Implement `PractitionerAgent`:
  ```python
  class PractitionerAgent(BaseAgent):
      """
      Specialist: searches practitioner sources (Reddit, HN, DuckDuckGo).
      Extracts: real-world experience, operational pain points, production war stories.
      System prompt emphasizes: practical experience, scale context, operational reality.
      Preferred sources: reddit, hackernews, duckduckgo
      Evaluation criteria: author credibility signals, scale context, specificity
      """
  ```
- [ ] Implement `FactCheckAgent`:
  ```python
  class FactCheckAgent(BaseAgent):
      """
      Specialist: takes claims from other agents and cross-references.
      Searches for: primary sources, official documentation, direct contradictions.
      System prompt emphasizes: verification, finding original sources, identifying bias.
      Can search any source.
      Evaluation criteria: claim verification rate, source authority
      """
  ```
- [ ] Implement `ResearchCoordinator`:
  ```python
  class ResearchCoordinator:
      """
      Orchestrates multi-agent research.

      Flow:
      1. Analyze query → decide if multi-agent is warranted
         (Simple factual → single agent. Complex comparative → multi-agent)
      2. Dispatch to specialist agents in parallel (Celery tasks)
      3. Collect results from all specialists
      4. Run FactCheckAgent on combined findings
      5. Synthesize final answer with attribution to which agent found what

      Decision criteria for multi-agent:
      - Query contains comparison ("X vs Y") → multi-agent
      - Query asks for trade-offs → multi-agent
      - Query is simple factual lookup → single agent
      - Query asks about implementation → PractitionerAgent only
      - Query asks about theory/research → AcademicAgent only
      """
      async def research(self, query: str, state: AgentState) -> AsyncGenerator[AgentEvent, None]:
          complexity = await self._assess_complexity(query)

          if complexity == "simple":
              async for event in single_agent.run(query, state):
                  yield event
          else:
              # Parallel specialist dispatch
              academic_task = run_agent.delay("academic", query, state.session_id)
              practitioner_task = run_agent.delay("practitioner", query, state.session_id)

              # Collect results (with timeout)
              academic_results = await wait_for_task(academic_task, timeout=30)
              practitioner_results = await wait_for_task(practitioner_task, timeout=30)

              # Fact-check combined findings
              combined = merge_results(academic_results, practitioner_results)
              verified = await self.fact_check_agent.verify(combined)

              # Synthesize with multi-perspective awareness
              async for token in self._multi_agent_synthesis(verified, query):
                  yield token
  ```
- [ ] Agent output format: each specialist returns structured findings, not free-form text
  ```python
  class AgentFindings(BaseModel):
      agent_type: str                     # "academic" | "practitioner" | "factcheck"
      key_claims: list[Claim]             # Structured claims with evidence
      confidence: float
      sources_used: list[SourceReference]
      contradictions_found: list[Contradiction]
      gaps_identified: list[str]
  ```
- [ ] Tests:
  - Test coordinator dispatches correct agents based on query type
  - Test multi-agent results are properly merged
  - Test timeout handling when one agent is slow
  - Test graceful degradation when one agent fails entirely

**Acceptance Criteria:**
- Complex queries dispatch multiple specialist agents in parallel
- Fact-check agent verifies claims from other agents
- Final synthesis attributes findings to specific agent perspectives
- Simple queries still use fast single-agent path

---

##### Task 4.5 — Agent Trace + Reasoning Transparency

**Owner:** Backend Engineer
**Files:** `backend/app/agents/trace.py`, database migration
**Duration:** 2 days

- [ ] Define agent trace model:
  ```python
  class AgentTrace(Base):
      __tablename__ = "agent_traces"
      id: Mapped[uuid.UUID]
      session_id: Mapped[str]
      turn_id: Mapped[uuid.UUID]
      agent_type: Mapped[str]        # "coordinator", "academic", "practitioner", "factcheck"
      iterations: Mapped[list[dict]] = mapped_column(JSON)
      # Each iteration:
      # {
      #   "iteration": 1,
      #   "reasoning": "Results are mostly blog posts. Need academic sources.",
      #   "action": "search",
      #   "action_params": {"sources": ["arxiv"], "queries": [...]},
      #   "result_summary": "Found 3 relevant papers",
      #   "confidence_after": 0.45,
      #   "duration_ms": 3200
      # }
      total_iterations: Mapped[int]
      total_duration_ms: Mapped[int]
      final_confidence: Mapped[float]
      tools_used: Mapped[list[str]] = mapped_column(ARRAY(String))
  ```
- [ ] Store trace for every agent execution
- [ ] API endpoint: `GET /api/v1/sessions/{id}/turns/{turn_id}/trace` returns the full agent trace
- [ ] SSE events during agent execution:
  ```
  event: agent_thinking
  data: {"agent": "coordinator", "reasoning": "This is a comparison query. Dispatching academic and practitioner agents."}

  event: agent_action
  data: {"agent": "academic", "action": "search", "sources": ["arxiv"], "queries": ["Kafka throughput benchmarks"]}

  event: agent_action_complete
  data: {"agent": "academic", "action": "search", "results_count": 3, "duration_ms": 2100}

  event: agent_evaluation
  data: {"agent": "academic", "confidence": 0.62, "gaps": ["No data beyond 50K msgs/sec"]}

  event: agent_thinking
  data: {"agent": "academic", "reasoning": "Confidence is below threshold. Refining search to include higher throughput benchmarks."}
  ```

**Acceptance Criteria:**
- Every agent decision is logged with reasoning
- Traces are stored in PostgreSQL and queryable via API
- Frontend can display the agent's thought process in real-time

---

#### Sprint 13 (Week 13): Agent Visualization + Proactive Intelligence

##### Task 4.6 — Agent Reasoning UI

**Owner:** Frontend Engineer
**Files:** `frontend/src/components/AgentTrace.tsx`, `frontend/src/components/AgentThinking.tsx`
**Duration:** 3 days

- [ ] Implement `AgentThinking` component (real-time during research):
  - Collapsible panel above the streaming answer
  - Shows agent reasoning steps as they happen:
    ```
    🤔 Analyzing query complexity... → Complex comparison detected
    📚 Academic Agent: Searching ArXiv for "Kafka throughput benchmarks"
    💬 Practitioner Agent: Searching Reddit for "Kafka vs RabbitMQ production experience"
    📚 Academic Agent: Found 3 papers (confidence: 0.62)
    📚 Academic Agent: Refining search — need higher throughput data
    💬 Practitioner Agent: Found 5 discussions (confidence: 0.71)
    ✅ Fact-check: Verifying claim "Kafka handles 100K msgs/sec"
    ✅ Fact-check: Confirmed by 2 independent sources
    📝 Synthesizing final answer from 8 chunks across 3 agents...
    ```
  - Each step is expandable to show full reasoning text
  - Color-coded by agent type
  - Animated: steps appear with a subtle fade-in as they arrive
- [ ] Implement `AgentTrace` component (post-research detailed view):
  - Timeline visualization of all agent iterations
  - Shows decision tree: which agents were dispatched and why
  - Each iteration shows: reasoning → action → result → confidence change
  - Expandable details for each step
  - Link from the trace to specific citations in the answer
- [ ] "Show agent reasoning" toggle (off by default for clean UX, on for power users)

**Acceptance Criteria:**
- Users can watch the agent think in real-time
- Post-research trace shows the full decision chain
- Toggle hides complexity for casual users

---

##### Task 4.7 — Proactive Research Agent (Background Intelligence)

**Owner:** Backend Engineer
**Files:** `backend/app/agents/proactive.py`, `backend/app/workers/scheduled.py` (extend)
**Duration:** 3 days

- [ ] Implement `ProactiveResearchAgent`:
  ```python
  class ProactiveResearchAgent:
      """
      Background agent that analyzes the user's knowledge graph and proactively
      identifies opportunities for new research.

      Runs via Celery Beat (daily or weekly, user-configurable).
      """
      async def analyze_knowledge_gaps(self, user_id: str) -> list[ResearchSuggestion]:
          """
          Scans knowledge graph for:
          1. Incomplete comparisons (researched A and B individually, never compared)
          2. Stale knowledge (entities researched >30 days ago in fast-moving fields)
          3. Missing context (entity mentioned but never deeply researched)
          4. Trending topics related to user's interests (via HN/Reddit trending)
          """
          graph = await knowledge_graph.get_full_graph(user_id)
          entities = graph.entities
          relationships = graph.relationships

          suggestions = []

          # Gap detection: find entities with few connections
          isolated = [e for e in entities if self._connection_count(e, relationships) < 2]
          for entity in isolated:
              suggestions.append(ResearchSuggestion(
                  type="knowledge_gap",
                  title=f"Explore connections for {entity.name}",
                  query=f"How does {entity.name} relate to {self._find_likely_connections(entity, entities)}?",
                  reasoning=f"{entity.name} appears in your research but has few connections to other concepts."
              ))

          # Staleness detection
          stale = [e for e in entities if (now() - e.last_seen).days > 30 and e.type == "technology"]
          for entity in stale:
              suggestions.append(ResearchSuggestion(
                  type="stale_knowledge",
                  title=f"Update: {entity.name}",
                  query=f"Latest developments in {entity.name} {current_year}",
                  reasoning=f"Your last research on {entity.name} was {days_ago} days ago."
              ))

          # Incomplete comparisons
          compared = {(r.source, r.target) for r in relationships if r.type == "compared_with"}
          # Find entity pairs that are same type but never compared
          ...

          return suggestions

      async def run_proactive_research(self, user_id: str, suggestion: ResearchSuggestion):
          """Execute a suggested research and notify the user."""
          # Run standard research pipeline with the suggested query
          # Tag session as "proactive" for UI differentiation
          # Store notification for user
  ```
- [ ] Notification model:
  ```python
  class Notification(Base):
      __tablename__ = "notifications"
      id: Mapped[uuid.UUID]
      user_id: Mapped[uuid.UUID]
      type: Mapped[str]        # "proactive_research", "knowledge_update", "contradiction_found"
      title: Mapped[str]
      body: Mapped[str]
      suggestion_query: Mapped[str | None]
      is_read: Mapped[bool] = mapped_column(default=False)
      created_at: Mapped[datetime]
  ```
- [ ] API endpoints:
  - `GET /api/v1/suggestions` — get proactive research suggestions (without executing them)
  - `POST /api/v1/suggestions/{id}/execute` — run the suggested research
  - `GET /api/v1/notifications` — get user notifications
  - `PATCH /api/v1/notifications/{id}/read` — mark as read
- [ ] Celery Beat schedule: run `analyze_knowledge_gaps` weekly for each active user
- [ ] Frontend: notification bell icon in header, suggestion cards on dashboard

**Acceptance Criteria:**
- System proactively identifies knowledge gaps and stale research
- Suggestions are actionable (one click to execute)
- Users receive notifications about proactive insights
- Background analysis doesn't impact real-time research performance

---

#### Sprint 14 (Week 14): Agent Integration Testing + Documentation

##### Task 4.8 — Comprehensive Agent Testing

**Owner:** Entire team
**Duration:** 2 days

- [ ] Agent-specific test suite:
  | Test | What It Validates |
  |------|------------------|
  | `test_react_loop_simple_query` | Simple query completes in ≤3 iterations |
  | `test_react_loop_complex_query` | Complex query uses 4-6 iterations, searches multiple sources |
  | `test_react_loop_refines_on_poor_results` | Agent rewrites query when initial results are low quality |
  | `test_react_loop_max_iterations` | Agent synthesizes at budget even if unsatisfied |
  | `test_coordinator_dispatches_multi_agent` | Comparison queries trigger academic + practitioner agents |
  | `test_coordinator_simple_single_agent` | Simple queries use single-agent path (faster) |
  | `test_factcheck_agent_catches_contradiction` | Conflicting claims are detected and verified |
  | `test_evaluator_confidence_increases` | Confidence grows with more diverse, agreeing sources |
  | `test_evaluator_low_confidence_disclaimer` | Low-confidence synthesis includes appropriate caveats |
  | `test_proactive_agent_finds_gaps` | Knowledge graph with isolated entities generates suggestions |
  | `test_proactive_agent_finds_stale` | Old technology entities trigger update suggestions |
  | `test_trace_records_all_iterations` | Agent trace captures every reasoning + action step |
  | `test_agent_reuses_existing_infrastructure` | All tool executions route through existing Sift components |

- [ ] Integration tests (with mocked LLM but real Celery/Redis/ChromaDB):
  - Full multi-agent research pipeline end-to-end
  - Agent trace stored and retrievable
  - Proactive agent analysis on a test knowledge graph
- [ ] Performance benchmarks:
  - Single-agent simple query: <10 seconds
  - Multi-agent complex query: <30 seconds
  - Proactive analysis for 100 entities: <60 seconds

**Acceptance Criteria:**
- All agent tests pass
- 85%+ coverage on agent code
- Performance within benchmark targets

---

##### Task 4.9 — Agent Architecture Documentation

**Owner:** Backend Lead
**Duration:** 2 days

- [ ] Write `docs/agent-architecture.md`:
  - Design philosophy: why agents over fixed orchestration
  - ReAct loop explanation with diagrams
  - Multi-agent coordination protocol
  - Tool registry and extension guide
  - Confidence scoring algorithm
  - Proactive intelligence design
- [ ] Write `docs/adding-agent-tools.md`:
  - Step-by-step guide to adding a new agent tool
  - Example: adding a "code execution" tool
- [ ] Update main README with Phase 4 architecture diagram
- [ ] Record demo video showing:
  - Agent reasoning in real-time (thinking panel)
  - Multi-agent dispatching for a complex query
  - Agent trace exploration after research
  - Proactive suggestion on knowledge graph

**Acceptance Criteria:**
- Agent architecture is documented well enough for a new team member to contribute
- Demo video showcases the "wow" factor

---

**Phase 4 Deliverable:** Autonomous, multi-agent research system with self-evaluation, dynamic tool use, reasoning transparency, and proactive intelligence.

**Exit Criteria for Phase 4:**
- [ ] All 9 tasks completed and merged to `main`
- [ ] Agent handles simple queries in single-agent mode (<10s)
- [ ] Agent handles complex queries in multi-agent mode (<30s)
- [ ] Agent trace is stored, retrievable, and visualized in frontend
- [ ] Proactive research suggestions are generated weekly
- [ ] Agent reasoning is visible in real-time in the UI
- [ ] 85%+ test coverage on agent code

---
---

### Full Roadmap Summary

```
Phase 1 (2 Weeks)    Phase 2 (4 Weeks)     Phase 3 (4 Weeks)     Phase 4 (4 Weeks)
───────────────────   ──────────────────    ──────────────────    ──────────────────
Core Engine           Production Hardening  Knowledge System      Agentic Intelligence
                                                                  
• FastAPI + SSE       • Celery fan-out      • Entity extraction   • ReAct agent loop
• 3 source adapters   • Hybrid retrieval    • Knowledge graph     • Multi-agent arch
• Ingestion pipeline  • Circuit breakers    • Cross-session       • Self-evaluation
• ChromaDB retrieval  • Redis caching       • Graph visualization • Agent tools
• LLM synthesis       • PostgreSQL sessions • Custom source       • Reasoning traces
• React frontend      • Auth (Supabase)       plugins             • Proactive research
• Docker Compose      • CI/CD + Deploy      • Export system       • Agent visualization
• 70% test coverage   • 85% test coverage   • Scheduled research  • 85% agent coverage
                                            • Collab sessions     
                                            • Perf dashboard      
                                                                  
Deliverable:          Deliverable:          Deliverable:          Deliverable:
  Demo-able MVP         Production system     Knowledge OS          Autonomous research
                                                                    intelligence

Total: 14 weeks (3.5 months) from zero to world-class portfolio project
Team: 2 backend + 1 frontend + 1 DevOps (part-time after Phase 2)
Cost: $0.00/month at MVP scale
```

---

## Performance Characteristics

Measured on Render free tier with Groq Llama 3.1 70B:

| Metric | Value | Notes |
|--------|-------|-------|
| **Time to first token** | ~3.5s | Query analysis + first source return + synthesis start |
| **Full response** | ~8-12s | All 5 sources + synthesis complete |
| **Cache hit response** | ~200ms | Redis cached result |
| **Stale-while-revalidate** | ~250ms | Stale result + background refresh |
| **Embedding generation** | ~50ms/chunk | HuggingFace all-MiniLM-L6-v2 |
| **Hybrid retrieval** | ~80ms | BM25 + dense + RRF on 10K chunks |
| **P99 latency** | ~15s | Worst case: all sources slow + large synthesis |
| **Concurrent users** | ~20 | Free tier limitation (single worker) |

### Scaling Path (Beyond Free Tier)

```
Free Tier (Phase 1-2):
  1 Render instance → FastAPI + Celery worker (in-process)
  Upstash Redis → 10K commands/day
  ~20 concurrent users

$0/mo → $25/mo (Phase 3):
  Render Starter → dedicated worker process
  Upstash Pro → 100K commands/day
  ~200 concurrent users

$25/mo → $100/mo (Scale):
  Render + 2 Celery workers → horizontal scaling
  Managed Redis → unlimited
  Pinecone Starter → managed vector DB
  ~2000 concurrent users
```

---

## Contributing

Sift is open source and welcomes contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Priority Areas

1. **New source adapters** — Google Scholar, StackOverflow, GitHub Discussions, PubMed
2. **Retrieval quality** — Better chunking strategies, cross-encoder reranking
3. **Frontend UX** — Knowledge graph visualization, mobile responsiveness
4. **Testing** — Edge cases in circuit breaker, cache invalidation scenarios
5. **Documentation** — API docs, self-hosting guides, architecture deep-dives

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/sift.git
cd sift

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run in development mode
make dev

# Run tests
make test

# Run linting
make lint
```

---

## Benchmarks

### Retrieval Quality (on Natural Questions subset)

| Method | Recall@10 | MRR@10 | Latency |
|--------|-----------|--------|---------|
| BM25 only | 0.72 | 0.58 | 12ms |
| Dense only (MiniLM) | 0.78 | 0.64 | 45ms |
| **Hybrid (RRF)** | **0.86** | **0.71** | **62ms** |
| Hybrid + Reranker | 0.91 | 0.79 | 180ms |

### Source Reliability (30-day rolling)

```
DuckDuckGo:  99.2% uptime, avg 1.1s latency
Wikipedia:   99.8% uptime, avg 0.4s latency
HackerNews:  99.5% uptime, avg 0.8s latency
Reddit:      97.1% uptime, avg 1.4s latency  ← most circuit breaker trips
ArXiv:       98.9% uptime, avg 1.8s latency
```

---

## Comparison with Alternatives

### Feature Matrix

| Feature | Sift | Perplexity | ChatGPT Browse | Google | Phind | Elicit | Khoj |
|---------|------|-----------|----------------|--------|-------|--------|------|
| **Open Source** | Yes | No | No | No | No | No | Yes |
| **Self-Hostable** | Yes | No | No | No | No | No | Yes |
| **Persistent Memory** | Full knowledge graph | No | Shallow preferences | Search history only | No | Partial (papers) | Document search |
| **Multi-Source Parallel** | 5+ sources, fan-out | Unknown (opaque) | Sequential single-source | Single index | Web only | Academic only | Web or docs (not both) |
| **Hybrid Retrieval** | BM25 + Dense + RRF | Unknown | N/A | BM25 + ML (proprietary) | Unknown | N/A | Dense only |
| **Source Control** | Full (toggle/add/remove) | None | None | None | None | None | Limited |
| **Citation Integrity** | Structurally verified | Mostly accurate | Hallucinates URLs | Links (no synthesis) | Mostly accurate | Accurate (papers) | Varies |
| **Knowledge Graph** | Entity + relationship graph | No | No | No | No | Partial | No |
| **Cross-Session Intelligence** | Yes (recall + graph traversal) | No | No | No | No | Limited | No |
| **Circuit Breakers** | Per-source, Redis-backed | Unknown (internal) | N/A | N/A | Unknown | N/A | No |
| **Resilience / Graceful Degradation** | Partial results on source failure | Unknown | Fails silently | N/A | Unknown | N/A | Fails on error |
| **Context Compression** | Progressive summarization | Unknown | Truncation | N/A | Unknown | N/A | No |
| **Custom Source Plugins** | Adapter interface | No | No | No | No | No | Limited |
| **Streaming Architecture** | SSE with source-level status | SSE | Streaming tokens | N/A | SSE | No | SSE |
| **Free Tier** | Unlimited (self-hosted) | 5 Pro queries/day | GPT-4 rate limits | Free (with ads) | Limited | Limited | Self-hosted free |
| **Privacy** | Full (self-hosted, zero telemetry) | Cloud only | Cloud only | Tracked + ads | Cloud only | Cloud only | Self-hostable |
| **LLM Provider Lock-in** | None (Groq/OpenAI/Ollama/any) | Proprietary | GPT-4 only | N/A | Proprietary | Proprietary | Configurable |
| **Cost at Scale (team of 10)** | $0 (self-hosted) | $200/mo | $200/mo | Free (data cost) | ~$100/mo | ~$100/mo | $0 (self-hosted) |

### Architectural Comparison

How each tool handles the same query: *"What are the trade-offs between Kafka and RabbitMQ for event-driven microservices at 10K messages/sec?"*

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  GOOGLE                                                                      │
│                                                                              │
│  1. Single BM25 + ML ranked search against web index                         │
│  2. Returns 10 blue links (3 are ads, 2 are SEO content farms)              │
│  3. You open 5 tabs, read for 20 minutes, synthesize mentally               │
│  4. Knowledge exists only in your head (or a Google Doc you'll lose)        │
│                                                                              │
│  Time: 20-45 minutes │ Retention: ~10% after 1 week │ Sources: Opaque      │
├──────────────────────────────────────────────────────────────────────────────┤
│  PERPLEXITY                                                                  │
│                                                                              │
│  1. Single query sent to internal search pipeline                            │
│  2. Sources selected opaquely (you can't control which)                     │
│  3. Synthesized answer with citations (mostly accurate)                     │
│  4. Session ends. Knowledge gone. Ask again next month = fresh start.       │
│                                                                              │
│  Time: 5-10 seconds │ Retention: 0% (no memory) │ Sources: 3-5 (opaque)   │
├──────────────────────────────────────────────────────────────────────────────┤
│  CHATGPT BROWSE                                                              │
│                                                                              │
│  1. Sequential web browsing: search → read → search → read → ...            │
│  2. Synthesized answer with citations (some hallucinated)                   │
│  3. Long queries may timeout during sequential browsing                     │
│  4. No persistent memory of research findings                               │
│                                                                              │
│  Time: 45-90 seconds │ Retention: 0% │ Sources: 3-5 (sequential, slow)    │
├──────────────────────────────────────────────────────────────────────────────┤
│  SIFT                                                                        │
│                                                                              │
│  1. Query decomposed into 3 sub-queries by LLM                              │
│  2. 5 source adapters × 3 sub-queries = 15 parallel Celery tasks           │
│  3. Results deduplicated (MinHash/LSH), chunked, embedded                   │
│  4. Hybrid retrieval: BM25 + dense + RRF → top-15 chunks                   │
│  5. Streaming synthesis with structurally-verified citations                │
│  6. Session persisted → knowledge graph updated → entities linked           │
│  7. Next month: "What did I research about message brokers?" → instant     │
│                                                                              │
│  Time: 8-12 seconds │ Retention: 100% (persistent) │ Sources: 5+ (parallel)│
└──────────────────────────────────────────────────────────────────────────────┘
```

### The Fundamental Difference

Every other tool treats research as a **single query → single answer** transaction.

Sift treats research as a **continuous process** where knowledge accumulates, connections emerge across sessions, and your personal knowledge graph becomes more valuable with every question you ask. The more you research, the smarter Sift gets — for YOU specifically.

---

## Inspiration & References

### Research Papers
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — Cormack et al., SIGIR 2009
- [Lost in the Middle](https://arxiv.org/abs/2307.03172) — Liu et al., 2023 — Why context position matters for LLMs
- [RAPTOR](https://arxiv.org/abs/2401.18059) — Recursive summarization for tree-organized retrieval

### Engineering Patterns
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html) — Martin Fowler
- [Stale-While-Revalidate](https://web.dev/stale-while-revalidate/) — HTTP caching strategy adapted for application layer
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket) — Rate limiting standard

### Projects That Inspired Sift
- [Perplexity AI](https://perplexity.ai) — The gold standard for AI search UX
- [Khoj](https://github.com/khoj-ai/khoj) — Open-source AI personal assistant
- [Obsidian](https://obsidian.md) — Knowledge management philosophy

---

## License

MIT License. See [LICENSE](LICENSE) for details.

Build your knowledge. Own your knowledge.

---

<div align="center">

**[Star this repo](https://github.com/yourusername/sift)** if you believe research knowledge shouldn't disappear when you close a tab.

Built with conviction by engineers who got tired of losing what they learned.

</div>
