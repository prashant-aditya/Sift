"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";
import type { Session } from "@/types/session";

const MOCK_SESSIONS: Session[] = [
  {
    id: "s-001",
    title: "Transformer architecture deep dive",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    query_count: 3,
    sources_used: ["arxiv", "wikipedia"],
  },
  {
    id: "s-002",
    title: "React Server Components vs SSR",
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    query_count: 5,
    sources_used: ["duckduckgo", "reddit", "hackernews"],
  },
  {
    id: "s-003",
    title: "Rust vs Go for backend services",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 20 * 60 * 60 * 1000).toISOString(),
    query_count: 2,
    sources_used: ["hackernews", "reddit"],
  },
  {
    id: "s-004",
    title: "PostgreSQL indexing strategies",
    created_at: new Date(Date.now() - 30 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 28 * 60 * 60 * 1000).toISOString(),
    query_count: 4,
    sources_used: ["duckduckgo", "wikipedia"],
  },
  {
    id: "s-005",
    title: "WebSocket vs SSE for real-time",
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    query_count: 1,
    sources_used: ["duckduckgo"],
  },
  {
    id: "s-006",
    title: "Kubernetes autoscaling patterns",
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    query_count: 6,
    sources_used: ["duckduckgo", "reddit", "hackernews"],
  },
  {
    id: "s-007",
    title: "LLM fine-tuning techniques comparison",
    created_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 9 * 24 * 60 * 60 * 1000).toISOString(),
    query_count: 8,
    sources_used: ["arxiv", "hackernews", "reddit"],
  },
  {
    id: "s-008",
    title: "CSS Container Queries adoption",
    created_at: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
    query_count: 2,
    sources_used: ["duckduckgo", "hackernews"],
  },
];

interface UseSessionReturn {
  sessions: Session[];
  isLoading: boolean;
  error: string | null;
  fetchSessions: () => Promise<void>;
  getSession: (id: string) => Session | undefined;
  archiveSession: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
}

export function useSession(): UseSessionReturn {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiFetch<Session[]>("/api/v1/sessions");
      setSessions(data);
    } catch {
      setSessions(MOCK_SESSIONS);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;
    fetchSessions();
  }, [fetchSessions]);

  const getSession = useCallback(
    (id: string) => sessions.find((s) => s.id === id),
    [sessions],
  );

  const archiveSession = useCallback(
    async (id: string) => {
      try {
        await apiFetch(`/api/v1/sessions/${id}`, { method: "DELETE" });
      } catch {
        // mock fallback — just remove locally
      }
      setSessions((prev) => prev.filter((s) => s.id !== id));
    },
    [],
  );

  const renameSession = useCallback(
    async (id: string, title: string) => {
      try {
        await apiFetch(`/api/v1/sessions/${id}`, {
          method: "PATCH",
          body: JSON.stringify({ title }),
        });
      } catch {
        // mock fallback — just rename locally
      }
      setSessions((prev) =>
        prev.map((s) =>
          s.id === id ? { ...s, title, updated_at: new Date().toISOString() } : s,
        ),
      );
    },
    [],
  );

  return {
    sessions,
    isLoading,
    error,
    fetchSessions,
    getSession,
    archiveSession,
    renameSession,
  };
}
