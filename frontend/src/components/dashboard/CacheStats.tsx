"use client";

import * as React from "react";
import {
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
} from "recharts";
import type { AnalyticsResponse } from "@/lib/analytics";

type Props = {
  data: AnalyticsResponse["cache_stats"];
};

function clamp01(n: number): number {
  return Math.max(0, Math.min(1, n));
}

function toPercent01(n: number): number {
  return Math.round(clamp01(n) * 1000) / 10;
}

function ms(n: number | undefined): string {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return `${Math.round(n)}ms`;
}

export function CacheStats({ data }: Props) {
  const hitRate = clamp01(data?.hit_rate ?? 0);
  const pct = toPercent01(hitRate);
  const chartData = React.useMemo(() => [{ name: "Hit rate", value: Math.round(hitRate * 100) }], [hitRate]);

  return (
    <div className="grid grid-cols-1 items-center gap-4 sm:grid-cols-[180px_1fr]">
      <div className="relative h-44 w-full sm:h-40 sm:w-44">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="72%"
            outerRadius="100%"
            barSize={12}
            data={chartData}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
            <RadialBar
              dataKey="value"
              cornerRadius={999}
              fill="hsl(var(--primary))"
              background={{ fill: "hsl(var(--muted))" }}
            />
          </RadialBarChart>
        </ResponsiveContainer>

        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="text-center">
            <div className="text-3xl font-semibold tabular-nums">{pct}%</div>
            <div className="text-xs text-muted-foreground">cache hit rate</div>
          </div>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border bg-card px-3 py-2">
          <dt className="text-xs text-muted-foreground">Avg hit latency</dt>
          <dd className="mt-1 text-sm font-medium tabular-nums">{ms(data?.avg_hit_latency_ms)}</dd>
        </div>
        <div className="rounded-lg border bg-card px-3 py-2">
          <dt className="text-xs text-muted-foreground">Avg miss latency</dt>
          <dd className="mt-1 text-sm font-medium tabular-nums">{ms(data?.avg_miss_latency_ms)}</dd>
        </div>
      </dl>
    </div>
  );
}

