"use client";
// @ts-nocheck

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Filter } from "lucide-react";
import { useKnowledge } from "@/hooks/useKnowledge";
import { ENTITY_TYPE_COLORS } from "@/lib/constants";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useSession } from "@/hooks/useSession";
import { EntityDetail } from "@/components/knowledge/EntityDetail";
import { GraphControls } from "@/components/knowledge/GraphControls";
import { GraphLegend } from "@/components/knowledge/GraphLegend";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import Link from "next/link";
import { ROUTES } from "@/lib/constants";
import type { Entity, GraphData } from "@/types/knowledge";

import * as d3 from "d3";

type SimNode = Entity & {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
};

type SimLink = {
  source: SimNode | string;
  target: SimNode | string;
  type: string;
  confidence: number;
};

function normalizeGraphData(graph: GraphData): { nodes: SimNode[]; links: SimLink[] } {
  const nodes: SimNode[] = graph.nodes.map((n) => ({ ...n }));
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const links: SimLink[] = graph.edges
    .map((e) => {
      const s = byId.get(e.source_id);
      const t = byId.get(e.target_id);
      if (!s || !t) return null;
      return {
        source: s,
        target: t,
        type: e.type,
        confidence: e.confidence,
      };
    })
    .filter(Boolean) as SimLink[];

  return { nodes, links };
}

type GraphView = "full" | "session" | "neighborhood";

function buildAdjacency(links: SimLink[]) {
  const neighbors = new Map<string, Set<string>>();
  for (const l of links) {
    const s = (l.source as SimNode).id ?? String(l.source);
    const t = (l.target as SimNode).id ?? String(l.target);
    if (!neighbors.has(s)) neighbors.set(s, new Set());
    if (!neighbors.has(t)) neighbors.set(t, new Set());
    neighbors.get(s)!.add(t);
    neighbors.get(t)!.add(s);
  }
  return neighbors;
}

function computeNeighborhoodIds(
  rootId: string,
  neighbors: Map<string, Set<string>>,
  hops: 1 | 2,
): Set<string> {
  const keep = new Set<string>();
  keep.add(rootId);
  let frontier = new Set<string>([rootId]);

  for (let i = 0; i < hops; i++) {
    const next = new Set<string>();
    for (const id of frontier) {
      const ns = neighbors.get(id);
      if (!ns) continue;
      for (const n of ns) {
        if (!keep.has(n)) next.add(n);
        keep.add(n);
      }
    }
    frontier = next;
  }

  return keep;
}

function filterGraphForView(
  graph: GraphData,
  view: GraphView,
  selectedEntityId: string | null,
): GraphData {
  if (view === "session") {
    // Data source already scopes by sessionId when provided.
    // If sessionId is absent, treat as full graph (toggle still functions without breaking).
    return graph;
  }

  if (view !== "neighborhood" || !selectedEntityId) return graph;

  const { nodes, links } = normalizeGraphData(graph);
  const adjacency = buildAdjacency(links);
  const keepIds = computeNeighborhoodIds(selectedEntityId, adjacency, 2);

  const filteredNodes = nodes.filter((n) => keepIds.has(n.id));
  const keepNode = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = graph.edges.filter(
    (e) => keepNode.has(e.source_id) && keepNode.has(e.target_id),
  );

  return { nodes: filteredNodes, edges: filteredEdges };
}

function nodeRadius(n: Entity): number {
  // Keep radii stable across datasets while reflecting mention_count.
  const clamped = Math.max(1, Math.min(50, n.mention_count));
  return 6 + Math.sqrt(clamped) * 1.6;
}

function nodeColor(type: string): string {
  return ENTITY_TYPE_COLORS[type]?.color ?? "#64748b";
}

function edgeOpacity(confidence: number): number {
  const c = Number.isFinite(confidence) ? confidence : 0.5;
  return Math.max(0.12, Math.min(0.9, c));
}

function useResizeObserver<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [rect, setRect] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const cr = entry.contentRect;
      setRect({
        width: Math.max(0, Math.floor(cr.width)),
        height: Math.max(0, Math.floor(cr.height)),
      });
    });

    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return { ref, rect };
}

