import { format, subWeeks } from "date-fns";
import { SOURCES } from "@/lib/constants";

export type CircuitBreakerStatus = "closed" | "half_open" | "open";

export type EntityType =
  | "technology"
  | "concept"
  | "organization"
  | "person"
  | "pattern"
  | "algorithm"
  | "protocol"
  | "library"
  | "service";

export type TopEntity = {
  name: string;
  mentions: number;
  type?: EntityType | string;
};

export interface AnalyticsResponse {
  total_sessions?: number;
  total_queries?: number;
  total_entities?: number;
  knowledge_graph_stats?: { nodes: number; edges: number };
  cache_stats?: {
    hit_rate: number; // 0..1
    avg_hit_latency_ms: number;
    avg_miss_latency_ms: number;
  };
  research_by_week: Array<{ week: string; queries: number }>;
  source_performance: Record<
    string,
    {
      avg_latency_ms: number;
      success_rate: number; // 0..1
      circuit_breaker?: CircuitBreakerStatus;
    }
  >;
  top_entities?: TopEntity[];
  knowledge_by_week?: Array<{
    week: string;
    nodes: number;
    edges: number;
    sessions: number;
  }>;
}

function clamp01(n: number): number {
  return Math.max(0, Math.min(1, n));
}

export function getMockAnalytics(): AnalyticsResponse {
  const now = new Date();
  const research_by_week = Array.from({ length: 12 }, (_, i) => {
    const d = subWeeks(now, 11 - i);
    const week = format(d, "RRRR-'W'II");
    const base = 18 + i * 2;
    const jitter = Math.round((Math.sin(i * 1.3) + 1) * 6);
    return { week, queries: base + jitter };
  });

  const knowledge_by_week: AnalyticsResponse["knowledge_by_week"] = Array.from(
    { length: 12 },
    (_, i) => {
      const d = subWeeks(now, 11 - i);
      const week = format(d, "RRRR-'W'II");
      const nodes = Math.round(120 + i * 18 + (Math.cos(i * 0.9) + 1) * 7);
      const edges = Math.round(nodes * (1.45 + (Math.sin(i * 0.8) + 1) * 0.06));
      const sessions = Math.round(8 + i * 1.2 + (Math.sin(i * 1.1) + 1) * 1.4);
      return { week, nodes, edges, sessions };
    },
  );

  const source_performance: AnalyticsResponse["source_performance"] =
    Object.fromEntries(
      SOURCES.map((s, idx) => {
        const avg_latency_ms = Math.round(850 + idx * 210 + (idx % 2) * 140);
        const success_rate = clamp01(0.995 - idx * 0.012);
        const circuit_breaker: CircuitBreakerStatus =
          success_rate >= 0.97 ? "closed" : success_rate >= 0.95 ? "half_open" : "open";
        return [
          s.name,
          {
            avg_latency_ms,
            success_rate,
            circuit_breaker,
          },
        ];
      }),
    );

  const cache_stats: AnalyticsResponse["cache_stats"] = {
    hit_rate: clamp01(0.34 + (Math.sin(Date.now() / 1000 / 60) + 1) * 0.04),
    avg_hit_latency_ms: 180,
    avg_miss_latency_ms: 8500,
  };

  const top_entities: AnalyticsResponse["top_entities"] = [
    { name: "Kafka", mentions: 12, type: "technology" },
    { name: "Redis", mentions: 11, type: "technology" },
    { name: "RRF", mentions: 10, type: "algorithm" },
    { name: "BM25", mentions: 9, type: "algorithm" },
    { name: "Embeddings", mentions: 9, type: "concept" },
    { name: "Stale-while-revalidate", mentions: 8, type: "pattern" },
    { name: "Circuit breaker", mentions: 7, type: "pattern" },
    { name: "Supabase", mentions: 7, type: "service" },
    { name: "PostgreSQL", mentions: 6, type: "technology" },
    { name: "Ollama", mentions: 6, type: "service" },
  ];

  const latestKnowledge = knowledge_by_week?.at(-1);
  const total_sessions =
    latestKnowledge?.sessions ?? Math.round(research_by_week.reduce((a, b) => a + b.queries, 0) / 6);
  const total_queries = research_by_week.reduce((a, b) => a + b.queries, 0);
  const total_entities = top_entities?.reduce((a, b) => a + b.mentions, 0) ?? 0;

  return {
    total_sessions,
    total_queries,
    total_entities,
    knowledge_graph_stats: latestKnowledge ? { nodes: latestKnowledge.nodes, edges: latestKnowledge.edges } : undefined,
    cache_stats,
    research_by_week,
    source_performance,
    top_entities,
    knowledge_by_week,
  };
}

