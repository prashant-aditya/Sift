export type AgentType =
  | "coordinator"
  | "academic"
  | "practitioner"
  | "factcheck";

export interface AgentThinkingEventData {
  agent: AgentType;
  reasoning: string;
}

export interface AgentActionEventData {
  agent: AgentType;
  action: "search" | "refine" | "verify" | "expand" | "recall";
  sources?: string[];
  queries?: string[];
}

export interface AgentActionCompleteEventData {
  agent: AgentType;
  action: string;
  results_count: number;
  duration_ms: number;
}

export interface AgentEvaluationEventData {
  agent: AgentType;
  confidence: number;
  gaps: string[];
}

export type AgentEvent =
  | { type: "thinking"; data: AgentThinkingEventData }
  | { type: "action"; data: AgentActionEventData }
  | { type: "action_complete"; data: AgentActionCompleteEventData }
  | { type: "evaluation"; data: AgentEvaluationEventData };
