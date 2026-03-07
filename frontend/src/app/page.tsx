"use client";

import { useCallback, useEffect, useRef } from "react";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { SearchBar } from "@/components/research/SearchBar";
import { ResearchView } from "@/components/research/ResearchView";
import { useResearch } from "@/hooks/useResearch";
import { cn } from "@/lib/utils";
import { Search, Sparkles, BookOpen } from "lucide-react";
import type { ResearchDepth } from "@/types/research";

export default function HomePage() {
  const {
    phase,
    tokens,
    citations,
    sourceStatuses,
    isStreaming,
    error,
    startResearch,
    reset,
  } = useResearch();

  const isActive = phase !== "idle";
  const searchInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    searchInputRef.current?.focus();
  }, []);

  const handleSubmit = useCallback(
    (query: string, sources: string[], depth: ResearchDepth) => {
      startResearch(query, sources, depth);
    },
    [startResearch],
  );

  const handleRetry = useCallback(() => {
    reset();
    requestAnimationFrame(() => searchInputRef.current?.focus());
  }, [reset]);

  return (
    <main className="flex min-h-screen flex-col items-center px-4">
      <div className="absolute top-4 right-4 z-10">
        <ThemeToggle />
      </div>

      <div
        className={cn(
          "w-full transition-all duration-500 motion-reduce:transition-none",
          isActive
            ? "max-w-6xl pt-8"
            : "flex min-h-screen max-w-3xl flex-col items-center justify-center",
        )}
      >
        {!isActive && (
          <div className="mb-10 text-center">
            <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
              Sift
            </h1>
            <p className="mt-3 text-lg text-muted-foreground sm:text-xl">
              AI-powered deep research across multiple sources
            </p>
            <div className="mx-auto mt-6 flex max-w-md flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Search className="size-4" />
                Multi-source search
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Sparkles className="size-4" />
                AI synthesis
              </span>
              <span className="inline-flex items-center gap-1.5">
                <BookOpen className="size-4" />
                Cited answers
              </span>
            </div>
          </div>
        )}

        <div className={cn(isActive && "mx-auto max-w-3xl")}>
          <SearchBar
            ref={searchInputRef}
            onSubmit={handleSubmit}
            isStreaming={isStreaming}
          />
        </div>

        {isActive && (
          <div className="mt-6 w-full">
            <ResearchView
              phase={phase}
              tokens={tokens}
              citations={citations}
              sourceStatuses={sourceStatuses}
              isStreaming={isStreaming}
              error={error}
              onRetry={handleRetry}
            />
          </div>
        )}
      </div>
    </main>
  );
}
