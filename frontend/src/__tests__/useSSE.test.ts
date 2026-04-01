import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useSSE } from "@/hooks/useSSE";

vi.mock("@/lib/mock-sse", () => ({
  shouldUseMock: () => false,
  createMockResponse: vi.fn(),
}));

function createSSEStream(events: Array<{ event: string; data: string }>) {
  const encoder = new TextEncoder();
  const chunks = events
    .map((e) => `event: ${e.event}\ndata: ${e.data}\n\n`)
    .join("");

  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(chunks));
      controller.close();
    },
  });
}

describe("useSSE", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    globalThis.fetch = originalFetch;
  });

  it("parses SSE event format correctly", async () => {
    const events = [
      { event: "status", data: JSON.stringify({ phase: "searching" }) },
      { event: "token", data: JSON.stringify({ content: "Hello" }) },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(createSSEStream(events), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const receivedEvents: Array<{ event: string; data: string }> = [];
    const onEvent = vi.fn((e: { event: string; data: string }) =>
      receivedEvents.push(e),
    );

    const { result } = renderHook(() =>
      useSSE({
        url: "http://localhost:8000/api/v1/research",
        onEvent,
      }),
    );

    await act(async () => {
      result.current.start();
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(receivedEvents[0]).toEqual({
      event: "status",
      data: JSON.stringify({ phase: "searching" }),
    });
    expect(receivedEvents[1]).toEqual({
      event: "token",
      data: JSON.stringify({ content: "Hello" }),
    });
  });

  it("handles abort correctly", async () => {
    const neverResolve = new Promise<Response>(() => {});
    globalThis.fetch = vi.fn().mockReturnValue(neverResolve);

    const { result } = renderHook(() =>
      useSSE({
        url: "http://localhost:8000/api/v1/research",
        onEvent: vi.fn(),
      }),
    );

    await act(async () => {
      result.current.start();
    });

    await act(async () => {
      result.current.abort();
    });

    expect(result.current.isConnected).toBe(false);
  });

  it("handles connection error and retries up to maxRetries", async () => {
    globalThis.fetch = vi
      .fn()
      .mockRejectedValue(new Error("Network failure"));

    const onClose = vi.fn();

    const { result } = renderHook(() =>
      useSSE({
        url: "http://localhost:8000/api/v1/research",
        onEvent: vi.fn(),
        onClose,
        maxRetries: 0,
      }),
    );

    await act(async () => {
      result.current.start();
      await vi.advanceTimersByTimeAsync(500);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("Network failure");
    expect(result.current.isConnected).toBe(false);
  });

  it("calls onOpen when connection is established", async () => {
    const events = [
      { event: "status", data: JSON.stringify({ phase: "searching" }) },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(createSSEStream(events), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const onOpen = vi.fn();

    const { result } = renderHook(() =>
      useSSE({
        url: "http://localhost:8000/api/v1/research",
        onEvent: vi.fn(),
        onOpen,
      }),
    );

    await act(async () => {
      result.current.start();
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("reports error for non-200 responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(null, { status: 500, statusText: "Internal Server Error" }),
    );

    const onClose = vi.fn();

    const { result } = renderHook(() =>
      useSSE({
        url: "http://localhost:8000/api/v1/research",
        onEvent: vi.fn(),
        onClose,
        maxRetries: 0,
      }),
    );

    await act(async () => {
      result.current.start();
      await vi.advanceTimersByTimeAsync(500);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toContain("500");
  });
});
