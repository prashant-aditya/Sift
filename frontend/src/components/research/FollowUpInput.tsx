"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface FollowUpInputProps {
  sessionId: string;
  isStreaming: boolean;
  onSubmit: (query: string) => void;
}

export function FollowUpInput({
  sessionId,
  isStreaming,
  onSubmit,
}: FollowUpInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed || isStreaming) return;
    onSubmit(trimmed);
    setQuery("");
  }, [query, isStreaming, onSubmit]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const isDisabled = isStreaming;
  const canSend = query.trim().length > 0 && !isStreaming;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-xl border bg-card p-2",
        "shadow-sm transition-shadow focus-within:shadow-md motion-reduce:transition-none",
        isDisabled && "opacity-60",
      )}
      data-session-id={sessionId}
    >
      <label htmlFor="follow-up-input" className="sr-only">
        Follow-up question
      </label>
      <Input
        id="follow-up-input"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a follow-up..."
        disabled={isDisabled}
        className="border-0 bg-transparent shadow-none focus-visible:ring-0"
      />
      <Button
        size="icon"
        onClick={handleSubmit}
        disabled={!canSend}
        className="shrink-0 size-9"
        aria-label="Send follow-up question"
      >
        {isStreaming ? (
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        ) : (
          <Send className="size-4" aria-hidden="true" />
        )}
      </Button>
    </div>
  );
}
