import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useResearch } from "@/hooks/useResearch";

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

describe("useResearch", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = originalFetch;
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    globalThis.fetch = originalFetch;
  });

  it("starts in idle phase with empty state", () => {
    const { result } = renderHook(() => useResearch());

    expect(result.current.phase).toBe("idle");
    expect(result.current.tokens).toBe("");
    expect(result.current.citations).toEqual([]);
    expect(result.current.sourceStatuses).toEqual([]);
    expect(result.current.sessionId).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isStreaming).toBe(false);
  });

  it("transitions through phases during research", async () => {
    const sseEvents = [
      {
        event: "status",
        data: JSON.stringify({ phase: "decomposing", message: "Analyzing..." }),
      },
      {
        event: "status",
        data: JSON.stringify({ phase: "searching", message: "Searching...", sources_active: 2 }),
      },
      {
        event: "source_complete",
        data: JSON.stringify({
          source: "duckduckgo",
          results_count: 5,
          latency_ms: 200,
        }),
      },
      {
        event: "status",
        data: JSON.stringify({ phase: "synthesizing", message: "Generating..." }),
      },
      {
        event: "token",
        data: JSON.stringify({ content: "Hello " }),
      },
      {
        event: "token",
        data: JSON.stringify({ content: "world" }),
      },
      {
        event: "complete",
        data: JSON.stringify({
          session_id: "test-session-123",
          sources_used: 2,
          latency_ms: 1500,
          citations: [
            {
              id: 1,
              title: "Test Citation",
              url: "https://example.com",
              source_name: "duckduckgo",
              relevance_score: 0.9,
            },
          ],
        }),
      },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(createSSEStream(sseEvents), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const { result } = renderHook(() => useResearch());

    await act(async () => {
      result.current.startResearch(
        "test query",
        ["duckduckgo", "reddit"],
        "standard",
      );
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(result.current.phase).toBe("complete");
    expect(result.current.tokens).toBe("Hello world");
    expect(result.current.citations).toHaveLength(1);
    expect(result.current.citations[0].title).toBe("Test Citation");
    expect(result.current.sessionId).toBe("test-session-123");
  });

  it("accumulates tokens from token events", async () => {
    const sseEvents = [
      { event: "token", data: JSON.stringify({ content: "Part1 " }) },
      { event: "token", data: JSON.stringify({ content: "Part2 " }) },
      { event: "token", data: JSON.stringify({ content: "Part3" }) },
      {
        event: "complete",
        data: JSON.stringify({
          session_id: "s1",
          sources_used: 1,
          latency_ms: 500,
          citations: [],
        }),
      },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(createSSEStream(sseEvents), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const { result } = renderHook(() => useResearch());

    await act(async () => {
      result.current.startResearch("test", ["duckduckgo"], "quick");
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(result.current.tokens).toBe("Part1 Part2 Part3");
  });

  it("populates citations on complete event", async () => {
    const citations = [
      {
        id: 1,
        title: "Citation A",
        url: "https://a.com",
        source_name: "duckduckgo",
        relevance_score: 0.9,
      },
      { id: 2, title: "Citation B", url: "https://b.com", source_name: "reddit", relevance_score: 0.8 },
    ];

    const sseEvents = [
      {
        event: "complete",
        data: JSON.stringify({
          session_id: "s2",
          sources_used: 2,
          latency_ms: 800,
          citations,
        }),
      },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(createSSEStream(sseEvents), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const { result } = renderHook(() => useResearch());

    await act(async () => {
      result.current.startResearch("test", ["duckduckgo", "reddit"], "standard");
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(result.current.citations).toHaveLength(2);
    expect(result.current.citations[0].title).toBe("Citation A");
    expect(result.current.citations[1].title).toBe("Citation B");
  });

  it("handles error events", async () => {
    const sseEvents = [
      {
        event: "error",
        data: JSON.stringify({ message: "Rate limit exceeded", code: "RATE_LIMIT" }),
      },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(createSSEStream(sseEvents), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const { result } = renderHook(() => useResearch());

    await act(async () => {
      result.current.startResearch("test", ["duckduckgo"], "quick");
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(result.current.phase).toBe("error");
    expect(result.current.error).toBe("Rate limit exceeded");
  });

  it("resets state correctly", async () => {
    const sseEvents = [
      { event: "token", data: JSON.stringify({ content: "data" }) },
      {
        event: "complete",
        data: JSON.stringify({
          session_id: "s3",
          sources_used: 1,
          latency_ms: 100,
          citations: [
            {
              id: 1,
              title: "C",
              url: "https://c.com",
              source_name: "duckduckgo",
              relevance_score: 0.5,
            },
          ],
        }),
      },
    ];

    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(createSSEStream(sseEvents), {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const { result } = renderHook(() => useResearch());

    await act(async () => {
      result.current.startResearch("test", ["duckduckgo"], "quick");
      await vi.advanceTimersByTimeAsync(200);
    });

    expect(result.current.phase).toBe("complete");

    act(() => {
      result.current.reset();
    });

    expect(result.current.phase).toBe("idle");
    expect(result.current.tokens).toBe("");
    expect(result.current.citations).toEqual([]);
    expect(result.current.sessionId).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("builds initial source statuses on startResearch", async () => {
    globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useResearch());

    await act(async () => {
      result.current.startResearch("test", ["duckduckgo", "reddit"], "standard");
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(result.current.sourceStatuses).toHaveLength(2);
    expect(result.current.sourceStatuses[0].name).toBe("duckduckgo");
    expect(result.current.sourceStatuses[0].status).toBe("waiting");
    expect(result.current.sourceStatuses[1].name).toBe("reddit");
    expect(result.current.sourceStatuses[1].status).toBe("waiting");
  });
});
