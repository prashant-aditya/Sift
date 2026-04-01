"use client";

import { useRef, useState, useCallback } from "react";
import { EventSourceParserStream } from "eventsource-parser/stream";
import { shouldUseMock, createMockResponse } from "@/lib/mock-sse";

interface UseSSEOptions {
  url: string;
  method?: "GET" | "POST";
  body?: unknown;
  headers?: Record<string, string>;
  onEvent: (event: { event: string; data: string }) => void;
  onOpen?: () => void;
  onClose?: () => void;
  maxRetries?: number;
}

interface UseSSEReturn {
  start: (overrides?: Partial<Pick<UseSSEOptions, "url" | "body">>) => void;
  abort: () => void;
  isConnected: boolean;
  error: Error | null;
}

const DEFAULT_MAX_RETRIES = 3;

export function useSSE(options: UseSSEOptions): UseSSEReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const connect = useCallback(async () => {
    const {
      url,
      method = "POST",
      body,
      headers,
      onEvent,
      onOpen,
      onClose,
    } = optionsRef.current;
    const maxRetries = optionsRef.current.maxRetries ?? DEFAULT_MAX_RETRIES;
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setError(null);

      let res: Response;
      if (shouldUseMock()) {
        res = createMockResponse();
      } else {
        res = await fetch(url, {
          method,
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
            ...headers,
          },
          body: body ? JSON.stringify(body) : undefined,
          cache: "no-store",
          credentials: "include",
          signal: controller.signal,
        });
      }

      if (!res.ok) {
        throw new Error(
          `SSE connection failed: ${res.status} ${res.statusText}`,
        );
      }

      if (!res.body) {
        throw new Error("Response body is null");
      }

      setIsConnected(true);
      retryCountRef.current = 0;
      onOpen?.();

      const stream = res.body
        .pipeThrough(new TextDecoderStream())
        .pipeThrough(new EventSourceParserStream());

      const reader = stream.getReader();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (controller.signal.aborted) break;

          onEvent({
            event: value.event || "message",
            data: value.data,
          });
        }
      } finally {
        reader.releaseLock();
      }

      setIsConnected(false);
      onClose?.();
    } catch (err) {
      if (controller.signal.aborted) {
        setIsConnected(false);
        return;
      }

      setIsConnected(false);

      if (retryCountRef.current < maxRetries) {
        retryCountRef.current++;
        const delay = Math.min(1000 * 2 ** retryCountRef.current, 10_000);
        await new Promise((r) => setTimeout(r, delay));
        if (!controller.signal.aborted) {
          connect();
        }
      } else {
        setError(err instanceof Error ? err : new Error(String(err)));
        onClose?.();
      }
    }
  }, []);

  const start = useCallback(
    (overrides?: Partial<Pick<UseSSEOptions, "url" | "body">>) => {
      if (overrides) {
        optionsRef.current = { ...optionsRef.current, ...overrides };
      }
      retryCountRef.current = 0;
      connect();
    },
    [connect],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsConnected(false);
  }, []);

  return { start, abort, isConnected, error };
}
