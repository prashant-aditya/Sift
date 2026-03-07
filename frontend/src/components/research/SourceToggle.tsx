"use client";

import { cn } from "@/lib/utils";
import type { SourceConfig } from "@/lib/constants";

interface SourceToggleProps {
  source: SourceConfig;
  active: boolean;
  onToggle: (name: string) => void;
  disabled?: boolean;
}

export function SourceToggle({
  source,
  active,
  onToggle,
  disabled,
}: SourceToggleProps) {
  const Icon = source.icon;

  return (
    <button
      type="button"
      role="switch"
      aria-pressed={active}
      aria-checked={active}
      aria-label={`Toggle ${source.displayName} source`}
      disabled={disabled}
      onClick={() => onToggle(source.name)}
      onKeyDown={(e) => {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          onToggle(source.name);
        }
      }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium",
        "min-h-[44px] sm:min-h-0",
        "transition-all duration-150 motion-reduce:transition-none cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        active
          ? "text-white shadow-sm"
          : "border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30",
      )}
      style={active ? { backgroundColor: source.color } : undefined}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      <span>{source.displayName}</span>
    </button>
  );
}
