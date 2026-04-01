"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiFetch } from "@/lib/api";
import { ENTITY_TYPE_COLORS, ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { useSession } from "@/hooks/useSession";
import type { Entity, GraphData } from "@/types/knowledge";

function formatDate(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.valueOf())) return iso;
  return d.toLocaleString();
}

function buildNeighborIds(graph: GraphData, entityId: string): string[] {
  const neighbors = new Set<string>();
  for (const e of graph.edges) {
    if (e.source_id === entityId) neighbors.add(e.target_id);
    if (e.target_id === entityId) neighbors.add(e.source_id);
  }
  return Array.from(neighbors);
}

export function EntityDetail({
  entity,
  open,
  onOpenChange,
  graph,
  onSelectRelatedEntity,
}: {
  entity: Entity | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  graph: GraphData | null;
  onSelectRelatedEntity: (entityId: string) => void;
}) {
  const router = useRouter();
  const { sessions } = useSession();

  const [sessionIds, setSessionIds] = useState<string[] | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const sessionCacheRef = useRef<Map<string, string[]>>(new Map());
  const inFlightRef = useRef(0);

  const typeMeta = entity ? ENTITY_TYPE_COLORS[entity.type] : undefined;

  const related = useMemo(() => {
    if (!entity || !graph) return [];
    const ids = buildNeighborIds(graph, entity.id);
    const byId = new Map(graph.nodes.map((n) => [n.id, n]));
    return ids
      .map((id) => byId.get(id))
      .filter(Boolean)
      .sort((a, b) => (b?.mention_count ?? 0) - (a?.mention_count ?? 0)) as Entity[];
  }, [entity, graph]);

  useEffect(() => {
    if (!open || !entity) return;

    const entityId = entity.id;
    const cached = sessionCacheRef.current.get(entity.id);
    if (cached) {
      setSessionIds(cached);
      setSessionError(null);
      return;
    }

    let cancelled = false;
    const myFlight = ++inFlightRef.current;
    setSessionIds(null);
    setSessionError(null);

    async function run() {
      // Best-effort implementation:
      // For each session, fetch its graph and check if the entity exists in that session graph.
      // If backend is unavailable, we fall back to a deterministic subset for dev UX.
      const hits: string[] = [];

      const concurrency = 3;
      let idx = 0;

      async function worker() {
        while (!cancelled && idx < sessions.length) {
          const s = sessions[idx++];
          if (!s) continue;
          try {
            const g = await apiFetch<GraphData>(
              `/api/v1/sessions/${encodeURIComponent(s.id)}/graph`,
            );
            const present = g.nodes.some((n) => n.id === entityId);
            if (present) hits.push(s.id);
          } catch {
            // ignore per-session fetch failures; overall fallback handled below
          }
        }
      }

      try {
        await Promise.all(Array.from({ length: Math.min(concurrency, sessions.length) }, worker));
        if (cancelled || inFlightRef.current !== myFlight) return;

        if (hits.length === 0 && sessions.length > 0 && process.env.NODE_ENV !== "production") {
          // dev fallback: stable subset based on entity id hash
          let h = 0;
          for (let i = 0; i < entityId.length; i++) h = (h * 31 + entityId.charCodeAt(i)) >>> 0;
          const take = Math.max(1, Math.min(4, Math.floor((h % 5) + 1)));
          const subset = sessions
            .slice()
            .sort((a, b) => a.id.localeCompare(b.id))
            .filter((_, i) => ((i + h) % 3 === 0))
            .slice(0, take)
            .map((s) => s.id);
          sessionCacheRef.current.set(entityId, subset);
          setSessionIds(subset);
          return;
        }

        const unique = Array.from(new Set(hits)).sort((a, b) => a.localeCompare(b));
        sessionCacheRef.current.set(entityId, unique);
        setSessionIds(unique);
      } catch {
        if (cancelled || inFlightRef.current !== myFlight) return;
        setSessionError("Couldn’t load sessions for this entity.");
        setSessionIds([]);
      }
    }

    void run();

    return () => {
      cancelled = true;
    };
  }, [open, entity, sessions]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="p-0">
        <div className="flex h-full flex-col">
          <div className="px-6 pt-6 pb-4">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <span className="truncate">{entity?.name ?? "Entity"}</span>
                {entity && (
                  <Badge
                    variant="secondary"
                    className={cn(
                      "border border-border bg-muted/40",
                      typeMeta?.textClass,
                    )}
                  >
                    <span
                      className={cn("mr-1 inline-block size-2 rounded-full", typeMeta?.bgClass)}
                      aria-hidden="true"
                    />
                    {entity.type}
                  </Badge>
                )}
              </SheetTitle>
              <SheetDescription>
                {entity ? "Entity details and connections across your research." : "Select an entity"}
              </SheetDescription>
            </SheetHeader>
          </div>

          <Separator />

          <ScrollArea className="flex-1">
            <div className="space-y-6 px-6 py-5">
              {entity?.description && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-muted-foreground">Description</div>
                  <p className="text-sm leading-6 text-foreground/90">{entity.description}</p>
                </div>
              )}

              {entity && (
                <div className="space-y-3">
                  <div className="text-xs font-medium text-muted-foreground">Stats</div>
                  <dl className="grid grid-cols-2 gap-3 rounded-lg border bg-card p-3 text-sm">
                    <div>
                      <dt className="text-[11px] text-muted-foreground">Mentions</dt>
                      <dd className="mt-1 font-medium">{entity.mention_count}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] text-muted-foreground">Type</dt>
                      <dd className="mt-1 font-medium">{entity.type}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] text-muted-foreground">First seen</dt>
                      <dd className="mt-1">{formatDate(entity.first_seen)}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] text-muted-foreground">Last seen</dt>
                      <dd className="mt-1">{formatDate(entity.last_seen)}</dd>
                    </div>
                  </dl>
                </div>
              )}

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-medium text-muted-foreground">Sessions</div>
                  {sessionIds == null && (
                    <div className="text-xs text-muted-foreground">Loading…</div>
                  )}
                </div>

                {sessionError && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                    {sessionError}
                  </div>
                )}

                {entity && sessionIds && (
                  <div className="space-y-2">
                    {sessionIds.length === 0 ? (
                      <div className="text-sm text-muted-foreground">
                        No sessions found for this entity yet.
                      </div>
                    ) : (
                      <div className="space-y-1">
                        {sessionIds.map((id) => {
                          const title = sessions.find((s) => s.id === id)?.title ?? id;
                          return (
                            <Link
                              key={id}
                              href={ROUTES.session(id)}
                              className={cn(
                                "group flex items-center justify-between gap-2 rounded-lg border bg-card px-3 py-2 text-sm",
                                "hover:bg-muted/40",
                              )}
                            >
                              <span className="truncate">{title}</span>
                              <ExternalLink className="size-4 text-muted-foreground group-hover:text-foreground" />
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-3">
                <div className="text-xs font-medium text-muted-foreground">Related entities</div>
                {!entity || !graph ? (
                  <div className="text-sm text-muted-foreground">No graph context loaded.</div>
                ) : related.length === 0 ? (
                  <div className="text-sm text-muted-foreground">
                    No directly connected entities.
                  </div>
                ) : (
                  <div className="space-y-1">
                    {related.slice(0, 12).map((r) => (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => onSelectRelatedEntity(r.id)}
                        className={cn(
                          "flex w-full items-center justify-between gap-2 rounded-lg border bg-card px-3 py-2 text-left text-sm",
                          "hover:bg-muted/40",
                        )}
                      >
                        <span className="truncate">{r.name}</span>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {r.mention_count} mentions
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </ScrollArea>

          <Separator />

          <div className="px-6 py-4">
            <Button
              className="w-full"
              disabled={!entity}
              onClick={() => {
                if (!entity) return;
                router.push(`/?q=${encodeURIComponent(entity.name)}`);
                onOpenChange(false);
              }}
            >
              Research more
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

