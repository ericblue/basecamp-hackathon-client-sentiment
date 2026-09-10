# Client Sentiment Radar: plugin use cases

What people can ask the radar from Claude Code or Cowork once the plugin is installed, and what comes back. Every answer cites the client messages behind it (email ids like E-14, transcript turns like T-3), and every answer is about what the client said, never about our own replies. Mockup: `mockup-2-plugin.png`.

## Why this is an always-on agent

The radar has two halves. A scheduled scan reads the shared mailbox and transcript folder every morning, scores anything new from the client, updates the trend, and posts a brief when something moved. The plugin is the on-demand half: a person asks a question in the tool they already have open, and the answer comes from the same scored store. Neither half needs the other to be watched. That is the always-on pattern: unattended reading of a growing source, evidence-backed alerts, and a way for humans to interrogate it without opening another app.

## Tools the plugin exposes

| Tool | What it does | Backed by |
|---|---|---|
| `radar_status(engagement, window?)` | Current temperature, trend, top contacts, at-risk deadlines | `GET /radar` |
| `radar_contact(name)` | One contact's trajectory and the quotes that moved it | `GET /timeline` filtered |
| `radar_search(query)` | Client messages matching a topic, risk, or deadline | `GET /timeline` filtered |
| `radar_brief(audience?, contact?)` | The Monday brief, or a brief scoped to one contact or one meeting | `POST /brief` |
| `radar_ingest(text or file)` | Score a new client message or transcript and update the roll-ups | `POST /ingest` |
| `radar_diff(since)` | What changed since a date or since the last brief | `GET /radar` compared |

## Use cases, as question and answer

### 1. Monday morning temperature check

Ask: "How is the Northwind account feeling this week?"

Get: a one-line verdict (cooling, stable, warming), the weekly average against kickoff, the event the change followed, two or three contacts with their tone and driving quote, and the deadline most at risk. About eight lines. The account lead reads it in the elevator.

### 2. Prepare for a specific call

Ask: "I have the steering call with Dana Whitfield at 2. What do I need to know?"

Get: her trajectory over the engagement (neutral to escalating, with the date it turned), her last three quotes, the deadline she has tied her position to, what she asked for that has not been answered, and one suggested opening line. Cites the emails and the transcript turn.

### 3. Find the pattern behind a complaint

Ask: "Marcus keeps saying we repeat defects. Is that fair?"

Get: every client message mentioning defects or rework, in order, with the count of distinct issues versus repeated ones, and whether the repeats cluster on one workstream (cost center mapping). The answer is evidence, not opinion; the lead decides whether it is fair.

### 4. Deadline risk from the client's point of view

Ask: "Which deadlines is the client worried about?"

Get: deadlines ranked by client mentions and tone, not by our project plan status. Payroll parallel run sign-off might be "on track" in the plan and "at risk" in the client's words; the radar shows the gap.

### 5. Score something new before replying

Ask: "Here is the email Dana just sent. How bad is it?" (paste the text)

Get: score, tone, the sentence that drove it, what changed versus her last message, and whether it references a known risk. Then, optionally: "Draft a reply that addresses the payroll variance," which the assistant writes with the radar context in hand.

### 6. Delta since the last brief

Ask: "Did anything change since Monday's brief?"

Get: only the new client messages, each with before and after tone, and a one-line net read (delivery signal improving, executive signal not). This is the question that makes the scheduled scan worth having.

### 7. Contrast contacts

Ask: "Who on the client side is still positive?"

Get: the contacts sorted by temperature with their most recent quote, and a note on who could act as an ally for re-baselining. Useful before deciding who to call first.

### 8. Meeting debrief

Ask: "Summarize how the client came across in yesterday's recovery plan call."

Get: client turns only, scored, with the moments the tone shifted and who shifted it. Our side's talk time is excluded from the read.

### 9. Write it up for someone else

Ask: "Give me three bullets for the partner update on Northwind."

Get: three cited bullets in the partner's register: where sentiment is, why, and what we are doing about it. Same underlying brief, different audience.

### 10. Push it somewhere

Ask: "Post the brief to #northwind-account and set a reminder to re-check after Thursday's call."

Get: confirmation, the next scheduled scan time, and the reminder. This is where the plugin stops being a query tool and starts being part of the workflow.

## What the plugin refuses to do

- Score our own messages. It will read them for context, but the number is always about the client.
- Guess a contact's mood without a quote. Every tone label carries the sentence behind it.
- Answer from stale data without saying so. Every answer carries the timestamp of the last scan.

## Demo line for the judges

"The dashboard is what you look at on Monday. The plugin is what you ask on Wednesday, from the tool you already have open. The scheduled scan is what makes both of them true without anyone remembering to run it."
