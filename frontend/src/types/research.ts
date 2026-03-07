import type { RESEARCH_DEPTHS } from "@/lib/constants";

export type ResearchDepth = (typeof RESEARCH_DEPTHS)[number];

export type ResearchPhase =
  | "idle"
  | "decomposing"
  | "searching"
  | "processing"
  | "synthesizing"
  | "complete"
  | "error";

export interface ResearchRequest {
  query: string;
  sources: string[];
  depth: ResearchDepth;
}

export interface Citation {
  id: number;
  title: string;
  url: string;
  source_name: string;
  relevance_score: number;
}

export type SourceSearchStatus =
  | "waiting"
  | "searching"
  | "done"
  | "error";

export interface SourceStatus {
  name: string;
  displayName: string;
  status: SourceSearchStatus;
  resultsCount?: number;
  latencyMs?: number;
  error?: string;
}

export interface SSEEvent {
  event: string;
  data: unknown;
}

export interface StatusEventData {
  phase: "decomposing" | "searching" | "processing" | "synthesizing";
  message: string;
  sources_active?: number;
}

export interface SourceCompleteEventData {
  source: string;
  results_count: number;
  latency_ms: number;
}

export interface SourceErrorEventData {
  source: string;
  error: string;
  circuit_breaker_open: boolean;
}

export interface TokenEventData {
  content: string;
  citations?: number[];
}

export interface CompleteEventData {
  session_id: string;
  sources_used: number;
  latency_ms: number;
  citations: Citation[];
}

export interface ErrorEventData {
  message: string;
  code: string;
}
