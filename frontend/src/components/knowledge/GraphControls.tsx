"use client";

import { useMemo } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Session } from "@/types/session";

export interface GraphControlsValue {
  selectedSessionId: string | null;
  selectedTypes: Set<string>;
  minMentions: number;
}

export function GraphControls({
  sessions,
  types,
  value,
  maxMentions,
  onChange,
}: {
  sessions: Session[];
  types: { type: string; count: number }[];
  value: GraphControlsValue;
  maxMentions: number;
  onChange: (next: GraphControlsValue) => void;
}) {
  const typeRows = useMemo(
    () => [...types].sort((a, b) => b.count - a.count || a.type.localeCompare(b.type)),
    [types],
  );

  const sliderMax = Math.max(1, Math.floor(maxMentions));
  const sliderValue = [Math.max(0, Math.min(sliderMax, value.minMentions))];

  return (
    <div className="space-y-4 rounded-xl border bg-card p-4">
      <div className="space-y-1">
        <div className="text-sm font-medium">Filters</div>
        <div className="text-xs text-muted-foreground">
          Changes apply instantly to the graph.
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">Session</Label>
        <Select
          value={value.selectedSessionId ?? "__all__"}
          onValueChange={(v) =>
            onChange({
              ...value,
              selectedSessionId: v === "__all__" ? null : v,
            })
          }
        >
          <SelectTrigger className="w-full" aria-label="Filter graph by session">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All sessions</SelectItem>
            {sessions.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {s.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">Entity types</Label>
        <div className="grid grid-cols-2 gap-x-3 gap-y-2">
          {typeRows.map(({ type, count }) => {
            const checked = value.selectedTypes.has(type);
            return (
              <label key={type} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={checked}
                  onCheckedChange={(nextChecked) => {
                    const next = new Set(value.selectedTypes);
                    if (nextChecked) next.add(type);
                    else next.delete(type);
                    onChange({ ...value, selectedTypes: next });
                  }}
                  aria-label={`Toggle entity type ${type}`}
                />
                <span className="truncate">{type}</span>
                <span className="ml-auto text-xs text-muted-foreground">{count}</span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <Label className="text-xs text-muted-foreground">Min mentions</Label>
          <span className="text-xs text-muted-foreground">{value.minMentions}+</span>
        </div>
        <Slider
          min={0}
          max={sliderMax}
          value={sliderValue}
          onValueChange={(vals) => {
            const v = Array.isArray(vals) ? vals[0] : 0;
            onChange({ ...value, minMentions: Math.floor(v ?? 0) });
          }}
          aria-label="Minimum mention count"
        />
      </div>
    </div>
  );
}

