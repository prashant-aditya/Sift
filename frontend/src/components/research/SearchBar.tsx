"use client";

import {
  useState,
  useCallback,
  useRef,
  useEffect,
  forwardRef,
  useMemo,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SourceToggle } from "./SourceToggle";
import { RESEARCH_DEPTHS } from "@/lib/constants";
import { useSources } from "@/hooks/useSources";
import type { ResearchDepth } from "@/types/research";

interface SearchBarProps {
  onSubmit: (query: string, sources: string[], depth: ResearchDepth) => void;
  isStreaming?: boolean;
  defaultSources?: string[];
}

const MIN_CHARS = 3;
const MAX_CHARS = 2000;
const CHAR_COUNT_THRESHOLD = 1900;

export const SearchBar = forwardRef<HTMLTextAreaElement, SearchBarProps>(
  function SearchBar({ onSubmit, isStreaming = false, defaultSources }, ref) {
    const { sources } = useSources();
    const availableSourceNames = useMemo(
      () => new Set(sources.map((s) => s.name)),
      [sources],
    );
    const [query, setQuery] = useState("");
    const [activeSources, setActiveSources] = useState<Set<string>>(
      () => new Set(defaultSources ?? sources.map((s) => s.name)),
    );
    const [depth, setDepth] = useState<ResearchDepth>("standard");
    const internalRef = useRef<HTMLTextAreaElement>(null);
    const textareaRef = (ref as React.RefObject<HTMLTextAreaElement>) ?? internalRef;

    const effectiveActiveSources = useMemo(() => {
      if (defaultSources && defaultSources.length > 0) {
        return defaultSources.filter((s) => availableSourceNames.has(s));
      }
      const selected = Array.from(activeSources).filter((s) =>
        availableSourceNames.has(s),
      );
      return selected.length > 0 ? selected : Array.from(availableSourceNames);
    }, [defaultSources, activeSources, availableSourceNames]);

    const canSubmit =
      query.trim().length >= MIN_CHARS &&
      effectiveActiveSources.length > 0 &&
      !isStreaming;

    useEffect(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    }, [query, textareaRef]);

    const handleToggle = useCallback((name: string) => {
      setActiveSources((prev) => {
        const next = new Set(prev);
        if (next.has(name)) {
          if (next.size > 1) next.delete(name);
        } else {
          next.add(name);
        }
        return next;
      });
    }, []);

    const handleSubmit = useCallback(
      (e?: FormEvent) => {
        e?.preventDefault();
        if (!canSubmit) return;
        onSubmit(query.trim(), effectiveActiveSources, depth);
      },
      [canSubmit, query, effectiveActiveSources, depth, onSubmit],
    );

    const handleKeyDown = useCallback(
      (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          handleSubmit();
        }
      },
      [handleSubmit],
    );

    return (
      <form onSubmit={handleSubmit} className="w-full max-w-2xl space-y-4">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value.slice(0, MAX_CHARS))}
            onKeyDown={handleKeyDown}
            placeholder="What would you like to research?"
            disabled={isStreaming}
            rows={1}
            className={cn(
              "w-full resize-none rounded-2xl border border-input bg-background",
              "px-4 py-3 pr-12 text-base leading-relaxed",
              "placeholder:text-muted-foreground",
              "focus:border-ring focus:ring-3 focus:ring-ring/50 focus:outline-none",
              "disabled:pointer-events-none disabled:opacity-50",
              "dark:bg-input/30",
            )}
            aria-label="Research query"
          />
          <Button
            type="submit"
            size="icon"
            disabled={!canSubmit}
            className="absolute right-2.5 bottom-2.5 size-9 touch-target rounded-xl"
            aria-label="Submit research query"
          >
            {isStreaming ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <ArrowRight className="size-4" />
            )}
          </Button>
        </div>

        {query.length > CHAR_COUNT_THRESHOLD && (
          <p
            className={cn(
              "text-right text-xs",
              query.length >= MAX_CHARS
                ? "text-destructive"
                : "text-muted-foreground",
            )}
            aria-live="polite"
          >
            {query.length}/{MAX_CHARS}
          </p>
        )}

        <div
          className="flex flex-wrap items-center gap-2"
          role="group"
          aria-label="Research sources"
        >
          {sources.map((source) => (
            <SourceToggle
              key={source.name}
              source={source}
              active={effectiveActiveSources.includes(source.name)}
              onToggle={handleToggle}
              disabled={isStreaming}
            />
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Depth:</span>
          <Select
            value={depth}
            onValueChange={(v) => setDepth(v as ResearchDepth)}
          >
            <SelectTrigger size="sm" aria-label="Research depth">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RESEARCH_DEPTHS.map((d) => (
                <SelectItem key={d} value={d}>
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </form>
    );
  },
);
