# Sift Frontend — Current UI Design (as-built)

This document describes the **current** frontend UI/UX implementation so the design team can improve it. It is based on the existing Next.js app and Tailwind/Shadcn component usage in `frontend/src`.

## Product snapshot

- **Product name**: Sift — AI Deep Research Engine
- **Primary workflow**: user enters a research query → selects sources + “depth” → sees streaming answer (markdown) with inline citations → explores citations in a side panel (desktop) or stacked list (mobile).
- **Current route implemented**: `/` (home). Other routes exist in `frontend/src/lib/constants.ts` but are not currently implemented as pages.

## Tech/design system used

- **Framework**: Next.js App Router (`frontend/src/app`)
- **Styling**: Tailwind CSS + Shadcn UI primitives (Radix-style patterns)
- **Animation**: `tw-animate-css` + a few custom keyframes in `globals.css`
- **Icons**: `lucide-react`
- **Markdown rendering**: `react-markdown` + `remark-gfm`
- **Theme**: `next-themes` (`system` default) with `light` + `dark` classes

## Information architecture & screens

### Home (`/`) — two states

#### 1) Idle / landing state (before research starts)

- **Layout**: centered column inside full height viewport.
- **Content**:
  - App wordmark: “Sift”
  - Tagline: “AI-powered deep research across multiple sources”
  - Feature chips (inline icon + label):
    - Multi-source search
    - AI synthesis
    - Cited answers
- **Top-right utility**: theme toggle icon button.

#### 2) Active research state (after submission)

- **Layout shift**: container widens and moves up (top padding) while keeping search bar visible.
- **Sections**:
  - Search bar (still available; disabled while streaming)
  - Research view region (appears with fade/slide-in)
    - Phase indicator (e.g., “Searching sources…”)
    - Per-source status pills (waiting/searching/done/error)
    - Main streaming results (markdown)
    - Citations panel (if citations exist)

## Layout & spacing (current)

- **Page container**: `main` is centered with `min-h-screen` and `px-4`.
- **Max widths**:
  - Idle: `max-w-3xl` container; search form `max-w-2xl`
  - Active: page container up to `max-w-6xl`, with content area `max-w-3xl`
- **Desktop results layout**: when citations exist, grid becomes:
  - main content: `1fr`
  - citations panel: fixed `320px`
- **Mobile results layout**: citations list stacks below the answer (no sticky aside).

## Typography (current)

- **Sans**: Inter (`--font-sans`)
- **Mono**: Geist Mono (`--font-geist-mono`)
- **Landing heading**: `text-5xl` (sm `text-6xl`), bold, tight tracking.
- **Body**: Tailwind defaults; markdown content uses `prose` (`prose-neutral` + `dark:prose-invert`).
- **Markdown headings**:
  - `h2`: `text-xl font-semibold`
  - `h3`: `text-lg font-semibold`
- **Inline code**: subtle pill background in muted color, mono.
- **Links**: underlined with underline offset, open in new tab with `rel="noopener noreferrer"`.

## Color system & tokens

Global color tokens are defined as **OKLCH** CSS variables in `frontend/src/app/globals.css` for both `:root` and `.dark`.

### Semantic tokens (examples)

- `--background`, `--foreground`
- `--muted`, `--muted-foreground`
- `--primary`, `--primary-foreground`
- `--accent`, `--accent-foreground`
- `--border`, `--input`, `--ring`
- `--destructive`

### Radius scale

- Base `--radius: 0.625rem` with derived sizes `--radius-sm` through `--radius-4xl`.

### Source color accents

Each research source has a hard-coded brand-ish color + utility classes in `frontend/src/lib/constants.ts`:

- DuckDuckGo: orange (`#f97316`)
- Reddit: red (`#ef4444`)
- HackerNews: amber (`#d97706`)
- ArXiv: blue (`#2563eb`)
- Wikipedia: slate (`#475569`) (with dark-mode overrides for some slate utility classes in `globals.css`)

