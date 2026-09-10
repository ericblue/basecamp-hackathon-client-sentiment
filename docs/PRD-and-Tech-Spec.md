# Client Sentiment Radar

PRD and tech spec, v0.1. Base Camp Agent Hackathon, Sep 10, 2026. Team: Eric Blue (backend) plus three Deloitte developers. Timebox: 60 minutes to a two-minute demo. Keep everything below at the level needed to divide the work; details get decided in the lane that owns them.

## 1. Problem

Account leads on services engagements find out a client is unhappy late, usually when it reaches an escalation email or a steering committee. The signal was there earlier, spread across email threads and meeting transcripts, but nobody reads all of it and nobody tracks the trend. Client Sentiment Radar reads the client's own words across an engagement and shows where the temperature is, where it is heading, and which deadlines and risks it is tied to.

Scope rule: sentiment is measured on what the client says (inbound email, client turns in transcripts). The company's own replies are context for the brief, not signal for the score.

## 2. Users and the moment

Primary user: the engagement or account lead, Monday morning, before the weekly client call. Secondary: the delivery lead who needs to know which contact is cooling and why.

## 3. What it does (MVP, in the hour)

1. Ingest a folder of engagement communications: client emails, meeting transcripts, and an engagement file with deadlines, milestones, risks, and contacts.
2. Score each client message (inbound email or a client's turn in a transcript): sentiment score (-1 to 1), tone label (positive, neutral, concerned, frustrated, escalating), the one quote that drove the score, and any deadline or risk it references.
3. Roll up: trend over time, temperature per client contact, risks and deadlines with the messages that mention them.
4. Brief: one paragraph of "what the account lead should know" plus three recommended actions, each citing the messages behind it.
5. Live ingest: drop in a new message and watch the radar move.
6. Always-on scan (essential, not stretch): a Claude Routine that runs on a schedule with nobody asking, pulls anything new, scores it, and reaches out when something moved. See section 5a. Without this the project is a query tool; with it, it is the track.

Stretch, only if the MVP is demoing by minute 45: a plugin surface so the same radar can be asked questions from Claude Code and Cowork.

## 4. Demo (two minutes)

Open on the radar for one fictional engagement over six weeks: warm early, a dip after a missed migration deadline, the client CFO in red. Click the dip and read the driving quote. Press Brief me, read the three actions. Paste in a new angry email, watch the line drop and the brief change. Close with: this runs on a schedule against the shared mailbox and posts to Slack every morning.

## 5. Architecture

Four parts, each buildable alone against a fixed contract: the data repo, the backend, the UI, and the always-on routine (section 5a). The plugin is a stretch on top.

Data repo. A folder (pushed to a GitHub repo so it matches the Track 1 pattern): `emails/*.json`, `transcripts/*.json`, `engagement.json`. Synthetic, one fictional client, one engagement, a deliberate tone arc. Transcripts are stored pre-split as turn records in the same `Message` shape as emails (one JSON array per meeting), not as prose files. This keeps the scorer to one input type, makes "client words only" a filter on `direction` rather than a parsing job, and gives the UI nothing new to render: a turn is an email row with a meeting title where the subject would be.

Backend. Python, FastAPI, Anthropic SDK, running from the Basecamp venv with the existing key. One scoring function using structured outputs (JSON schema) on Sonnet; results cached in memory so the UI is fast. Endpoints:

- `GET /timeline` every item, scored if client-authored, with direction, contact, tone, score, quote, linked risk or deadline ids
- `GET /radar` weekly trend, per-contact temperature, risks and deadlines joined to messages
- `POST /brief` the paragraph plus three cited actions
- `POST /ingest` accept one new message, score it, update the roll-ups
- `GET /stub/*` the same shapes with canned data, live from minute 10, so the UI never waits on the model

UI. Single page, Vite plus React plus TypeScript (Eric's standard scaffold), four components: trend line with meeting and deadline markers, contact grid, message feed with tone chips and quotes, brief panel. Reads the stub first, flips to live by changing one base URL.

Plugin (stretch). An MCP server exposing `radar_status`, `radar_brief`, and `radar_ingest` as tools over the same backend, packaged so it loads in both Claude Code and Cowork. Use the `mcp-plugin-pattern` scaffold (`make new NAME=client-sentiment-radar`) rather than a hand layout.

## 5a. The always-on half: a Claude Routine

The UI and the plugin are reactive: they answer when a person asks. The always-on track requires a trigger nobody presses. That trigger is a Claude Routine (a scheduled task) rather than a poll loop inside the backend, because the routine is the production shape (it is what the Track 1 README means by "point your routine at this repo") and because it demonstrates the pattern the room was taught.

What the routine does on each run:

1. Pull: read the engagement data source for anything new since the last run (for the hackathon, the `data/` folder in the GitHub repo; in production, the shared mailbox and transcript store).
2. Score: call `POST /ingest` for each new client message, so scoring logic lives in one place.
3. Compare: call `GET /radar` and diff against the last run.
4. Reach out: if any contact crossed into escalating, or the weekly average fell by more than 0.3, post an alert with the driving quote and the message ids. Otherwise, on the daily run, post the Monday-style brief from `POST /brief`.
5. Record: write a one-line run log (time, new messages, alerts fired) so the UI can show "last scan 07:02, next 08:00".

Where it posts: Slack channel `#northwind-account` if a webhook is available; otherwise a `alerts.json` in the repo that the UI renders as a banner. Either is fine for the demo; the point is that the message appears without a click.

Schedule: hourly during the demo window (or fire it manually once on stage), daily at 07:00 in the production story.

Reachability, the one gotcha: a cloud-hosted routine cannot call `localhost:8000`. Two options, pick one at the table: (a) expose the backend through a tunnel (`cloudflared tunnel --url http://localhost:8000` or ngrok) and give the routine that URL; (b) run the routine as a local scheduled task on Eric's Mac, where localhost is reachable. Option (a) is cleaner for the demo because the routine then looks exactly like production.

Demo moment: commit one new escalating email to `data/emails/` from a second laptop, fire the routine, and let the alert land in Slack (or the banner appear) while nobody touches the dashboard. Then open the dashboard and show the line already moved.

## 6. Data contract (the thing everyone builds against)

```
Message {
  id, thread_id, kind: "email" | "transcript_turn",
  direction: "inbound" | "outbound",
  contact: { name, role, org },
  date, subject?, text,
  meeting?: { title, date },   // transcript_turn only, denormalised on each turn
  seq?: number,                // transcript_turn only, order within the meeting
  score?: number,        // only when direction == inbound
  tone?: "positive"|"neutral"|"concerned"|"frustrated"|"escalating",
  quote?: string,
  refs?: string[]        // ids from engagement.json risks/deadlines
}
Engagement {
  client, project, contacts[], deadlines[{id,title,due,status}], risks[{id,title,severity}]
}
Radar {
  trend[{week, avg_score, n}], contacts[{name, role, temperature, last_quote}],
  deadlines[{...deadline, at_risk, mentions[]}], risks[{...risk, mentions[]}]
}
Brief { summary, actions[{text, cites[]}] }
```

Freeze this by minute 10. Anything not in it is decided by the lane that needs it and announced in the shared thread.

## 7. Model use

Sonnet with a JSON schema for scoring; one call per client message at startup (about 20 calls, cached), one call per ingest, one call per brief. Effort low on scoring. Prompt caching on the engagement context for the brief. Haiku is fine for scoring if latency matters; keep Sonnet for the brief.

## 8. Out of scope for the hour

Real mailbox or calendar integration, authentication, persistence beyond process memory, multi-engagement, anything mobile.

## 9. Risks

- Time: the UI is the long pole; it must start against the stub at minute 10, not against the live API.
- Scoring quality: a single prompt with a clear rubric and two examples is enough for a demo; do not iterate the rubric past minute 35.
- Plugin: only if the demo is safe; it is the first thing to cut. The routine is not cuttable; if time is short, fire it by hand on stage rather than on a schedule, but it must exist.
- Routine reachability: decide tunnel versus local scheduled task by minute 15; a routine that cannot reach the backend is the most likely demo failure.
- No shared repo: create one in the first five minutes and put the contract in its README.
