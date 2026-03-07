"use client";

import { useEffect, useState } from "react";
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
  const [visible, setVisible] = useState(false);
  const [currentConfig, setCurrentConfig] = useState<PhaseConfig | null>(null);

  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    const config = getPhaseConfig(phase, sourcesActive);

    if (!config) {
      setVisible(false);
      if (prefersReducedMotion) {
        setCurrentConfig(null);
      } else {
        const timeout = setTimeout(() => setCurrentConfig(null), 200);
        return () => clearTimeout(timeout);
      }
      return;
    }

    if (prefersReducedMotion) {
      setCurrentConfig(config);
      setVisible(true);
    } else {
      setVisible(false);
      const timeout = setTimeout(() => {
        setCurrentConfig(config);
        setVisible(true);
      }, 150);
      return () => clearTimeout(timeout);
    }
  }, [phase, sourcesActive, prefersReducedMotion]);

  if (!currentConfig) return null;

  const Icon = currentConfig.icon;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className={cn(
        "flex items-center gap-2 text-sm text-muted-foreground",
        "transition-opacity duration-200 motion-reduce:transition-none",
        visible ? "opacity-100" : "opacity-0 motion-reduce:opacity-100",
      )}
    >
      <Icon
        className="size-4 animate-pulse motion-reduce:animate-none"
        aria-hidden="true"
      />
      <span>{currentConfig.label}</span>
    </div>
  );
}