function KnowledgeGraphSvgRenderer({
  graph,
  onNodeClick,
  onNodeHover,
  hoveredId,
}: {
  graph: GraphData;
  onNodeClick: (entity: Entity) => void;
  onNodeHover: (entityId: string | null) => void;
  hoveredId: string | null;
}) {
  const { ref: containerRef, rect } = useResizeObserver<HTMLDivElement>();
  const svgRef = useRef<SVGSVGElement | null>(null);

  const { nodes, links } = useMemo(() => normalizeGraphData(graph), [graph]);

  useEffect(() => {
    let mounted = true;
    let simulation: import("d3").Simulation<SimNode, undefined> | null = null;

    async function run() {
      if (!svgRef.current) return;
      if (rect.width <= 0 || rect.height <= 0) return;
      if (nodes.length === 0) return;

      if (!mounted) return;

      const svg = d3.select(svgRef.current) as any;
      svg.selectAll("*").remove();

      svg
        .attr("viewBox", `0 0 ${rect.width} ${rect.height}`)
        .attr("role", "img")
        .attr("aria-label", "Knowledge graph visualization");

      const g = svg.append("g");

      const zoom = d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.25, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform.toString());
        });

      svg.call(zoom);

      // Edges
      const link = g
        .append("g")
        .attr("stroke", "rgba(148, 163, 184, 0.6)")
        .attr("stroke-linecap", "round")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", (d: SimLink) => 1 + d.confidence * 1.8)
        .attr("opacity", (d: SimLink) => edgeOpacity(d.confidence));

      // Edge labels
      const linkLabel = g
        .append("g")
        .selectAll("text")
        .data(links)
        .join("text")
        .attr("font-size", 10)
        .attr("fill", "rgba(226, 232, 240, 0.72)")
        .attr("pointer-events", "none")
        .attr("text-anchor", "middle")
        .text((d: SimLink) => d.type);

      // Nodes
      const nodeLayer = g
        .append("g")
        .attr("fill-opacity", 1)
        .selectAll("circle")
        .data(nodes, (d: SimNode) => d.id)
        .join("circle")
        .attr("r", (d: SimNode) => nodeRadius(d))
        .attr("fill", (d: SimNode) => nodeColor(d.type))
        .attr("fill-opacity", 0.95)
        .attr("stroke", "rgba(15, 23, 42, 0.6)")
        .attr("stroke-width", 1)
        .attr("cursor", "pointer")
        .attr("tabindex", 0)
        .attr("role", "button")
        .attr("aria-label", (d: SimNode) => `Entity ${d.name}`);

      nodeLayer
        .append("title")
        .text((d: SimNode) => `${d.name} • ${d.type} • mentions: ${d.mention_count}`);

      // Node labels
      const nodeLabel = g
        .append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("font-size", 11)
        .attr("fill", "rgba(226, 232, 240, 0.86)")
        .attr("pointer-events", "none")
        .attr("text-anchor", "middle")
        .text((d: SimNode) => d.name);

      const adjacency = buildAdjacency(links);

      function isNeighbor(a: string, b: string) {
        return adjacency.get(a)?.has(b) ?? false;
      }

      function updateHoverStyles(hoverId: string | null) {
        if (!hoverId) {
          nodeLayer.attr("opacity", 1);
          link.attr("opacity", (d: SimLink) => edgeOpacity(d.confidence));
          linkLabel.attr("opacity", 0.9);
          nodeLabel.attr("opacity", 1);
          return;
        }

        nodeLayer.attr("opacity", (d: SimNode) => (d.id === hoverId || isNeighbor(hoverId, d.id) ? 1 : 0.15));
        nodeLabel.attr("opacity", (d: SimNode) => (d.id === hoverId || isNeighbor(hoverId, d.id) ? 1 : 0.12));

        link.attr("opacity", (d: SimLink) => {
          const s = (d.source as SimNode).id;
          const t = (d.target as SimNode).id;
          const active = s === hoverId || t === hoverId || (s && t && isNeighbor(hoverId, s) && isNeighbor(hoverId, t));
          return active ? Math.min(1, edgeOpacity(d.confidence) + 0.25) : 0.08;
        });

        linkLabel.attr("opacity", (d: SimLink) => {
          const s = (d.source as SimNode).id;
          const t = (d.target as SimNode).id;
          return s === hoverId || t === hoverId ? 1 : 0.08;
        });
      }

      nodeLayer
        .on("pointerenter", (_: unknown, d: SimNode) => {
          onNodeHover(d.id);
          updateHoverStyles(d.id);
        })
        .on("pointerleave", () => {
          onNodeHover(null);
          updateHoverStyles(null);
        })
        .on("click", (_: unknown, d: SimNode) => {
          onNodeClick(d);
        })
        .on("keydown", (event: KeyboardEvent, d: SimNode) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onNodeClick(d);
          }
        });

      const collide = d3
        .forceCollide<SimNode>()
        .radius((d) => nodeRadius(d) + 8)
        .strength(0.9);

      const charge = d3.forceManyBody<SimNode>().strength(-160);

      const center = d3.forceCenter(rect.width / 2, rect.height / 2);

      const linkForce = d3
        .forceLink<SimNode, SimLink>(links)
        .id((d) => d.id)
        .distance((d) => 70 + (1 - d.confidence) * 60)
        .strength((d) => 0.25 + d.confidence * 0.45);

      simulation = d3
        .forceSimulation<SimNode>(nodes)
        .force("link", linkForce)
        .force("charge", charge)
        .force("center", center)
        .force("collide", collide)
        .alpha(1)
        .alphaDecay(0.06);

      const drag = d3
        .drag<SVGCircleElement, SimNode>()
        .on("start", (event, d) => {
          event.sourceEvent?.stopPropagation?.();
          if (!event.active) simulation?.alphaTarget(0.25).restart();
          d.fx = d.x ?? rect.width / 2;
          d.fy = d.y ?? rect.height / 2;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation?.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        });

      nodeLayer.call(drag);

      simulation.on("tick", () => {
        // Note: link data uses object refs (SimNode).
        link
          .attr("x1", (d: SimLink) => (d.source as SimNode).x ?? 0)
          .attr("y1", (d: SimLink) => (d.source as SimNode).y ?? 0)
          .attr("x2", (d: SimLink) => (d.target as SimNode).x ?? 0)
          .attr("y2", (d: SimLink) => (d.target as SimNode).y ?? 0);

        linkLabel
          .attr(
            "x",
            (d: SimLink) => (((d.source as SimNode).x ?? 0) + ((d.target as SimNode).x ?? 0)) / 2,
          )
          .attr(
            "y",
            (d: SimLink) => (((d.source as SimNode).y ?? 0) + ((d.target as SimNode).y ?? 0)) / 2,
          );

        nodeLabel
          .attr("x", (d: SimNode) => d.x ?? 0)
          .attr("y", (d: SimNode) => (d.y ?? 0) + nodeRadius(d) + 12);

        nodeLayer
          .attr("cx", (d: SimNode) => d.x ?? 0)
          .attr("cy", (d: SimNode) => d.y ?? 0);
      });

      updateHoverStyles(hoveredId);
    }

    void run();

    return () => {
      mounted = false;
      simulation?.stop();
    };
  }, [nodes, links, rect.width, rect.height, onNodeClick, onNodeHover, hoveredId]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative h-[70vh] min-h-[420px] w-full overflow-hidden rounded-xl border",
        "bg-gradient-to-b from-background to-muted/20",
      )}
    >
      <svg ref={svgRef} className="h-full w-full" />
    </div>
  );
}

