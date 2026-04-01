import type { Citation } from "@/types/research";

export function shouldUseMock(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK === "true";
}

const MOCK_CITATIONS: Citation[] = [
  {
    id: 1,
    title: "Understanding Large Language Models",
    url: "https://arxiv.org/abs/example1",
    source_name: "arxiv",
    relevance_score: 0.95,
  },
  {
    id: 2,
    title: "Discussion on LLM architectures",
    url: "https://reddit.com/r/MachineLearning/comments/example",
    source_name: "reddit",
    relevance_score: 0.87,
  },
  {
    id: 3,
    title: "Transformer Architecture Explained",
    url: "https://en.wikipedia.org/wiki/Transformer_(machine_learning_model)",
    source_name: "wikipedia",
    relevance_score: 0.82,
  },
  {
    id: 4,
    title: "HN: New advances in language models",
    url: "https://news.ycombinator.com/item?id=example",
    source_name: "hackernews",
    relevance_score: 0.78,
  },
  {
    id: 5,
    title: "Introduction to Neural Networks",
    url: "https://example.com/neural-networks",
    source_name: "duckduckgo",
    relevance_score: 0.75,
  },
];

const MOCK_ANSWER_TOKENS = [
  "Large",
  " Language",
  " Models",
  " (LLMs)",
  " are",
  " a",
  " class",
  " of",
  " deep",
  " learning",
  " models",
  " trained",
  " on",
  " vast",
  " amounts",
  " of",
  " text",
  " data",
  ".",
  " They",
  " use",
  " transformer",
  " architectures",
  " [1]",
  " to",
  " understand",
  " and",
  " generate",
  " human-like",
  " text",
  ".\n\n",
  "Key",
  " characteristics",
  " include",
  ":\n\n",
  "- ",
  "**Self-attention",
  " mechanisms**",
  " that",
  " allow",
  " the",
  " model",
  " to",
  " weigh",
  " the",
  " importance",
  " of",
  " different",
  " parts",
  " of",
  " the",
  " input",
  " [2]",
  "\n",
  "- ",
  "**Scale**:",
  " modern",
  " LLMs",
  " contain",
  " billions",
  " of",
  " parameters",
  " [3]",
  "\n",
  "- ",
  "**Transfer",
  " learning**:",
  " pre-trained",
  " models",
  " can",
  " be",
  " fine-tuned",
  " for",
  " specific",
  " tasks",
  " [4]",
  "\n\n",
  "The",
  " transformer",
  " architecture",
  ",",
  " introduced",
  " in",
  " the",
  ' "Attention',
  " Is",
  " All",
  " You",
  ' Need"',
  " paper",
  ",",
  " remains",
  " the",
  " foundation",
  " for",
  " most",
  " modern",
  " LLMs",
  " [5]",
  ".",
];

function formatSSE(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function* generateMockEvents(): AsyncGenerator<string> {
  yield formatSSE("status", {
    phase: "decomposing",
    message: "Analyzing your query and breaking it into sub-questions...",
  });
  await sleep(800);

  yield formatSSE("status", {
    phase: "searching",
    message: "Searching across sources...",
    sources_active: 5,
  });
  await sleep(400);

  const sources = [
    { source: "duckduckgo", results_count: 8, latency_ms: 320 },
    { source: "reddit", results_count: 5, latency_ms: 450 },
    { source: "hackernews", results_count: 3, latency_ms: 280 },
    { source: "arxiv", results_count: 4, latency_ms: 620 },
    { source: "wikipedia", results_count: 2, latency_ms: 180 },
  ];

  for (const src of sources) {
    await sleep(150 + Math.random() * 300);
    yield formatSSE("source_complete", src);
  }

  yield formatSSE("status", {
    phase: "processing",
    message: "Processing and ranking results...",
  });
  await sleep(600);

  yield formatSSE("status", {
    phase: "synthesizing",
    message: "Generating comprehensive answer...",
  });
  await sleep(300);

  for (const token of MOCK_ANSWER_TOKENS) {
    await sleep(20 + Math.random() * 40);
    const citationMatch = token.match(/\[(\d+)\]/);
    yield formatSSE("token", {
      content: token,
      ...(citationMatch
        ? { citations: [parseInt(citationMatch[1])] }
        : {}),
    });
  }

  await sleep(200);
  yield formatSSE("complete", {
    session_id: `mock-${Date.now()}`,
    sources_used: 5,
    latency_ms: 4200,
    citations: MOCK_CITATIONS,
  });
}

export function createMockResponse(): Response {
  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        for await (const chunk of generateMockEvents()) {
          controller.enqueue(encoder.encode(chunk));
        }
        controller.close();
      } catch {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
