"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import type { ResearchDepth } from "@/types/research";

const MIN_CHARS = 3;
const MAX_CHARS = 2000;
const CHAR_COUNT_THRESHOLD = 1900;

const SOURCES_V2 = [
  { name: "duckduckgo", className: "src src-ddg", icon: "◉", label: "DuckDuckGo" },
  { name: "reddit", className: "src src-reddit", icon: "◎", label: "Reddit" },
  { name: "hackernews", className: "src src-hn", icon: "▲", label: "HackerNews" },
  { name: "arxiv", className: "src src-arxiv", icon: "∂", label: "ArXiv" },
  { name: "wikipedia", className: "src src-wiki", icon: "⊞", label: "Wikipedia" },
] as const;

const PLACEHOLDERS = [
  "What would you like to research?",
  "How does CRISPR gene editing work?",
  "Latest research on sleep and cognition...",
  "Best Rust frameworks for web servers?",
  "Is GPT-5 better than Claude 4?",
] as const;

const SUGGESTIONS = [
  { ico: "🔬", text: "Latest breakthroughs in quantum computing 2025" },
  { ico: "⚡", text: "Compare transformer vs state space models for LLMs" },
  { ico: "🌱", text: "Best open-source tools replacing proprietary SaaS in 2025" },
] as const;

function titleCaseDepth(depth: ResearchDepth) {
  return depth.charAt(0).toUpperCase() + depth.slice(1);
}

