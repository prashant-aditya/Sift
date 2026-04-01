"use client";

import { ENTITY_TYPE_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function GraphLegend({
  types,
  className,
}: {
  types: string[];
  className?: string;
}) {
  const normalized = Array.from(new Set(types)).sort((a, b) =>
    a.localeCompare(b),
  );

  if (normalized.length === 0) return null;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border bg-card px-3 py-2",
        className,
      )}
      aria-label="Entity type legend"
    >
      {normalized.map((t) => {
        const color = ENTITY_TYPE_COLORS[t]?.color ?? "#64748b";
        return (
          <div key={t} className="inline-flex items-center gap-2 text-xs">
            <span
              className="size-2.5 rounded-full"
              style={{ backgroundColor: color }}
              aria-hidden="true"
            />
            <span className="text-muted-foreground">{t}</span>
          </div>
        );
      })}
    </div>
  );
}

