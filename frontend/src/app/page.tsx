"use client";

import { useCallback } from "react";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { SearchBar } from "@/components/research/SearchBar";
import type { ResearchDepth } from "@/types/research";

export default function HomePage() {
  const handleSubmit = useCallback(
    (query: string, sources: string[], depth: ResearchDepth) => {
      console.log("Research submitted:", { query, sources, depth });
    },
    [],
  );

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight">Sift</h1>
        <p className="mt-2 text-muted-foreground">
          AI-powered deep research across multiple sources
        </p>
      </div>

      <SearchBar onSubmit={handleSubmit} />
    </main>
  );
}
