import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SourceToggle } from "@/components/research/SourceToggle";
import { SOURCES } from "@/lib/constants";

describe("SourceToggle", () => {
  const duckDuckGo = SOURCES[0]; // duckduckgo

  it("renders source display name and icon", () => {
    render(
      <SourceToggle source={duckDuckGo} active={false} onToggle={vi.fn()} />,
    );
    expect(screen.getByText("DuckDuckGo")).toBeInTheDocument();
  });

  it("calls onToggle with the source name when clicked", () => {
    const onToggle = vi.fn();
    render(
      <SourceToggle source={duckDuckGo} active={false} onToggle={onToggle} />,
    );

    fireEvent.click(screen.getByRole("switch"));
    expect(onToggle).toHaveBeenCalledWith("duckduckgo");
  });

  it("has aria-checked=true when active", () => {
    render(
      <SourceToggle source={duckDuckGo} active={true} onToggle={vi.fn()} />,
    );
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
  });

  it("has aria-checked=false when inactive", () => {
    render(
      <SourceToggle source={duckDuckGo} active={false} onToggle={vi.fn()} />,
    );
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "false");
  });

  it("applies the source color as background when active", () => {
    render(
      <SourceToggle source={duckDuckGo} active={true} onToggle={vi.fn()} />,
    );
    const button = screen.getByRole("switch");
    expect(button.style.backgroundColor).toBeTruthy();
  });

  it("does not apply background color when inactive", () => {
    render(
      <SourceToggle source={duckDuckGo} active={false} onToggle={vi.fn()} />,
    );
    const button = screen.getByRole("switch");
    expect(button.style.backgroundColor).toBe("");
  });

  it("is disabled when disabled prop is true", () => {
    render(
      <SourceToggle
        source={duckDuckGo}
        active={false}
        onToggle={vi.fn()}
        disabled
      />,
    );
    expect(screen.getByRole("switch")).toBeDisabled();
  });

  it("responds to keyboard Enter and Space", () => {
    const onToggle = vi.fn();
    render(
      <SourceToggle source={duckDuckGo} active={false} onToggle={onToggle} />,
    );

    const button = screen.getByRole("switch");
    fireEvent.keyDown(button, { key: "Enter" });
    fireEvent.keyDown(button, { key: " " });

    expect(onToggle).toHaveBeenCalledTimes(2);
  });
});
