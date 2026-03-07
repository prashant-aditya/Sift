"use client";

import { useRef, useEffect, useMemo, useCallback } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { CitationCard } from "./CitationCard";
import { SOURCE_MAP } from "@/lib/constants";
import type { Citation } from "@/types/research";

interface CitationSidebarProps {
  citations: Citation[];
  highlightedId: number | null;
  onHighlightClear?: () => void;
}

interface GroupedCitations {
  sourceName: string;
  displayName: string;
  citations: Citation[];
}

function groupCitationsBySource(citations: Citation[]): GroupedCitations[] {
  const groups = new Map<string, Citation[]>();

  for (const c of citations) {
    const existing = groups.get(c.source_name) ?? [];
    existing.push(c);
    groups.set(c.source_name, existing);
  }

  return Array.from(groups.entries())
    .map(([sourceName, cits]) => ({
      sourceName,
      displayName: SOURCE_MAP[sourceName]?.displayName ?? sourceName,
      citations: cits.sort((a, b) => b.relevance_score - a.relevance_score),
    }))
    .sort((a, b) => b.citations.length - a.citations.length);
}

function CitationList({
  citations,
  highlightedId,
  cardRefs,
}: {
  citations: Citation[];
  highlightedId: number | null;
  cardRefs: React.MutableRefObject<Map<number, HTMLAnchorElement>>;
}) {
  const groups = useMemo(() => groupCitationsBySource(citations), [citations]);

  const setCardRef = useCallback(
    (id: number) => (el: HTMLAnchorElement | null) => {
      if (el) {
        cardRefs.current.set(id, el);
      } else {
        cardRefs.current.delete(id);
      }
    },
    [cardRefs],
  );

  return (
    <div className="space-y-5">
      {groups.map((group) => {
        const sourceConfig = SOURCE_MAP[group.sourceName];
        const Icon = sourceConfig?.icon;

        return (
          <section
            key={group.sourceName}
            aria-label={`${group.displayName} citations`}
          >
            <div className="mb-2 flex items-center gap-1.5 px-1">
              {Icon && (
                <Icon
                  className="size-3.5"
                  style={{ color: sourceConfig?.color }}
                  aria-hidden="true"
                />
              )}
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {group.displayName}
              </h3>
              <span className="text-[10px] text-muted-foreground/70">
                ({group.citations.length})
              </span>
            </div>

            <div className="space-y-2">
              {group.citations.map((citation) => (
                <CitationCard
                  key={citation.id}
                  ref={setCardRef(citation.id)}
                  citation={citation}
                  isHighlighted={highlightedId === citation.id}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export function CitationSidebar({
  citations,
  highlightedId,
  onHighlightClear,
}: CitationSidebarProps) {
  const cardRefs = useRef<Map<number, HTMLAnchorElement>>(new Map());

  useEffect(() => {
    if (highlightedId == null) return;

    const el = cardRefs.current.get(highlightedId);
    if (!el) return;

    el.scrollIntoView({ behavior: "smooth", block: "center" });

    const timer = setTimeout(() => onHighlightClear?.(), 4500);
    return () => clearTimeout(timer);
  }, [highlightedId, onHighlightClear]);

  if (citations.length === 0) return null;

  return (
    <>
      <aside className="hidden lg:block" aria-label="Citations panel">
        <nav aria-label="Source citations">
          <div className="sticky top-8">
            <h2 className="mb-3 text-sm font-semibold">
              Sources ({citations.length})
            </h2>
            <ScrollArea className="max-h-[calc(100vh-8rem)]">
              <CitationList
                citations={citations}
                highlightedId={highlightedId}
                cardRefs={cardRefs}
              />
            </ScrollArea>
          </div>
        </nav>
      </aside>

      <div className="mt-6 lg:hidden" aria-label="Citations">
        <h2 className="mb-3 text-sm font-semibold">
          Sources ({citations.length})
        </h2>
        <CitationList
          citations={citations}
          highlightedId={highlightedId}
          cardRefs={cardRefs}
        />
      </div>
    </>
  );
}

interface CitationSheetProps extends CitationSidebarProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CitationSheet({
  citations,
  highlightedId,
  onHighlightClear,
  open,
  onOpenChange,
}: CitationSheetProps) {
  const cardRefs = useRef<Map<number, HTMLAnchorElement>>(new Map());

  useEffect(() => {
    if (!open || highlightedId == null) return;

    const el = cardRefs.current.get(highlightedId);
    if (!el) return;

    requestAnimationFrame(() => {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    });

    const timer = setTimeout(() => onHighlightClear?.(), 4500);
    return () => clearTimeout(timer);
  }, [open, highlightedId, onHighlightClear]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="max-h-[70vh]">
        <SheetHeader>
          <SheetTitle>Sources ({citations.length})</SheetTitle>
          <SheetDescription>Citations from your research</SheetDescription>
        </SheetHeader>
        <ScrollArea className="flex-1 px-4 pb-4">
          <CitationList
            citations={citations}
            highlightedId={highlightedId}
            cardRefs={cardRefs}
          />
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
