"use client";

import * as React from "react";
import type { AnalyticsResponse } from "@/lib/analytics";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  data: AnalyticsResponse["research_by_week"];
};

function formatWeekLabel(week: string): string {
  const match = week.match(/W(\d{1,2})$/);
  return match ? `W${match[1]}` : week;
}

export function ActivityChart({ data }: Props) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
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
            width={36}
          />
          <Tooltip
            formatter={(value) => [String(value ?? ""), "Queries"]}
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
            dataKey="queries"
            stroke="hsl(var(--primary))"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

