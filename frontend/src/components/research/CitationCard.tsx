"use client";

import { forwardRef } from "react";
import { ExternalLink } from "lucide-react";
import { cn, truncateUrl } from "@/lib/utils";
import { SOURCE_MAP } from "@/lib/constants";
import type { Citation } from "@/types/research";

interface CitationCardProps {
  citation: Citation;
  isHighlighted?: boolean;
}

export const CitationCard = forwardRef<HTMLAnchorElement, CitationCardProps>(
  function CitationCard({ citation, isHighlighted = false }, ref) {
    const sourceConfig = SOURCE_MAP[citation.source_name];
    const Icon = sourceConfig?.icon;
    const relevancePercent = Math.round(citation.relevance_score * 100);

    return (
      <a
        ref={ref}
        href={citation.url}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          "group block rounded-lg border p-3 transition-all duration-200",
          "min-h-[44px]",
          "hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          "motion-reduce:transition-none",
          isHighlighted
            ? "animate-citation-highlight border-primary/60 bg-primary/5 shadow-sm ring-1 ring-primary/20 motion-reduce:border-primary motion-reduce:ring-2 motion-reduce:ring-primary/40"
            : "border-border bg-card",
        )}
        aria-label={`Source ${citation.id}: ${citation.title}`}
      >
        <div className="flex items-start gap-2.5">
          <span
            className={cn(
              "flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white",
              sourceConfig?.bgClass ?? "bg-primary",
            )}
            aria-hidden="true"
          >
            {citation.id}
          </span>

          <div className="min-w-0 flex-1 space-y-1.5">
            <p className="line-clamp-2 text-sm font-medium leading-snug group-hover:text-primary transition-colors motion-reduce:transition-none">
              {citation.title}
            </p>

            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {Icon && (
                <Icon
                  className="size-3 shrink-0"
                  style={{ color: sourceConfig?.color }}
                  aria-hidden="true"
                />
              )}
              <span>
                {sourceConfig?.displayName ?? citation.source_name}
              </span>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ExternalLink
                className="size-3 shrink-0 opacity-50"
                aria-hidden="true"
              />
              <span className="truncate">{truncateUrl(citation.url, 40)}</span>
            </div>

            <div className="pt-0.5">
              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>Relevance</span>
                <span>{relevancePercent}%</span>
              </div>
              <div
                className="mt-0.5 h-1 w-full overflow-hidden rounded-full bg-muted"
                role="progressbar"
                aria-valuenow={relevancePercent}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Relevance: ${relevancePercent}%`}
              >
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500 motion-reduce:transition-none",
                    sourceConfig?.bgClass ?? "bg-primary",
                  )}
                  style={{ width: `${relevancePercent}%`, opacity: 0.7 }}
                />
              </div>
            </div>
          </div>
        </div>
      </a>
    );
  },
);
