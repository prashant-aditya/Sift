# Sift — Demo Queries

Ten research queries that showcase Sift's multi-source synthesis, parallel search, and cited answers. Each query is designed to pull information from multiple sources (DuckDuckGo, Wikipedia, Hacker News) and produce a comprehensive, well-structured response.

---

## How to Run

Send any query via `curl` (SSE stream) or through the interactive docs at `http://localhost:8000/docs`.

```bash
curl -N -X POST http://localhost:8000/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{"query": "YOUR QUERY HERE", "depth": "standard"}'
```

**Depth options:**
- `quick` — 3 results per source, top-10 retrieval (fastest)
- `standard` — 5 results per source, top-15 retrieval (default)
- `deep` — 10 results per source, top-20 retrieval (most thorough)

---

## Query 1: Technology Comparison

```json
{
  "query": "Compare Kafka vs RabbitMQ for building an event-driven microservices architecture. What are the trade-offs in terms of ordering guarantees, throughput, and operational complexity?",
  "depth": "deep"
}
```

**Why this works well:** Triggers sub-query decomposition (ordering, throughput, ops complexity). DuckDuckGo finds recent blog posts and benchmarks, Wikipedia provides foundational context on both systems, and Hacker News surfaces practitioner war stories. The synthesizer identifies tensions between sources and builds a structured comparison.

---

## Query 2: Emerging Technology Deep Dive

```json
{
  "query": "What is WebAssembly (WASM) and how is it being used outside the browser? What are the most promising use cases for server-side WASM in 2025?",
  "depth": "standard"
}
```

**Why this works well:** Wikipedia provides technical foundation on WASM, DuckDuckGo finds recent articles on server-side use cases (Spin, Fermyon, Wasmer), and Hacker News captures developer discussions about real-world adoption. The synthesizer bridges the gap between specification and practical usage.

---

## Query 3: Security & Privacy Analysis

```json
{
  "query": "How do zero-knowledge proofs work, and what are their practical applications in blockchain and identity verification systems?",
  "depth": "standard"
}
```

**Why this works well:** Zero-knowledge proofs span mathematics (Wikipedia), implementation projects (DuckDuckGo), and developer opinions on feasibility (Hacker News). The synthesizer must reconcile theoretical explanations with practical limitations discussed by practitioners.

---

## Query 4: Software Architecture Decision

```json
{
  "query": "When should you use a monorepo vs polyrepo structure? What are the tooling requirements, build system implications, and team scaling considerations for each approach?",
  "depth": "deep"
}
```

**Why this works well:** Decomposes into tooling (Nx, Turborepo, Bazel), team dynamics, and CI/CD implications. This surfaces diverse opinions: corporate engineering blogs favor monorepos (Google, Meta), while indie developers and smaller teams often prefer polyrepos. The synthesizer highlights the context-dependent nature of the decision.

---

## Query 5: AI/ML Concepts Explained

```json
{
  "query": "Explain Retrieval-Augmented Generation (RAG). What are the key components, common failure modes, and best practices for building production RAG systems?",
  "depth": "deep"
}
```

**Why this works well:** Directly relevant to Sift's own architecture. Wikipedia covers the academic foundation, DuckDuckGo finds implementation guides and framework comparisons (LangChain, LlamaIndex), and Hacker News discussions reveal real-world pitfalls (chunking strategies, embedding model selection, hallucination mitigation).

---

## Query 6: Historical + Technical Intersection

```json
{
  "query": "What is the history of the Unix philosophy and how do its principles apply to modern API design and microservices architecture?",
  "depth": "standard"
}
```

**Why this works well:** Wikipedia provides the historical narrative (Thompson, Ritchie, McIlroy), DuckDuckGo finds modern interpretations, and Hacker News discussions connect classic Unix principles to contemporary practices. The synthesizer bridges a 50-year gap between historical context and modern application.

---

## Query 7: Database Selection Guide

