# Client Sentiment Radar - MCP plugin

Ask the radar questions from Claude Code without opening the dashboard.

## Load it

`.mcp.json` at the repo root already points at this server. Open the repo in
Claude Code and approve the server when prompted, then ask:

> How is the Meridian account feeling this week?

## Point it at a deployed backend

The server runs locally and talks to the backend over HTTP. To use a local backend instead of the deployed one, change one
Render deployment instead of localhost, change one variable in `.mcp.json`:

```json
"env": { "RADAR_API_BASE": "http://127.0.0.1:8000" }
```

## Tools

| Tool | What it answers |
|---|---|
| `radar_status` | Per-contact temperature with the driving quote, the trend, at-risk deadlines. Optional `contact` narrows it. |
| `radar_brief` | The account brief plus actions, each citing message ids. |
| `radar_ingest` | Add one client message, score it, report how the radar moved. |

## What it refuses

- **Scoring our own messages.** `radar_ingest` with `direction: "outbound"`
  is refused, not silently scored.
- **A tone with no quote.** A tone label is only ever printed alongside the
  client's own words; without a quote it says the label is unevidenced.
- **Answering without a timestamp.** Every response is stamped with the last
  scan time, so nobody reads a stale number as current.

## Why it is hand-rolled

CLAUDE.md calls for the `mcp-plugin-pattern` generator. That generator was
not available at the table, and the `mcp` Python SDK could not be installed
(its `cryptography` dependency needs a Rust toolchain). MCP is line-delimited
JSON-RPC over stdio, so this is stdlib-only with nothing to install. It
speaks the standard protocol, so it should load in any MCP client - though
only Claude Code has been verified.
