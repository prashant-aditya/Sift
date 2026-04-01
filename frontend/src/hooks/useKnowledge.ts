"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import type { GraphData, Entity, Relationship } from "@/types/knowledge";

function mulberry32(seed: number) {
  return function rand() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const ENTITY_TYPES = [
  "technology",
  "concept",
  "organization",
  "person",
  "pattern",
  "algorithm",
  "protocol",
  "library",
  "service",
] as const;

function buildMockGraphData(seed = 42, nodeCount = 42): GraphData {
  const rand = mulberry32(seed);

  const nodes: Entity[] = Array.from({ length: nodeCount }).map((_, i) => {
    const type = ENTITY_TYPES[Math.floor(rand() * ENTITY_TYPES.length)];
    const mention_count = 1 + Math.floor(rand() * 30);
    const now = Date.now();
    const firstSeen = new Date(now - Math.floor(rand() * 60) * 86400000);
    const lastSeen = new Date(now - Math.floor(rand() * 10) * 86400000);

    return {
      id: `entity-${i + 1}`,
      name: `${type}-${i + 1}`,
      type,
      description: `Mock ${type} entity`,
      mention_count,
      first_seen: firstSeen.toISOString(),
      last_seen: lastSeen.toISOString(),
    };
  });

  const edges: Relationship[] = [];
  const edgeCount = Math.max(50, Math.floor(nodeCount * 2.2));
  const relTypes = [
    "related_to",
    "depends_on",
    "influences",
    "uses",
    "implements",
    "extends",
    "mentions",
  ];

  for (let i = 0; i < edgeCount; i++) {
    const a = nodes[Math.floor(rand() * nodes.length)];
    const b = nodes[Math.floor(rand() * nodes.length)];
    if (!a || !b || a.id === b.id) continue;
    edges.push({
      id: `rel-${i + 1}`,
      source_id: a.id,
      target_id: b.id,
      type: relTypes[Math.floor(rand() * relTypes.length)] ?? "related_to",
      confidence: Math.min(1, Math.max(0.1, rand())),
    });
  }

  return { nodes, edges };
}

export interface UseKnowledgeOptions {
  sessionId?: string;
  enabled?: boolean;
}

export function useKnowledge(options: UseKnowledgeOptions = {}) {
  const { sessionId, enabled = true } = options;

  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const requestIdRef = useRef(0);

  const fetchGraph = useCallback(async () => {
    if (!enabled) return;

    const reqId = ++requestIdRef.current;
    setIsLoading(true);
    setError(null);

    const path = sessionId
      ? `/api/v1/sessions/${encodeURIComponent(sessionId)}/graph`
      : "/api/v1/knowledge/graph";

    try {
      const data = await apiFetch<GraphData>(path);
      if (requestIdRef.current !== reqId) return;
      setGraphData(data);
    } catch (err) {
      if (requestIdRef.current !== reqId) return;
      setError(err);

      if (process.env.NODE_ENV !== "production") {
        setGraphData(buildMockGraphData(sessionId ? sessionId.length * 17 : 42));
      } else {
        setGraphData(null);
      }
    } finally {
      if (requestIdRef.current === reqId) {
        setIsLoading(false);
      }
    }
  }, [enabled, sessionId]);

  useEffect(() => {
    void fetchGraph();
  }, [fetchGraph]);

  return {
    graphData,
    isLoading,
    error,
    refetch: fetchGraph,
  };
}

