"use client";

import * as React from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SOURCES, SOURCE_MAP } from "@/lib/constants";
import type { AnalyticsResponse, CircuitBreakerStatus } from "@/lib/mock-analytics";
import { cn } from "@/lib/utils";

type SortKey = "source" | "latency" | "success" | "circuit";
type SortDir = "asc" | "desc";

type Props = {
  data: AnalyticsResponse["source_performance"];
};

type Row = {
  name: string;
  displayName: string;
  Icon: React.ComponentType<{ className?: string }>;
  avgLatencyMs: number;
  successRate: number; // 0..1
  circuit: CircuitBreakerStatus | "unknown";
};

function toPercent(n: number): number {
  return Math.round(n * 1000) / 10;
}

function circuitBadgeVariant(
  status: Row["circuit"],
): React.ComponentProps<typeof Badge>["variant"] {
  if (status === "closed") return "secondary";
  if (status === "half_open") return "outline";
  if (status === "open") return "destructive";
  return "ghost";
}

function circuitLabel(status: Row["circuit"]): string {
  if (status === "half_open") return "Half-open";
  if (status === "closed") return "Closed";
  if (status === "open") return "Open";
  return "Unknown";
}

function compare(a: Row, b: Row, key: SortKey): number {
  switch (key) {
    case "source":
      return a.displayName.localeCompare(b.displayName);
    case "latency":
      return a.avgLatencyMs - b.avgLatencyMs;
    case "success":
      return a.successRate - b.successRate;
    case "circuit": {
      const order: Record<Row["circuit"], number> = {
        closed: 0,
        half_open: 1,
        open: 2,
        unknown: 3,
      };
      return order[a.circuit] - order[b.circuit];
    }
  }
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ArrowUpDown className="h-4 w-4 opacity-50" />;
  return dir === "asc" ? (
    <ArrowUp className="h-4 w-4" />
  ) : (
    <ArrowDown className="h-4 w-4" />
  );
}

export function SourcePerformance({ data }: Props) {
  const [sortKey, setSortKey] = React.useState<SortKey>("latency");
  const [sortDir, setSortDir] = React.useState<SortDir>("asc");

  const rows = React.useMemo<Row[]>(() => {
    return SOURCES.map((s) => {
      const perf = data[s.name];
      return {
        name: s.name,
        displayName: s.displayName,
        Icon: (SOURCE_MAP[s.name]?.icon ?? s.icon) as unknown as Row["Icon"],
        avgLatencyMs: perf?.avg_latency_ms ?? 0,
        successRate: perf?.success_rate ?? 0,
        circuit: perf?.circuit_breaker ?? "unknown",
      };
    });
  }, [data]);

  const maxLatency = React.useMemo(() => {
    const m = Math.max(1, ...rows.map((r) => r.avgLatencyMs || 0));
    return Number.isFinite(m) ? m : 1;
  }, [rows]);

  const sorted = React.useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const base = compare(a, b, sortKey);
      return sortDir === "asc" ? base : -base;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    setSortKey((prevKey) => {
      if (prevKey !== key) {
        setSortDir("asc");
        return key;
      }
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      return prevKey;
    });
  };

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full border-separate border-spacing-0">
        <thead>
          <tr className="text-left text-xs text-muted-foreground">
            <th className="sticky top-0 bg-card px-4 py-3 font-medium">
              <Button
                variant="ghost"
                size="sm"
                className="-ml-2 h-7"
                onClick={() => toggleSort("source")}
              >
                Source
                <SortIcon active={sortKey === "source"} dir={sortDir} />
              </Button>
            </th>
            <th className="sticky top-0 bg-card px-4 py-3 font-medium">
              <Button
                variant="ghost"
                size="sm"
                className="-ml-2 h-7"
                onClick={() => toggleSort("latency")}
              >
                Avg latency
                <SortIcon active={sortKey === "latency"} dir={sortDir} />
              </Button>
            </th>
            <th className="sticky top-0 bg-card px-4 py-3 font-medium">
              <Button
                variant="ghost"
                size="sm"
                className="-ml-2 h-7"
                onClick={() => toggleSort("success")}
              >
                Success
                <SortIcon active={sortKey === "success"} dir={sortDir} />
              </Button>
            </th>
            <th className="sticky top-0 bg-card px-4 py-3 font-medium">
              <Button
                variant="ghost"
                size="sm"
                className="-ml-2 h-7"
                onClick={() => toggleSort("circuit")}
              >
                Circuit breaker
                <SortIcon active={sortKey === "circuit"} dir={sortDir} />
              </Button>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const ratio = Math.max(0, Math.min(1, r.avgLatencyMs / maxLatency));
            return (
              <tr
                key={r.name}
                className="border-t border-foreground/10 last:border-b hover:bg-muted/40"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <r.Icon className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{r.displayName}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div
                      className="h-2 w-28 rounded-full bg-muted"
                      aria-hidden="true"
                    >
                      <div
                        className="h-2 rounded-full bg-primary"
                        style={{ width: `${Math.round(ratio * 100)}%` }}
                      />
                    </div>
                    <span className="tabular-nums text-sm text-muted-foreground">
                      {r.avgLatencyMs}ms
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "tabular-nums text-sm",
                      r.successRate >= 0.98
                        ? "text-foreground"
                        : r.successRate >= 0.95
                          ? "text-amber-600 dark:text-amber-400"
                          : "text-destructive",
                    )}
                  >
                    {toPercent(r.successRate)}%
                  </span>
                </td>
                <td className="px-4 py-3">
                  <Badge variant={circuitBadgeVariant(r.circuit)}>
                    {circuitLabel(r.circuit)}
                  </Badge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