function KnowledgeGraphCanvasRenderer({
  graph,
  onNodeClick,
  onNodeHover,
  hoveredId,
}: {
  graph: GraphData;
  onNodeClick: (entity: Entity) => void;
  onNodeHover: (entityId: string | null) => void;
  hoveredId: string | null;
}) {
  const { ref: containerRef, rect } = useResizeObserver<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const { nodes, links } = useMemo(() => normalizeGraphData(graph), [graph]);

  const hoveredIdRef = useRef<string | null>(null);
  const draggingRef = useRef<{ id: string; offsetX: number; offsetY: number } | null>(null);
  const transformRef = useRef<{ x: number; y: number; k: number }>({ x: 0, y: 0, k: 1 });
  const needsRedrawRef = useRef(true);

  useEffect(() => {
    hoveredIdRef.current = hoveredId;
    needsRedrawRef.current = true;
  }, [hoveredId]);

  useEffect(() => {
    let mounted = true;
    let simulation: import("d3").Simulation<SimNode, undefined> | null = null;
    let rafId: number | null = null;
    const canvasEl = canvasRef.current;

    async function run() {
      if (!canvasEl) return;
      if (rect.width <= 0 || rect.height <= 0) return;
      if (nodes.length === 0) return;

      if (!mounted) return;

      const canvas = canvasEl;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const context = ctx;

      const dpr = typeof window !== "undefined" ? window.devicePixelRatio ?? 1 : 1;
      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);

      const adjacency = buildAdjacency(links);

      function worldPoint(clientX: number, clientY: number) {
        const bounds = canvas.getBoundingClientRect();
        const sx = clientX - bounds.left;
        const sy = clientY - bounds.top;
        const t = transformRef.current;
        return { x: (sx - t.x) / t.k, y: (sy - t.y) / t.k };
      }

      function pickNode(x: number, y: number) {
        // Linear scan is fine for ~200 nodes.
        let best: SimNode | null = null;
        let bestDist2 = Infinity;
        for (const n of nodes) {
          const nx = n.x ?? 0;
          const ny = n.y ?? 0;
          const r = nodeRadius(n) + 2;
          const dx = nx - x;
          const dy = ny - y;
          const d2 = dx * dx + dy * dy;
          if (d2 <= r * r && d2 < bestDist2) {
            best = n;
            bestDist2 = d2;
          }
        }
        return best;
      }

      function draw() {
        needsRedrawRef.current = false;

        context.clearRect(0, 0, rect.width, rect.height);
        context.save();

        const t = transformRef.current;
        context.translate(t.x, t.y);
        context.scale(t.k, t.k);

        const hoverId = hoveredIdRef.current;
        const isNeighbor = (a: string, b: string) => adjacency.get(a)?.has(b) ?? false;

        // Links
        for (const l of links) {
          const s = l.source as SimNode;
          const tg = l.target as SimNode;
          const sx = s.x ?? 0;
          const sy = s.y ?? 0;
          const tx = tg.x ?? 0;
          const ty = tg.y ?? 0;

          let alpha = edgeOpacity(l.confidence);
          if (hoverId) {
            const active = s.id === hoverId || tg.id === hoverId || isNeighbor(hoverId, s.id) || isNeighbor(hoverId, tg.id);
            alpha = active ? Math.min(1, alpha + 0.3) : 0.06;
          }

          context.strokeStyle = `rgba(148,163,184,${alpha})`;
          context.lineWidth = 1 + l.confidence * 1.6;
          context.beginPath();
          context.moveTo(sx, sy);
          context.lineTo(tx, ty);
          context.stroke();
        }

        // Nodes
        for (const n of nodes) {
          const x = n.x ?? 0;
          const y = n.y ?? 0;
          const r = nodeRadius(n);
          let alpha = 0.95;
          if (hoverId && n.id !== hoverId && !isNeighbor(hoverId, n.id)) alpha = 0.18;

          context.beginPath();
          context.arc(x, y, r, 0, Math.PI * 2);
          const fill = nodeColor(n.type);
          context.fillStyle = fill.replace("rgb(", "rgba(").replace(")", `,${alpha})`);
          if (!context.fillStyle.includes("rgba(")) {
            context.fillStyle = fill;
            context.globalAlpha = alpha;
          }
          context.fill();
          context.globalAlpha = 1;

          context.strokeStyle = "rgba(15,23,42,0.55)";
          context.lineWidth = 1;
          context.stroke();
        }

        // Labels (only hovered node + neighbors for performance)
        if (hoverId) {
          context.font = "12px ui-sans-serif, system-ui, -apple-system";
          context.textAlign = "center";
          context.textBaseline = "top";
          for (const n of nodes) {
            if (n.id !== hoverId && !isNeighbor(hoverId, n.id)) continue;
            const x = n.x ?? 0;
            const y = (n.y ?? 0) + nodeRadius(n) + 10;
            context.fillStyle = "rgba(226,232,240,0.9)";
            context.fillText(n.name, x, y);
          }
        }

        context.restore();

        if (needsRedrawRef.current) {
          rafId = requestAnimationFrame(draw);
        }
      }

      function scheduleDraw() {
        needsRedrawRef.current = true;
        if (rafId == null) {
          rafId = requestAnimationFrame(() => {
            rafId = null;
            draw();
          });
        }
      }

      const collide = d3
        .forceCollide<SimNode>()
        .radius((d) => nodeRadius(d) + 8)
        .strength(0.9);

      const charge = d3.forceManyBody<SimNode>().strength(-160);
      const center = d3.forceCenter(rect.width / 2, rect.height / 2);

      const linkForce = d3
        .forceLink<SimNode, SimLink>(links)
        .id((d) => d.id)
        .distance((d) => 70 + (1 - d.confidence) * 60)
        .strength((d) => 0.25 + d.confidence * 0.45);

      simulation = d3
        .forceSimulation<SimNode>(nodes)
        .force("link", linkForce)
        .force("charge", charge)
        .force("center", center)
        .force("collide", collide)
        .alpha(1)
        .alphaDecay(0.06);

      simulation.on("tick", scheduleDraw);

      const zoom = d3
        .zoom<HTMLCanvasElement, unknown>()
        .scaleExtent([0.25, 4])
        .on("zoom", (event) => {
          transformRef.current = { x: event.transform.x, y: event.transform.y, k: event.transform.k };
          scheduleDraw();
        });

      d3.select(canvas).call(zoom);

      // Center initial view.
      const initial = d3.zoomIdentity.translate(rect.width * 0.15, rect.height * 0.1).scale(1);
      d3.select(canvas).call(zoom.transform, initial);

      const handlePointerMove = (ev: PointerEvent) => {
        const p = worldPoint(ev.clientX, ev.clientY);
        const dragging = draggingRef.current;
        if (dragging && simulation) {
          const node = nodes.find((n) => n.id === dragging.id);
          if (node) {
            node.fx = p.x + dragging.offsetX;
            node.fy = p.y + dragging.offsetY;
            simulation.alphaTarget(0.25).restart();
          }
          scheduleDraw();
          return;
        }

        const picked = pickNode(p.x, p.y);
        const nextHover = picked?.id ?? null;
        if (nextHover !== hoveredIdRef.current) {
          onNodeHover(nextHover);
        }
      };

      const handlePointerDown = (ev: PointerEvent) => {
        const p = worldPoint(ev.clientX, ev.clientY);
        const picked = pickNode(p.x, p.y);
        if (!picked) return;
        const nx = picked.x ?? 0;
        const ny = picked.y ?? 0;
        draggingRef.current = { id: picked.id, offsetX: nx - p.x, offsetY: ny - p.y };
        picked.fx = nx;
        picked.fy = ny;
        canvas.setPointerCapture(ev.pointerId);
      };

      const handlePointerUp = (ev: PointerEvent) => {
        const dragging = draggingRef.current;
        if (!dragging) return;
        const node = nodes.find((n) => n.id === dragging.id);
        if (node) {
          node.fx = null;
          node.fy = null;
        }
        draggingRef.current = null;
        simulation?.alphaTarget(0);
        scheduleDraw();
        try {
          canvas.releasePointerCapture(ev.pointerId);
        } catch {
          // no-op
        }
      };

      const handleClick = (ev: MouseEvent) => {
        const p = worldPoint(ev.clientX, ev.clientY);
        const picked = pickNode(p.x, p.y);
        if (picked) onNodeClick(picked);
      };

      canvas.addEventListener("pointermove", handlePointerMove);
      canvas.addEventListener("pointerdown", handlePointerDown);
      canvas.addEventListener("pointerup", handlePointerUp);
      canvas.addEventListener("pointercancel", handlePointerUp);
      canvas.addEventListener("click", handleClick);

      scheduleDraw();
    }

    void run();

    return () => {
      mounted = false;
      simulation?.stop();
      if (rafId != null) cancelAnimationFrame(rafId);
      if (canvasEl) canvasEl.replaceWith(canvasEl.cloneNode(false));
    };
  }, [nodes, links, rect.width, rect.height, onNodeClick, onNodeHover]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative h-[70vh] min-h-[420px] w-full overflow-hidden rounded-xl border",
        "bg-gradient-to-b from-background to-muted/20",
      )}
    >
      <canvas
        ref={canvasRef}
        className="h-full w-full"
        role="img"
        aria-label="Knowledge graph visualization"
      />
    </div>
  );
}

