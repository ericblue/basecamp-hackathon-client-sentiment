# Client Sentiment Radar: divide and conquer

Four people, sixty minutes, four lanes. Each lane has an owner, a deliverable, the minute it must hand off, and what it needs from the others. Names to be filled in at the table. The contract in the PRD is the only shared dependency; freeze it first.

## The clock

| Minute | Everyone |
|---|---|
| 0 to 5 | Create the shared GitHub repo, paste the PRD in as README, agree the data contract, pick lanes. One Slack or WhatsApp thread for handoffs. |
| 10 | Stub endpoints live (Lane B). UI starts building against them (Lane C). Dataset first draft committed (Lane A). |
| 30 | Scoring live on real data (Lane B). Dataset final (Lane A). UI shows stub data end to end (Lane C). |
| 40 | UI flips to live API. Routine fires by hand against the tunnel URL and an alert lands. Integration fixes only. |
| 50 | Freeze. Rehearse the demo twice (Lane D drives). |
| 60 | Demo. |

## Lane A: Data and scenario

Owner: one Deloitte dev (the one closest to the client-side story; HR or Workday domain knowledge is an asset here).

Deliverable: the synthetic engagement. One fictional client, one project (a Workday rollout works well for this team), six weeks, with a deliberate arc: warm, then a missed deadline, then a cooling CFO, then partial recovery. About 25 to 30 emails in four or five threads (mark each inbound or outbound), three meetings stored as arrays of turn records in the `Message` shape (six to ten client turns each, `direction` set per speaker, `meeting` and `seq` on every turn; see the README), and `engagement.json` with contacts, deadlines, milestones and risks. Every risk and deadline should be mentioned by at least two client messages so the roll-up has something to join.

Method: write the arc and the cast on paper first (ten minutes), then have Claude generate the messages from that outline in the contract's JSON shape, one call per thread and one call per meeting ("write this meeting as an array of turn records in this shape"). Do not hand-write emails or prose transcripts.

Hands off: a first ten messages by minute 10 so Lane B can score real text; the full set by minute 30.

Needs: the contract (minute 5).

## Lane B: Backend and scoring

Owner: Eric.

Deliverable: FastAPI app with `/stub/*` first, then `/timeline`, `/radar`, `/brief`, `/ingest` live. One scoring function with a JSON schema and a short rubric; only inbound messages and client transcript turns are scored. In-memory cache. CORS open so the UI can call it from Vite's dev port.

Order: stubs with canned data (minute 10), scoring on Lane A's first ten messages (minute 20), ingest and roll-ups (minute 30), brief (minute 40). Ingest is not cuttable: the routine depends on it. Also: start a tunnel (`cloudflared tunnel --url http://localhost:8000`) as soon as the stubs are up and post the public URL in the chat so Lane D can point the routine at it.

Hands off: stub URLs at minute 10, live base URL at minute 40.

Needs: the contract; Lane A's messages.

## Lane C: UI

Owner: one or two Deloitte devs (two if three are available; split trend plus contacts from feed plus brief).

Deliverable: single-page app, Vite plus React plus TypeScript, four components: trend line with deadline and meeting markers, contact temperature grid, message feed with tone chips and driving quotes (outbound messages shown greyed, unscored), and a brief panel with a Brief me button and an ingest box. Built entirely against `/stub/*` until minute 40; the base URL is one constant.

Method: generate the scaffold with Claude Code from the contract in the README; a chart library like Recharts is fine; do not spend time on styling past readable.

Hands off: end to end on stub data at minute 30; live at minute 40.

Needs: stub endpoints (minute 10).

## Lane D: Always-on routine, demo, and plugin stretch

Owner: the remaining Deloitte dev, or shared by whoever finishes first.

Deliverable, in priority order:

1. The always-on routine (PRD section 5a): a Claude Routine that on each run pulls new messages from the repo, calls `POST /ingest`, diffs `GET /radar`, and posts an alert (Slack webhook or `alerts.json` in the repo) when a contact turns escalating or the weekly average drops. Build it against the stub URL first, switch to the tunnel URL when Lane B posts it. Must be fireable by hand by minute 40. This is what makes the project an always-on agent; it is not optional.
2. The two-minute demo script, written by minute 30, with the exact clicks, the one hostile email committed from a second laptop, and the routine fired live. This lane owns rehearsal at minute 50.
3. The pitch line for the judges: who the user is, what it replaces, why "client words only" is the right scope, what the always-on version looks like (scheduled run, Slack post).
4. Stretch, only if lanes B and C are green by minute 45: an MCP plugin exposing `radar_status`, `radar_brief`, `radar_ingest` over the backend, scaffolded with `mcp-plugin-pattern` so it loads in Claude Code and Cowork. Demo it as one question asked from Claude Code: "How is the Acme account feeling this week?"

Hands off: script at minute 30, rehearsal at minute 50.

Needs: nothing to start; the live API for the stretch.

## Rules for the hour

- Contract changes go in the shared thread with a one-line reason, and only before minute 30.
- Anything not demoing by minute 45 is cut, not fixed.
- Commit small and often to the shared repo; one branch per lane, merge to main at the handoff minutes.
- The demo shows one engagement, one arc, one live ingest. Resist adding a second scenario.