```json
{
  "query": "Compare PostgreSQL, MongoDB, and DynamoDB for a high-traffic e-commerce application. Consider data modeling, query patterns, scalability, and total cost of ownership.",
  "depth": "deep"
}
```

**Why this works well:** Three-way comparison with multiple evaluation axes triggers rich sub-query decomposition. Each source contributes differently: Wikipedia for technical specifications, DuckDuckGo for benchmark data and migration guides, Hacker News for real operational experience. The synthesizer produces a structured comparison matrix with nuanced trade-offs.

---

## Query 8: DevOps & Infrastructure

```json
{
  "query": "What are the best practices for implementing CI/CD pipelines for containerized applications? Compare GitHub Actions, GitLab CI, and Jenkins for a team of 10-20 developers.",
  "depth": "standard"
}
```

**Why this works well:** Practical DevOps query that benefits from multiple perspectives. DuckDuckGo finds recent feature comparisons and pricing updates, Wikipedia provides background on CI/CD concepts, and Hacker News captures real team experiences with migration stories and gotchas.

---

## Query 9: Distributed Systems Concepts

```json
{
  "query": "Explain the CAP theorem and its practical implications. How do modern distributed databases like CockroachDB, Spanner, and YugabyteDB navigate the CAP trade-offs?",
  "depth": "deep"
}
```

**Why this works well:** Classic CS theory meets modern engineering. Wikipedia explains the theorem rigorously, DuckDuckGo finds vendor documentation and architecture papers, and Hacker News discussions challenge simplified CAP interpretations (Brewer's 2012 clarification, PACELC). The synthesizer reconciles theoretical constraints with practical engineering approaches.

---

## Query 10: Programming Language Evolution

```json
{
  "query": "How has Rust's ownership model influenced other programming languages? What languages have adopted similar memory safety concepts, and what are the ergonomic trade-offs?",
  "depth": "standard"
}
```

**Why this works well:** Cross-cuts language design (Wikipedia on Rust, ownership, affine types), recent developments in other languages like Swift, Vale, and Carbon (DuckDuckGo), and heated community debates about borrow checker ergonomics (Hacker News). The synthesizer identifies the ripple effects of Rust's design decisions across the programming language landscape.

---

## Tips for Crafting Good Queries

1. **Be specific about what you want**: "Compare X and Y for use case Z" works better than "X vs Y".
2. **Ask multi-faceted questions**: Queries with 2-3 dimensions (e.g., performance, cost, complexity) produce richer synthesis.
3. **Use the `deep` depth**: For complex topics, `deep` retrieves more results per source and considers more chunks during synthesis.
4. **Mention constraints**: Adding context like "for a startup" or "for a team of 5" helps the synthesizer provide more targeted analysis.
5. **Ask follow-up questions**: Each query creates a new research session. Reference insights from previous answers to build deeper understanding.

---

## Expected Output Format

Every research query produces an SSE stream with this event sequence:

```
event: status       → {"phase": "decomposing", "session_id": "session_abc123"}
event: status       → {"phase": "decomposed", "sub_queries": ["...", "..."]}
event: status       → {"phase": "searching", "sources_active": 3, ...}
event: source_complete → {"source": "duckduckgo", "results_count": 5}
event: source_complete → {"source": "wikipedia", "results_count": 5}
event: source_complete → {"source": "hackernews", "results_count": 5}
event: status       → {"phase": "processing", "results_count": 15}
event: status       → {"phase": "storing", "chunks_count": 42}
event: status       → {"phase": "retrieving"}
event: status       → {"phase": "synthesizing"}
event: token        → {"content": "## Overview\n\n"}
event: token        → {"content": "Kafka and RabbitMQ..."}
...
event: complete     → {"session_id": "...", "sources_used": 15, "citations": [...]}
```

The final `complete` event includes full citation metadata with verified source URLs, titles, and relevance scores.