export interface KnowledgeGraphProps {
  sessionId?: string;
}

export function KnowledgeGraph({ sessionId }: KnowledgeGraphProps) {
  const [view, setView] = useState<GraphView>("full");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const { sessions } = useSession();

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    sessionId ?? null,
  );
  const [selectedTypesOverride, setSelectedTypesOverride] = useState<Set<string> | null>(
    null,
  );
  const [minMentions, setMinMentions] = useState(0);

  const effectiveSessionId =
    view === "session" ? selectedSessionId ?? sessionId : undefined;
  const { graphData, isLoading, error, refetch } = useKnowledge({ sessionId: effectiveSessionId });

  const typeCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const n of graphData?.nodes ?? []) {
      counts.set(n.type, (counts.get(n.type) ?? 0) + 1);
    }
    return Array.from(counts.entries()).map(([type, count]) => ({ type, count }));
  }, [graphData]);

  const maxMentions = useMemo(() => {
    let m = 0;
    for (const n of graphData?.nodes ?? []) m = Math.max(m, n.mention_count);
    return m;
  }, [graphData]);

  const selectedTypes = useMemo(() => {
    if (selectedTypesOverride) return selectedTypesOverride;
    return new Set((graphData?.nodes ?? []).map((n) => n.type));
  }, [selectedTypesOverride, graphData]);

  const filteredGraph = useMemo(() => {
    if (!graphData) return null;
    const base = filterGraphForView(graphData, view, selectedEntityId);

    const keepNodes = base.nodes.filter((n) => {
      if (selectedTypes.size > 0 && !selectedTypes.has(n.type)) return false;
      if (n.mention_count < minMentions) return false;
      return true;
    });
    const keep = new Set(keepNodes.map((n) => n.id));
    const keepEdges = base.edges.filter(
      (e) => keep.has(e.source_id) && keep.has(e.target_id),
    );

    return { nodes: keepNodes, edges: keepEdges };
  }, [graphData, view, selectedEntityId, selectedTypes, minMentions]);

  const handleNodeClick = useCallback((entity: Entity) => {
    setSelectedEntityId(entity.id);
    setSelectedEntity(entity);
    setDetailOpen(true);
  }, []);

  const handleNodeHover = useCallback((id: string | null) => {
    setHoveredId(id);
  }, []);

  const handleSelectRelatedEntity = useCallback(
    (entityId: string) => {
      if (!graphData) return;
      const next = graphData.nodes.find((n) => n.id === entityId) ?? null;
      setSelectedEntityId(entityId);
      setSelectedEntity(next);
      setDetailOpen(true);
      setView("neighborhood");
    },
    [graphData],
  );

  if (isLoading && !graphData) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">Loading knowledge graph…</p>
      </div>
    );
  }

  if (graphData && graphData.nodes.length === 0) {
    return (
      <div className="rounded-xl border bg-card p-10">
        <div className="mx-auto max-w-md space-y-3 text-center">
          <div className="text-sm font-medium">Start researching to build your knowledge graph</div>
          <p className="text-sm text-muted-foreground">
            Once you run a few sessions, entities and relationships will appear here for exploration.
          </p>
          <div className="pt-2">
            <Link
              href={ROUTES.home}
              className={cn(buttonVariants({ variant: "secondary" }))}
            >
              Go to research
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className="rounded-xl border bg-card p-6">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 size-4 text-destructive" />
          <div className="space-y-2">
            <p className="text-sm font-medium">Couldn’t load the knowledge graph.</p>
            <p className="text-sm text-muted-foreground">
              {error ? "An error occurred while fetching graph data." : "No data returned."}
            </p>
            <Button variant="secondary" size="sm" onClick={() => void refetch()}>
              <RefreshCw className="size-4" />
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {Boolean(error) && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          Showing mock graph data (API unavailable).
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[320px,1fr] lg:items-start">
        <div className="hidden space-y-3 lg:block">
          <GraphControls
            sessions={sessions}
            types={typeCounts}
            maxMentions={maxMentions}
            value={{
              selectedSessionId,
              selectedTypes,
              minMentions,
            }}
            onChange={(next) => {
              setSelectedSessionId(next.selectedSessionId);
              setSelectedTypesOverride(next.selectedTypes);
              setMinMentions(next.minMentions);
            }}
          />
        </div>

        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="inline-flex w-full flex-wrap gap-2 rounded-lg border bg-card p-1 sm:w-auto">
              <Button
                variant={view === "full" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setView("full")}
              >
                Full
              </Button>
              <Button
                variant={view === "session" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setView("session")}
                disabled={(selectedSessionId ?? sessionId) == null}
                title={
                  (selectedSessionId ?? sessionId) == null
                    ? "Pick a session to view a session-scoped graph"
                    : undefined
                }
              >
                Session
              </Button>
              <Button
                variant={view === "neighborhood" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setView("neighborhood")}
                disabled={!selectedEntityId}
                title={!selectedEntityId ? "Select an entity first" : undefined}
              >
                Neighborhood
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Sheet open={filtersOpen} onOpenChange={setFiltersOpen}>
                <SheetTrigger
                  className="lg:hidden"
                  render={
                    <Button variant="outline" size="sm" aria-label="Open filters" />
                  }
                >
                  <Filter className="size-4" />
                  Filters
                </SheetTrigger>
                <SheetContent side="left" className="w-full max-w-none p-0 sm:max-w-md" showCloseButton>
                  <SheetTitle className="sr-only">Graph filters</SheetTitle>
                  <div className="flex h-full flex-col gap-3 px-4 pt-10 pb-4">
                    <GraphControls
                      sessions={sessions}
                      types={typeCounts}
                      maxMentions={maxMentions}
                      value={{
                        selectedSessionId,
                        selectedTypes,
                        minMentions,
                      }}
                      onChange={(next) => {
                        setSelectedSessionId(next.selectedSessionId);
                        setSelectedTypesOverride(next.selectedTypes);
                        setMinMentions(next.minMentions);
                      }}
                    />
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>

          <div className="text-xs text-muted-foreground">
            Tip: scroll to zoom • drag background to pan • drag nodes to reposition
          </div>

          {filteredGraph && filteredGraph.nodes.length > 100 ? (
            <KnowledgeGraphCanvasRenderer
              graph={filteredGraph}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              hoveredId={hoveredId}
            />
          ) : (
            <KnowledgeGraphSvgRenderer
              graph={filteredGraph ?? graphData}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              hoveredId={hoveredId}
            />
          )}

          <GraphLegend types={(filteredGraph ?? graphData).nodes.map((n) => n.type)} />

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>
              {(filteredGraph ?? graphData).nodes.length} nodes • {(filteredGraph ?? graphData).edges.length} edges
            </span>
            <Button variant="ghost" size="sm" onClick={() => void refetch()}>
              <RefreshCw className="size-4" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <EntityDetail
        entity={selectedEntity}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        graph={filteredGraph ?? graphData}
        onSelectRelatedEntity={handleSelectRelatedEntity}
      />
    </div>
  );
}

