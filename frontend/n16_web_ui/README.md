# N16 Web UI Module (Next.js)

N16 is the primary frontend for Travel Experience Planner. It is a Next.js 15 / React 19 web application built with the App Router, Tailwind CSS, and shadcn/ui. It replaced the legacy Streamlit UI (N7) and communicates exclusively with the Flask backend (N8).

## Responsibilities

- Provide the main user-facing interface for travel planning
- Collect user input through a multi-step Wizard (questionnaire + free-text + image upload)
- Call N8 API endpoints and progressively render ranked results
- Lazy-load location images independently of the main data response
- Manage global session state (auth, results, activity lists) via Zustand
- Provide an Explore mode (`/explore`) to browse all available locations
- Provide a Profile page (`/profile`) for registration, login, and recommendation history
- Handle feedback loops: refine recommendations and activity lists via N8 feedback endpoints

## Tech Stack

| Layer            | Technology                             |
| ---------------- | -------------------------------------- |
| Framework        | Next.js 15 (App Router)                |
| UI Library       | React 19                               |
| Styling          | Tailwind CSS + shadcn/ui               |
| State management | Zustand (`src/store/planner-store.ts`) |
| Language         | TypeScript                             |
| Testing          | Vitest                                 |

---

## Getting Started

Install dependencies and start the development server:

```bash
npm install
npm run dev
```

The app runs at [http://localhost:3000](http://localhost:3000).

For a full-stack startup (backend + frontend together), use the project root script:

```bash
# Windows
run.bat

# Linux / macOS
./run.sh
```

---

## Directory Structure

```
frontend/n16_web_ui/src/
├── app/
│   ├── (planner)/          # Main planner flow
│   │   ├── page.tsx        # Input Wizard (questionnaire + prompt + image upload)
│   │   └── results/        # Results page (ranked locations + activity drawers)
│   ├── explore/            # Explore Grid — browse all locations
│   ├── profile/            # Auth (register/login) + recommendation history
│   ├── feedback/           # Feedback page
│   ├── about/              # About page
│   └── api/                # Next.js API Routes (proxy / auth / images)
│       ├── activities/
│       ├── auth/
│       ├── feedback/
│       ├── images/
│       ├── locations/
│       ├── profile/
│       └── recommend/
├── components/
│   ├── app-shell/          # Layout shell and navigation
│   ├── auth/               # Login / register forms
│   ├── explore/            # Explore grid cards
│   ├── header/             # Top nav
│   ├── input/              # Wizard steps, tag chips, image uploader
│   ├── map/                # Map view component
│   ├── result/             # Location cards, activity drawers, feedback panels
│   └── ui/                 # shadcn/ui primitives
├── hooks/                  # Custom React hooks
├── lib/                    # API client functions, utility helpers
└── store/
    └── planner-store.ts    # Zustand store — global app state
```

---

## User Flows

### 1. Planner Flow (main path)

1. User opens `/(planner)` — the Wizard Slider collects:
   - **Questionnaire**: preference chips (travel style, budget, time)
   - **Free-text prompt**: natural language description of the desired trip
   - **Image upload**: optional inspiration image (processed by N2 vision)
2. On submit, N16 calls `POST /recommend` via the Next.js API route proxy
3. While waiting, skeleton loaders are shown
4. On response, ranked location cards are rendered immediately; image URLs are lazy-loaded by the browser as cards scroll into view
5. Activity drawers are opened per-location on demand via `POST /activities/v2`
6. A global feedback panel allows users to refine the full result list via `POST /feedback/recommend`
7. Each location card has a local feedback button for activity refinement via `POST /feedback/activities`

### 2. Explore Mode (`/explore`)

- Calls `POST /locations` to load all available locations as slim cards
- Each card shows the location name, a thumbnail, and tags
- No AI ranking — purely a browse interface for the database

### 3. Profile & History (`/profile`)

- **Register / Login** via `POST /api/auth/register` and `POST /api/auth/login`
- After login, `user_id` is stored in Zustand state (client-side session)
- Recommendation history is fetched via `GET /api/profile/history/{user_id}` and displayed as a list of past trips
- Clicking a past trip reloads its full result into the planner store

---

## State Management

All cross-page state lives in the Zustand store at `src/store/planner-store.ts`:

| State key              | Purpose                                           |
| ---------------------- | ------------------------------------------------- |
| `wizardInput`          | Captured questionnaire + prompt + image payload   |
| `locations`            | Ranked location results from `/recommend`         |
| `activitiesByLocation` | Per-location activity lists from `/activities/v2` |
| `user`                 | Authenticated user info (`user_id`, `username`)   |
| `history`              | Recommendation history list                       |
| `isLoading`            | Global loading flag for skeleton rendering        |

---

## API Communication

N16 communicates with N8 through **Next.js API Routes** (`src/app/api/`). These routes act as a proxy layer that:

- Attaches the `X-Internal-Key` header (kept server-side, never exposed to the browser)
- Forwards request bodies to the Flask backend
- Streams or returns JSON responses to the client

This keeps the internal API key out of client-side bundles.

Backend base URL is configured via `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
INTERNAL_API_KEY=your_secret_key
```

---

## Image Loading Strategy

N16 uses a pure lazy-loading model for location images:

1. `/recommend` returns only image URL strings: `/api/images/{location_id}_{idx}.jpg`
2. Next.js `<Image>` components use those URLs with `loading="lazy"`
3. Each image is fetched from the Next.js image proxy → N8 → PostgreSQL only when the card enters the viewport
4. Missing images return a 1×1 transparent PNG fallback — no broken image icons

This eliminates the need to wait for large image blobs before rendering the results page.

---

## Running Tests

```bash
npm run test
```

Tests use Vitest. Configuration is in `vitest.config.ts`.

---

## Runtime Notes

- `next.config.ts` configures image domains and any rewrites needed for the backend proxy
- `components.json` holds shadcn/ui component configuration
- Husky pre-commit hooks run Prettier formatting checks (`.husky/`)
- Service worker registered via `src/app/sw.ts` for offline/caching support
- `CLAUDE.md` and `AGENTS.md` contain brief notes for AI coding assistants working in this repo
