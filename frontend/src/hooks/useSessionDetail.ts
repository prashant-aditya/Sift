"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";
import type { SessionDetail, Turn } from "@/types/session";
import type { Citation } from "@/types/research";

const MOCK_CITATIONS: Citation[] = [
  {
    id: 1,
    title: "Attention Is All You Need — Vaswani et al.",
    url: "https://arxiv.org/abs/1706.03762",
    source_name: "arxiv",
    relevance_score: 0.96,
  },
  {
    id: 2,
    title: "The Illustrated Transformer",
    url: "https://jalammar.github.io/illustrated-transformer/",
    source_name: "duckduckgo",
    relevance_score: 0.91,
  },
  {
    id: 3,
    title: "Transformer (machine learning model)",
    url: "https://en.wikipedia.org/wiki/Transformer_(machine_learning_model)",
    source_name: "wikipedia",
    relevance_score: 0.88,
  },
];

function buildMockTurns(sessionId: string): Turn[] {
  const turnData: Record<string, Turn[]> = {
    "s-001": [
      {
        id: "t-001",
        query: "How do transformer architectures work?",
        answer:
          "Transformers are a class of deep learning architectures introduced in the landmark paper " +
          '"Attention Is All You Need" [1]. They rely on **self-attention mechanisms** to process ' +
          "input sequences in parallel rather than sequentially.\n\n" +
          "Key components include:\n\n" +
          "- **Multi-head attention** — allows the model to attend to different representation subspaces [2]\n" +
          "- **Positional encoding** — injects sequence-order information since the architecture has no recurrence\n" +
          "- **Feed-forward networks** — applied identically to each position after attention layers [3]\n\n" +
          "This architecture has become the backbone of modern NLP, powering models like GPT, BERT, and T5.",
        citations: MOCK_CITATIONS,
        created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      },
      {
        id: "t-002",
        query: "What are the limitations of transformers?",
        answer:
          "Despite their success, transformers have several notable limitations:\n\n" +
          "1. **Quadratic complexity** — self-attention scales as O(n²) with sequence length, making long documents expensive [1]\n" +
          "2. **Memory requirements** — large models require significant GPU memory for both training and inference\n" +
          "3. **Positional encoding limitations** — standard positional encodings struggle with extrapolation to unseen sequence lengths\n" +
          "4. **Lack of explicit reasoning** — transformers learn statistical patterns rather than logical rules [3]\n\n" +
          "Research on efficient attention (Linformer, Performer, Flash Attention) attempts to address the computational bottleneck.",
        citations: MOCK_CITATIONS.slice(0, 2),
        created_at: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
      },
      {
        id: "t-003",
        query: "How does Flash Attention improve performance?",
        answer:
          "Flash Attention is an IO-aware exact attention algorithm that reduces memory reads/writes between GPU HBM and SRAM.\n\n" +
          "Key improvements:\n\n" +
          "- **Tiling** — computes attention in blocks that fit in SRAM, avoiding materialization of the full N×N attention matrix\n" +
          "- **Kernel fusion** — combines multiple operations into a single GPU kernel to reduce memory bandwidth overhead\n" +
          "- **2–4× speedup** over standard attention with **5–20× memory savings** for long sequences\n\n" +
          "Flash Attention 2 further optimizes parallelism and achieves near-optimal FLOP utilization on modern GPUs.",
        citations: [MOCK_CITATIONS[0]],
        created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      },
    ],
    "s-002": [
      {
        id: "t-010",
        query: "What are React Server Components?",
        answer:
          "React Server Components (RSCs) are a paradigm where components render **exclusively on the server**, sending only their serialized output to the client.\n\n" +
          "Benefits include:\n\n" +
          "- **Zero client-side JS** for server components — they never ship JavaScript to the browser\n" +
          "- **Direct data access** — server components can query databases, file systems, or APIs without an intermediate API layer\n" +
          "- **Automatic code splitting** — client components are only loaded when needed\n\n" +
          "RSCs differ from SSR in that they are not re-rendered on the client — they produce a static serialized tree that the client reconciles without hydration.",
        citations: MOCK_CITATIONS.slice(1),
        created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      },
    ],
  };

  return turnData[sessionId] ?? [
    {
      id: "t-default",
      query: "Tell me about this topic",
      answer:
        "This is a research session covering the selected topic. " +
        "The AI analyzed multiple sources to provide a comprehensive overview with citations and key findings.",
      citations: [],
      created_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    },
  ];
}

const MOCK_SESSIONS_BASE: Record<string, Omit<SessionDetail, "turns">> = {
  "s-001": {
    id: "s-001",
    title: "Transformer architecture deep dive",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    query_count: 3,
    sources_used: ["arxiv", "wikipedia"],
  },
  "s-002": {
    id: "s-002",
    title: "React Server Components vs SSR",
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    query_count: 5,
    sources_used: ["duckduckgo", "reddit", "hackernews"],
  },
  "s-003": {
    id: "s-003",
    title: "Rust vs Go for backend services",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 20 * 60 * 60 * 1000).toISOString(),
    query_count: 2,
    sources_used: ["hackernews", "reddit"],
  },
};

function getMockSessionDetail(id: string): SessionDetail | null {
  const base = MOCK_SESSIONS_BASE[id];
  if (!base) return null;
  return { ...base, turns: buildMockTurns(id) };
}

interface UseSessionDetailReturn {
  session: SessionDetail | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useSessionDetail(
  id: string,
  options?: { shareToken?: string | null },
): UseSessionDetailReturn {
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);

  const fetchDetail = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const shareToken = options?.shareToken?.trim();
      const path = shareToken
        ? `/api/v1/sessions/${encodeURIComponent(id)}?share=${encodeURIComponent(
            shareToken,
          )}`
        : `/api/v1/sessions/${encodeURIComponent(id)}`;
      const data = await apiFetch<SessionDetail>(
        path,
      );
      setSession(data);
    } catch {
      const mock = getMockSessionDetail(id);
      if (mock) {
        setSession(mock);
      } else {
        setError("Session not found");
      }
    } finally {
      setIsLoading(false);
    }
  }, [id, options?.shareToken]);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;
    fetchDetail();
  }, [fetchDetail]);

  return { session, isLoading, error, refetch: fetchDetail };
}
