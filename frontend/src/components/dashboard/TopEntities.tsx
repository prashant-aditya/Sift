"use client";

import * as React from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyticsResponse } from "@/lib/analytics";
import { ENTITY_TYPE_COLORS } from "@/lib/constants";

type Props = {
  data: AnalyticsResponse["top_entities"];
};

type Row = { name: string; mentions: number; type: string };

function safeType(t: unknown): string {
  return typeof t === "string" && t.trim().length ? t : "concept";
}

export function TopEntities({ data }: Props) {
  const rows = React.useMemo<Row[]>(() => {
    const list = (data ?? []).slice(0, 10);
    return list.map((e) => ({
      name: e.name,
      mentions: e.mentions,
      type: safeType(e.type),
    }));
  }, [data]);

  if (!rows.length) {
    return (
      <div className="text-sm text-muted-foreground">
        No entity data yet. Run a few research sessions to populate this chart.
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
          <XAxis
            type="number"
            stroke="hsl(var(--muted-foreground))"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={110}
            stroke="hsl(var(--muted-foreground))"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--muted))", opacity: 0.45 }}
            formatter={(value, _name, p) => [String(value ?? ""), safeType(p?.payload?.type)]}
            contentStyle={{
              background: "hsl(var(--popover))",
              borderColor: "hsl(var(--border))",
              color: "hsl(var(--popover-foreground))",
              borderRadius: 12,
            }}
            itemStyle={{ color: "hsl(var(--popover-foreground))" }}
            labelStyle={{ color: "hsl(var(--muted-foreground))" }}
          />
          <Bar dataKey="mentions" radius={[6, 6, 6, 6]}>
            {rows.map((r) => {
              const c = ENTITY_TYPE_COLORS[r.type]?.color ?? "hsl(var(--primary))";
              return <Cell key={r.name} fill={c} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