export function V2Landing({
  isStreaming,
  onSubmit,
}: {
  isStreaming: boolean;
  onSubmit: (query: string, sources: string[], depth: ResearchDepth) => void;
}) {
  const [query, setQuery] = useState(() => {
    if (typeof window === "undefined") return "";
    const url = new URL(window.location.href);
    const q = url.searchParams.get("q");
    return q ? q.slice(0, MAX_CHARS) : "";
  });
  const [activeSources, setActiveSources] = useState<Set<string>>(
    () => new Set(SOURCES_V2.map((s) => s.name)),
  );
  const [depth, setDepth] = useState<ResearchDepth>("standard");

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const cardRef = useRef<HTMLDivElement | null>(null);

  const canSubmit =
    query.trim().length >= MIN_CHARS && activeSources.size > 0 && !isStreaming;

  const charCount = query.length;
  const showCharCount = charCount > CHAR_COUNT_THRESHOLD;
  const charCountText = showCharCount ? `${charCount}/${MAX_CHARS}` : "";
  const charCountWarn = charCount > CHAR_COUNT_THRESHOLD;

  useEffect(() => {
    if (!query) return;
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [query]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [query]);

  const toggleSource = useCallback((name: string) => {
    setActiveSources((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        if (next.size <= 1) return next;
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmed = query.trim();
    if (trimmed.length < MIN_CHARS) return;
    onSubmit(trimmed, Array.from(activeSources), depth);
  }, [query, activeSources, depth, onSubmit]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (canSubmit) handleSubmit();
      }
    },
    [canSubmit, handleSubmit],
  );

  const fillSuggestion = useCallback((text: string) => {
    setQuery(text);
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, []);

  // Animated placeholder (exact behavior as template: only when textarea not focused)
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;

    let pi = 0;
    let ci = 0;
    let typing = true;
    let delay = 0;
    let timer: number | undefined;

    const tick = () => {
      if (!ta) return;
      if (document.activeElement === ta) {
        timer = window.setTimeout(tick, 500);
        return;
      }
      if (delay > 0) {
        delay -= 1;
        timer = window.setTimeout(tick, 80);
        return;
      }
      const target = PLACEHOLDERS[pi];
      if (typing) {
        if (ci < target.length) {
          ci += 1;
          ta.setAttribute("placeholder", `${target.slice(0, ci)}|`);
          timer = window.setTimeout(tick, 45 + Math.random() * 30);
        } else {
          delay = 38;
          typing = false;
          timer = window.setTimeout(tick, 80);
        }
      } else {
        if (ci > 0) {
          ci -= 1;
          ta.setAttribute("placeholder", `${target.slice(0, ci)}|`);
          timer = window.setTimeout(tick, 22);
        } else {
          pi = (pi + 1) % PLACEHOLDERS.length;
          typing = true;
          timer = window.setTimeout(tick, 300);
        }
      }
    };

    timer = window.setTimeout(tick, 1200);
    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  // Mouse parallax on search card
  useEffect(() => {
    const card = cardRef.current;
    if (!card) return;

    const onMove = (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = (e.clientX - cx) / window.innerWidth;
      const dy = (e.clientY - cy) / window.innerHeight;
      card.style.transform = `perspective(1000px) rotateY(${dx * 4}deg) rotateX(${-dy * 2}deg)`;
    };
    const onLeave = () => {
      card.style.transform = "perspective(1000px) rotateY(0deg) rotateX(0deg)";
    };

    document.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseleave", onLeave);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  const depthOptions = useMemo(
    () =>
      (["quick", "standard", "deep"] as const).map((d) => ({
        value: d,
        label: titleCaseDepth(d),
      })),
    [],
  );

  return (
    <>
      <nav className="main-nav">
        <a href="#" className="nav-brand">
          Sift
          <span className="brand-badge">
            <span className="brand-dot" />
            Beta
          </span>
        </a>
        <div className="nav-links">
          <a href="#">How it works</a>
          <a href="#">Sources</a>
          <a href="#">API</a>
          <a href="#">Pricing</a>
        </div>
        <div className="nav-right">
          <button className="nav-btn nav-btn-ghost" type="button">
            Sign in
          </button>
          <button className="nav-btn nav-btn-filled" type="button">
            Get started →
          </button>
        </div>
      </nav>

      <div className="page">
        <section className="hero-section">
          <div className="hero-inner">
            <div className="hero-tag">
              <span className="tag-pip" />
              AI-Powered Deep Research Engine
            </div>

            <h1 className="hero-title">
              <span className="word-main">Research,</span>
              <span className="word-italic">synthesised.</span>
            </h1>

            <p className="hero-sub" id="heroSub">
              Ask anything. Sift searches across the web, papers, and communities
              — then synthesises a cited answer in seconds.
            </p>

            <div className="stats">
              <div className="stat">
                <span className="stat-num" id="s1">
                  5
                </span>
                <span className="stat-label">Sources</span>
              </div>
              <div className="stat">
                <span className="stat-num" id="s2">
                  12M+
                </span>
                <span className="stat-label">Papers indexed</span>
              </div>
              <div className="stat">
                <span className="stat-num" id="s3">
                  ~8s
                </span>
                <span className="stat-label">Avg. response</span>
              </div>
              <div className="stat">
                <span className="stat-num" id="s4">
                  100%
                </span>
                <span className="stat-label">Cited answers</span>
              </div>
            </div>

            <div className="search-card" ref={cardRef}>
              <div className="search-glow" />
              <div className="search-box">
                <div className="search-top">
                  <div className="search-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">
                      <circle cx="11" cy="11" r="8" />
                      <path d="m21 21-4.35-4.35" />
                    </svg>
                  </div>
                  <textarea
                    ref={textareaRef}
                    className="search-ta"
                    rows={1}
                    placeholder="What would you like to research?"
                    value={query}
                    onChange={(e) =>
                      setQuery(e.target.value.slice(0, MAX_CHARS))
                    }
                    onKeyDown={handleKeyDown}
                    disabled={isStreaming}
                    aria-label="Research query"
                  />
                </div>

                <div className="search-controls" role="group" aria-label="Sources">
                  {SOURCES_V2.map((s) => {
                    const on = activeSources.has(s.name);
                    return (
                      <button
                        key={s.name}
                        type="button"
                        className={`${s.className}${on ? "" : " off"}`}
                        onClick={() => toggleSource(s.name)}
                        role="switch"
                        aria-checked={on}
                        disabled={isStreaming}
                      >
                        <span className="src-ico" aria-hidden="true">
                          {s.icon}
                        </span>
                        {s.label}
                      </button>
                    );
                  })}

                  <span className="search-spacer" />

                  <div className="depth-group">
                    <span className="depth-lbl">Depth</span>
                    <div className="depth-seg" role="tablist" aria-label="Depth">
                      {depthOptions.map((d) => (
                        <button
                          key={d.value}
                          type="button"
                          className={`depth-opt${
                            depth === d.value ? " active" : ""
                          }`}
                          onClick={() => setDepth(d.value)}
                          aria-pressed={depth === d.value}
                          disabled={isStreaming}
                        >
                          {d.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="search-submit-row">
                  <span
                    className={`char-count${charCountWarn ? " warn" : ""}`}
                    aria-live="polite"
                  >
                    {charCountText}
                  </span>
                  <button
                    className="submit-btn"
                    type="button"
                    onClick={handleSubmit}
                    disabled={!canSubmit}
                  >
                    Research
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <div className="sugg-section">
              <div className="sugg-head">
                <span className="sugg-head-text">Try these</span>
                <div className="sugg-line" />
              </div>
              <div className="sugg-grid">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s.text}
                    type="button"
                    className="sugg-card"
                    onClick={() => fillSuggestion(s.text)}
                    disabled={isStreaming}
                  >
                    <span className="sugg-card-ico" aria-hidden="true">
                      {s.ico}
                    </span>
                    <span className="sugg-card-text">{s.text}</span>
                    <span className="sugg-arrow" aria-hidden="true">
                      →
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="feat-row">
              <div className="feat-chip">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                Inline citations
              </div>
              <div className="feat-chip">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
                Streaming answers
              </div>
              <div className="feat-chip">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                </svg>
                Multi-source search
              </div>
              <div className="feat-chip">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
                AI synthesis
              </div>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}

