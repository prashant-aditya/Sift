"use client";

import { Loader2, Check, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { SOURCE_MAP } from "@/lib/constants";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import type { SourceStatus } from "@/types/research";

interface SourceIndicatorProps {
  sourceStatuses: SourceStatus[];
}

function SourcePill({ source }: { source: SourceStatus }) {
  const config = SOURCE_MAP[source.name];
  const Icon = config?.icon;

  const statusLabel =
    source.status === "waiting"
      ? "Waiting"
      : source.status === "searching"
        ? "Searching"
        : source.status === "done"
          ? `Done: ${source.resultsCount ?? 0} results`
          : `Error: ${source.error ?? "Unknown error"}`;

  const pill = (
    <div
      role="status"
      aria-label={`${source.displayName}: ${statusLabel}`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        "min-h-[44px] sm:min-h-0",
        "transition-colors duration-200 motion-reduce:transition-none",
        source.status === "waiting" &&
          cn(
            "border bg-muted/50",
            config?.borderClass ?? "border-border",
            config?.textClass ?? "text-muted-foreground",
          ),
        source.status === "searching" &&
          "border border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400",
        source.status === "done" &&
          "border border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400",
        source.status === "error" &&
          "border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400",
      )}
    >
      {Icon && source.status === "waiting" && (
        <Icon
          className={cn("size-3", config?.textClass)}
          aria-hidden="true"
        />
      )}

      {source.status === "searching" && (
        <Loader2
          className="size-3 animate-spin motion-reduce:animate-none"
          aria-hidden="true"
        />
      )}

      {source.status === "done" && (
        <Check className="size-3" aria-hidden="true" />
      )}

      {source.status === "error" && (
        <AlertCircle className="size-3" aria-hidden="true" />
      )}

      <span>{source.displayName}</span>

      {source.status === "done" && source.resultsCount != null && (
        <span className="text-[10px] opacity-70">
          {source.resultsCount} · {source.latencyMs}ms
        </span>
      )}
    </div>
  );

  if (source.status === "error" && source.error) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger
            aria-label={`${source.displayName}: Error — ${source.error}`}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
              "min-h-[44px] sm:min-h-0",
              "border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400",
            )}
          >
            <AlertCircle className="size-3" aria-hidden="true" />
            <span>{source.displayName}</span>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p>{source.error}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return pill;
}

export function SourceIndicator({ sourceStatuses }: SourceIndicatorProps) {
  if (sourceStatuses.length === 0) return null;

  return (
    <div
      className="flex flex-wrap gap-2"
      role="group"
      aria-label="Source search statuses"
      aria-live="polite"
    >
      {sourceStatuses.map((source) => (
        <SourcePill key={source.name} source={source} />
      ))}
    </div>
  );
}
