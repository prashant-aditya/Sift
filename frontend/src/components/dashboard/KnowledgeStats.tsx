"use client";

import * as React from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyticsResponse } from "@/lib/analytics";

type Props = {
  totalSessions?: AnalyticsResponse["total_sessions"];
  graph?: AnalyticsResponse["knowledge_graph_stats"];
  byWeek?: AnalyticsResponse["knowledge_by_week"];
};

function formatWeekLabel(week: string): string {
  const match = week.match(/W(\d{1,2})$/);
  return match ? `W${match[1]}` : week;
}

function pctChange(prev: number, next: number): number | null {
  if (!Number.isFinite(prev) || !Number.isFinite(next) || prev <= 0) return null;
  return Math.round(((next - prev) / prev) * 1000) / 10;
}

export function KnowledgeStats({ totalSessions, graph, byWeek }: Props) {
  const nodes = graph?.nodes ?? 0;
  const edges = graph?.edges ?? 0;
  const sessions = totalSessions ?? 0;

  const series = React.useMemo(() => (byWeek ?? []).slice(-12), [byWeek]);
  const growth = React.useMemo(() => {
    if (series.length < 2) return null;
    const prev = series.at(-2)?.nodes ?? 0;
    const next = series.at(-1)?.nodes ?? 0;
    return pctChange(prev, next);
  }, [series]);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border bg-card px-3 py-2">
          <div className="text-xs text-muted-foreground">Total nodes</div>
          <div className="mt-1 text-sm font-medium tabular-nums">{nodes.toLocaleString()}</div>
        </div>
        <div className="rounded-lg border bg-card px-3 py-2">
          <div className="text-xs text-muted-foreground">Total edges</div>
          <div className="mt-1 text-sm font-medium tabular-nums">{edges.toLocaleString()}</div>
        </div>
        <div className="rounded-lg border bg-card px-3 py-2">
          <div className="text-xs text-muted-foreground">Total sessions</div>
          <div className="mt-1 text-sm font-medium tabular-nums">{sessions.toLocaleString()}</div>
        </div>
        <div className="rounded-lg border bg-card px-3 py-2">
          <div className="text-xs text-muted-foreground">Weekly growth</div>
          <div className="mt-1 text-sm font-medium tabular-nums">
            {growth == null ? "—" : `${growth > 0 ? "+" : ""}${growth}%`}
          </div>
        </div>
      </div>

      <div className="h-40 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 6, right: 12, left: 0, bottom: 0 }}>
            <XAxis
              dataKey="week"
              tickFormatter={formatWeekLabel}
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip
              formatter={(value) => [String(value ?? ""), "Nodes"]}
              labelFormatter={(label) => `Week ${String(label ?? "")}`}
              contentStyle={{
                background: "hsl(var(--popover))",
                borderColor: "hsl(var(--border))",
                color: "hsl(var(--popover-foreground))",
                borderRadius: 12,
              }}
              itemStyle={{ color: "hsl(var(--popover-foreground))" }}
              labelStyle={{ color: "hsl(var(--muted-foreground))" }}
            />
            <Line
              type="monotone"
              dataKey="nodes"
              stroke="hsl(var(--primary))"
              strokeWidth={2.5}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

