"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { V2Effects } from "@/components/landing/V2Effects";
import { V2Landing } from "@/components/landing/V2Landing";
import { ResearchView } from "@/components/research/ResearchView";
import { FollowUpInput } from "@/components/research/FollowUpInput";
import { CitationCard } from "@/components/research/CitationCard";
import { SignInToSave } from "@/components/auth/SignInToSave";
import { useResearch } from "@/hooks/useResearch";
import { useAuth } from "@/hooks/useAuth";
import { useAnonymousSession } from "@/hooks/useAnonymousSession";
import { cn } from "@/lib/utils";
import type { ResearchDepth, Citation } from "@/types/research";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

interface CompletedTurn {
  id: string;
  query: string;
  answer: string;
  citations: Citation[];
}

function parseTurnCitations(
  text: string,
  citations: Citation[],
): ReactNode[] {
  const parts: ReactNode[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const citationId = parseInt(match[1], 10);
    const citation = citations.find((c) => c.id === citationId);
    parts.push(
      <span
        key={`cite-${match.index}`}
        className={cn(
          "inline-flex size-5 items-center justify-center rounded-full text-[10px] font-bold",
          "align-super bg-primary/15 text-primary",
        )}
        title={citation?.title}
        aria-label={`Citation ${citationId}`}
      >
        {citationId}
      </span>,
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

function processTurnChildren(
  children: ReactNode,
  citations: Citation[],
): ReactNode {
  if (!children) return children;
  if (typeof children === "string") {
    return parseTurnCitations(children, citations);
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => {
      if (typeof child === "string") {
        const parsed = parseTurnCitations(child, citations);
        return parsed.length === 1 ? parsed[0] : <span key={i}>{parsed}</span>;
      }
      return child;
    });
  }
  return children;
}

function buildTurnComponents(citations: Citation[]) {
  return {
    p: ({ children, ...props }: ComponentPropsWithoutRef<"p">) => (
      <p className="mb-3 leading-7" {...props}>
        {processTurnChildren(children, citations)}
      </p>
    ),
    li: ({ children, ...props }: ComponentPropsWithoutRef<"li">) => (
      <li className="leading-7" {...props}>
        {processTurnChildren(children, citations)}
      </li>
    ),
    a: ({ children, href, ...props }: ComponentPropsWithoutRef<"a">) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary underline underline-offset-4 hover:text-primary/80"
        {...props}
      >
        {children}
      </a>
    ),
  };
}

function PastTurnView({ turn }: { turn: CompletedTurn }) {
  const components = buildTurnComponents(turn.citations);

  return (
    <div className="space-y-3 rounded-lg border border-border/50 bg-card/50 p-5">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px] font-bold">
          Q
        </div>
        <p className="font-semibold leading-snug">{turn.query}</p>
      </div>

      <article className="prose prose-neutral dark:prose-invert max-w-none pl-9 text-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
          {turn.answer}
        </ReactMarkdown>
      </article>

      {turn.citations.length > 0 && (
        <div className="pl-9">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {turn.citations.map((c) => (
              <CitationCard key={c.id} citation={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function HomePage() {
  const {
    phase,
    tokens,
    citations,
    sourceStatuses,
    sessionId,
    isStreaming,
    error,
    startResearch,
    startFollowUp,
    reset,
  } = useResearch();

  const { isAuthenticated } = useAuth();
  const { saveSession, addTurnToSession } = useAnonymousSession();

  const isActive = phase !== "idle";
  const isComplete = phase === "complete";
  const resultsRef = useRef<HTMLDivElement>(null);

  const [currentQuery, setCurrentQuery] = useState("");
  const [pastTurns, setPastTurns] = useState<CompletedTurn[]>([]);
  const turnCounter = useRef(0);
  const anonSessionIdRef = useRef<string | null>(null);
  const savedTurnRef = useRef(false);

  useEffect(() => {
    if (isActive && pastTurns.length === 0) {
      requestAnimationFrame(() => {
        resultsRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    }
  }, [isActive, pastTurns.length]);

  useEffect(() => {
    if (!isAuthenticated && isComplete && tokens && currentQuery && !savedTurnRef.current) {
      savedTurnRef.current = true;
      if (anonSessionIdRef.current) {
        addTurnToSession(anonSessionIdRef.current, currentQuery, tokens, citations);
      } else {
        anonSessionIdRef.current = saveSession(currentQuery, tokens, citations);
      }
    }
  }, [isAuthenticated, isComplete, tokens, currentQuery, citations, saveSession, addTurnToSession]);

  const handleSubmit = useCallback(
    (query: string, sources: string[], depth: ResearchDepth) => {
      setPastTurns([]);
      turnCounter.current = 0;
      anonSessionIdRef.current = null;
      savedTurnRef.current = false;
      setCurrentQuery(query);
      startResearch(query, sources, depth);
    },
    [startResearch],
  );

  const handleFollowUp = useCallback(
    (query: string) => {
      if (!sessionId) return;

      setPastTurns((prev) => [
        ...prev,
        {
          id: `turn-${++turnCounter.current}`,
          query: currentQuery,
          answer: tokens,
          citations,
        },
      ]);

      savedTurnRef.current = false;
      setCurrentQuery(query);
      startFollowUp(sessionId, query);
    },
    [sessionId, currentQuery, tokens, citations, startFollowUp],
  );

  const handleRetry = useCallback(() => {
    setPastTurns([]);
    setCurrentQuery("");
    turnCounter.current = 0;
    anonSessionIdRef.current = null;
    savedTurnRef.current = false;
    reset();
  }, [reset]);

  return (
    <div>
      <V2Effects />
      <V2Landing isStreaming={isStreaming} onSubmit={handleSubmit} />

      {isActive && (
        <div
          ref={resultsRef}
          style={{
            position: "relative",
            zIndex: 2,
            padding: "0 1.5rem 6rem",
            maxWidth: 1100,
            margin: "0 auto",
          }}
        >
          {pastTurns.length > 0 && (
            <div className="mb-6 space-y-4">
              {pastTurns.map((turn) => (
                <PastTurnView key={turn.id} turn={turn} />
              ))}
            </div>
          )}

          <ResearchView
            phase={phase}
            tokens={tokens}
            citations={citations}
            sourceStatuses={sourceStatuses}
            isStreaming={isStreaming}
            error={error}
            onRetry={handleRetry}
          />

          {isComplete && (
            <div className="mt-6 space-y-4">
              {!isAuthenticated && (
                <div className="flex items-center justify-center gap-3 rounded-lg border border-dashed border-border bg-muted/30 px-4 py-3">
                  <p className="text-sm text-muted-foreground">
                    Sign in to save this research and access it later.
                  </p>
                  <SignInToSave />
                </div>
              )}
              {sessionId && (
                <FollowUpInput
                  sessionId={sessionId}
                  isStreaming={isStreaming}
                  onSubmit={handleFollowUp}
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