These colors are used for:
- active source toggle background
- citation badges/cards source markers
- citation list section icons

## Components & UI patterns (current)

### Search bar (query input)

- **Control**: auto-growing `<textarea>` (1 row up to ~200px height).
- **Submit behavior**:
  - `Enter` submits
  - `Shift+Enter` creates newline
  - Submit button is an icon button inside the field (bottom-right).
- **Validation**:
  - min 3 characters
  - max 2000 characters (shows counter after 1900)
  - requires at least one source selected
  - disabled while streaming
- **Visual**: rounded “pill-ish” container (`rounded-2xl`), subtle border, focus ring.

### Source selection

- **UI**: row of rounded pills (one per source), with icon + label.
- **Behavior**:
  - toggleable; last active source cannot be turned off
  - uses `role="switch"` + `aria-checked`
  - adds custom keydown handler for Space/Enter
- **Visual**:
  - active: solid background using source color + white text
  - inactive: border + muted text, hover increases contrast

### Research depth selection

- **UI**: compact select (“Quick / Standard / Deep”)
- **Placement**: below sources row.

### Phase indicator

- **UI**: inline icon + phase label (“Decomposing…”, “Searching…”, “Processing…”, “Synthesizing…”).
- **Motion**: fade-in on phase changes; icon pulses.

### Source indicator (per-source statuses)

- **UI**: status pills (waiting/searching/done/error) with different colors.
- **Details**: on done, shows results count + latency; on error, tooltip shows error string.
- **A11y**: each pill is `role="status"` with an `aria-label` including status detail.

### Streaming answer (markdown)

- **Container**: scrollable region `max-h-[60vh]` with `pr-2`.
- **Auto-scroll**:
  - follows output while user is at the bottom
  - if user scrolls up during streaming, shows “Scroll to bottom” button pinned near bottom.
- **Typing cursor**: blinking caret-like bar at the end while streaming (disabled for reduced motion).
- **Markdown theme**: `prose` styles + custom renderers for tables, code blocks, lists, blockquotes, etc.

### Inline citations

- **Parsing rule**: tokens containing `[number]` render as clickable citation badges (superscript-like).
- **Badge UI**:
  - small round badge (5×5) with primary tinted background
  - hover darkens
  - includes tooltip with title + source + URL when citation is known
- **Interaction**: clicking a badge highlights/scrolls to the corresponding citation card in the citations panel.

### Citations panel

- **Desktop**:
  - right-side `aside`, sticky heading and scrollable list (`ScrollArea`)
  - grouped by source, sorted by group size; citations within group sorted by relevance score
- **Mobile**:
  - stacked list below answer (no sticky)
  - a bottom sheet variant exists (`CitationSheet`) but is not currently wired in the main view

### Citation card

- **Visual**:
  - rounded card with border + subtle hover background
  - left badge shows citation id, colored by source
  - shows title (2-line clamp), source, URL (truncated), relevance progress bar
- **Highlight state**:
  - when a citation is clicked from the answer, the card animates (“citation-highlight”) and gets ring/shadow emphasis, then clears after ~4.5s
- **A11y**:
  - card is an anchor opening in new tab; has descriptive `aria-label`
  - relevance bar uses `role="progressbar"` with aria values

### Error and empty states

- **Error state**:
  - centered, icon + title + helper text
  - optional “Try again”
  - expandable error details via collapsible section
- **No results**:
  - centered, icon + title + helper text
  - optional “Try again”
- **Loading**:
  - skeleton blocks for phase + pills + content

## Motion & reduced motion handling

- Many components include `motion-reduce:*` fallbacks.
- Global `prefers-reduced-motion: reduce` rule forces minimal animation/transition durations.
- Custom animations:
  - `citation-highlight`: border + soft ring pulse
  - `typing-blink`: caret blink

## Accessibility (current highlights)

