"use client";

import { useState, useCallback, useRef } from "react";
import { useSSE } from "./useSSE";
import { sseUrl } from "@/lib/api";
import { SOURCES } from "@/lib/constants";
import type {
  ResearchPhase,
  ResearchDepth,
  Citation,
  SourceStatus,
  StatusEventData,
  SourceCompleteEventData,
  SourceErrorEventData,
  TokenEventData,
  CompleteEventData,
  ErrorEventData,
} from "@/types/research";
import type { AgentEvent } from "@/types/agent";

interface UseResearchReturn {
  phase: ResearchPhase;
  tokens: string;
  citations: Citation[];
  sourceStatuses: SourceStatus[];
  sessionId: string | null;
  agentEvents: AgentEvent[];
  error: string | null;
  isStreaming: boolean;
  startResearch: (
    query: string,
    sources: string[],
    depth: ResearchDepth,
  ) => void;
  startFollowUp: (sessionId: string, query: string) => void;
  reset: () => void;
}

function buildInitialSourceStatuses(sourceNames: string[]): SourceStatus[] {
  return sourceNames.map((name) => {
    const config = SOURCES.find((s) => s.name === name);
    return {
      name,
      displayName: config?.displayName ?? name,
      status: "waiting" as const,
    };
  });
}

function parseEventData<T>(raw: string): T {
  return JSON.parse(raw) as T;
}

export function useResearch(): UseResearchReturn {
  const [phase, setPhase] = useState<ResearchPhase>("idle");
  const [tokens, setTokens] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [sourceStatuses, setSourceStatuses] = useState<SourceStatus[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const tokensRef = useRef("");

  const handleEvent = useCallback(
    (event: { event: string; data: string }) => {
      const { event: eventType, data: raw } = event;

      switch (eventType) {
        case "status": {
          const payload = parseEventData<StatusEventData>(raw);
          setPhase(payload.phase);

          if (payload.phase === "searching") {
            setSourceStatuses((prev) =>
              prev.map((s) =>
                s.status === "waiting" ? { ...s, status: "searching" } : s,
              ),
            );
          }
          break;
        }

        case "source_complete": {
          const payload = parseEventData<SourceCompleteEventData>(raw);
          setSourceStatuses((prev) =>
            prev.map((s) =>
              s.name === payload.source
                ? {
                    ...s,
                    status: "done",
                    resultsCount: payload.results_count,
                    latencyMs: payload.latency_ms,
                  }
                : s,
            ),
          );
          break;
        }

        case "source_error": {
          const payload = parseEventData<SourceErrorEventData>(raw);
          setSourceStatuses((prev) =>
            prev.map((s) =>
              s.name === payload.source
                ? { ...s, status: "error", error: payload.error }
                : s,
            ),
          );
          break;
        }

        case "token": {
          const payload = parseEventData<TokenEventData>(raw);
          tokensRef.current += payload.content;
          setTokens(tokensRef.current);
          break;
        }

        case "complete": {
          const payload = parseEventData<CompleteEventData>(raw);
          setPhase("complete");
          setCitations(payload.citations);
          setSessionId(payload.session_id);
          break;
        }

        case "error": {
          const payload = parseEventData<ErrorEventData>(raw);
          setPhase("error");
          setError(payload.message);
          break;
        }

        case "agent_thinking": {
          const data = parseEventData<AgentEvent["data"]>(raw);
          setAgentEvents((prev) => [
            ...prev,
            { type: "thinking", data } as AgentEvent,
          ]);
          break;
        }

        case "agent_action": {
          const data = parseEventData<AgentEvent["data"]>(raw);
          setAgentEvents((prev) => [
            ...prev,
            { type: "action", data } as AgentEvent,
          ]);
          break;
        }

        case "agent_action_complete": {
          const data = parseEventData<AgentEvent["data"]>(raw);
          setAgentEvents((prev) => [
            ...prev,
            { type: "action_complete", data } as AgentEvent,
          ]);
          break;
        }

        case "agent_evaluation": {
          const data = parseEventData<AgentEvent["data"]>(raw);
          setAgentEvents((prev) => [
            ...prev,
            { type: "evaluation", data } as AgentEvent,
          ]);
          break;
        }
      }
    },
    [],
  );

  const { start: sseStart, abort: sseAbort, isConnected } = useSSE({
    url: "",
    method: "POST",
    onEvent: handleEvent,
    onOpen: () => setPhase("decomposing"),
    onClose: () => {},
  });

  const resetState = useCallback(() => {
    setPhase("idle");
    setTokens("");
    setCitations([]);
    setSourceStatuses([]);
    setSessionId(null);
    setAgentEvents([]);
    setError(null);
    tokensRef.current = "";
  }, []);

  const startResearch = useCallback(
    (query: string, sources: string[], depth: ResearchDepth) => {
      sseAbort();
      resetState();

      setSourceStatuses(buildInitialSourceStatuses(sources));
      setPhase("decomposing");

      sseStart({
        url: sseUrl("/api/v1/research"),
        body: { query, sources, depth },
      });
    },
    [sseStart, sseAbort, resetState],
  );

  const startFollowUp = useCallback(
    (sid: string, query: string) => {
      sseAbort();

      setTokens("");
      setCitations([]);
      setAgentEvents([]);
      setError(null);
      tokensRef.current = "";
      setPhase("decomposing");

      sseStart({
        url: sseUrl(`/api/v1/research/${sid}/followup`),
        body: { query },
      });
    },
    [sseStart, sseAbort],
  );

  const reset = useCallback(() => {
    sseAbort();
    resetState();
  }, [sseAbort, resetState]);

  return {
    phase,
    tokens,
    citations,
    sourceStatuses,
    sessionId,
    agentEvents,
    error,
    isStreaming: isConnected,
    startResearch,
    startFollowUp,
    reset,
  };
}
