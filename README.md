# Sift Frontend — Day-by-Day Execution Roadmap

> **Total Duration:** 6 Weeks (30 Working Days)
> **Phases:** 4 | **Sprints:** 6
> **Stack:** Next.js 14 (App Router) · Tailwind CSS · shadcn/ui · Lucide Icons · D3.js · Recharts
> **Hosting:** Vercel (free tier)
> **Backend:** Assumed available — FastAPI with SSE streaming (developed separately)

---

## How to Use This Roadmap

Each day has:
- **Goal** — What you should accomplish by end of day
- **Tasks** — Specific, checkboxable items
- **Checkpoint** — How you know you're done (testable acceptance criteria)

The frontend is developed independently from the backend. Where the backend isn't ready, use **mock SSE streams** or **static JSON fixtures** to develop against the [API contracts](#api-contracts--sse-protocol-reference) documented at the end of this file.

---

## Table of Contents

- [Phase 1 — Core Research UI (Days 1–7)](#phase-1--core-research-ui-days-17)
- [Phase 2 — Sessions, Auth & Follow-ups (Days 8–14)](#phase-2--sessions-auth--follow-ups-days-814)
- [Phase 3 — Knowledge Graph, Dashboard & Export (Days 15–24)](#phase-3--knowledge-graph-dashboard--export-days-1524)
- [Phase 4 — Agent Reasoning UI & Final Polish (Days 25–30)](#phase-4--agent-reasoning-ui--final-polish-days-2530)
- [API Contracts & SSE Protocol Reference](#api-contracts--sse-protocol-reference)
- [Tech Stack Reference](#tech-stack-reference)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)

---

## Phase 1 — Core Research UI (Days 1–7)

> **Deliverable:** Users can type a research query, see sources searching in real-time, and read a streamed cited answer. Responsive, accessible, dark-mode ready.

---

#### Day 1 — Project Setup + Design System

**Goal:** Next.js app runs with shadcn/ui, dark mode, Inter font, all theme tokens configured. Foundation layer (`lib/`, `types/`) ready.

- [x] Initialize project:
  ```bash
  npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --eslint
  ```
- [x] Initialize shadcn/ui:
  ```bash
  npx shadcn@latest init  # New York style, Zinc, CSS variables
  npx shadcn@latest add button input badge card dialog sheet tabs scroll-area separator tooltip avatar dropdown-menu checkbox slider select command popover toggle collapsible switch label
  ```
- [x] Install all dependencies:
  ```bash
  npm install lucide-react react-markdown remark-gfm eventsource-parser d3 @types/d3 recharts date-fns zod react-hook-form @hookform/resolvers next-themes @supabase/supabase-js @supabase/auth-helpers-nextjs
  ```
- [x] Set up `next-themes` dark mode provider in root `layout.tsx`
- [x] Set up `Inter` font via `next/font/google`
- [x] Configure `globals.css` with shadcn theme tokens + indigo primary color override
- [x] Create `.env.local.example`:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_SUPABASE_URL=
  NEXT_PUBLIC_SUPABASE_ANON_KEY=
  ```
- [x] Create `src/lib/api.ts` — base fetch wrapper with auth token header support
- [x] Create `src/lib/constants.ts` — source configs:
  | Source | Color | Icon |
  |--------|-------|------|
  | DuckDuckGo | `orange-500` | `Globe` |
  | Reddit | `red-500` | `MessageCircle` |
  | HackerNews | `amber-600` | `Flame` |
  | ArXiv | `blue-600` | `GraduationCap` |
  | Wikipedia | `slate-600` | `BookOpen` |
- [x] Create `src/lib/utils.ts` — `cn()` helper (shadcn), `formatDate()`, `truncateUrl()`
- [x] Create `src/types/research.ts` — `ResearchRequest`, `Citation`, `SSEEvent`, `SourceStatus`, `ResearchDepth`
- [x] Create `src/types/session.ts` — `Session`, `SessionDetail`, `ResearchTurn`
- [x] Create `src/types/knowledge.ts` — `Entity`, `Relationship`, `GraphData`
- [x] Create `src/types/agent.ts` — `AgentEvent`, `AgentTrace`

**Checkpoint:**
- [x] `npm run dev` → blank page on `localhost:3000`
- [x] Dark mode toggle works (system preference detected)
- [x] Inter font loads correctly
- [x] `npm run build` passes with zero errors

---

#### Day 2 — SearchBar + Source Toggles + useSSE Hook

**Goal:** User can type a query, toggle sources, and submit. SSE hook can parse events from any SSE endpoint (or mock).

**Morning — SourceToggle + SearchBar:**
- [x] Create `components/research/SourceToggle.tsx`:
  - Pill-shaped toggle: source Lucide icon + name
  - Active: filled background with source color
  - Inactive: outline with muted text
  - `aria-pressed` for accessibility
- [x] Create `components/research/SearchBar.tsx`:
  - Large centered input, placeholder: `"What would you like to research?"`
  - Row of `SourceToggle` pills below (all on by default)
  - Submit on `Enter` or click button (Lucide `ArrowRight`)
  - Validation: min 3 chars, max 2000 chars (show character count near limit)
  - Disabled state while streaming
  - Optional depth selector: `quick | standard | deep` (shadcn `Select`)
  - Props: `onSubmit(query, sources, depth)`, `isStreaming`, `defaultSources?`
- [x] Scaffold landing state in `app/page.tsx`: centered SearchBar on the page (Perplexity-style)
- [x] Wire keyboard handler: `Enter` to submit, `Tab` through toggles

**Afternoon — useSSE Hook:**
- [x] Create `src/hooks/useSSE.ts`:
  - Uses `fetch()` with `ReadableStream` reader (not `EventSource` — POST support needed)
  - Parses SSE with `eventsource-parser` library's `createParser()`
  - Handles reconnection on network errors (max 3 retries with backoff)
  - Supports `AbortController` for cancellation
  - Interface:
    ```typescript
    interface UseSSEReturn {
      start: () => void;
      abort: () => void;
      isConnected: boolean;
      error: Error | null;
    }
    ```
- [x] Create `src/lib/mock-sse.ts` — mock SSE stream for development without backend:
  - Returns simulated `status`, `source_complete`, `token`, `complete` events with realistic delays
  - Toggleable via `NEXT_PUBLIC_USE_MOCK=true` env var

**Checkpoint:**
- [x] SearchBar renders centered, toggles switch on/off visually
- [x] Submitting logs query + sources + depth to console
- [x] `useSSE` parses SSE events from either real backend or mock stream
- [x] Keyboard-only: Tab to toggles, Enter to submit

---

#### Day 3 — useResearch Hook + Source/Phase Indicators + ResearchStream

**Goal:** Full research state machine wired up. Source pills update live. Streamed markdown renders beautifully.

**Morning — useResearch + Indicators:**
- [x] Create `src/hooks/useResearch.ts`:
  - State machine: `idle → decomposing → searching → processing → synthesizing → complete → error`
  - Wraps `useSSE` internally
  - Maps SSE events to state updates:
    - `status` → update `phase`
    - `source_complete` → update `sourceStatuses[]`
    - `token` → append to `tokens` string
    - `complete` → set phase, populate `citations[]` + `sessionId`
    - `agent_*` → append to `agentEvents[]` (Phase 4 prep)
  - Returns: `phase`, `tokens`, `citations`, `sourceStatuses`, `sessionId`, `agentEvents`, `error`, `startResearch()`, `startFollowUp()`, `reset()`
- [x] Create `components/research/PhaseIndicator.tsx`:
  - Subtle text + Lucide icon above stream area
  - Phases: "Decomposing query..." (`BrainCircuit`) → "Searching N sources..." (`Search`) → "Processing results..." (`Cog`) → "Synthesizing answer..." (`Sparkles`)
  - Fade-out / fade-in transition between phases
- [x] Create `components/research/SourceIndicator.tsx`:
  - Horizontal row of status pills, one per active source
  - Per source: `waiting` (gray) → `searching` (blue, `Loader2` + `animate-spin`) → `done` (green, `Check`, count + latency) → `error` (red, `AlertCircle`, tooltip with message)
  - Updates in real-time from `sourceStatuses`

**Afternoon — ResearchStream:**
- [x] Create `components/research/ResearchStream.tsx`:
  - `react-markdown` + `remark-gfm` for rendering (tables, lists, bold, headers, code blocks)
  - **Citation rendering:** regex `/\[(\d+)\]/g` in paragraph text → clickable superscript badges
  - Citation badge: on hover → tooltip with source title + URL; on click → scroll to sidebar / open URL
  - Typing cursor (blinking `|`) at end of text while streaming
  - Auto-scroll to bottom as content grows
  - "Scroll to bottom" floating button if user scrolls up
  - Custom markdown renderers:
    - `p` — `mb-4 leading-7`, parse citations
    - `h2` — `text-xl font-semibold mt-6 mb-3`
    - `code` — inline vs block styling
  - Props: `tokens`, `citations[]`, `isStreaming`, `onCitationClick(id)`

**Checkpoint:**
- [x] Submit query → PhaseIndicator transitions through all states
- [x] Source pills update in real-time as `source_complete` events arrive
- [x] Markdown answer streams token-by-token with proper formatting
- [x] `[1]`, `[2]` rendered as clickable superscript badges with tooltips
- [x] Auto-scroll works, "scroll to bottom" button appears on user scroll-up

---

#### Day 4 — Citations + ResearchView Composition + Page Layout

**Goal:** Full end-to-end flow: query → phases → sources → streamed answer with citations panel. Responsive two-column layout.

**Morning — Citations:**
- [x] Create `components/research/CitationCard.tsx`:
  - Shows: citation number badge (colored by source), title, source name with icon + color, URL (truncated, linked), relevance score progress bar
  - Click → opens source URL in new tab (`rel="noopener noreferrer"`)
  - `isHighlighted` prop → pulsing border animation when scrolled to from in-text click
  - Props: `citation: Citation`, `isHighlighted?: boolean`
- [x] Create `components/research/CitationSidebar.tsx`:
  - Right sidebar (desktop) using `ScrollArea`
  - Bottom `Sheet` (mobile)
  - Citations grouped by source type, each group with source icon + count header
  - Sorted by relevance within each group (descending)
  - Only appears after citations arrive

**Afternoon — ResearchView + Page Wiring:**
- [x] Create `components/research/ResearchView.tsx`:
  - Composes: `PhaseIndicator` + `SourceIndicator` + `ResearchStream` + `CitationSidebar`
  - Manages citation highlight state (which citation is focused)
- [x] Wire into `app/page.tsx`:
  - Default state: centered `SearchBar` (hero)
  - On submit: `SearchBar` transitions to top, `ResearchView` appears below
  - Layout: `grid grid-cols-1 lg:grid-cols-[1fr_320px]` (stream + sidebar on desktop)
- [x] Citation click flow: `[1]` in answer → `onCitationClick(1)` → scroll CitationSidebar to card #1, highlight it

**Checkpoint:**
- [x] Full flow: type query → see phases → see sources → read streamed answer → citations panel
- [x] Click `[1]` in answer → citation #1 highlights in sidebar
- [x] Desktop (>1024px): two-column (stream + sidebar)
- [x] Mobile (<640px): single column, citations below answer
- [x] No visual glitches in both light and dark mode

---

#### Day 5 — Dark Mode Polish + Empty States + Accessibility

**Goal:** App is visually polished across all states and breakpoints. WCAG AA on core flow.

- [x] Verify every component in dark mode — fix any contrast or color issues
- [x] Add empty states:
  - Landing: clean hero with SearchBar + subtle tagline
  - No results: "No sources returned results. Try a different query." + retry button
  - Error: friendly message with error details (collapsible) + retry button
- [x] Add loading skeleton for initial page load (`Skeleton` component from shadcn)
- [x] Add `prefers-reduced-motion` media query:
  - Disable typing cursor animation
  - Disable phase fade transitions
  - Disable citation highlight pulse
- [x] Accessibility pass:
  - `aria-live="polite"` on streaming text region + phase indicator
  - `aria-pressed` on source toggles
  - `aria-label="Source N: <title>"` on citation badges
  - Keyboard navigation: Tab through all interactive elements, Enter/Space to activate
  - Focus management: focus search input on page load
- [x] Test responsiveness at: 375px, 640px, 768px, 1024px, 1440px
- [x] Minimum touch targets: 44x44px on mobile

**Checkpoint:**
- [x] Dark mode: correct contrast on all components (no invisible text)
- [x] Empty/error/loading states render correctly
- [x] Keyboard-only navigation works for full research flow
- [x] No layout breaks between 375px and 1440px
- [x] `prefers-reduced-motion` disables all animations

---

#### Day 6 — Dockerfile + Vercel Prep + Frontend Tests

**Goal:** Frontend containerizable. Build passes for Vercel. Core hooks have unit tests.

**Morning — Docker + Build:**
- [ ] Create `frontend/Dockerfile`:
  ```dockerfile
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
- [ ] Add `output: 'standalone'` to `next.config.js` (for Docker)
- [ ] Verify: `npm run build` passes cleanly
- [ ] Verify: `docker build -t sift-frontend .` succeeds

**Afternoon — Frontend Tests:**
- [ ] Install: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`
- [ ] Configure `vitest.config.ts`
- [ ] Write tests:
  | Test | What it validates |
  |------|-------------------|
  | `SearchBar.test.tsx` | Submit emits correct query + sources; validation rejects <3 chars; disabled while streaming |
  | `SourceToggle.test.tsx` | Toggle state changes on click; renders correct icon + color |
  | `useSSE.test.ts` | Parses SSE event format correctly; handles abort; handles connection error |
  | `useResearch.test.ts` | State transitions through all phases; tokens accumulate; citations populated on complete |
  | `CitationCard.test.tsx` | Renders title, URL, source icon; highlight animation triggers |
  | `SourceIndicator.test.tsx` | Shows correct state for waiting/searching/done/error |
- [ ] Setup CI-compatible test command: `npx vitest run`

**Checkpoint:**
- [ ] `npm run build` — zero errors
- [ ] `docker build` — succeeds
- [ ] `npx vitest run` — all tests pass
- [ ] All tests run without backend dependency (mocked)

---

#### Day 7 — Buffer / Integration Polish

**Goal:** Phase 1 complete. No rough edges. Ready to build on.

- [ ] Fix any failing tests or visual bugs from the week
- [ ] Test full flow with mock SSE and (if available) real backend
- [ ] Ensure `SearchBar` → `ResearchView` transition animation is smooth
- [ ] Review code: remove TODO comments, clean up unused imports
- [ ] Verify dark mode one final time across all components
- [ ] `npm run lint` — zero warnings

**Checkpoint:**
- [ ] Phase 1 exit criteria met (below)

---

### Phase 1 Exit Criteria

- [ ] All 7 days completed
- [ ] Full research flow works: query → phases → sources → streamed answer → citations
- [ ] Responsive on mobile (375px) through desktop (1440px)
- [ ] Dark mode fully functional
- [ ] Accessible: keyboard navigable, aria labels, reduced motion
- [ ] Core hooks and components have unit tests
- [ ] `npm run build` and `docker build` both pass
- [ ] Works with mock SSE (no backend dependency for development)

---
---

## Phase 2 — Sessions, Auth & Follow-ups (Days 8–14)

> **Deliverable:** Authenticated users have persistent session history, can ask follow-ups, and see a polished navigation shell. Anonymous users can still research.

---

#### Day 8 — AppShell + Session Sidebar

**Goal:** App has a layout shell with a collapsible session sidebar. Sessions load from API (or mock).

- [ ] Create `src/hooks/useSession.ts`:
  - `sessions[]`, `isLoading`, `fetchSessions()`, `getSession(id)`, `archiveSession(id)`, `renameSession(id, title)`
  - Fetches from `GET /api/v1/sessions` (with mock fallback)
- [ ] Create `components/layout/AppShell.tsx`:
  - Main layout wrapper: sidebar (left) + content area (right)
  - Sidebar width: `280px` on desktop, full-screen `Sheet` on mobile
  - Collapsible via toggle button
- [ ] Create `components/layout/SessionSidebar.tsx`:
  - "New Research" button at top (Lucide `Plus`)
  - Search/filter input
  - Session list grouped by date: "Today", "Yesterday", "This Week", "Older" (using `date-fns`)
  - Each item: title, date, query count badge
  - Click → navigates to `/session/[id]` or loads in main content
  - Ghost button variant for list items
  - `ScrollArea` for long lists
  - Desktop: collapsible; Mobile: `Sheet` drawer

**Checkpoint:**
- [ ] Sidebar lists sessions (from API or mock data)
- [ ] Sessions grouped by date correctly
- [ ] "New Research" navigates to home/landing
- [ ] Desktop: sidebar collapsible; Mobile: opens as Sheet
- [ ] Search/filter narrows the list

---

#### Day 9 — Session Detail Page + Follow-up Input

**Goal:** Clicking a past session loads its full conversation. Users can ask follow-ups.

**Morning — Session Detail Page:**
- [ ] Create `app/session/[id]/page.tsx`:
  - Fetches session from `GET /api/v1/sessions/{id}`
  - Displays full conversation: all turns in chronological order
  - Each turn: user query (styled as chat bubble / heading), synthesized answer (markdown), citations
  - Session metadata header: title, date, query count, sources used
  - Loading skeleton while fetching

**Afternoon — Follow-up Input:**
- [ ] Create `components/research/FollowUpInput.tsx`:
  - Compact input below completed answer: placeholder `"Ask a follow-up..."`
  - Submit sends to `POST /api/v1/research/{session_id}/followup`
  - New streamed answer appends below previous in conversation thread
  - Disabled while streaming
  - Props: `sessionId`, `isStreaming`, `onSubmit(query)`
- [ ] Wire follow-up into main research page:
  - After initial research completes → show `FollowUpInput`
  - On follow-up submit → stream new answer below, growing the conversation

**Checkpoint:**
- [ ] `/session/abc123` loads full conversation with all turns
- [ ] Follow-up input appears after research completes
- [ ] Follow-up answer streams below previous answer (conversation grows)
- [ ] Loading skeleton shows while session data loads

---

#### Day 10 — Auth UI: Login, Signup, UserMenu

**Goal:** Users can sign up, log in (email + GitHub), and log out. Auth state available app-wide.

- [ ] Create `src/lib/supabase.ts`: browser + server Supabase client initialization
- [ ] Create `src/hooks/useAuth.ts`:
  - `user`, `isLoading`, `isAuthenticated`
  - `signIn(email, password)`, `signUp(email, password)`, `signInWithGitHub()`, `signOut()`
- [ ] Create `components/auth/LoginForm.tsx`:
  - Email + password fields (React Hook Form + Zod validation)
  - "Sign in with GitHub" button
  - Link to signup page
  - Error messages for invalid credentials
- [ ] Create `components/auth/SignupForm.tsx`:
  - Email + password + confirm password
  - Password strength indicator (optional)
  - Link to login page
- [ ] Create `components/auth/UserMenu.tsx`:
  - Avatar + name in `DropdownMenu`
  - Items: Profile (placeholder), Settings, Logout
- [ ] Create `app/auth/login/page.tsx` — renders `LoginForm` centered
- [ ] Create `app/auth/signup/page.tsx` — renders `SignupForm` centered
- [ ] Create `app/auth/callback/route.ts` — Supabase OAuth redirect handler

**Checkpoint:**
- [ ] Signup → email confirmation → login works
- [ ] GitHub OAuth redirects and completes (if Supabase configured)
- [ ] `useAuth().isAuthenticated` reflects login state
- [ ] UserMenu shows avatar/email after login
- [ ] Logout clears session

---

#### Day 11 — Header + Mobile Nav + Protected Routes

**Goal:** Complete navigation shell. Protected routes redirect to login. Anonymous mode works.

- [ ] Create `components/layout/Header.tsx`:
  - Logo (left), dark mode toggle (Lucide `Sun`/`Moon`), UserMenu or "Sign in" button (right)
  - Clean, minimal top bar
- [ ] Create `components/layout/MobileNav.tsx`:
  - Hamburger button → opens `SessionSidebar` as `Sheet`
  - Visible only on mobile (<1024px)
- [ ] Wire `Header` + `MobileNav` + `SessionSidebar` into `AppShell`
- [ ] Implement anonymous mode:
  - Research works without auth → session stored in `localStorage` (ephemeral)
  - "Save this session" button prompts sign-in modal
  - Session sidebar hidden for unauthenticated users
- [ ] Create `middleware.ts` (Next.js middleware):
  - Protected routes: `/session/*`, `/knowledge`, `/dashboard`, `/settings/*`
  - Redirect unauthenticated → `/auth/login?redirect=<original_url>`
  - Unprotected: `/`, `/auth/*`

**Checkpoint:**
- [ ] Header renders logo + dark mode toggle + user menu (or "Sign in")
- [ ] Mobile: hamburger opens sidebar as Sheet
- [ ] Anonymous user: can research, no sidebar, "Sign in to save" CTA
- [ ] Authenticated user: sidebar visible, sessions load
- [ ] Navigating to `/dashboard` while logged out → redirects to `/auth/login`

---

#### Day 12 — Source Indicator Expansion + Frontend CI

**Goal:** All 5 sources have correct icons/colors. CI pipeline validates lint + build + test.

**Morning — Dynamic Source Support:**
- [ ] Update `SourceToggle` and `SourceIndicator` to support all 5 sources:
  - DuckDuckGo (`orange-500`, `Globe`)
  - Reddit (`red-500`, `MessageCircle`)
  - HackerNews (`amber-600`, `Flame`)
  - ArXiv (`blue-600`, `GraduationCap`)
  - Wikipedia (`slate-600`, `BookOpen`)
- [ ] Make source list dynamic: optionally fetch from `GET /api/v1/sources`
  - Fallback to hardcoded `constants.ts` if API unavailable

**Afternoon — CI Pipeline:**
- [ ] Create `.github/workflows/frontend-ci.yml`:
  ```yaml
  jobs:
    frontend:
      steps:
        - npm ci
        - npm run lint
        - npm run build
        - npx vitest run
  ```
- [ ] Verify pipeline passes locally before pushing
- [ ] Set branch protection: require CI pass on PRs

**Checkpoint:**
- [ ] All 5 sources render with correct icon and color in both SourceToggle and SourceIndicator
- [ ] CI pipeline runs lint + build + test on push
- [ ] CI passes with zero failures

---

#### Day 13 — Vercel Deployment + Production Smoke Test

**Goal:** Frontend deployed to Vercel. Works against production (or staging) backend API.

- [ ] **Vercel setup:**
  - Connect GitHub repo → auto-deploy `frontend/` directory
  - Root directory: `frontend`
  - Framework preset: Next.js
  - Environment variable: `NEXT_PUBLIC_API_URL=<backend_url>` (or mock service URL)
  - Environment variable: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] Verify `npm run build` passes on Vercel
- [ ] Test SSE streaming works over Vercel's edge network (potential buffering issues — may need `next.config.js` adjustments)
- [ ] Smoke test checklist:
  - [ ] Frontend loads at Vercel URL
  - [ ] Dark mode works
  - [ ] Research query streams answer (mock or real backend)
  - [ ] Auth flow works (signup, login, logout)
  - [ ] Session sidebar loads after auth
  - [ ] Follow-up input works
  - [ ] Mobile layout correct

**Checkpoint:**
- [ ] Frontend accessible at public Vercel URL
- [ ] All smoke tests pass
- [ ] No CORS errors or broken SSE connections

---

#### Day 14 — Phase 2 Buffer / Polish

**Goal:** Phase 2 complete. Navigation, auth, and sessions are rock-solid.

- [ ] Fix any bugs from the week
- [ ] Test full flow: anonymous research → sign up → see session saved → follow-up
- [ ] Run `npx vitest run` — all pass
- [ ] Run `npm run lint` — zero warnings
- [ ] Visual review on mobile (375px) and desktop (1440px)

**Checkpoint:**
- [ ] Phase 2 exit criteria met (below)

---

### Phase 2 Exit Criteria

- [ ] All 7 days (Days 8–14) completed
- [ ] Session sidebar loads, groups by date, click to view
- [ ] Session detail page shows full conversation
- [ ] Follow-up questions stream below previous answer
- [ ] Auth: signup, login, GitHub OAuth, logout all work
- [ ] Anonymous mode: research works, "sign in to save" prompt shown
- [ ] Protected routes redirect to login
- [ ] Deployed on Vercel
- [ ] CI pipeline passing

---
---

## Phase 3 — Knowledge Graph, Dashboard & Export (Days 15–24)

> **Deliverable:** Interactive knowledge graph, analytics dashboard, session export, scheduled research UI, and notification system.

---

#### Day 15 — D3.js Force-Directed Graph (Rendering)

**Goal:** Knowledge graph renders with nodes and edges. Entity types visually distinguishable.

- [ ] Create `src/hooks/useKnowledge.ts`:
  - Fetches graph data from `GET /api/v1/knowledge/graph` or `GET /api/v1/sessions/{id}/graph`
  - Returns: `graphData`, `isLoading`, `error`, `refetch()`
  - Mock data fallback: 30–50 entities with relationships for development
- [ ] Create `components/knowledge/KnowledgeGraph.tsx`:
  - D3.js `d3-force` simulation with collision detection
  - Nodes: circles sized by `mention_count`, colored by entity type
  - Entity type color palette:
    | Type | Color | Icon |
    |------|-------|------|
    | technology | `blue-500` | `Cpu` |
    | concept | `purple-500` | `Lightbulb` |
    | organization | `green-500` | `Building2` |
    | person | `orange-500` | `User` |
    | pattern | `teal-500` | `Layers` |
    | algorithm | `red-500` | `Binary` |
    | protocol | `cyan-500` | `Network` |
    | library | `pink-500` | `Package` |
    | service | `emerald-500` | `Cloud` |
  - Edges: lines labeled with relationship type, opacity weighted by confidence
  - Dynamic import D3.js (only on `/knowledge` — code splitting)

**Checkpoint:**
- [ ] Graph renders with nodes colored by type, sized by mentions
- [ ] Edges labeled with relationship types
- [ ] D3 bundle only loads on `/knowledge` page

---

#### Day 16 — D3.js Graph (Interaction)

**Goal:** Graph is fully interactive — drag, zoom, click, hover. Performant for 200 nodes.

- [ ] Add drag: click + drag repositions nodes
- [ ] Add zoom/pan: mouse wheel zooms, drag on background pans
- [ ] Add click: click node → opens `EntityDetail` panel (wired next day)
- [ ] Add hover: hover node → highlight connected edges and neighbor nodes, dim everything else
- [ ] Performance: switch to `<canvas>` rendering for >100 nodes
- [ ] Graph views (toggle buttons above graph):
  - Full graph — all entities
  - Session graph — filtered to specific session
  - Entity neighborhood — selected entity + 1-2 hop connections

**Checkpoint:**
- [ ] Drag, zoom, pan all smooth
- [ ] Hover highlights connections (rest dims)
- [ ] <1s render for 200 nodes
- [ ] View toggles work

---

#### Day 17 — Entity Detail Panel + Graph Controls + Legend

**Goal:** Clicking a node shows full entity details. Filter controls narrow the graph.

- [ ] Create `components/knowledge/EntityDetail.tsx`:
  - Slide-in `Sheet` panel on node click
  - Shows: entity name, type badge (colored), description
  - Stats: mention count, first seen date, last seen date
  - "Sessions" section: list of sessions where entity appears (links to `/session/[id]`)
  - "Related entities" section: directly connected entities (clickable → refocuses graph)
  - "Research more" button → navigates to `/` with entity name as prefilled query
- [ ] Create `components/knowledge/GraphControls.tsx`:
  - Entity type: checkboxes (filter by type)
  - Session: `Select` dropdown (show only entities from a session)
  - Min mentions: `Slider` (hide rarely-mentioned entities)
  - Filters apply reactively to the graph
- [ ] Create `components/knowledge/GraphLegend.tsx`:
  - Color legend for entity types (horizontal strip below graph)

**Checkpoint:**
- [ ] Click node → EntityDetail Sheet opens with all fields
- [ ] "Research more" prefills SearchBar and navigates home
- [ ] Type filters hide/show nodes
- [ ] Min mentions slider removes low-count nodes
- [ ] Legend clearly maps colors to types

---

#### Day 18 — Knowledge Page Assembly

**Goal:** `/knowledge` route is a complete, polished page.

- [ ] Create `app/knowledge/page.tsx`:
  - Layout: graph area (main) + controls sidebar (left or top) + entity detail (right Sheet)
  - Full graph loads by default
  - Controls collapse on mobile (behind a filter button)
  - Loading state while graph fetches
  - Empty state: "Start researching to build your knowledge graph"
- [ ] Responsive: graph takes full width, controls as drawer on mobile
- [ ] Performance: verify 200-node render in <1s
- [ ] Test: changing filters re-renders graph smoothly

**Checkpoint:**
- [ ] `/knowledge` page loads graph + controls + detail panel
- [ ] Mobile: graph fullscreen, controls in drawer
- [ ] Empty state shows for new users
- [ ] Visually compelling (portfolio screenshot quality)

---

#### Day 19 — Export Menu + Share Dialog

**Goal:** Sessions exportable. Sessions shareable via link.

**Morning — Export:**
- [ ] Create `components/shared/ExportMenu.tsx`:
  - `DropdownMenu` on session page header
  - Options: "Export as Markdown", "Export as JSON", "Export to Obsidian"
  - Markdown/JSON: `GET /api/v1/sessions/{id}/export?format=<fmt>` → trigger download via `<a download>` or `URL.createObjectURL`
  - Obsidian (knowledge-level): `GET /api/v1/knowledge/export?format=obsidian` → ZIP download

**Afternoon — Share:**
- [ ] Create `components/shared/ShareDialog.tsx`:
  - `Dialog` modal triggered by "Share" button on session page
  - Role selector: Viewer / Editor (shadcn `Select`)
  - "Generate Link" button → calls API → shows link
  - "Copy Link" button → clipboard
  - Shared session indicator: avatar pills of collaborators

**Checkpoint:**
- [ ] Export dropdown triggers file downloads for each format
- [ ] Share dialog generates link, copy-to-clipboard works
- [ ] Share link opens session for viewer

---

#### Day 20 — Dashboard: Activity Chart + Source Performance

**Goal:** `/dashboard` page with first two chart components.

- [ ] Create `app/dashboard/page.tsx` — layout with grid of chart cards
- [ ] Create `components/dashboard/ActivityChart.tsx`:
  - Recharts `LineChart` — queries per week (time series)
  - Responsive, dark-mode compatible colors
- [ ] Create `components/dashboard/SourcePerformance.tsx`:
  - Table: source name (with icon), avg latency (bar visualization), success rate %, circuit breaker status badge
  - Sortable columns
- [ ] Data from `GET /api/v1/analytics` (with mock fallback)
- [ ] Dynamic import Recharts (only on `/dashboard`)

**Checkpoint:**
- [ ] Activity chart renders with time series data
- [ ] Source performance table shows all 5 sources with stats
- [ ] Recharts bundle only loads on `/dashboard`

---

#### Day 21 — Dashboard: Cache Stats + Top Entities + Knowledge Stats

**Goal:** Dashboard complete with all 5 stat/chart components.

- [ ] Create `components/dashboard/CacheStats.tsx`:
  - Recharts `RadialBarChart` or custom progress ring — cache hit rate percentage
  - Shows: hit rate, avg hit latency, avg miss latency
- [ ] Create `components/dashboard/TopEntities.tsx`:
  - Recharts `BarChart` (horizontal) — top 10 entities by mention count
  - Colored by entity type
- [ ] Create `components/dashboard/KnowledgeStats.tsx`:
  - Stat cards (shadcn `Card`): total nodes, total edges, total sessions, growth trend
- [ ] Responsive grid: 2-column on desktop, single column on mobile
- [ ] Dashboard loading skeleton

**Checkpoint:**
- [ ] Dashboard loads in <2s with all 5 components
- [ ] All charts render with real or mock data
- [ ] Responsive: cards stack on mobile
- [ ] Loading skeleton shows while data fetches

---

#### Day 22 — Scheduled Research UI + Settings Page

**Goal:** Users can manage research schedules from settings.

- [ ] Create `app/settings/page.tsx`: general settings (theme preference, default sources — placeholder for now)
- [ ] Create `app/settings/schedules/page.tsx`:
  - Form to create schedule (React Hook Form + Zod):
    - Query template: text input
    - Topics: tag input (comma-separated or chip input)
    - Frequency: `daily` | `weekly` (shadcn `Select`)
    - Source selection: checkboxes
  - List existing schedules:
    - Each row: query template, frequency, last run, active/paused `Switch` toggle
    - Edit and delete actions
  - API: `POST/GET/PATCH/DELETE /api/v1/schedules`

**Checkpoint:**
- [ ] Create schedule via form → appears in list
- [ ] Edit, pause/resume, delete work
- [ ] Form validation catches empty fields, invalid frequency

---

#### Day 23 — Notification System

**Goal:** Notification bell in header with unread count and dropdown.

- [ ] Create `src/hooks/useNotifications.ts`:
  - Fetches from `GET /api/v1/notifications`
  - Polls every 60 seconds
  - `markAsRead(id)` → `PATCH /api/v1/notifications/{id}/read`
  - Returns: `notifications[]`, `unreadCount`, `markAsRead()`, `isLoading`
- [ ] Create `components/shared/NotificationBell.tsx`:
  - Bell icon (Lucide `Bell`) in header
  - Unread count badge (red dot with number)
  - `DropdownMenu` with list of recent notifications
  - Each notification: icon by type, title, body, timestamp
  - Click notification → navigate to relevant session/suggestion
  - Mark as read on click
- [ ] Wire into `Header` component

**Checkpoint:**
- [ ] Bell shows unread count
- [ ] Dropdown lists notifications
- [ ] Click navigates to relevant page
- [ ] Mark-as-read updates count

---

#### Day 24 — Phase 3 Buffer / Polish

**Goal:** Phase 3 features polished. All pages tested.

- [ ] Smoke test: knowledge graph, dashboard, exports, schedules, notifications
- [ ] Run full test suite, add new tests for Phase 3 components
- [ ] Visual review in dark mode
- [ ] Mobile responsiveness pass on all new pages
- [ ] Fix any remaining issues

**Checkpoint:**
- [ ] Phase 3 exit criteria met (below)

---

### Phase 3 Exit Criteria

- [ ] All 10 days (Days 15–24) completed
- [ ] Knowledge graph renders <1s with 200 nodes, interactive (drag/zoom/click/hover)
- [ ] Entity detail panel shows all fields with working navigation
- [ ] Graph filters work (type, session, min mentions)
- [ ] Dashboard shows 5 chart/stat components with real or mock data
- [ ] Export triggers file downloads (Markdown, JSON, Obsidian)
- [ ] Share dialog generates and copies link
- [ ] Scheduled research UI: create, edit, pause, delete
- [ ] Notification bell with unread count and dropdown
- [ ] All pages responsive and dark-mode compatible

---
---

## Phase 4 — Agent Reasoning UI & Final Polish (Days 25–30)

> **Deliverable:** Agent reasoning transparency, proactive suggestion cards, full accessibility audit, performance benchmarks, and production-ready documentation.

---

#### Day 25 — AgentThinking Component (Real-Time)

**Goal:** Users can watch the agent think during research via a collapsible panel.

- [ ] Create `components/agent/AgentThinking.tsx`:
  - Collapsible panel above the streaming answer (hidden by default)
  - "Show agent reasoning" toggle button (off by default, for power users)
  - Shows agent reasoning steps in real-time as `agent_*` SSE events arrive
  - Each step: icon + agent type badge + reasoning text + timestamp
  - Color-coded by agent type:
    | Agent | Color | Emoji |
    |-------|-------|-------|
    | Coordinator | `slate` | thinking |
    | Academic | `blue` | book |
    | Practitioner | `amber` | speech |
    | Fact-checker | `green` | check |
  - Steps appear with subtle fade-in animation
  - Each step expandable to show full reasoning text
  - Uses `Collapsible`, `Badge`, `ScrollArea` from shadcn
- [ ] Wire to `useResearch` hook: consume `agent_thinking`, `agent_action`, `agent_action_complete`, `agent_evaluation` events

**Checkpoint:**
- [ ] Toggle shows/hides reasoning panel
- [ ] Agent steps appear in real-time during research
- [ ] Color coding matches agent type
- [ ] Expandable for full reasoning text
- [ ] Hidden by default — clean UX for casual users

---

#### Day 26 — AgentTrace Component (Post-Research)

**Goal:** After research completes, users can explore the full agent decision timeline.

- [ ] Create `components/agent/AgentTrace.tsx`:
  - Timeline visualization of all agent iterations (post-research)
  - Fetches from `GET /api/v1/sessions/{id}/turns/{turn_id}/trace`
  - Each iteration shows: reasoning → action → result → confidence change
  - Decision tree: which agents dispatched and why
  - Expandable details for each step (shadcn `Collapsible` + `Card`)
  - Links from trace steps to specific citations in the answer
  - Visual: vertical timeline with connected cards
- [ ] Add "View Agent Trace" button on completed research (only if trace data available)

**Checkpoint:**
- [ ] Trace timeline renders with all iterations
- [ ] Each step expandable with full details
- [ ] Clicking trace step highlights relevant citation
- [ ] Clean fallback when no trace data available

---

#### Day 27 — Proactive Suggestion Cards + EmptyState Component

**Goal:** Dashboard shows proactive suggestions. Reusable empty state for all pages.

**Morning — Suggestion Cards:**
- [ ] Add suggestion section to `/dashboard`:
  - Fetch from `GET /api/v1/suggestions`
  - Each card: title, reasoning paragraph, suggested query, "Research Now" button
  - "Research Now" → `POST /api/v1/suggestions/{id}/execute` → navigate to `/` with streaming
  - Card types with icons: knowledge_gap (Lucide `CircleHelp`), stale_knowledge (`Clock`), incomplete_comparison (`GitCompare`)
- [ ] Update `NotificationBell` to include proactive suggestion notifications

**Afternoon — Reusable EmptyState:**
- [ ] Create `components/shared/EmptyState.tsx`:
  - Props: `icon`, `title`, `description`, `action?` (button)
  - Used on: knowledge graph (no entities), dashboard (no data), sessions (no history), schedules (none created)
- [ ] Apply to all pages that need empty states

**Checkpoint:**
- [ ] Suggestion cards render on dashboard with mock or real data
- [ ] "Research Now" triggers research
- [ ] EmptyState renders on all pages when no data

---

#### Day 28 — Performance Benchmarks + Optimization

**Goal:** All frontend performance targets met. Bundle optimized.

- [ ] Benchmark targets:
  | Metric | Target |
  |--------|--------|
  | First Contentful Paint (FCP) | <1.5s |
  | Largest Contentful Paint (LCP) | <2.5s |
  | Time to Interactive (TTI) | <3.5s |
  | Token rendering lag | <50ms after SSE event |
  | Knowledge graph (200 nodes) | <1s render |
  | Dashboard page load | <2s |
  | Initial JS bundle (gzipped) | <200KB |
- [ ] Run Lighthouse audit on all pages
- [ ] Optimization pass:
  - Verify D3.js dynamic import (only `/knowledge`)
  - Verify Recharts dynamic import (only `/dashboard`)
  - Lazy-load `CitationSidebar` on mobile (Sheet, not always rendered)
  - Use `next/image` for any static images
  - Virtualize session list if >100 sessions (`react-window`)
  - Minimize `react-markdown` plugins
- [ ] Document results

**Checkpoint:**
- [ ] Lighthouse Performance score ≥ 90 on home page
- [ ] All metrics within targets (or documented with explanation)
- [ ] No unnecessary bundles on pages that don't need them

---

#### Day 29 — Accessibility Audit + Final Visual Polish

**Goal:** WCAG AA compliance on all critical flows. Visual perfection.

**Morning — Accessibility:**
- [ ] Run `axe-core` audit on all pages (install `@axe-core/react` for dev)
- [ ] Verify keyboard navigation on every page:
  - Home: Tab to toggles → Enter to submit → Tab to follow-up
  - Knowledge: Tab to graph controls → Enter to apply
  - Dashboard: Tab through cards
  - Auth: Tab through form fields → Enter to submit
- [ ] Verify screen reader (VoiceOver):
  - Streaming text region announced with `aria-live="polite"`, `aria-atomic="false"`
  - Phase indicator announced
  - Citation links have `aria-label="Source N: <title>"`
  - Graph nodes have `aria-label` with entity name + type
- [ ] Check color contrast: 4.5:1 for normal text, 3:1 for large text
- [ ] Verify `prefers-reduced-motion` → all animations disabled
- [ ] Focus trapping: modals/dialogs trap focus, closing returns focus to trigger
- [ ] Fix all critical a11y violations

**Afternoon — Visual Polish:**
- [ ] Final dark mode review across all pages
- [ ] Smooth page transitions
- [ ] Consistent spacing and typography
- [ ] Toast notifications (shadcn `Sonner` or `Toast`) for: export complete, share link copied, session saved, errors

**Checkpoint:**
- [ ] Zero critical a11y violations from axe-core
- [ ] Full flow navigable with keyboard only
- [ ] Screen reader announces streaming text and phase changes
- [ ] Toast notifications for key user actions

---

#### Day 30 — Documentation + Screenshots + Demo

**Goal:** Frontend is presentation-ready. Portfolio-quality screenshots and documentation.

- [ ] Take screenshots of every major view (both light and dark mode):
  - Landing page with SearchBar
  - Research in progress: streaming answer + source indicators
  - Completed research with citations sidebar
  - Agent reasoning panel (expanded)
  - Knowledge graph with colorful nodes
  - Entity detail panel
  - Dashboard with charts
  - Session sidebar with history
  - Auth pages
- [ ] Update `frontend/README.md` with:
  - Setup instructions (dev + production)
  - Architecture overview (pages, components, hooks, lib)
  - API contract summary
  - Design system reference (colors, fonts, spacing)
- [ ] Record short demo (optional): screen recording of full research flow
- [ ] Final checks:
  - [ ] `npm run lint` — zero warnings
  - [ ] `npm run build` — zero errors
  - [ ] `npx vitest run` — all pass
  - [ ] Vercel deployment green

**Checkpoint:**
- [ ] All Phase 4 exit criteria met (below)
- [ ] Screenshots captured for portfolio
- [ ] Frontend README comprehensive
- [ ] Production deployment stable

---

### Phase 4 Exit Criteria

- [ ] All 6 days (Days 25–30) completed
- [ ] Agent reasoning panel shows real-time thinking (togglable)
- [ ] Agent trace timeline explorable post-research
- [ ] Proactive suggestion cards actionable on dashboard
- [ ] Lighthouse Performance ≥ 90
- [ ] Zero critical a11y violations
- [ ] All pages keyboard navigable
- [ ] Screenshots and documentation complete
- [ ] Production deployment stable on Vercel

---
---

## Project Completion Summary

```
Day 1-7     Phase 1: Core Research UI            query → streamed cited answer
Day 8-14    Phase 2: Sessions, Auth, Follow-ups  session history, auth, conversations
Day 15-24   Phase 3: Knowledge Graph + Dashboard  D3 graph, charts, export, schedules
Day 25-30   Phase 4: Agent UI + Final Polish      reasoning panel, a11y, performance

Total: 30 working days (~6 weeks)
```

---

## API Contracts & SSE Protocol Reference

> The frontend consumes these backend APIs. Use mock data when the backend isn't available.

### REST Endpoints

| Method | Endpoint | Response | Used By |
|--------|----------|----------|---------|
| `POST` | `/api/v1/research` | SSE stream | SearchBar → useResearch |
| `POST` | `/api/v1/research/{session_id}/followup` | SSE stream | FollowUpInput → useResearch |
| `GET` | `/api/v1/sessions` | `{ sessions: Session[] }` | SessionSidebar |
| `GET` | `/api/v1/sessions/{id}` | `SessionDetail` | Session page |
| `DELETE` | `/api/v1/sessions/{id}` | `204` | SessionSidebar |
| `PATCH` | `/api/v1/sessions/{id}` | `Session` | SessionSidebar (rename) |
| `GET` | `/api/v1/knowledge/graph` | `GraphData { nodes, edges }` | KnowledgeGraph |
| `GET` | `/api/v1/sessions/{id}/graph` | `GraphData { nodes, edges }` | KnowledgeGraph |
| `GET` | `/api/v1/knowledge/search?q=...` | `{ results[] }` | Knowledge page |
| `GET` | `/api/v1/analytics` | `AnalyticsData` | Dashboard |
| `GET` | `/api/v1/sources` | `{ sources: SourceConfig[] }` | SearchBar |
| `GET` | `/api/v1/sessions/{id}/export?format=markdown` | File download | ExportMenu |
| `GET` | `/api/v1/knowledge/export?format=obsidian` | ZIP download | ExportMenu |
| `POST` | `/api/v1/sessions/{id}/share` | `{ link, role }` | ShareDialog |
| `GET` | `/api/v1/suggestions` | `Suggestion[]` | Dashboard |
| `POST` | `/api/v1/suggestions/{id}/execute` | SSE stream | Suggestion card |
| `GET` | `/api/v1/notifications` | `Notification[]` | NotificationBell |
| `PATCH` | `/api/v1/notifications/{id}/read` | `204` | NotificationBell |
| `POST` | `/api/v1/schedules` | `Schedule` | Schedules page |
| `GET` | `/api/v1/schedules` | `Schedule[]` | Schedules page |
| `PATCH` | `/api/v1/schedules/{id}` | `Schedule` | Schedules page |
| `DELETE` | `/api/v1/schedules/{id}` | `204` | Schedules page |
| `GET` | `/api/v1/sessions/{id}/turns/{turn_id}/trace` | `AgentTrace` | AgentTrace |

### SSE Event Protocol

The `/research` and `/followup` endpoints return Server-Sent Events:

```
event: status
data: {"phase": "decomposing", "message": "Breaking query into sub-queries..."}

event: source_complete
data: {"source": "ddg", "results_count": 8, "latency_ms": 1200}

event: source_error
data: {"source": "reddit", "error": "Timeout", "circuit_breaker_open": false}

event: token
data: {"content": "Based on analysis of 24 sources...", "citations": []}

event: token
data: {"content": " Kafka excels at high-throughput [1][2]", "citations": [1, 2]}

event: complete
data: {"session_id": "sess_abc", "sources_used": 24, "latency_ms": 7800, "citations": [...]}

event: error
data: {"message": "Rate limit exceeded", "code": "RATE_LIMIT"}

event: agent_thinking
data: {"agent": "coordinator", "reasoning": "Complex comparison detected..."}

event: agent_action
data: {"agent": "academic", "action": "search", "sources": ["arxiv"], "queries": [...]}

event: agent_action_complete
data: {"agent": "academic", "action": "search", "results_count": 3, "duration_ms": 2100}

event: agent_evaluation
data: {"agent": "academic", "confidence": 0.62, "gaps": ["No data beyond 50K msgs/sec"]}
```

---

## Tech Stack Reference

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | Next.js 14 (App Router) | SSR, file-based routing, RSC |
| **Styling** | Tailwind CSS 3.4+ | Utility-first CSS |
| **Components** | shadcn/ui | Accessible, composable primitives |
| **Icons** | Lucide Icons (`lucide-react`) | Consistent icon set |
| **Markdown** | `react-markdown` + `remark-gfm` | Render streamed markdown |
| **SSE** | `eventsource-parser` | Parse Server-Sent Events |
| **Graph** | D3.js (`d3-force`) | Force-directed knowledge graph |
| **Charts** | Recharts | Dashboard charts |
| **Auth** | `@supabase/supabase-js` + helpers | Supabase Auth integration |
| **State** | React Context + `useReducer` | Client state management |
| **Forms** | React Hook Form + Zod | Form validation |
| **Date** | `date-fns` | Date formatting and grouping |
| **Testing** | Vitest + React Testing Library | Unit + integration tests |
| **Hosting** | Vercel (free tier) | Production deployment |

---

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                    # Root layout (theme, providers, AppShell)
│   │   ├── page.tsx                      # Home / research page
│   │   ├── knowledge/page.tsx            # Knowledge graph
│   │   ├── dashboard/page.tsx            # Analytics dashboard
│   │   ├── session/[id]/page.tsx         # Session detail
│   │   ├── settings/
│   │   │   ├── page.tsx                  # General settings
│   │   │   └── schedules/page.tsx        # Scheduled research
│   │   ├── auth/
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/page.tsx
│   │   │   └── callback/route.ts
│   │   ├── globals.css
│   │   └── middleware.ts                 # Protected route redirects
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── SessionSidebar.tsx
│   │   │   └── MobileNav.tsx
│   │   ├── research/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── SourceToggle.tsx
│   │   │   ├── SourceIndicator.tsx
│   │   │   ├── ResearchStream.tsx
│   │   │   ├── CitationCard.tsx
│   │   │   ├── CitationSidebar.tsx
│   │   │   ├── FollowUpInput.tsx
│   │   │   ├── PhaseIndicator.tsx
│   │   │   └── ResearchView.tsx
│   │   ├── knowledge/
│   │   │   ├── KnowledgeGraph.tsx
│   │   │   ├── EntityDetail.tsx
│   │   │   ├── GraphControls.tsx
│   │   │   └── GraphLegend.tsx
│   │   ├── agent/
│   │   │   ├── AgentThinking.tsx
│   │   │   └── AgentTrace.tsx
│   │   ├── dashboard/
│   │   │   ├── ActivityChart.tsx
│   │   │   ├── SourcePerformance.tsx
│   │   │   ├── CacheStats.tsx
│   │   │   ├── TopEntities.tsx
│   │   │   └── KnowledgeStats.tsx
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── SignupForm.tsx
│   │   │   └── UserMenu.tsx
│   │   ├── shared/
│   │   │   ├── NotificationBell.tsx
│   │   │   ├── ShareDialog.tsx
│   │   │   ├── ExportMenu.tsx
│   │   │   └── EmptyState.tsx
│   │   └── ui/                           # shadcn/ui generated
│   │
│   ├── hooks/
│   │   ├── useSSE.ts
│   │   ├── useResearch.ts
│   │   ├── useSession.ts
│   │   ├── useKnowledge.ts
│   │   ├── useAuth.ts
│   │   └── useNotifications.ts
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── supabase.ts
│   │   ├── constants.ts
│   │   ├── utils.ts
│   │   └── mock-sse.ts                   # Mock SSE for backend-less dev
│   │
│   └── types/
│       ├── research.ts
│       ├── session.ts
│       ├── knowledge.ts
│       └── agent.ts
│
├── public/
│   ├── logo.svg
│   └── og-image.png
│
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── vitest.config.ts
├── package.json
├── Dockerfile
└── .env.local.example
```

---

## Environment Variables

```bash
# .env.local.example

# Required
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase Auth (required for auth features, Phase 2+)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# Development
NEXT_PUBLIC_USE_MOCK=true                  # Use mock SSE when backend unavailable
```

---

*This roadmap is the single source of truth for frontend execution. Check off tasks as you complete them. Each checkpoint is a testable proof of progress. The backend is developed separately — use mock data until API endpoints are available.*