- **Good**:
  - semantic regions (`main`, `article`, `aside`, `nav`, `section`)
  - proper `aria-label` usage for controls and dynamic regions
  - touch targets: `.touch-target` and `min-h-[44px]` on pills/buttons
  - external links use `rel="noopener noreferrer"`
  - reduced motion support
- **Watch-outs**:
  - citation badges inside markdown use a custom trigger; ensure keyboard focus/activation is consistent across browsers (currently uses focus-visible styles, but tooltip trigger is not a `<button>` in the “known citation” path).
  - `TooltipProvider` is nested inside `CitationBadge` instances (many providers). Consider a single shared provider for performance/consistency.

## Visual tone (current)

- **Overall**: minimalist, neutral palette (Shadcn “neutral”) with brand color accents per source.
- **Shape language**: large radii (rounded-2xl textarea, rounded-full pills) for a friendly/modern look.
- **Density**: moderate; compact controls with clear separation (`space-y-4`, `gap-2`).

## Known UI constraints (from implementation)

- The answer stream is constrained to `max-h-[60vh]` with internal scrolling (instead of full page scroll).
- Citations appear only when the backend returns citations; the layout changes when citations exist (grid with sidebar).
- The source colors are currently hard-coded; they do not come from design tokens.

## Improvement opportunities for design team (actionable)

### 1) Brand & hierarchy

- **Define a brand system**: logo/wordmark usage, primary accent color (separate from “source colors”), and consistent emphasis styles.
- **Clarify the landing experience**: add a short “how it works” line, examples, or suggested queries to reduce blank-state friction.
- **Refine layout shift**: the transition from centered landing to active state can feel jumpy; consider a more intentional “sticky header” search layout.

### 2) Search input & controls

- **Improve depth selection**: depth is currently a small select; consider segmented control with descriptions (speed vs thoroughness).
- **Source selection clarity**:
  - add tooltips/“about” descriptions for each source (what it’s good for)
  - show selection count and/or “Select all / Reset”
- **Loading/disabled affordance**: while streaming, textarea disables; consider allowing edits for the next query while current stream runs (with “Stop” / “New search” controls).

### 3) Reading experience for answers

- **Typography polish**: define a typographic scale for markdown content (line length, spacing, heading separation).
- **Inline citation UX**:
  - make citation badges feel more like footnote links (better hover/focus, larger hit area)
  - consider a small side peek panel on hover for citation details
- **Scroll model**: evaluate whether `max-h-[60vh]` internal scroll is ideal; full-page scroll may feel more natural.

### 4) Citations panel UX

- **Desktop panel**: consider collapsible/resizable sidebar, filtering/sorting citations, and pinned “Top sources”.
- **Mobile**: consider using the existing bottom sheet (`CitationSheet`) for better ergonomics than a long stacked list.
- **Relevance clarity**: add explanations for relevance score and what it means; or normalize to a tiered label (High/Med/Low).

### 5) Color & theming

- **Unify source colors with theme tokens**: source colors could be expressed as CSS variables and adapted for dark mode for contrast.
- **Contrast audit**: confirm all source pill colors meet WCAG on both light/dark backgrounds.
- **Reduce ad-hoc overrides**: there are explicit `.dark .text-slate-600` / `.bg-slate-600` overrides; prefer token-based approach.

### 6) States & feedback

- Add “Stop generating” (cancel stream) and “Copy answer” / “Export” actions.
- Show source progress more prominently (e.g., progress bar for overall research).
- Better empty/error recovery: suggested adjustments (change sources/depth) embedded in the state.

## References (implementation pointers)

- Home page + layout states: `frontend/src/app/page.tsx`
- Global styles/tokens: `frontend/src/app/globals.css`
- Search + toggles: `frontend/src/components/research/SearchBar.tsx`, `SourceToggle.tsx`
- Research view and states: `frontend/src/components/research/ResearchView.tsx`
- Markdown stream + inline citations: `frontend/src/components/research/ResearchStream.tsx`
- Citations panel + cards: `frontend/src/components/research/CitationSidebar.tsx`, `CitationCard.tsx`
- Theme toggle: `frontend/src/components/shared/ThemeToggle.tsx`
- Source colors/config: `frontend/src/lib/constants.ts`

