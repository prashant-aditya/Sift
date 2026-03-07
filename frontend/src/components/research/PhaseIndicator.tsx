"use client";

import { BrainCircuit, Search, Cog, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ResearchPhase } from "@/types/research";
import type { LucideIcon } from "lucide-react";

interface PhaseIndicatorProps {
  phase: ResearchPhase;
  sourcesActive?: number;
}

interface PhaseConfig {
  label: string;
  icon: LucideIcon;
}

const PHASE_CONFIGS: Record<string, PhaseConfig> = {
  decomposing: { label: "Decomposing query...", icon: BrainCircuit },
  searching: { label: "Searching sources...", icon: Search },
  processing: { label: "Processing results...", icon: Cog },
  synthesizing: { label: "Synthesizing answer...", icon: Sparkles },
};

function getPhaseConfig(
  phase: ResearchPhase,
  sourcesActive?: number,
): PhaseConfig | null {
  const config = PHASE_CONFIGS[phase];
  if (!config) return null;

  if (phase === "searching" && sourcesActive) {
    return {
      ...config,
      label: `Searching ${sourcesActive} sources...`,
    };
  }

  return config;
}

export function PhaseIndicator({ phase, sourcesActive }: PhaseIndicatorProps) {
  const config = getPhaseConfig(phase, sourcesActive);

  if (!config) return null;

  const Icon = config.icon;

  return (
    <div
      key={phase}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground",
        "animate-in fade-in duration-200 motion-reduce:animate-none",
      )}
    >
      <Icon
        className="size-4 animate-pulse motion-reduce:animate-none"
        aria-hidden="true"
      />
      <span>{config.label}</span>
    </div>
  );
}
