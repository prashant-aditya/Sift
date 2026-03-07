"use client";

import {
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
  type ComponentPropsWithoutRef,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { SOURCE_MAP } from "@/lib/constants";
import type { Citation } from "@/types/research";

interface ResearchStreamProps {
  tokens: string;
  citations: Citation[];
  isStreaming: boolean;
  onCitationClick?: (id: number) => void;
}

function CitationBadge({
  id,
  citations,
  onClick,
}: {
  id: number;
  citations: Citation[];
  onClick?: (id: number) => void;
}) {
  const citation = citations.find((c) => c.id === id);

  const handleActivate = useCallback(() => onClick?.(id), [onClick, id]);

  const badgeClasses = cn(
    "inline-flex size-5 items-center justify-center rounded-full text-[10px] font-bold",
    "align-super cursor-pointer transition-colors motion-reduce:transition-none",
    "bg-primary/15 text-primary hover:bg-primary/25",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
  );

  const label = citation
    ? `Source ${id}: ${citation.title}`
    : `Citation ${id}`;

  if (!citation) {
    return (
      <button
        type="button"
        onClick={handleActivate}
        className={badgeClasses}
        aria-label={label}
      >
        {id}
      </button>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger
          onClick={handleActivate}
          className={badgeClasses}
          aria-label={label}
        >
          {id}
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="space-y-1">
            <p className="font-medium">{citation.title}</p>
            <p className="text-[10px] opacity-70">
              {SOURCE_MAP[citation.source_name]?.displayName ??
                citation.source_name}{" "}
              · {citation.url}
            </p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function parseCitations(
  text: string,
  citations: Citation[],
  onCitationClick?: (id: number) => void,
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
    parts.push(
      <CitationBadge
        key={`cite-${match.index}-${citationId}`}
        id={citationId}
        citations={citations}
        onClick={onCitationClick}
      />,
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

export function ResearchStream({
  tokens,
  citations,
  isStreaming,
  onCitationClick,
}: ResearchStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const autoScrollRef = useRef(true);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    setUserScrolledUp(false);
    autoScrollRef.current = true;
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    function handleScroll() {
      if (!el) return;
      const threshold = 60;
      const isAtBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
      autoScrollRef.current = isAtBottom;
      setUserScrolledUp(!isAtBottom);
    }

    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (autoScrollRef.current && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [tokens]);

  const markdownComponents = {
    p: ({ children, ...props }: ComponentPropsWithoutRef<"p">) => {
      const processed = processChildren(children, citations, onCitationClick);
      return (
        <p className="mb-4 leading-7" {...props}>
          {processed}
        </p>
      );
    },
    h2: ({ children, ...props }: ComponentPropsWithoutRef<"h2">) => (
      <h2 className="mt-6 mb-3 text-xl font-semibold" {...props}>
        {children}
      </h2>
    ),
    h3: ({ children, ...props }: ComponentPropsWithoutRef<"h3">) => (
      <h3 className="mt-5 mb-2 text-lg font-semibold" {...props}>
        {children}
      </h3>
    ),
    code: ({
      children,
      className,
      ...props
    }: ComponentPropsWithoutRef<"code">) => {
      const isInline = !className;
      if (isInline) {
        return (
          <code
            className="rounded-md bg-muted px-1.5 py-0.5 text-sm font-mono"
            {...props}
          >
            {children}
          </code>
        );
      }
      return (
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
    ul: ({ children, ...props }: ComponentPropsWithoutRef<"ul">) => (
      <ul className="mb-4 list-disc space-y-1 pl-6" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }: ComponentPropsWithoutRef<"ol">) => (
      <ol className="mb-4 list-decimal space-y-1 pl-6" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }: ComponentPropsWithoutRef<"li">) => {
      const processed = processChildren(children, citations, onCitationClick);
      return (
        <li className="leading-7" {...props}>
          {processed}
        </li>
      );
    },
    table: ({ children, ...props }: ComponentPropsWithoutRef<"table">) => (
      <div className="mb-4 overflow-x-auto">
        <table className="w-full border-collapse text-sm" {...props}>
          {children}
        </table>
      </div>
    ),
    th: ({ children, ...props }: ComponentPropsWithoutRef<"th">) => (
      <th
        className="border border-border bg-muted/50 px-3 py-2 text-left font-medium"
        {...props}
      >
        {children}
      </th>
    ),
    td: ({ children, ...props }: ComponentPropsWithoutRef<"td">) => (
      <td className="border border-border px-3 py-2" {...props}>
        {children}
      </td>
    ),
    blockquote: ({
      children,
      ...props
    }: ComponentPropsWithoutRef<"blockquote">) => (
      <blockquote
        className="mb-4 border-l-4 border-primary/30 pl-4 italic text-muted-foreground"
        {...props}
      >
        {children}
      </blockquote>
    ),
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
  };

  if (!tokens) return null;

  return (
    <div className="relative">
      <div
        ref={containerRef}
        className="max-h-[60vh] overflow-y-auto scroll-smooth pr-2"
        aria-live="polite"
        aria-atomic="false"
        role="region"
        aria-label="Research results"
        tabIndex={0}
      >
        <article className="prose prose-neutral dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={markdownComponents}
          >
            {tokens}
          </ReactMarkdown>
          {isStreaming && (
            <span
              className="inline-block h-5 w-0.5 animate-typing-blink bg-foreground align-text-bottom motion-reduce:hidden"
              aria-hidden="true"
            />
          )}
        </article>
      </div>

      {userScrolledUp && isStreaming && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
          <Button
            variant="secondary"
            size="sm"
            onClick={scrollToBottom}
            className="shadow-lg touch-target"
            aria-label="Scroll to bottom of results"
          >
            <ArrowDown className="mr-1 size-3.5" aria-hidden="true" />
            Scroll to bottom
          </Button>
        </div>
      )}
    </div>
  );
}

function processChildren(
  children: ReactNode,
  citations: Citation[],
  onCitationClick?: (id: number) => void,
): ReactNode {
  if (!children) return children;

  if (typeof children === "string") {
    return parseCitations(children, citations, onCitationClick);
  }

  if (Array.isArray(children)) {
    return children.map((child, i) => {
      if (typeof child === "string") {
        const parsed = parseCitations(child, citations, onCitationClick);
        return parsed.length === 1 ? (
          parsed[0]
        ) : (
          <span key={i}>{parsed}</span>
        );
      }
      return child;
    });
  }

  return children;
}