## V2 landing (from `sift-v2.html`) — hardcoded values to be aware of

The `/` landing UI was updated to match the provided `sift-v2.html` template. The following values are currently **hardcoded** (copied from the template) and are likely candidates to move into a design token system or config later.

### Visual tokens (CSS variables)

Defined in `frontend/src/app/sift-v2.css` under `.sift-v2`:

- **Backgrounds**: `--bg #07070e`, `--bg1 #0c0c18`, `--bg2 #101022`
- **Glass**: `--glass rgba(255,255,255,0.032)`, `--glass2 rgba(255,255,255,0.06)`
- **Borders**: `--border rgba(255,255,255,0.07)`, `--border2 rgba(255,255,255,0.14)`
- **Text**: `--text #f2ede4`, `--text2 rgba(242,237,228,0.5)`, `--text3 rgba(242,237,228,0.22)`
- **Accents**: `--indigo #8b7cf8`, `--indigo2 #6c5ce7`, `--rose #f472b6`, `--amber #f59e0b`
- **Radius**: `--r 14px`

### Fonts

Applied globally via `frontend/src/app/layout.tsx`:

- **Sans**: Syne (`--font-sans`)
- **Mono**: Syne Mono (`--font-sift-mono`)
- **Serif**: Cormorant Garamond (`--font-sift-serif`)

### Copy (strings)

Hardcoded in `frontend/src/components/landing/V2Landing.tsx`:

- **Nav links**: “How it works”, “Sources”, “API”, “Pricing”
- **Nav CTAs**: “Sign in”, “Get started →”
- **Hero tag**: “AI-Powered Deep Research Engine”
- **Hero title**: “Research,” + “synthesised.”
- **Hero subtitle**: “Ask anything. Sift searches across the web, papers, and communities — then synthesises a cited answer in seconds.”

### Stats (numbers shown on landing)

Hardcoded:

- **Sources**: `5`
- **Papers indexed**: `12M+`
- **Avg. response**: `~8s`
- **Cited answers**: `100%`

### Suggestions (“Try these” cards)

Hardcoded:

- “Latest breakthroughs in quantum computing 2025”
- “Compare transformer vs state space models for LLMs”
- “Best open-source tools replacing proprietary SaaS in 2025”

### Placeholder animation phrases

Hardcoded list (used when textarea is not focused):

- “What would you like to research?”
- “How does CRISPR gene editing work?”
- “Latest research on sleep and cognition...”
- “Best Rust frameworks for web servers?”
- “Is GPT-5 better than Claude 4?”

### Marquee topics (bottom ticker)

Hardcoded list:

- Quantum Computing, Machine Learning, Climate Science, Genomics, Astrophysics, Materials Science, Neuroscience, Cryptography, Protein Folding, Dark Matter, CRISPR, Large Language Models, Fusion Energy, Nanotechnology

### UI constraints (dimensions / thresholds)

Hardcoded:

- **Nav height**: `60px`
- **Marquee height**: `36px`
- **Hero spotlight**: `900×600px` gradient
- **Search card max width**: `660px`
- **Textarea max height**: `160px`
- **Query length limits**: min `3`, max `2000`, warning threshold `1900`

### Source toggle visuals

Hardcoded per-source styling (rgba backgrounds/borders + text colors) and symbols:

- DuckDuckGo `◉`, Reddit `◎`, HackerNews `▲`, ArXiv `∂`, Wikipedia `⊞`

### “Active research results” container styling

Hardcoded inline styles in `frontend/src/app/page.tsx` for the results block (z-index, padding, maxWidth 1100, bottom padding to clear marquee).

