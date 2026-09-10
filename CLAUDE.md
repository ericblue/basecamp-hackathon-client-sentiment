# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

Docs-only scaffold. `README.md` and `docs/` describe a system that has **not been written yet** — there is no `backend/`, `ui/`, `data/`, or `plugin/` directory on disk. When asked to build here, create those trees to match the architecture below rather than inventing a different layout, and don't assume any code exists.

This is a 60-minute hackathon build (Anthropic Partner Base Camp, San Francisco, 2026-09-10), four people in four lanes. `docs/Workstreams.md` owns the minute-by-minute clock and lane boundaries; `docs/PRD-and-Tech-Spec.md` is the spec of record.

## The one rule that shapes everything

**Sentiment is scored only on what the client says.** Inbound emails and client speaker turns in transcripts get `score`, `tone`, and `quote`. Outbound (our own) messages are read for context in the brief but never carry a score — the UI greys them, the plugin refuses to score them. Any code that scores an outbound message is a bug, not a feature.

## Data contract (frozen)

All four lanes build against these shapes. Changing them mid-build breaks three other people, so treat them as fixed unless the user explicitly re-opens the contract.

```
Message   { id, thread_id, kind: "email"|"transcript_turn", direction: "inbound"|"outbound",
            contact{name,role,org}, date, subject?, text,
            score?: number (-1..1), tone?: positive|neutral|concerned|frustrated|escalating,
            quote?: string, refs?: string[] }   // refs are engagement.json risk/deadline ids
Engagement{ client, project, contacts[], deadlines[{id,title,due,status}], risks[{id,title,severity}] }
Radar     { trend[{week,avg_score,n}], contacts[{name,role,temperature,last_quote}],
            deadlines[{...deadline, at_risk, mentions[]}], risks[{...risk, mentions[]}] }
Brief     { summary, actions[{text, cites[]}] }
```

Message ids follow `E-14` (email) / `T-3` (transcript turn); every brief action and plugin answer cites them.

## Architecture

```
data/       synthetic engagement — emails/*.json, transcripts/*.md, engagement.json
backend/    FastAPI + Anthropic SDK; scores, caches in memory, serves the contract
ui/         Vite + React + TS single page; one API base-URL constant
plugin/     MCP server (stretch) over the same backend
```

Two decisions that the code has to preserve:

- **`GET /stub/*` mirrors every live endpoint with canned data.** It exists so the UI never blocks on the model or on the dataset. Build stubs before live handlers; keep the stub shapes byte-compatible with the live ones. The UI flips from stub to live by changing one base URL (`VITE_API_BASE`), not by editing components.
- **State is process memory only.** Scoring results are cached in-process; there is no database, no auth, no persistence across restarts. That is deliberate (see the PRD's out-of-scope list), not a gap to fill.

Endpoints: `GET /timeline`, `GET /radar`, `POST /brief`, `POST /ingest`, `GET /stub/*`. CORS must be open for Vite's dev port.

`POST /ingest` is the always-on story in miniature — one new message in, re-score, roll-ups and brief move. The unattended half is a scheduled job hitting `/ingest` for anything new in `data/`.

## Model use

Sonnet with a JSON schema (structured output) for scoring — one call per client message at startup (~20, cached), one per ingest, one per brief. Low effort on scoring; Haiku is an acceptable swap for scoring if latency bites, but the brief stays on Sonnet. Prompt-cache the engagement context used by the brief.

Runs from the Basecamp venv with the existing Anthropic key in `backend/.env`.

## Commands

Nothing is installed yet; these are the intended commands from the README.

```bash
# backend
cd backend && pip install -r requirements.txt
uvicorn app:app --reload --port 8000     # stub: localhost:8000/stub/radar   live: /radar

# ui
cd ui && npm install && npm run dev       # localhost:5173
```

Note: Eric prefers Yarn generally, but the README specifies npm for this repo's UI lane — follow the README here so the four lanes stay identical.

Plugin scaffolding uses the `mcp-plugin-pattern` generator (`make new NAME=client-sentiment-radar`) rather than a hand-rolled layout, so the same server loads in both Claude Code and Cowork.

## Working conventions for this repo

- **Cut, don't chase.** Anything not demoing by minute 45 gets removed from the demo path. The plugin is the first thing to cut; ingest is second.
- One branch per lane, merged at the handoff minutes (10 / 30 / 40).
- Six plugin tools are specified in `docs/Plugin-Use-Cases.md` (`radar_status`, `radar_contact`, `radar_search`, `radar_brief`, `radar_ingest`, `radar_diff`) — that doc also fixes the refusal behaviors: never score our own messages, never emit a tone label without the quote behind it, always stamp answers with the last-scan timestamp.
- The demo is one engagement, one arc, one live ingest. Don't add a second scenario.

## Orchestration
Dev-loop policy for this project is declared in @ORCHESTRATION.md
