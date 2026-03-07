# Sift — Frontend Engineering Specification

> **Audience:** Frontend Engineering Team
> **Stack:** Next.js 14 (App Router) · Tailwind CSS · shadcn/ui · Lucide Icons · v0.dev (scaffolding)
> **Hosting:** Vercel (free tier)
> **Backend API:** FastAPI (Server-Sent Events for streaming)

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Tech Stack & Tooling](#2-tech-stack--tooling)
3. [Project Structure](#3-project-structure)
4. [Design System & UI Principles](#4-design-system--ui-principles)
5. [Pages & Routing](#5-pages--routing)
6. [Component Specifications](#6-component-specifications)
7. [Custom Hooks](#7-custom-hooks)
8. [API Contracts & SSE Protocol](#8-api-contracts--sse-protocol)
9. [State Management](#9-state-management)
10. [Authentication Flow](#10-authentication-flow)
11. [Phased Implementation Plan](#11-phased-implementation-plan)
12. [Docker & Deployment](#12-docker--deployment)
13. [Testing Strategy](#13-testing-strategy)
14. [Performance Requirements](#14-performance-requirements)
15. [Accessibility & Responsiveness](#15-accessibility--responsiveness)

---

## 1. Product Overview

Sift is an AI deep research engine. Users type a research question, and Sift:

1. Decomposes the query into sub-queries
2. Searches 5+ sources in parallel (DuckDuckGo, Reddit, HackerNews, ArXiv, Wikipedia)
3. Streams a synthesized, cited answer in real-time via SSE
4. Persists the research session into a knowledge graph

The frontend must feel like **Perplexity AI** — clean, fast, streaming-first — but with added features: session history, knowledge graph visualization, source control, and agent reasoning transparency.

### Core User Flows

```
Flow 1: First-time Research
  Landing → Type query → Toggle sources → Submit
  → See source status indicators update live
  → Stream answer with inline citations [1][2]
  → View citations sidebar
  → Ask follow-up question

Flow 2: Returning User
  Open app → See session sidebar (past research)
  → Click old session → View full conversation
  → Ask follow-up or start new research

Flow 3: Knowledge Exploration
  Navigate to /knowledge → Interactive graph
  → Click entity node → See details + sessions
  → "Research more" → Triggers new query

Flow 4: Dashboard
  Navigate to /dashboard → Research activity
  → Source performance → Cache stats → Top entities
```

---

## 2. Tech Stack & Tooling

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | Next.js 14 (App Router) | SSR, file-based routing, RSC |
| **Styling** | Tailwind CSS 3.4+ | Utility-first CSS |
| **Component Library** | shadcn/ui | Accessible, composable primitives (Dialog, Sheet, Tabs, Badge, Button, etc.) |
| **Icons** | Lucide Icons (`lucide-react`) | Consistent icon set |
| **Scaffolding** | v0.dev | Rapid UI prototyping, generate initial component shells |
| **Markdown Rendering** | `react-markdown` + `remark-gfm` | Render streamed markdown |
| **SSE Parsing** | `eventsource-parser` | Parse Server-Sent Events from fetch streams |
| **Graph Visualization** | D3.js (`d3-force`) | Force-directed knowledge graph |
| **Charts** | Recharts | Dashboard charts (line, bar, gauge) |
| **Auth** | `@supabase/supabase-js` + `@supabase/auth-helpers-nextjs` | Supabase Auth integration |
| **State** | React Context + `useReducer` (or Zustand if needed) | Client state management |
| **Forms** | React Hook Form + Zod | Form validation |
| **Date** | `date-fns` | Date formatting |
| **HTTP Client** | Native `fetch` (SSE) + lightweight wrapper | API communication |

### Initial Setup

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --eslint
cd frontend
npx shadcn@latest init     # Select "New York" style, Zinc color, CSS variables = yes
npx shadcn@latest add button input badge card dialog sheet tabs scroll-area separator tooltip avatar dropdown-menu checkbox slider select command popover toggle
npm install lucide-react react-markdown remark-gfm eventsource-parser d3 @types/d3 recharts @supabase/supabase-js @supabase/auth-helpers-nextjs date-fns zod react-hook-form @hookform/resolvers
```

---

## 3. Project Structure

```
frontend/
├── src/
│   ├── app/                             # Next.js App Router
│   │   ├── layout.tsx                   # Root layout (theme, sidebar shell, providers)
│   │   ├── page.tsx                     # Home / research page (search + stream)
│   │   ├── knowledge/
│   │   │   └── page.tsx                 # Knowledge graph visualization
│   │   ├── dashboard/
│   │   │   └── page.tsx                 # Analytics dashboard
│   │   ├── session/
│   │   │   └── [id]/
│   │   │       └── page.tsx             # Session detail (conversation history)
│   │   ├── settings/
│   │   │   ├── page.tsx                 # General settings
│   │   │   └── schedules/
│   │   │       └── page.tsx             # Scheduled research management
│   │   ├── auth/
│   │   │   ├── login/page.tsx           # Login page
│   │   │   ├── signup/page.tsx          # Signup page
│   │   │   └── callback/route.ts        # Supabase auth callback
│   │   └── globals.css                  # Tailwind + shadcn/ui theme overrides
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx             # Main layout wrapper (sidebar + content)
│   │   │   ├── Header.tsx               # Top bar (logo, notifications, user menu)
│   │   │   ├── SessionSidebar.tsx       # Left sidebar: session history list
│   │   │   └── MobileNav.tsx            # Mobile bottom nav / hamburger
│   │   │
│   │   ├── research/
│   │   │   ├── SearchBar.tsx            # Main query input + source toggles
│   │   │   ├── SourceToggle.tsx         # Individual source toggle pill
│   │   │   ├── SourceIndicator.tsx      # Real-time source status strip
│   │   │   ├── ResearchStream.tsx       # Streaming markdown answer
│   │   │   ├── CitationCard.tsx         # Single citation card
│   │   │   ├── CitationSidebar.tsx      # Citations panel (list of CitationCards)
│   │   │   ├── FollowUpInput.tsx        # Follow-up question input
│   │   │   ├── PhaseIndicator.tsx       # "Decomposing..." / "Searching..." / "Synthesizing..."
│   │   │   └── ResearchView.tsx         # Composed view: phases + stream + citations
│   │   │
│   │   ├── knowledge/
│   │   │   ├── KnowledgeGraph.tsx       # D3.js force-directed graph
│   │   │   ├── EntityDetail.tsx         # Entity detail panel (on node click)
│   │   │   ├── GraphControls.tsx        # Filter controls (type, session, date)
│   │   │   └── GraphLegend.tsx          # Color legend for entity types
│   │   │
│   │   ├── agent/
│   │   │   ├── AgentThinking.tsx        # Real-time agent reasoning steps
│   │   │   └── AgentTrace.tsx           # Post-research agent trace timeline
│   │   │
│   │   ├── dashboard/
│   │   │   ├── ActivityChart.tsx         # Research activity over time (line chart)
│   │   │   ├── SourcePerformance.tsx     # Source latency + success rate table
│   │   │   ├── CacheStats.tsx            # Cache hit rate gauge
│   │   │   ├── TopEntities.tsx           # Top entities bar chart
│   │   │   └── KnowledgeStats.tsx        # Nodes/edges count cards
│   │   │
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx             # Email/password + GitHub OAuth
│   │   │   ├── SignupForm.tsx
│   │   │   └── UserMenu.tsx              # Avatar dropdown (profile, settings, logout)
│   │   │
│   │   ├── shared/
│   │   │   ├── NotificationBell.tsx       # Header notification icon + dropdown
│   │   │   ├── ShareDialog.tsx            # Session sharing modal
│   │   │   ├── ExportMenu.tsx             # Export dropdown (Markdown, JSON, Obsidian)
│   │   │   └── EmptyState.tsx             # Reusable empty state illustrations
│   │   │
│   │   └── ui/                            # shadcn/ui generated components (auto)
│   │       ├── button.tsx
│   │       ├── badge.tsx
│   │       ├── card.tsx
│   │       └── ... (all shadcn primitives)
│   │
│   ├── hooks/
│   │   ├── useSSE.ts                     # SSE connection + event parsing
│   │   ├── useResearch.ts                # Research state machine (idle → searching → streaming → done)
│   │   ├── useSession.ts                 # Session CRUD operations
│   │   ├── useKnowledge.ts               # Knowledge graph data fetching
│   │   ├── useAuth.ts                    # Supabase auth state
│   │   └── useNotifications.ts           # Notification polling/state
│   │
│   ├── lib/
│   │   ├── api.ts                        # API client (base URL, headers, fetch wrappers)
│   │   ├── supabase.ts                   # Supabase client init (browser + server)
│   │   ├── constants.ts                  # Source configs, theme colors, routes
│   │   └── utils.ts                      # Shared utilities (cn, formatDate, etc.)
│   │
│   └── types/
│       ├── research.ts                   # ResearchRequest, Citation, SSEEvent types
│       ├── session.ts                    # Session, Turn types
│       ├── knowledge.ts                  # Entity, Relationship, GraphData types
│       └── agent.ts                      # AgentEvent, AgentTrace types
│
├── public/
│   ├── logo.svg
│   └── og-image.png
│
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── Dockerfile
└── .env.local.example
```

---

## 4. Design System & UI Principles

### Visual Identity

| Property | Value |
|----------|-------|
| Primary color | Indigo (`indigo-600` / shadcn primary) |
| Background | White (light), Zinc-950 (dark) |
| Font | `Inter` (via `next/font/google`) |
| Border radius | `0.5rem` (shadcn default) |
| Spacing | 4px grid (Tailwind default) |
| Max content width | `1280px` (`max-w-7xl`) |

### Source Color Palette

Used consistently across SourceToggle, SourceIndicator, CitationCard, and Graph nodes.

| Source | Color | Lucide Icon |
|--------|-------|-------------|
| DuckDuckGo | `orange-500` | `Globe` |
| Reddit | `red-500` | `MessageCircle` |
| HackerNews | `amber-600` | `Flame` |
| ArXiv | `blue-600` | `GraduationCap` |
| Wikipedia | `slate-600` | `BookOpen` |

### Entity Type Color Palette (Knowledge Graph)

| Entity Type | Color | Lucide Icon |
|-------------|-------|-------------|
| technology | `blue-500` | `Cpu` |
| concept | `purple-500` | `Lightbulb` |
| organization | `green-500` | `Building2` |
| person | `orange-500` | `User` |
| pattern | `teal-500` | `Layers` |
| algorithm | `red-500` | `Binary` |
| protocol | `cyan-500` | `Network` |
| library | `pink-500` | `Package` |
| service | `emerald-500` | `Cloud` |

### Dark Mode

- All components must support dark mode via Tailwind `dark:` classes
- shadcn/ui handles this natively when theme provider is configured
- Use `next-themes` for toggle (install: `npm install next-themes`)
- Default: system preference, user can override

### Design Tenets

1. **Streaming-first**: The answer streams token-by-token. Never show a loading spinner for the answer — show progressive content.
2. **Source transparency**: Always show which sources are being searched and their status.
3. **Citation integrity**: Every `[n]` in the answer must be a clickable link resolving to a real source.
4. **Progressive disclosure**: Agent reasoning, advanced filters, and debug info should be behind toggles — clean by default, powerful on demand.
5. **Mobile-ready**: Single-column layout on mobile, two-column on desktop. Session sidebar becomes a Sheet/drawer on mobile.

---

## 5. Pages & Routing

| Route | Page | Description |
|-------|------|-------------|
| `/` | Home / Research | Main research interface (SearchBar + ResearchView) |
| `/session/[id]` | Session Detail | Full conversation for a past session with follow-up |
| `/knowledge` | Knowledge Graph | Interactive D3 graph + entity detail + filters |
| `/dashboard` | Analytics | Charts: activity, source perf, cache, top entities |
| `/settings` | Settings | User preferences, API keys (if self-hosted) |
| `/settings/schedules` | Scheduled Research | CRUD for daily/weekly research schedules |
| `/auth/login` | Login | Email/password + GitHub OAuth |
| `/auth/signup` | Sign Up | Registration form |
| `/auth/callback` | Auth Callback | Supabase OAuth redirect handler (route handler) |

### Layout Architecture

```
RootLayout (layout.tsx)
├── ThemeProvider (next-themes)
├── AuthProvider (Supabase context)
├── AppShell
│   ├── Header (logo, search shortcut, NotificationBell, UserMenu)
│   ├── SessionSidebar (left, collapsible, sheet on mobile)
│   └── Main Content Area
│       └── {children} — page content
```

---

## 6. Component Specifications

### 6.1 SearchBar

**Location:** `components/research/SearchBar.tsx`
**Scaffold with v0.dev:** *"A large centered search input with placeholder text, submit button on the right, and a row of toggleable source badges below"*

**Behavior:**
- Large input field, centered on page (when no active research), shifts to top when results are showing
- Placeholder: `"What would you like to research?"`
- Source toggles below the input: row of `SourceToggle` pills (all on by default)
- Submit on `Enter` key or click the submit button (use Lucide `ArrowRight` or `Search` icon)
- Disable input + button while streaming
- Validate: min 3 chars, max 2000 chars (show character count near limit)
- Optional depth selector: `quick | standard | deep` (use shadcn `Select`)

**shadcn components used:** `Input`, `Button`, `Badge`, `Select`, `Tooltip`

**Props:**
```typescript
interface SearchBarProps {
  onSubmit: (query: string, sources: string[], depth: ResearchDepth) => void;
  isStreaming: boolean;
  defaultSources?: string[];
}
```

---

### 6.2 SourceToggle

**Location:** `components/research/SourceToggle.tsx`

**Behavior:**
- Pill-shaped toggle for a single source
- Shows: source icon (Lucide) + source name
- Active state: filled background with source color
- Inactive state: outline with muted text
- Click toggles on/off

**shadcn components used:** `Toggle` or custom pill using `Badge` variant

**Props:**
```typescript
interface SourceToggleProps {
  source: SourceConfig;     // { name, displayName, icon, color }
  isActive: boolean;
  onToggle: (sourceName: string) => void;
}
```

---

### 6.3 SourceIndicator

**Location:** `components/research/SourceIndicator.tsx`

**Behavior:**
- Horizontal row of status pills, one per active source
- States per source (driven by SSE events):
  - `waiting` → Gray pill, no icon
  - `searching` → Blue pill, animated spinner (Lucide `Loader2` with `animate-spin`)
  - `done` → Green pill, Lucide `Check`, show result count + latency: `"✓ 8 results (1.2s)"`
  - `error` → Red pill, Lucide `AlertCircle`, tooltip shows error message
- Updates in real-time as `source_complete` SSE events arrive

**shadcn components used:** `Badge`, `Tooltip`

**Props:**
```typescript
interface SourceIndicatorProps {
  sources: SourceStatus[];
  // SourceStatus: { name, displayName, status, resultsCount?, latencyMs?, error? }
}
```

---

### 6.4 PhaseIndicator

**Location:** `components/research/PhaseIndicator.tsx`

**Behavior:**
- Shows current pipeline phase as a subtle text + icon above the stream
- Phases (from SSE `status` events):
  1. `"Decomposing query..."` — Lucide `BrainCircuit`
  2. `"Searching N sources..."` — Lucide `Search`
  3. `"Processing results..."` — Lucide `Cog`
  4. `"Synthesizing answer..."` — Lucide `Sparkles`
- Transition animation: fade out old phase, fade in new

**shadcn components used:** None (custom, lightweight)

---

### 6.5 ResearchStream

**Location:** `components/research/ResearchStream.tsx`

**Behavior:**
- Renders streamed markdown tokens as they arrive from the SSE `token` events
- Uses `react-markdown` + `remark-gfm` for rendering (supports tables, lists, bold, headers, code blocks)
- **Citation rendering:** Citation markers like `[1]`, `[2]` in the text are rendered as:
  - Clickable superscript badges
  - On hover: tooltip showing source title + URL
  - On click: scroll to corresponding CitationCard in the sidebar, or open URL in new tab
- Typing cursor: blinking cursor at end of text while streaming
- Auto-scroll to bottom as content grows (with "scroll to bottom" button if user scrolls up)
- After streaming completes: remove typing cursor, finalize rendering

**shadcn components used:** `Tooltip`, `Badge`

**Markdown custom renderers:**
```typescript
const components = {
  // Custom renderer for citation markers [1], [2], etc.
  // Parse inline text for /\[(\d+)\]/ pattern
  // Render as <CitationBadge id={n} /> superscript
  p: ({ children }) => <p className="mb-4 leading-7">{parseCitations(children)}</p>,
  h2: ({ children }) => <h2 className="text-xl font-semibold mt-6 mb-3">{children}</h2>,
  // ... etc
};
```

**Props:**
```typescript
interface ResearchStreamProps {
  tokens: string;            // Accumulated token string
  citations: Citation[];     // Full citation data (from `complete` event)
  isStreaming: boolean;
  onCitationClick: (citationId: number) => void;
}
```

---

### 6.6 CitationCard

**Location:** `components/research/CitationCard.tsx`

**Behavior:**
- Displays a single citation source
- Shows: citation number badge, title, source name with source icon + color, URL (truncated, linked), relevance score bar
- Click opens source URL in new tab
- Grouped by source type in the sidebar
- Highlight animation when scrolled to (from in-text citation click)

**shadcn components used:** `Card`, `Badge`, `Tooltip`

**Props:**
```typescript
interface CitationCardProps {
  citation: Citation;
  isHighlighted?: boolean;
}

interface Citation {
  id: number;
  title: string;
  url: string;
  source_name: string;       // "duckduckgo", "reddit", etc.
  relevance_score: float;    // 0.0 to 1.0
}
```

---

### 6.7 CitationSidebar

**Location:** `components/research/CitationSidebar.tsx`

**Behavior:**
- Right sidebar panel (desktop) or bottom sheet (mobile) listing all citations
- Grouped by source type, each group with source icon + count header
- Sorted within each group by relevance score (descending)
- Only appears after research completes or partial citations arrive
- Scrollable with shadcn `ScrollArea`

**shadcn components used:** `ScrollArea`, `Separator`, `Sheet` (mobile)

---

### 6.8 FollowUpInput

**Location:** `components/research/FollowUpInput.tsx`

**Behavior:**
- Appears below the completed answer
- Compact input field with "Ask a follow-up..." placeholder
- Submit sends to `POST /api/v1/research/{session_id}/followup`
- New answer streams below the previous one (conversation thread)
- Disabled while streaming

**shadcn components used:** `Input`, `Button`

---

### 6.9 SessionSidebar

**Location:** `components/layout/SessionSidebar.tsx`

**Behavior:**
- Left sidebar listing past research sessions
- Each item shows: title (auto-generated from first query), date, query count badge
- Click loads session into the main content area
- "New Research" button at top (Lucide `Plus`)
- Grouped by date: "Today", "Yesterday", "This Week", "Older"
- Search/filter field at top
- Shows only for authenticated users
- Collapsible on desktop, Sheet/drawer on mobile

**Data source:** `GET /api/v1/sessions` (paginated)

**shadcn components used:** `ScrollArea`, `Button`, `Input`, `Sheet` (mobile), `Badge`

---

### 6.10 KnowledgeGraph

**Location:** `components/knowledge/KnowledgeGraph.tsx`

**Behavior:**
- Force-directed graph using D3.js (`d3-force`)
- **Nodes:** Entities, sized by `mention_count`, colored by entity type (see color palette)
- **Edges:** Relationships, labeled with type, weighted by confidence
- **Interactions:**
  - Drag nodes to rearrange
  - Zoom/pan with mouse wheel + drag
  - Click node → open EntityDetail panel
  - Hover node → highlight connected edges and nodes
- **Performance:** Must render <1s for up to 200 entities. Use canvas rendering for >100 nodes.

**Graph views (toggle):**
1. Full graph — all entities and relationships
2. Session graph — filtered to a specific session
3. Entity neighborhood — selected entity + 1-2 hop connections

**Data source:** `GET /api/v1/sessions/{id}/graph` or `GET /api/v1/knowledge/graph`

---

### 6.11 EntityDetail

**Location:** `components/knowledge/EntityDetail.tsx`

**Behavior:**
- Slide-in panel (shadcn `Sheet` or custom panel) on entity node click
- Shows: entity name, type badge (colored), description
- Stats: mention count, first seen date, last seen date
- "Sessions" section: list of sessions where this entity appears (linked to `/session/[id]`)
- "Related entities" section: directly connected entities (clickable, refocus graph)
- "Research more" button → prefills search bar with entity name and navigates to `/`

**shadcn components used:** `Sheet`, `Badge`, `Button`, `Separator`, `ScrollArea`

---

### 6.12 GraphControls

**Location:** `components/knowledge/GraphControls.tsx`

**Behavior:**
- Filter panel (left sidebar or top bar on the knowledge page)
- Filters:
  - **Entity type:** Checkboxes (technology, concept, organization, etc.)
  - **Session:** Dropdown/select to show only entities from a specific session
  - **Date range:** Date pickers for first_seen / last_seen
  - **Min mentions:** Slider to hide rarely-mentioned entities
- Filters apply reactively to the graph

**shadcn components used:** `Checkbox`, `Select`, `Slider`, `Popover`, `Button`

---

### 6.13 AgentThinking (Phase 4)

**Location:** `components/agent/AgentThinking.tsx`

**Behavior:**
- Collapsible panel above the streaming answer (hidden by default, toggled via "Show reasoning")
- Shows agent reasoning steps in real-time as SSE events arrive
- Each step: icon + agent type badge + reasoning text + timestamp
- Color-coded by agent:
  - Coordinator → `slate`
  - Academic → `blue`
  - Practitioner → `amber`
  - Fact-checker → `green`
- Steps appear with subtle fade-in animation
- Each step expandable to show full reasoning text

**SSE events consumed:** `agent_thinking`, `agent_action`, `agent_action_complete`, `agent_evaluation`

**Example rendering:**
```
🤔 Coordinator: Analyzing query complexity → Complex comparison detected
📚 Academic Agent: Searching ArXiv for "Kafka throughput benchmarks"
💬 Practitioner Agent: Searching Reddit for "Kafka vs RabbitMQ production"
📚 Academic Agent: Found 3 papers (confidence: 62%)
📚 Academic Agent: Refining — need higher throughput data
✅ Fact Check: Verifying "Kafka handles 100K msgs/sec" → Confirmed by 2 sources
📝 Synthesizing from 8 chunks across 3 agents...
```

**shadcn components used:** `Collapsible`, `Badge`, `ScrollArea`

---

### 6.14 AgentTrace (Phase 4)

**Location:** `components/agent/AgentTrace.tsx`

**Behavior:**
- Post-research detailed timeline of all agent iterations
- Shows decision tree: which agents were dispatched and why
- Each iteration: reasoning → action → result → confidence delta
- Expandable details for each step
- Links from trace steps to specific citations in the answer

**Data source:** `GET /api/v1/sessions/{id}/turns/{turn_id}/trace`

**shadcn components used:** `Card`, `Collapsible`, `Badge`, `Separator`

---

### 6.15 Dashboard Components (Phase 3)

**ActivityChart** — Line chart (Recharts `LineChart`) showing queries per week
**SourcePerformance** — Table: source name, avg latency, success rate, circuit breaker status
**CacheStats** — Gauge or progress ring showing cache hit rate
**TopEntities** — Horizontal bar chart of top 10 entities by mention count
**KnowledgeStats** — Stat cards: total nodes, total edges, growth trend

**Data source:** `GET /api/v1/analytics`

---

### 6.16 Shared Components

**NotificationBell** — Header bell icon with unread count badge. Dropdown shows recent notifications (proactive research suggestions, knowledge updates). Mark-as-read on click.

**ShareDialog** — Modal to share a session. Generates a link with role selection (viewer/editor). Copy link button.

**ExportMenu** — Dropdown on session page: "Export as Markdown", "Export as JSON", "Export to Obsidian". Triggers file download.

---

## 7. Custom Hooks

### 7.1 `useSSE`

**File:** `hooks/useSSE.ts`

The core hook for all real-time streaming. Uses `fetch` with `ReadableStream` + `eventsource-parser`.

```typescript
interface UseSSEOptions {
  url: string;
  method: 'GET' | 'POST';
  body?: object;
  headers?: Record<string, string>;
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

interface SSEEvent {
  event: string;     // "status", "source_complete", "token", "complete", "agent_thinking", etc.
  data: any;         // Parsed JSON data
}

interface UseSSEReturn {
  start: () => void;
  abort: () => void;
  isConnected: boolean;
  error: Error | null;
}
```

**Implementation notes:**
- Use `fetch()` with `ReadableStream` reader (not `EventSource` — we need POST support)
- Parse SSE format: `event: <type>\ndata: <json>\n\n`
- Use `eventsource-parser` library's `createParser()` for reliable parsing
- Handle reconnection on network errors (max 3 retries with backoff)
- Support `AbortController` for cancellation

---

### 7.2 `useResearch`

**File:** `hooks/useResearch.ts`

State machine for the research lifecycle.

```typescript
type ResearchPhase = 'idle' | 'decomposing' | 'searching' | 'processing' | 'synthesizing' | 'complete' | 'error';

interface UseResearchReturn {
  // State
  phase: ResearchPhase;
  tokens: string;                  // Accumulated answer text
  citations: Citation[];
  sourceStatuses: SourceStatus[];
  sessionId: string | null;
  agentEvents: AgentEvent[];       // Phase 4
  error: Error | null;

  // Actions
  startResearch: (query: string, sources: string[], depth: ResearchDepth) => void;
  startFollowUp: (sessionId: string, query: string) => void;
  reset: () => void;
}
```

**Implementation:**
- Wraps `useSSE` internally
- Maps SSE events to state updates:
  - `status` event → update `phase`
  - `source_complete` event → update `sourceStatuses` array
  - `token` event → append to `tokens` string
  - `complete` event → set `phase = 'complete'`, populate `citations` + `sessionId`
  - `agent_*` events → append to `agentEvents` array

---

### 7.3 `useSession`

**File:** `hooks/useSession.ts`

Session CRUD operations.

```typescript
interface UseSessionReturn {
  sessions: Session[];
  isLoading: boolean;
  fetchSessions: () => Promise<void>;
  getSession: (id: string) => Promise<SessionDetail>;
  archiveSession: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
}
```

---

### 7.4 `useAuth`

**File:** `hooks/useAuth.ts`

Supabase auth wrapper.

```typescript
interface UseAuthReturn {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signInWithGitHub: () => Promise<void>;
  signOut: () => Promise<void>;
}
```

---

## 8. API Contracts & SSE Protocol

### 8.1 Base Configuration

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken(); // from Supabase session
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) throw new ApiError(res.status, await res.json());
  return res.json();
}
```

### 8.2 REST Endpoints

| Method | Endpoint | Request Body | Response | Used By |
|--------|----------|-------------|----------|---------|
| `POST` | `/api/v1/research` | `{ query, sources[], depth }` | SSE stream | SearchBar → useResearch |
| `POST` | `/api/v1/research/{session_id}/followup` | `{ query }` | SSE stream | FollowUpInput → useResearch |
| `GET` | `/api/v1/sessions` | — | `{ sessions: Session[] }` | SessionSidebar |
| `GET` | `/api/v1/sessions/{id}` | — | `SessionDetail` (with turns) | Session page |
| `DELETE` | `/api/v1/sessions/{id}` | — | `204` | SessionSidebar |
| `PATCH` | `/api/v1/sessions/{id}` | `{ title }` | `Session` | SessionSidebar (rename) |
| `GET` | `/api/v1/knowledge/search?q=...&limit=10` | — | `{ results: KnowledgeResult[] }` | Knowledge page |
| `GET` | `/api/v1/knowledge/recall?q=...` | — | `RecallResult` | Knowledge page |
| `GET` | `/api/v1/sessions/{id}/graph` | — | `GraphData { nodes, edges }` | KnowledgeGraph |
| `GET` | `/api/v1/analytics` | — | `AnalyticsData` | Dashboard |
| `GET` | `/api/v1/sources` | — | `{ sources: SourceConfig[] }` | SearchBar (source list) |
| `GET` | `/api/v1/sessions/{id}/export?format=markdown` | — | File download | ExportMenu |
| `GET` | `/api/v1/knowledge/export?format=obsidian` | — | ZIP file | ExportMenu |
| `GET` | `/api/v1/suggestions` | — | `Suggestion[]` | Dashboard / Notifications |
| `POST` | `/api/v1/suggestions/{id}/execute` | — | SSE stream | Suggestion card |
| `GET` | `/api/v1/notifications` | — | `Notification[]` | NotificationBell |
| `PATCH` | `/api/v1/notifications/{id}/read` | — | `204` | NotificationBell |
| `POST` | `/api/v1/schedules` | `ScheduleInput` | `Schedule` | Schedules page |
| `GET` | `/api/v1/schedules` | — | `Schedule[]` | Schedules page |
| `PATCH` | `/api/v1/schedules/{id}` | `Partial<ScheduleInput>` | `Schedule` | Schedules page |
| `DELETE` | `/api/v1/schedules/{id}` | — | `204` | Schedules page |
| `GET` | `/api/v1/sessions/{id}/turns/{turn_id}/trace` | — | `AgentTrace` | AgentTrace component |

### 8.3 SSE Event Protocol

The research endpoints (`/research` and `/followup`) return Server-Sent Events streams.

**Event types and their data shapes:**

```typescript
// Phase status updates
type StatusEvent = {
  event: 'status';
  data: {
    phase: 'decomposing' | 'searching' | 'processing' | 'synthesizing';
    message: string;
    sources_active?: number;
  };
};

// Individual source completion
type SourceCompleteEvent = {
  event: 'source_complete';
  data: {
    source: string;           // "ddg", "reddit", "hackernews", "arxiv", "wikipedia"
    results_count: number;
    latency_ms: number;
  };
};

// Source failure
type SourceErrorEvent = {
  event: 'source_error';
  data: {
    source: string;
    error: string;
    circuit_breaker_open: boolean;
  };
};

// Streamed answer tokens
type TokenEvent = {
  event: 'token';
  data: {
    content: string;          // Token text chunk
    citations?: number[];     // Citation IDs referenced in this chunk
  };
};

// Research complete
type CompleteEvent = {
  event: 'complete';
  data: {
    session_id: string;
    sources_used: number;
    latency_ms: number;
    citations: Citation[];
  };
};

// Error event
type ErrorEvent = {
  event: 'error';
  data: {
    message: string;
    code: string;
  };
};

// --- Agent events (Phase 4) ---

type AgentThinkingEvent = {
  event: 'agent_thinking';
  data: {
    agent: string;            // "coordinator", "academic", "practitioner", "factcheck"
    reasoning: string;
  };
};

type AgentActionEvent = {
  event: 'agent_action';
  data: {
    agent: string;
    action: string;           // "search", "refine", "verify", "expand", "recall"
    sources?: string[];
    queries?: string[];
  };
};

type AgentActionCompleteEvent = {
  event: 'agent_action_complete';
  data: {
    agent: string;
    action: string;
    results_count: number;
    duration_ms: number;
  };
};

type AgentEvaluationEvent = {
  event: 'agent_evaluation';
  data: {
    agent: string;
    confidence: number;       // 0.0 to 1.0
    gaps: string[];
  };
};
```

---

## 9. State Management

Use a layered approach:

| Layer | Tool | Scope |
|-------|------|-------|
| Server state | `fetch` + React cache / SWR pattern | API data: sessions, knowledge, analytics |
| Research state | `useResearch` hook (useReducer) | SSE-driven research lifecycle |
| Auth state | Supabase client + React context | User session |
| UI state | Local component state (`useState`) | Modals, toggles, sidebar open/close |
| Theme | `next-themes` | Light/dark mode |

Avoid pulling in a heavy global store (Redux, etc.) unless complexity warrants it. Start with hooks + context. Evaluate Zustand if state sharing becomes painful after Phase 2.

---

## 10. Authentication Flow

### Architecture

- **Supabase Auth** handles user management (email/password + GitHub OAuth)
- Backend verifies JWT tokens from Supabase in every protected request
- Frontend sends `Authorization: Bearer <token>` header

### Flow

```
1. User clicks "Sign In" → /auth/login
2. Email/Password → supabase.auth.signInWithPassword()
   OR
   GitHub → supabase.auth.signInWithOAuth({ provider: 'github' })
3. Supabase returns session with access_token
4. Token stored in cookie (via @supabase/auth-helpers-nextjs)
5. All API calls include Bearer token in header
6. Backend validates JWT, extracts user_id
```

### Anonymous Mode

- The research engine works WITHOUT auth
- Anonymous users get full research (SSE streaming, citations)
- Sessions are stored only in browser `localStorage` (not persisted server-side)
- "Save this session" or "View past research" prompts sign-in
- Session sidebar shows only after authentication

### Protected Routes

| Route | Auth Required? |
|-------|---------------|
| `/` (research) | No (anonymous allowed) |
| `/session/[id]` | Yes |
| `/knowledge` | Yes |
| `/dashboard` | Yes |
| `/settings/*` | Yes |

Use Next.js middleware (`middleware.ts`) to redirect unauthenticated users on protected routes.

---

## 11. Phased Implementation Plan

### Phase 1 — Core Research UI (Sprint 2, Days 8-14)

> **Goal:** Users can type a query, see sources searching in real-time, and read a streamed cited answer.

#### Step 1.1: Project Setup (Day 8, 0.5 day)
- [ ] `npx create-next-app@latest` with TypeScript + Tailwind + App Router
- [ ] Install and initialize shadcn/ui (New York style, Zinc, CSS variables)
- [ ] Add all dependencies (see [Tech Stack section](#2-tech-stack--tooling))
- [ ] Set up `next-themes` dark mode provider in root layout
- [ ] Set up `Inter` font via `next/font/google`
- [ ] Create `.env.local.example` with `NEXT_PUBLIC_API_URL`
- [ ] Configure `globals.css` with shadcn theme tokens + any custom overrides
- [ ] Set up `lib/api.ts` with base fetch wrapper
- [ ] Set up `lib/constants.ts` with source configs (name, color, icon)
- [ ] Set up `types/` directory with initial TypeScript interfaces

**Acceptance criteria:** `npm run dev` shows a blank page with dark mode toggle working.

#### Step 1.2: SearchBar + Source Toggles (Day 8-9, 1 day)
- [ ] Build `SourceToggle` pill component
- [ ] Build `SearchBar` component with input + source toggle row + submit
- [ ] Scaffold landing state: centered SearchBar on the page (Perplexity-like)
- [ ] Use v0.dev to scaffold the initial layout, then customize
- [ ] Add query validation (min 3 chars) with error message
- [ ] Wire up keyboard handler: Enter to submit

**Acceptance criteria:** User can type a query, toggle sources, and "submit" (console.log at this point).

#### Step 1.3: useSSE Hook (Day 9, 0.5 day)
- [ ] Implement `useSSE` hook with fetch + ReadableStream + eventsource-parser
- [ ] Handle event parsing, error recovery, abort
- [ ] Write a simple test page that connects to a mock SSE endpoint

**Acceptance criteria:** Hook correctly parses SSE events from the backend `/research` endpoint.

#### Step 1.4: useResearch Hook + Research State (Day 9, 0.5 day)
- [ ] Implement `useResearch` hook wrapping `useSSE`
- [ ] State machine: idle → decomposing → searching → processing → synthesizing → complete → error
- [ ] Map SSE events to state transitions

**Acceptance criteria:** Submitting a query transitions through all phases and accumulates tokens.

#### Step 1.5: SourceIndicator + PhaseIndicator (Day 9-10, 0.5 day)
- [ ] Build `SourceIndicator` component (horizontal status pills)
- [ ] Build `PhaseIndicator` component (subtle text + icon)
- [ ] Wire to `useResearch` state

**Acceptance criteria:** Source pills update live as SSE `source_complete` events arrive. Phase text transitions.

#### Step 1.6: ResearchStream (Day 10, 1 day)
- [ ] Build `ResearchStream` component with react-markdown rendering
- [ ] Implement citation parsing: regex `/\[(\d+)\]/g` → clickable superscript badges
- [ ] Add typing cursor animation while streaming
- [ ] Add auto-scroll behavior with "scroll to bottom" button
- [ ] Handle code blocks, tables, lists properly via remark-gfm

**Acceptance criteria:** Markdown answer streams in real-time with formatted text and clickable `[n]` citations.

#### Step 1.7: CitationCard + CitationSidebar (Day 10, 0.5 day)
- [ ] Build `CitationCard` component
- [ ] Build `CitationSidebar` wrapper (grouped by source)
- [ ] Wire citation click from ResearchStream → highlight in sidebar

**Acceptance criteria:** Citations display with source icon, title, URL. Clicking `[1]` in answer highlights citation #1 in sidebar.

#### Step 1.8: ResearchView Composition + Page Layout (Day 11, 0.5 day)
- [ ] Build `ResearchView` composing: PhaseIndicator + SourceIndicator + ResearchStream + CitationSidebar
- [ ] Wire into `page.tsx`: SearchBar (top) + ResearchView (below, appears on submit)
- [ ] Responsive: two-column on desktop (stream + citation sidebar), single-column on mobile (citations below)
- [ ] Transition: SearchBar moves from centered to top when research starts

**Acceptance criteria:** Full end-to-end flow works: type query → see phases → see sources → read streamed answer with citations.

#### Step 1.9: Dark Mode + Polish (Day 11-12, 0.5 day)
- [ ] Verify all components look correct in dark mode
- [ ] Add empty states (no results, error state, etc.)
- [ ] Add loading skeleton for initial page load
- [ ] Test mobile responsiveness (375px - 768px breakpoints)

#### Step 1.10: Docker Integration (Day 12, 0.5 day)
- [ ] Create `Dockerfile` (multi-stage: Node 18-alpine build → runtime)
- [ ] `npm ci` → `npm run build` → `npm start`
- [ ] Integrate into project `docker-compose.yml` as `frontend` service
- [ ] Environment variable: `NEXT_PUBLIC_API_URL` from Docker env

**Acceptance criteria:** `docker compose up` starts frontend on port 3000, connects to backend on port 8000.

---

### Phase 2 — Sessions, Auth, Follow-ups (Sprints 4-6, Weeks 4-6)

> **Goal:** Authenticated users have persistent sessions, can ask follow-ups, and see their history.

#### Step 2.1: Session Sidebar (Week 4, 2 days)
- [ ] Build `SessionSidebar` component
- [ ] Implement `useSession` hook (fetch sessions, CRUD)
- [ ] Group sessions by date (Today, Yesterday, This Week, Older) using `date-fns`
- [ ] New Research button
- [ ] Session click → load into main content
- [ ] Collapsible on desktop, Sheet/drawer on mobile
- [ ] AppShell layout: sidebar + content

#### Step 2.2: Session Detail Page (Week 4, 1 day)
- [ ] Build `/session/[id]/page.tsx`
- [ ] Display full conversation (all turns in order)
- [ ] Each turn shows: query, streamed answer, citations
- [ ] Session metadata: title, date, query count, sources used

#### Step 2.3: Follow-Up Input (Week 4, 1 day)
- [ ] Build `FollowUpInput` component
- [ ] Wire to `POST /api/v1/research/{session_id}/followup`
- [ ] Stream follow-up answer below previous answers (conversation thread UI)
- [ ] Share session context across follow-ups

#### Step 2.4: Authentication UI (Week 5, 2 days)
- [ ] Set up Supabase client (`lib/supabase.ts`)
- [ ] Build `LoginForm` (email/password + GitHub OAuth button)
- [ ] Build `SignupForm`
- [ ] Build `UserMenu` (avatar dropdown: profile, settings, logout)
- [ ] Implement `useAuth` hook
- [ ] Set up `/auth/callback/route.ts` for OAuth redirect
- [ ] Add auth middleware for protected routes
- [ ] Implement anonymous mode: research works without auth, "save" prompts sign-in

#### Step 2.5: Header + Navigation (Week 5, 1 day)
- [ ] Build `Header` component: logo, (optional: global search shortcut), UserMenu
- [ ] Build `MobileNav`: responsive bottom nav or hamburger menu
- [ ] Dark mode toggle in header

#### Step 2.6: Source Indicator Updates (Week 5, 0.5 day)
- [ ] Add Reddit and ArXiv to source configs (icons, colors)
- [ ] Source list now driven by `GET /api/v1/sources` (dynamic, not hardcoded)

#### Step 2.7: Vercel Deployment Prep (Week 6, 0.5 day)
- [ ] Verify build passes: `npm run build`
- [ ] Set `NEXT_PUBLIC_API_URL` env var for production
- [ ] Test SSE streaming works over Vercel's edge network
- [ ] Configure `next.config.js` for production (output: standalone if Docker, or default for Vercel)

**Phase 2 Acceptance Criteria:**
- [ ] Authenticated users see session history in sidebar
- [ ] Click past session → view full conversation
- [ ] Follow-up questions work within a session
- [ ] Auth flow works (signup, login, GitHub OAuth, logout)
- [ ] Anonymous users can research but can't save sessions
- [ ] Deployed on Vercel

---

### Phase 3 — Knowledge Graph, Dashboard, Export (Sprints 8-10, Weeks 8-10)

> **Goal:** Interactive knowledge graph, analytics dashboard, export, sharing, scheduled research UI.

#### Step 3.1: Knowledge Graph Page (Week 8, 3 days)
- [ ] Build `/knowledge/page.tsx` layout: graph area + controls sidebar + entity detail panel
- [ ] Implement `KnowledgeGraph` with D3.js force simulation
  - Canvas rendering for performance
  - Nodes: entities (circle, sized by mention_count, colored by type)
  - Edges: relationships (line, labeled, weighted by confidence)
  - Zoom, pan, drag interactions
  - Click node → EntityDetail panel
  - Hover node → highlight connections
- [ ] Build `GraphControls` (entity type filters, session filter, date range, min mentions)
- [ ] Build `GraphLegend` (entity type color key)
- [ ] Implement `useKnowledge` hook

#### Step 3.2: Entity Detail Panel (Week 8, 1 day)
- [ ] Build `EntityDetail` as a Sheet panel
- [ ] Display: name, type, description, mention count, first/last seen
- [ ] Sessions list (linked to `/session/[id]`)
- [ ] Related entities (clickable, refocuses graph)
- [ ] "Research more" button → navigates to `/` with query prefilled

#### Step 3.3: Export Functionality (Week 9, 1 day)
- [ ] Build `ExportMenu` dropdown on session page
- [ ] "Export as Markdown" → `GET /api/v1/sessions/{id}/export?format=markdown` → file download
- [ ] "Export as JSON" → same endpoint with `format=json`
- [ ] "Export to Obsidian" (knowledge-level) → `GET /api/v1/knowledge/export?format=obsidian` → ZIP download
- [ ] Use `<a download>` or `URL.createObjectURL` for triggering downloads

#### Step 3.4: Share Dialog (Week 9, 1 day)
- [ ] Build `ShareDialog` modal (shadcn `Dialog`)
- [ ] Role selector: Viewer / Editor
- [ ] "Generate Link" → `POST /api/v1/sessions/{id}/share`
- [ ] Copy link to clipboard button
- [ ] Shared session indicator: avatar pills of collaborators on session page

#### Step 3.5: Analytics Dashboard (Week 9-10, 2 days)
- [ ] Build `/dashboard/page.tsx`
- [ ] `ActivityChart`: Recharts `LineChart` — queries per week
- [ ] `SourcePerformance`: Table — source, avg latency (bar), success rate, circuit breaker status badge
- [ ] `CacheStats`: Recharts `RadialBarChart` or progress ring — cache hit rate percentage
- [ ] `TopEntities`: Recharts `BarChart` (horizontal) — top 10 entities by mentions
- [ ] `KnowledgeStats`: Stat cards (shadcn `Card`) — total nodes, edges, sessions
- [ ] Data from `GET /api/v1/analytics`

#### Step 3.6: Scheduled Research UI (Week 10, 1 day)
- [ ] Build `/settings/schedules/page.tsx`
- [ ] Form to create schedule: query template, topics (tag input), frequency (daily/weekly), source selection
- [ ] List existing schedules with edit/pause/delete
- [ ] Active/paused status toggle
- [ ] Use React Hook Form + Zod for validation

#### Step 3.7: Notification System (Week 10, 1 day)
- [ ] Build `NotificationBell` in header
- [ ] Unread count badge
- [ ] Dropdown: list of notifications (proactive research, schedule completions)
- [ ] Click notification → navigate to relevant session/suggestion
- [ ] Mark as read on click
- [ ] Poll `GET /api/v1/notifications` every 60 seconds (or WebSocket if available)

**Phase 3 Acceptance Criteria:**
- [ ] Knowledge graph renders <1s with up to 200 entities
- [ ] Nodes are interactive (drag, click, hover)
- [ ] Entity filters work
- [ ] Dashboard shows meaningful analytics
- [ ] Sessions are exportable (Markdown, JSON, Obsidian)
- [ ] Share links work
- [ ] Scheduled research is manageable from UI
- [ ] Notifications appear in header bell

---

### Phase 4 — Agent Reasoning UI (Sprint 13, Week 13)

> **Goal:** Make agent reasoning visible and explorable — the "wow factor."

#### Step 4.1: AgentThinking Component (3 days)
- [ ] Build collapsible reasoning panel
- [ ] Parse and display agent SSE events in real-time
- [ ] Color-code by agent type
- [ ] Animate step appearance (fade-in)
- [ ] Expandable steps for full reasoning text
- [ ] "Show agent reasoning" toggle button (off by default)

#### Step 4.2: AgentTrace Component (2 days)
- [ ] Build post-research trace timeline
- [ ] Fetch from `GET /api/v1/sessions/{id}/turns/{turn_id}/trace`
- [ ] Timeline visualization: each iteration as a node with expand
- [ ] Show reasoning → action → result → confidence for each step
- [ ] Link trace steps to citations in the answer

#### Step 4.3: Proactive Suggestion Cards (1 day)
- [ ] Suggestion cards on dashboard: knowledge gap, stale research, incomplete comparison
- [ ] Each card: title, reasoning, suggested query, "Research Now" button
- [ ] "Research Now" → `POST /api/v1/suggestions/{id}/execute` → opens research with streaming

**Phase 4 Acceptance Criteria:**
- [ ] Agent reasoning is visible in real-time via toggle
- [ ] Post-research trace is explorable
- [ ] Proactive suggestions are actionable with one click

---

## 12. Docker & Deployment

### Dockerfile

```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

### docker-compose.yml (frontend service)

```yaml
frontend:
  build: ./frontend
  ports: ["3000:3000"]
  environment:
    - NEXT_PUBLIC_API_URL=http://backend:8000
  depends_on:
    backend:
      condition: service_healthy
```

### Vercel Deployment

- Connect GitHub repo → auto-deploy `frontend/` directory
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `.next`
- Environment variable: `NEXT_PUBLIC_API_URL=https://sift-backend.onrender.com`
- Framework preset: Next.js (auto-detected)

---

## 13. Testing Strategy

| Type | Tool | Scope |
|------|------|-------|
| Unit | Vitest + React Testing Library | Individual components, hooks |
| Integration | Vitest + MSW (Mock Service Worker) | SSE streaming, API interactions |
| E2E | Playwright | Full user flows (research, auth, knowledge graph) |
| Visual | Storybook (optional) | Component catalog, visual regression |

### Priority Tests

| Test | Priority | Phase |
|------|----------|-------|
| SearchBar submit emits correct query + sources | P0 | 1 |
| useSSE parses all event types correctly | P0 | 1 |
| useResearch transitions through all phases | P0 | 1 |
| ResearchStream renders streaming markdown | P0 | 1 |
| Citation click highlights correct CitationCard | P1 | 1 |
| SourceIndicator shows correct states | P1 | 1 |
| Dark mode renders all components correctly | P1 | 1 |
| Mobile layout: single column, sidebar as sheet | P1 | 1 |
| Auth flow: login → token → protected route | P0 | 2 |
| Session sidebar loads and filters sessions | P1 | 2 |
| Follow-up streams below previous answer | P1 | 2 |
| Knowledge graph renders 100 nodes in <1s | P0 | 3 |
| Graph filters update visible nodes | P1 | 3 |
| Export triggers file download | P2 | 3 |
| Agent events render in AgentThinking panel | P1 | 4 |

### CI (GitHub Actions)

```yaml
frontend:
  steps:
    - npm ci
    - npm run lint
    - npm run build          # Catch TypeScript errors
    - npx vitest run         # Unit + integration tests
```

---

## 14. Performance Requirements

| Metric | Target |
|--------|--------|
| First Contentful Paint (FCP) | < 1.5s |
| Largest Contentful Paint (LCP) | < 2.5s |
| Time to Interactive (TTI) | < 3.5s |
| Token rendering lag | < 50ms after SSE event received |
| Knowledge graph render (200 nodes) | < 1s |
| Dashboard page load | < 2s |
| Bundle size (initial JS) | < 200KB gzipped |

### Optimization Strategies

- Use Next.js App Router with Server Components where possible (layout, static pages)
- Dynamic import D3.js (only on `/knowledge` page)
- Dynamic import Recharts (only on `/dashboard` page)
- Lazy-load CitationSidebar on mobile (Sheet, not always rendered)
- Use `react-markdown` with minimal plugins
- Virtualize long session lists (react-window) if >100 sessions
- Image optimization: `next/image` for any static images

---

## 15. Accessibility & Responsiveness

### Accessibility (a11y)

- shadcn/ui components are built on Radix UI primitives (WCAG 2.1 AA compliant)
- All interactive elements must be keyboard navigable
- Focus trapping in modals/dialogs
- ARIA labels for:
  - Source toggle states (`aria-pressed`)
  - Phase indicator status (`aria-live="polite"`)
  - Streaming text region (`aria-live="polite"`, `aria-atomic="false"`)
  - Citation links (`aria-label="Source N: title"`)
  - Graph nodes (`aria-label` with entity name + type)
- Color contrast: 4.5:1 minimum for text (built into shadcn/ui Zinc theme)
- Reduced motion: respect `prefers-reduced-motion` — disable graph animations, typing cursor animation

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `< 640px` (mobile) | Single column. Sidebar as Sheet. Citations below answer. Simplified graph. |
| `640px - 1024px` (tablet) | Single column with wider content. Sidebar collapsible. |
| `> 1024px` (desktop) | Two-column: answer + citation sidebar. Persistent sidebar. Full graph. |

---

## Appendix: Quick Reference — shadcn/ui Component Mapping

| Sift Feature | shadcn/ui Components |
|--------------|---------------------|
| Search bar | `Input`, `Button` |
| Source toggles | `Toggle` or `Badge` |
| Source status pills | `Badge`, `Tooltip` |
| Streaming answer | Custom (react-markdown) |
| Citation cards | `Card`, `Badge` |
| Citation sidebar | `ScrollArea`, `Sheet` (mobile) |
| Session sidebar | `ScrollArea`, `Sheet` (mobile), `Button` |
| Session list items | `Button` (variant ghost) |
| Knowledge graph | D3.js (custom canvas) |
| Entity detail | `Sheet`, `Badge`, `Separator` |
| Graph controls | `Checkbox`, `Select`, `Slider`, `Popover` |
| Dashboard stats | `Card` |
| Dashboard charts | Recharts (custom) |
| Auth forms | `Input`, `Button`, `Label` |
| User menu | `DropdownMenu`, `Avatar` |
| Notifications | `DropdownMenu`, `Badge` |
| Share dialog | `Dialog`, `Select`, `Button` |
| Export menu | `DropdownMenu` |
| Agent reasoning | `Collapsible`, `Badge` |
| Dark mode toggle | `Button` + Lucide `Sun`/`Moon` |
| Settings forms | `Input`, `Select`, `Switch`, `Button` |
| Toasts/alerts | `Sonner` or shadcn `Toast` |

---

## Appendix: Environment Variables

```bash
# .env.local.example

# Required
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase (required for auth in Phase 2+)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

---

*This document is the single source of truth for frontend implementation. Update it as API contracts evolve or new components are added.*
