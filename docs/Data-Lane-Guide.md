# Data lane: how to change the dataset without breaking the build

For Mike. Short version: **your data no longer feeds the backend directly — it goes through a converter.** Generate in whatever shape you like, run one command, and the rest of the team stays unblocked.

```bash
cd backend
python convert_data.py     # reads your files, writes contract-shaped data/
```

Run that after every change, commit the `data/` output alongside your source files, and nothing downstream breaks. If you skip it, the backend keeps serving the previous dataset and your new messages silently never appear.

---

## Why a converter exists

The four lanes build against a frozen contract (CLAUDE.md, PRD §6). Your files use different field names for the same things, and the backend validates strictly — a mismatch isn't a degraded result, it's a hard failure to load. Rather than teach the backend a second schema (which would mean the UI and routine lanes get a second schema too), `backend/convert_data.py` translates once.

**What it reads:** `docs/data.json` and `engagement.json` (repo root).
**What it writes:** `data/emails/all.json`, `data/transcripts/all.json`, `data/engagement.json`.

Don't hand-edit anything under `data/` — it's generated and will be overwritten.

---

## Field mapping

| Contract wants | Your files have | Handled by converter |
|---|---|---|
| `text` | `body` | ✅ |
| `direction: "inbound"` / `"outbound"` | `"client"`, or inferred from sender domain | ✅ |
| `contact: {name, role, org}` | `contact_id`, or a bare email address | ✅ |
| `role` | `title` | ✅ |
| `seq` | `sequence` | ✅ |
| `meeting: {title, date}` | `meeting_id` | ✅ |
| `due` | `due_date` | ✅ |
| pre-split transcript turn records | prose `transcript_excerpt` | ✅ (split on speaker labels) |
| `refs: []` (risk/deadline ids) | `related_risk_ids`, `related_deadline_ids` | ⚠️ **not wired** — see below |

---

## Three things that will silently break it

These are real failures hit while converting your current data, not hypotheticals.

### 1. Speaker labels in transcripts

Turns are split on `ALLCAPS:` followed by a space. A label must start the line or follow whitespace.

```
✅  OKAFOR: The runbook was the best I've seen.
✅  ENGAGEMENT LEAD: Glad to hear it.
❌  Okafor: mixed case is not recognised as a speaker
❌  ...the DELTA QBR. VASQUEZ: said...   ← "QBR." parses as a speaker
```

Avoid ALL-CAPS abbreviations followed by a colon inside dialogue — one turn in your current data ("QBR.") became a phantom speaker. It fails safe (the turn is treated as ours and left unscored) but you lose a client quote.

### 2. Our own people must **not** be `org: "client"`

`engagement.json` lists `Engagement Lead` and `Engagement Team` as contacts. That's fine and useful — but they must keep a non-`client` `org` value, exactly as they have now.

This is load-bearing. The entire product rests on one rule: **sentiment is scored only on what the client says.** The converter decides inbound vs outbound by checking `org == "client"`. If one of our own people is tagged as a client, our own words get scored as client sentiment — which is the single worst bug this system can have. Please don't change those entries.

### 3. Client email addresses drive direction

For `docs/data.json`, direction is inferred from the sender's domain: `@meridianholdings.com` → inbound, anything else → outbound. If the client's domain changes, tell me and I'll update `CLIENT_DOMAIN` in the converter.

---

## What the dataset still needs

Ranked by how much it costs the demo.

1. **Outbound emails.** All 15 emails are currently client→us. The UI has a feature that greys our own replies as context-not-signal, and the brief reads our replies to see what we promised — with no outbound emails, neither has anything to show. Transcripts do have our turns, so it's not invisible, but a few outbound email replies would make the feed look real.
2. **Deadline mentions.** `docs/Workstreams.md` asks that every risk and deadline be referenced by at least two client messages, so the roll-up has something to join. Right now no deadline has any message tied to it, so "at-risk deadlines" is empty on the dashboard. Two fixes, either works: mention the deadline explicitly in the message text (the scorer will tie it), or add `related_deadline_ids` to your records and tell me — the converter doesn't map that field yet, and wiring it is a five-minute change.
3. **Pick one source file.** There are three overlapping formats right now: `docs/data.json`, `docs/emails/atlas.json`, and root `engagement.json`. The converter uses `docs/data.json` + `engagement.json` because that pair is complete (all four workstreams, 15 emails, 8 meetings). `docs/emails/atlas.json` is currently ignored. If you'd rather that be the canonical shape, say so and I'll repoint the converter — but two sources of truth will drift within the hour.

---

## Before you push

- [ ] `cd backend && python convert_data.py` runs without error
- [ ] The counts it prints look right (currently: 15 emails, 24 turns, 4 contacts, 3 deadlines, 7 risks)
- [ ] `inbound_turns` is **not** 0 and **not** equal to `turns` — if either, speaker attribution broke
- [ ] Commit both your source files and the regenerated `data/`
- [ ] Pull `main` into your branch first; it moves fast

## A note on scope

CLAUDE.md says *"The demo is one engagement, one arc, one live ingest. Don't add a second scenario."* You've built four workstreams with four separate arcs, which is more material than the two-minute demo can show — the trend line currently zigzags because it averages four unrelated stories together. This isn't wasted work, and nothing needs deleting. But the demo will likely feature **Delta alone** (it has the clearest decline and the strongest quotes), so if you have time to deepen one workstream rather than broaden all four, Delta is the one.
