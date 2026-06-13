# Cortex — frontend

A premium React + Vite interface for the Enterprise AI Knowledge Copilot:
streaming chat, auto-routed agents with reasoning traces, an interactive
force-directed knowledge graph, document library, and long-term memory.

## Prerequisites

- **Node.js 18+** (LTS recommended) — https://nodejs.org
- The backend running on **http://localhost:8000** (see the project root README)

## Run it

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

The dev server proxies every `/api` request to the backend on port 8000, so you
don't need to configure CORS for local development. If your backend runs
elsewhere, set `VITE_API_TARGET`, e.g.:

```bash
VITE_API_TARGET=http://localhost:9000 npm run dev
```

## First steps in the UI

1. **Create an account** (this also creates your organization).
2. You'll be prompted to **create a workspace**.
3. Go to **Knowledge Graph → Load sample org graph** to see the interactive
   visualization immediately — drag nodes, hover to focus, click to inspect,
   and use the search box to trace relationships.
4. Try **Chat** (streaming answers) and flip to **Agents** to watch a request
   get routed to the research / SQL / graph specialist with a full reasoning
   trace.

> With the backend's `fake` LLM/embedding settings, answers are deterministic
> placeholder text — the routing, citations, graph, and streaming are all real.
> Set `LLM_BACKEND=anthropic` (+ `ANTHROPIC_API_KEY`) on the backend for real
> prose.

## Build for production

```bash
npm run build      # outputs to dist/
npm run preview    # serve the built app locally
```

## Stack

- React 18 + Vite 5 + TypeScript
- `d3-force` for the knowledge-graph simulation
- `lucide-react` for icons
- Server-Sent Events (read via `fetch`) for streaming chat
