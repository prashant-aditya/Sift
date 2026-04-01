"use client";

import dynamic from "next/dynamic";
import { ROUTES } from "@/lib/constants";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const KnowledgeGraph = dynamic(
  () =>
    import("@/components/knowledge/KnowledgeGraph").then((m) => m.KnowledgeGraph),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-xl border bg-card p-6">
        <p className="text-sm text-muted-foreground">Loading graph…</p>
      </div>
    ),
  },
);

export default function KnowledgePage() {
  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Phase 3 • {ROUTES.knowledge}</div>
          <h1 className="text-2xl font-semibold tracking-tight">Knowledge Graph</h1>
          <p className="text-sm text-muted-foreground">
            Explore entities and relationships extracted from your research sessions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link href={ROUTES.home} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            New research
          </Link>
        </div>
      </div>

      <KnowledgeGraph />
    </div>
  );
}

