"use client";

import { useCallback, useState } from "react";
import type { Citation } from "@/types/research";

const STORAGE_KEY = "sift_anonymous_sessions";

export interface AnonymousTurn {
  id: string;
  query: string;
  answer: string;
  citations: Citation[];
  timestamp: string;
}

export interface AnonymousSession {
  id: string;
  title: string;
  turns: AnonymousTurn[];
  created_at: string;
  updated_at: string;
}

function readSessions(): AnonymousSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AnonymousSession[]) : [];
  } catch {
    return [];
  }
}

function writeSessions(sessions: AnonymousSession[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {
    // localStorage full or unavailable
  }
}

export function useAnonymousSession() {
  const [sessions, setSessions] = useState<AnonymousSession[]>(() =>
    readSessions(),
  );

  const saveSession = useCallback(
    (query: string, answer: string, citations: Citation[]) => {
      const now = new Date().toISOString();
      const id = `anon-${Date.now()}`;
      const title = query.length > 60 ? query.slice(0, 60) + "..." : query;

      const newSession: AnonymousSession = {
        id,
        title,
        turns: [
          {
            id: `${id}-t0`,
            query,
            answer,
            citations,
            timestamp: now,
          },
        ],
        created_at: now,
        updated_at: now,
      };

      const updated = [newSession, ...readSessions()].slice(0, 20);
      writeSessions(updated);
      setSessions(updated);
      return id;
    },
    [],
  );

  const addTurnToSession = useCallback(
    (
      sessionId: string,
      query: string,
      answer: string,
      citations: Citation[],
    ) => {
      const current = readSessions();
      const updated = current.map((s) => {
        if (s.id !== sessionId) return s;
        return {
          ...s,
          updated_at: new Date().toISOString(),
          turns: [
            ...s.turns,
            {
              id: `${s.id}-t${s.turns.length}`,
              query,
              answer,
              citations,
              timestamp: new Date().toISOString(),
            },
          ],
        };
      });
      writeSessions(updated);
      setSessions(updated);
    },
    [],
  );

  const clearSessions = useCallback(() => {
    writeSessions([]);
    setSessions([]);
  }, []);

  return { sessions, saveSession, addTurnToSession, clearSessions };
}
