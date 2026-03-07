import type { Citation } from "./research";

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  query_count: number;
  sources_used: string[];
}

export interface Turn {
  id: string;
  query: string;
  answer: string;
  citations: Citation[];
  created_at: string;
}

export interface SessionDetail extends Session {
  turns: Turn[];
}
