import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { CitationCard } from "@/components/research/CitationCard";
import type { Citation } from "@/types/research";

const mockCitation: Citation = {
  id: 1,
  title: "Understanding Large Language Models",
  url: "https://arxiv.org/abs/example1",
  source_name: "arxiv",
  relevance_score: 0.95,
};

describe("CitationCard", () => {
  it("renders the citation title", () => {
    render(<CitationCard citation={mockCitation} />);
    expect(
      screen.getByText("Understanding Large Language Models"),
    ).toBeInTheDocument();
  });

  it("renders the source display name", () => {
    render(<CitationCard citation={mockCitation} />);
    expect(screen.getByText("ArXiv")).toBeInTheDocument();
  });

  it("renders the truncated URL", () => {
    render(<CitationCard citation={mockCitation} />);
    expect(screen.getByText(/arxiv\.org/)).toBeInTheDocument();
  });

  it("opens link in a new tab with noopener noreferrer", () => {
    render(<CitationCard citation={mockCitation} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows the correct relevance percentage", () => {
    render(<CitationCard citation={mockCitation} />);
    expect(screen.getByText("95%")).toBeInTheDocument();
  });

  it("renders the relevance progressbar", () => {
    render(<CitationCard citation={mockCitation} />);
    const progressbar = screen.getByRole("progressbar");
    expect(progressbar).toHaveAttribute("aria-valuenow", "95");
    expect(progressbar).toHaveAttribute("aria-valuemin", "0");
    expect(progressbar).toHaveAttribute("aria-valuemax", "100");
  });

  it("applies highlight class when isHighlighted is true", () => {
    render(<CitationCard citation={mockCitation} isHighlighted />);
    const link = screen.getByRole("link");
    expect(link.className).toContain("animate-citation-highlight");
  });

  it("does not apply highlight class when isHighlighted is false", () => {
    render(<CitationCard citation={mockCitation} isHighlighted={false} />);
    const link = screen.getByRole("link");
    expect(link.className).not.toContain("animate-citation-highlight");
  });

  it("renders the citation id badge", () => {
    render(<CitationCard citation={mockCitation} />);
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("sets accessible label with citation id and title", () => {
    render(<CitationCard citation={mockCitation} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute(
      "aria-label",
      "Source 1: Understanding Large Language Models",
    );
  });
});
