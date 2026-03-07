"use client";

import { useState, useCallback } from "react";
import { AlertTriangle, RefreshCw, SearchX, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { PhaseIndicator } from "./PhaseIndicator";
import { SourceIndicator } from "./SourceIndicator";
import { ResearchStream } from "./ResearchStream";
import { CitationSidebar } from "./CitationSidebar";
import type { ResearchPhase, Citation, SourceStatus } from "@/types/research";

interface ResearchViewProps {
  phase: ResearchPhase;
  tokens: string;
  citations: Citation[];
  sourceStatuses: SourceStatus[];
  isStreaming: boolean;
  error: string | null;
  onRetry?: () => void;
}

function ResearchSkeleton() {
  return (
    <div className="space-y-4" aria-label="Loading research results" role="status">
      <Skeleton className="h-5 w-48" />
      <div className="flex gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-24 rounded-full" />
        ))}
      </div>
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  );
}

function NoResultsState({ onRetry }: { onRetry?: () => void }) {
  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <div className="mb-4 rounded-full bg-muted p-4">
        <SearchX className="size-8 text-muted-foreground" aria-hidden="true" />
      </div>
      <h2 className="text-lg font-semibold">No results found</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        No sources returned results. Try a different query or adjust your source
        selection.
      </p>
      {onRetry && (
        <Button
          variant="outline"
          onClick={onRetry}
          className="mt-6 touch-target"
        >
          <RefreshCw className="mr-2 size-4" aria-hidden="true" />
          Try again
        </Button>
      )}
    </div>
  );
}

function ErrorState({
  error,
  onRetry,
}: {
  error: string;
  onRetry?: () => void;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <div className="mb-4 rounded-full bg-destructive/10 p-4">
        <AlertTriangle
          className="size-8 text-destructive"
          aria-hidden="true"
        />
      </div>
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        An error occurred while processing your research query. Please try
        again.
      </p>

      <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen}>
        <CollapsibleTrigger
          className={cn(
            "mt-3 inline-flex items-center gap-1 rounded-md px-3 py-1.5 text-xs text-muted-foreground",
            "hover:bg-accent hover:text-accent-foreground transition-colors motion-reduce:transition-none",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          )}
        >
          <ChevronDown
            className={cn(
              "size-3 transition-transform motion-reduce:transition-none",
              detailsOpen && "rotate-180",
            )}
            aria-hidden="true"
          />
          {detailsOpen ? "Hide" : "Show"} error details
        </CollapsibleTrigger>
        <CollapsibleContent>
          <pre className="mt-2 max-w-md overflow-x-auto rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-left text-xs text-destructive">
            {error}
          </pre>
        </CollapsibleContent>
      </Collapsible>

      {onRetry && (
        <Button
          variant="outline"
          onClick={onRetry}
          className="mt-6 touch-target"
        >
          <RefreshCw className="mr-2 size-4" aria-hidden="true" />
          Try again
        </Button>
      )}
    </div>
  );
}

export function ResearchView({
  phase,
  tokens,
  citations,
  sourceStatuses,
  isStreaming,
  error,
  onRetry,
}: ResearchViewProps) {
  const [highlightedCitationId, setHighlightedCitationId] = useState<
    number | null
  >(null);

  const handleCitationClick = useCallback((id: number) => {
    setHighlightedCitationId(id);
  }, []);

  const handleHighlightClear = useCallback(() => {
    setHighlightedCitationId(null);
  }, []);

  const hasCitations = citations.length > 0;
  const isInitialLoading =
    (phase === "decomposing" || phase === "searching") && !tokens;
  const isComplete = phase === "complete";
  const isError = phase === "error";
  const hasNoResults = isComplete && !tokens && citations.length === 0;

  if (isError && error) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }

  if (hasNoResults) {
    return <NoResultsState onRetry={onRetry} />;
  }

  return (
    <div
      className={
        hasCitations
          ? "grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]"
          : "w-full"
      }
    >
      <div className="min-w-0 space-y-4">
        <PhaseIndicator phase={phase} />
        <SourceIndicator sourceStatuses={sourceStatuses} />

        {isInitialLoading ? (
          <ResearchSkeleton />
        ) : (
          <ResearchStream
            tokens={tokens}
            citations={citations}
            isStreaming={isStreaming}
            onCitationClick={handleCitationClick}
          />
        )}
      </div>

      {hasCitations && (
        <CitationSidebar
          citations={citations}
          highlightedId={highlightedCitationId}
          onHighlightClear={handleHighlightClear}
        />
      )}
    </div>
  );
}
