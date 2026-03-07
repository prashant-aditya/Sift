import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SourceIndicator } from "@/components/research/SourceIndicator";
import type { SourceStatus } from "@/types/research";

function makeStatus(
  overrides: Partial<SourceStatus> & Pick<SourceStatus, "name" | "status">,
): SourceStatus {
  return {
    displayName: overrides.name.charAt(0).toUpperCase() + overrides.name.slice(1),
    ...overrides,
  };
}

describe("SourceIndicator", () => {
  it("renders nothing when sourceStatuses is empty", () => {
    const { container } = render(<SourceIndicator sourceStatuses={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows waiting state correctly", () => {
    const statuses: SourceStatus[] = [
      makeStatus({ name: "ddg", displayName: "DuckDuckGo", status: "waiting" }),
    ];
    render(<SourceIndicator sourceStatuses={statuses} />);

    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute(
      "aria-label",
      "DuckDuckGo: Waiting",
    );
    expect(screen.getByText("DuckDuckGo")).toBeInTheDocument();
  });

  it("shows searching state correctly", () => {
    const statuses: SourceStatus[] = [
      makeStatus({ name: "reddit", displayName: "Reddit", status: "searching" }),
    ];
    render(<SourceIndicator sourceStatuses={statuses} />);

    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute(
      "aria-label",
      "Reddit: Searching",
    );
  });

  it("shows done state with results count", () => {
    const statuses: SourceStatus[] = [
      makeStatus({
        name: "arxiv",
        displayName: "ArXiv",
        status: "done",
        resultsCount: 5,
        latencyMs: 320,
      }),
    ];
    render(<SourceIndicator sourceStatuses={statuses} />);

    const pill = screen.getByRole("status");
    expect(pill).toHaveAttribute(
      "aria-label",
      "ArXiv: Done: 5 results",
    );
    expect(screen.getByText("ArXiv")).toBeInTheDocument();
  });

  it("shows error state with tooltip trigger", () => {
    const statuses: SourceStatus[] = [
      makeStatus({
        name: "hackernews",
        displayName: "HackerNews",
        status: "error",
        error: "Connection timeout",
      }),
    ];
    render(<SourceIndicator sourceStatuses={statuses} />);

    const trigger = screen.getByLabelText(
      "HackerNews: Error — Connection timeout",
    );
    expect(trigger).toBeInTheDocument();
    expect(screen.getByText("HackerNews")).toBeInTheDocument();
  });

  it("renders multiple sources simultaneously", () => {
    const statuses: SourceStatus[] = [
      makeStatus({ name: "ddg", displayName: "DuckDuckGo", status: "waiting" }),
      makeStatus({ name: "reddit", displayName: "Reddit", status: "searching" }),
      makeStatus({
        name: "arxiv",
        displayName: "ArXiv",
        status: "done",
        resultsCount: 3,
        latencyMs: 200,
      }),
    ];
    render(<SourceIndicator sourceStatuses={statuses} />);

    expect(screen.getByText("DuckDuckGo")).toBeInTheDocument();
    expect(screen.getByText("Reddit")).toBeInTheDocument();
    expect(screen.getByText("ArXiv")).toBeInTheDocument();
  });
});
