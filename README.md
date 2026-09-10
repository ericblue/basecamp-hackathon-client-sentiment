# Client Sentiment Radar

An always-on agent that reads a client's own words across an engagement (emails, meeting transcripts) and shows the account lead where the temperature is, where it is heading, and which deadlines and risks it is tied to. Built in 60 minutes at the Anthropic Partner Base Camp Agent Hackathon, San Francisco, September 10, 2026.

Track: Always-on agent. Team: Eric Blue (Andela, backend) with three Deloitte developers (data, UI, routine and demo).

![Radar dashboard](docs/mockup-1-dashboard.png)

## The idea in one paragraph

Account leads find out a client is unhappy late, when it reaches an escalation email or a steering committee. The signal was there earlier, spread across threads and transcripts nobody reads end to end. The radar scores every client message on a schedule, rolls it up into a trend, a per-contact temperature and a list of at-risk deadlines, and writes a cited Monday brief. A plugin lets anyone ask it questions from Claude Code or Cowork. One rule throughout: sentiment is measured on what the client says; our own replies are context for the brief, never signal for the score.

## Docs

| Doc | What it is |
|---|---|
| [PRD and tech spec](docs/PRD-and-Tech-Spec.md) | Problem, scope rule, MVP capabilities, demo, architecture, the data contract everyone builds against, model use, risks |
| [Workstreams](docs/Workstreams.md) | The hour split into four lanes (data, backend, UI, routine and demo) with a shared clock and handoff minutes |
| [Data lane guide](docs/Data-Lane-Guide.md) | How to change the dataset without breaking the backend: the converter, the field mapping, and the three things that silently break it |
| [Plugin use cases](docs/Plugin-Use-Cases.md) | The six plugin tools and ten question-and-answer examples, plus what the plugin refuses to do |
| [Architecture](docs/architecture.png) | End to end: sources, data repo, backend, the always-on routine and alert, the UI and plugin. v0.1, to be updated with what was built |
| [Mockup: dashboard](docs/mockup-1-dashboard.png) | The single-page radar UI |
| [Mockup: plugin](docs/mockup-2-plugin.png) | The same intelligence asked from Claude Code and Cowork |

## Architecture

![Architecture](docs/architecture.png)

```
data/                      synthetic engagement: emails/*.json, transcripts/*.json (turn records), engagement.json
backend/  (FastAPI)        scores client messages with Claude (structured output), caches, serves:
                           GET /timeline  GET /radar  POST /brief  POST /ingest  GET /stub/*
ui/       (Vite+React+TS)  trend line, contact grid, message feed, brief panel; one base URL
plugin/   (MCP, stretch)   radar_status, radar_contact, radar_search, radar_brief, radar_ingest, radar_diff
routine/                   the always-on half: a Claude Routine that on a schedule pulls new messages from data/,
                           calls POST /ingest, diffs GET /radar, and posts an alert (Slack or alerts.json)
                           when a contact turns escalating or the weekly average drops. Essential, not stretch.
```

The routine is the unattended half; the UI and plugin are the on-demand half. The backend is reached from the routine through a tunnel (`cloudflared tunnel --url http://localhost:8000`) during the hackathon. See the PRD, section 5a.

## Data contract

Frozen at minute 10. Everything builds against these shapes; see the PRD for the full version.

```
Message   { id, thread_id, kind, direction: inbound|outbound, contact{name,role,org}, date, subject?, text,
            score?, tone?: positive|neutral|concerned|frustrated|escalating, quote?, refs?[] }
Engagement{ client, project, contacts[], deadlines[{id,title,due,status}], risks[{id,title,severity}] }
Radar     { trend[{week,avg_score,n}], contacts[{name,role,temperature,last_quote}],
            deadlines[{...,at_risk,mentions[]}], risks[{...,mentions[]}] }
Brief     { summary, actions[{text, cites[]}] }
```

Only `direction: inbound` messages get `score`, `tone` and `quote`.

Transcripts are stored pre-split as turn records in the same `Message` shape, not as whole files: `kind: "transcript_turn"`, `thread_id` = the meeting id, plus `meeting: {title, date}` denormalised on each turn and `seq` for order. A client's turn is `direction: inbound`, ours is `outbound`, so the scorer filters transcripts exactly the way it filters email. The data lane generates each meeting as an array of turns in one Claude call; a readable transcript, if wanted for the demo, is rendered from the turns rather than stored twice.

## Live URLs

| What | URL | Notes |
|---|---|---|
| API | https://client-sentiment-radar.onrender.com | Render. Free tier sleeps; warm it before demoing. |
| Dashboard (tunnel) | https://b383d7c8be98.ngrok.app | ngrok to the local static preview. Serves the page; data comes from the API above. |

The tunnel forwards to the UI preview server, not the backend, so `/health` and
`/radar` are not on it. That still works: the page probes its own origin for the
API, does not find one, and falls back to the Render URL. To put both on one
origin, point ngrok at the FastAPI port instead — it serves the dashboard at `/`
and the API alongside it.

## Running it

Get an Anthropic key from the Base Camp key server (see above) and put it in
`backend/.env` as `ANTHROPIC_API_KEY`.

```bash
# backend — serves the API *and* the dashboard at /
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
# dashboard:  http://localhost:8000/
# stub data:  http://localhost:8000/stub/radar
# live:       http://localhost:8000/radar
```

The dashboard is a single static file (`ui/index.html`) with no build step — no
npm, no bundler. FastAPI serves it at `/`. To preview it on its own instead:

```bash
cd ui && python -m http.server 5173
# then http://localhost:5173/?api=http://localhost:8000
```

It picks its API in this order: an explicit `?api=...`, else the same origin when
FastAPI is serving it, else the deployed Render URL. If live data is unreachable
it falls back to `/stub/*` and labels itself `(stub)` rather than passing canned
numbers off as real.

Regenerate `data/` after the data lane pushes (see [Data lane guide](docs/Data-Lane-Guide.md)):

```bash
cd backend && python convert_data.py
```

Check nothing is broken — 31 contract checks against any deployment:

```bash
cd backend && python smoke_test.py https://client-sentiment-radar.onrender.com
```

Plugin: `.mcp.json` at the repo root loads the MCP server in Claude Code; set
`RADAR_API_BASE` there to point it at a different backend. See
[plugin/README.md](plugin/README.md).

## Demo (two minutes)

1. Open the radar on the Northwind Retail engagement: warm in weeks one and two, a dip after the missed May 19 migration deadline, the CFO in red.
2. Click the dip, read the driving quote.
3. Press Brief me, read the three cited actions.
4. Paste in a new escalating email, watch the line drop and the brief change.
5. Switch to Claude Code: "How is the Northwind account feeling this week?"
6. From a second laptop, commit one new escalating email to `data/emails/` and fire the routine. The alert lands in Slack (or the banner appears) with nobody touching the dashboard; open the dashboard and the line has already moved.
7. Close: in production this runs every morning against the shared mailbox.

## Status

Hackathon scaffold. Synthetic data only; no mailbox or calendar integration, no auth, in-memory state. See the PRD's out-of-scope list.
