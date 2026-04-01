"use client";

import { use, useCallback, useRef, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  Calendar,
  MessageSquare,
  Globe,
} from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback, AvatarGroup, AvatarImage } from "@/components/ui/avatar";
import { CitationCard } from "@/components/research/CitationCard";
import { PhaseIndicator } from "@/components/research/PhaseIndicator";
import { SourceIndicator } from "@/components/research/SourceIndicator";
import { ResearchStream } from "@/components/research/ResearchStream";
import { FollowUpInput } from "@/components/research/FollowUpInput";
import { ExportMenu } from "@/components/shared/ExportMenu";
import { ShareDialog, type Collaborator } from "@/components/shared/ShareDialog";
import { useSessionDetail } from "@/hooks/useSessionDetail";
import { useResearch } from "@/hooks/useResearch";
import { SOURCE_MAP, ROUTES } from "@/lib/constants";
import type { Turn } from "@/types/session";
import type { Citation } from "@/types/research";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

function initialsFor(nameOrEmail?: string | null): string {
  const raw = (nameOrEmail ?? "").trim();
  if (!raw) return "U";
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  const left = raw.includes("@") ? raw.split("@")[0] : raw;
  return left.slice(0, 2).toUpperCase();
}

function SessionDetailSkeleton() {
  return (
    <div
      className="space-y-6 p-6"
      aria-label="Loading session"
      role="status"
    >
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <div className="flex gap-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-28" />
        </div>
      </div>

      <div className="space-y-8">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="space-y-4">
            <Skeleton className="h-6 w-3/4" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-4/6" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-20 w-48 rounded-lg" />
              <Skeleton className="h-20 w-48 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Loading...</span>
    </div>
  );
}

function parseCitationsInline(
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

function processChildNodes(
  children: ReactNode,
  citations: Citation[],
): ReactNode {
  if (!children) return children;
  if (typeof children === "string") {
    return parseCitationsInline(children, citations);
  }
  if (Array.isArray(children)) {
    return children.map((child, i) => {
      if (typeof child === "string") {
        const parsed = parseCitationsInline(child, citations);
        return parsed.length === 1 ? parsed[0] : <span key={i}>{parsed}</span>;
      }
      return child;
    });
  }
  return children;
}

function buildMarkdownComponents(citations: Citation[]) {
  return {
    p: ({ children, ...props }: ComponentPropsWithoutRef<"p">) => (
      <p className="mb-3 leading-7" {...props}>
        {processChildNodes(children, citations)}
      </p>
    ),
    h2: ({ children, ...props }: ComponentPropsWithoutRef<"h2">) => (
      <h2 className="mt-5 mb-2 text-xl font-semibold" {...props}>
        {children}
      </h2>
    ),
    h3: ({ children, ...props }: ComponentPropsWithoutRef<"h3">) => (
      <h3 className="mt-4 mb-2 text-lg font-semibold" {...props}>
        {children}
      </h3>
    ),
    ul: ({ children, ...props }: ComponentPropsWithoutRef<"ul">) => (
      <ul className="mb-3 list-disc space-y-1 pl-6" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }: ComponentPropsWithoutRef<"ol">) => (
      <ol className="mb-3 list-decimal space-y-1 pl-6" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }: ComponentPropsWithoutRef<"li">) => (
      <li className="leading-7" {...props}>
        {processChildNodes(children, citations)}
      </li>
    ),
    code: ({
      children,
      className,
      ...props
    }: ComponentPropsWithoutRef<"code">) => {
      const isInline = !className;
      return isInline ? (
        <code
          className="rounded-md bg-muted px-1.5 py-0.5 text-sm font-mono"
          {...props}
        >
          {children}
        </code>
      ) : (
        <code
          className={cn(
            "block overflow-x-auto rounded-lg bg-muted p-4 text-sm font-mono",
            className,
          )}
          {...props}
        >
          {children}
        </code>
      );
    },
    a: ({ children, href, ...props }: ComponentPropsWithoutRef<"a">) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary underline underline-offset-4 hover:text-primary/80 transition-colors motion-reduce:transition-none"
        {...props}
      >
        {children}
      </a>
    ),
    blockquote: ({
      children,
      ...props
    }: ComponentPropsWithoutRef<"blockquote">) => (
      <blockquote
        className="mb-3 border-l-4 border-primary/30 pl-4 italic text-muted-foreground"
        {...props}
      >
        {children}
      </blockquote>
    ),
  };
}

