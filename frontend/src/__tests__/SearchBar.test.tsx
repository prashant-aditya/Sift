import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { SearchBar } from "@/components/research/SearchBar";

vi.mock("@/components/ui/select", () => ({
  Select: ({
    children,
    onValueChange,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    // The real `Select` consumes `onValueChange`; our mock shouldn't forward it to the DOM.
    // We still "use" it to avoid unused-var lint warnings.
    (void onValueChange,
    (
      <div data-testid="select" {...props}>
        {children}
      </div>
    ))
  ),
  SelectContent: ({ children }: React.PropsWithChildren) => <div>{children}</div>,
  SelectItem: ({ children, value }: React.PropsWithChildren<{ value: string }>) => <option value={value}>{children}</option>,
  SelectTrigger: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => <button {...props}>{children}</button>,
  SelectValue: () => <span>Standard</span>,
}));

describe("SearchBar", () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    isStreaming: false,
  };

  function renderSearchBar(overrides = {}) {
    return render(<SearchBar {...defaultProps} {...overrides} />);
  }

  it("renders the textarea and submit button", () => {
    renderSearchBar();
    expect(screen.getByLabelText("Research query")).toBeInTheDocument();
    expect(screen.getByLabelText("Submit research query")).toBeInTheDocument();
  });

  it("emits correct query and sources on submit", async () => {
    const onSubmit = vi.fn();
    renderSearchBar({ onSubmit });

    const textarea = screen.getByLabelText("Research query");
    await userEvent.type(textarea, "What is Kafka?");
    fireEvent.submit(textarea.closest("form")!);

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const [query, sources, depth] = onSubmit.mock.calls[0];
    expect(query).toBe("What is Kafka?");
    expect(sources).toBeInstanceOf(Array);
    expect(sources.length).toBeGreaterThan(0);
    expect(depth).toBe("standard");
  });

  it("rejects queries shorter than 3 characters", async () => {
    const onSubmit = vi.fn();
    renderSearchBar({ onSubmit });

    const textarea = screen.getByLabelText("Research query");
    await userEvent.type(textarea, "ab");
    fireEvent.submit(textarea.closest("form")!);

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables textarea and submit button while streaming", () => {
    renderSearchBar({ isStreaming: true });

    const textarea = screen.getByLabelText("Research query");
    const button = screen.getByLabelText("Submit research query");

    expect(textarea).toBeDisabled();
    expect(button).toBeDisabled();
  });

  it("renders all source toggles", () => {
    renderSearchBar();
    expect(screen.getByLabelText(/Toggle DuckDuckGo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Toggle Reddit/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Toggle HackerNews/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Toggle ArXiv/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Toggle Wikipedia/i)).toBeInTheDocument();
  });

  it("submits on Enter key (without Shift)", async () => {
    const onSubmit = vi.fn();
    renderSearchBar({ onSubmit });

    const textarea = screen.getByLabelText("Research query");
    await userEvent.type(textarea, "Large Language Models");
    await userEvent.type(textarea, "{Enter}");

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