function TurnView({ turn }: { turn: Turn }) {
  const components = buildMarkdownComponents(turn.citations);

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
          Q
        </div>
        <h3 className="text-lg font-semibold leading-snug pt-0.5">
          {turn.query}
        </h3>
      </div>

      <article className="prose prose-neutral dark:prose-invert max-w-none pl-10">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
          {turn.answer}
        </ReactMarkdown>
      </article>

      {turn.citations.length > 0 && (
        <div className="pl-10">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Sources
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {turn.citations.map((citation) => (
              <CitationCard key={citation.id} citation={citation} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SessionMetadata({
  title,
  createdAt,
  queryCount,
  sourcesUsed,
  actions,
}: {
  title: string;
  createdAt: string;
  queryCount: number;
  sourcesUsed: string[];
  actions?: ReactNode;
}) {
  return (
    <header className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <Link href={ROUTES.home}>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Back to home"
            >
              <ArrowLeft className="size-4" />
            </Button>
          </Link>
          <h1 className="truncate text-2xl font-bold tracking-tight">{title}</h1>
        </div>
        {actions ? (
          <div className="flex shrink-0 items-center gap-2">{actions}</div>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <Calendar className="size-3.5" aria-hidden="true" />
          {formatDate(createdAt, "MMM d, yyyy 'at' h:mm a")}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <MessageSquare className="size-3.5" aria-hidden="true" />
          {queryCount} {queryCount === 1 ? "query" : "queries"}
        </span>
        <div className="flex items-center gap-1.5">
          <Globe className="size-3.5 shrink-0" aria-hidden="true" />
          <div className="flex flex-wrap gap-1">
            {sourcesUsed.map((src) => {
              const config = SOURCE_MAP[src];
              return (
                <Badge
                  key={src}
                  variant="secondary"
                  className="text-[10px] px-1.5 py-0"
                >
                  {config?.displayName ?? src}
                </Badge>
              );
            })}
          </div>
        </div>
      </div>
    </header>
  );
}

export default function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const searchParams = useSearchParams();
  const shareToken = searchParams.get("share");
  const isSharedView = Boolean(shareToken);

  const { session, isLoading, error } = useSessionDetail(id, { shareToken });
  const research = useResearch();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);

  const isFollowUpActive = research.phase !== "idle";
  const followUpSessionId = research.sessionId ?? id;

  useEffect(() => {
    if (isFollowUpActive) {
      requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    }
  }, [isFollowUpActive, research.tokens]);

  const handleFollowUp = useCallback(
    (query: string) => {
      research.startFollowUp(id, query);
    },
    [id, research],
  );

  if (isLoading) {
    return <SessionDetailSkeleton />;
  }

  if (error || !session) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <h2 className="text-lg font-semibold">Session not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {error ?? "The session you're looking for doesn't exist."}
        </p>
        <Link href={ROUTES.home} className="mt-6">
          <Button variant="outline">Back to home</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 px-4 py-6 sm:px-6">
      <SessionMetadata
        title={session.title}
        createdAt={session.created_at}
        queryCount={session.query_count}
        sourcesUsed={session.sources_used}
        actions={
          <>
            {collaborators.length > 0 ? (
              <AvatarGroup aria-label="Session collaborators">
                {collaborators.slice(0, 3).map((c) => {
                  const label = c.name || c.email || c.id;
                  return (
                    <Avatar key={c.id} size="sm" aria-label={label}>
                      {c.avatar_url ? (
                        <AvatarImage src={c.avatar_url} alt={label} />
                      ) : null}
                      <AvatarFallback>{initialsFor(label)}</AvatarFallback>
                    </Avatar>
                  );
                })}
              </AvatarGroup>
            ) : null}
            <ExportMenu sessionId={session.id} sessionTitle={session.title} />
            <ShareDialog
              sessionId={session.id}
              sessionTitle={session.title}
              onCollaboratorsChange={setCollaborators}
            />
          </>
        }
      />

      <div className="h-px bg-border" role="separator" />

      <div className="space-y-10">
        {session.turns.map((turn) => (
          <TurnView key={turn.id} turn={turn} />
        ))}
      </div>

      {isFollowUpActive && (
        <div ref={bottomRef} className="space-y-4">
          <div className="h-px bg-border" role="separator" />
          <PhaseIndicator phase={research.phase} />
          <SourceIndicator sourceStatuses={research.sourceStatuses} />
          <ResearchStream
            tokens={research.tokens}
            citations={research.citations}
            isStreaming={research.isStreaming}
          />
        </div>
      )}

      {!isSharedView ? (
        <div className="sticky bottom-4">
          <FollowUpInput
            sessionId={followUpSessionId}
            isStreaming={research.isStreaming}
            onSubmit={handleFollowUp}
          />
        </div>
      ) : (
        <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
          This session is in shared view mode. Sign in with edit access to add
          follow-up queries.
        </div>
      )}
    </div>
  );
}
