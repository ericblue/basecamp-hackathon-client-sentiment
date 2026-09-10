"""Client Sentiment Radar - MCP server.

Hand-rolled JSON-RPC over stdio rather than the mcp SDK: the SDK pulls
cryptography, which needs a Rust toolchain we do not have at the table.
MCP is line-delimited JSON-RPC on stdin/stdout, so stdlib is enough and
there is nothing to install.

Three tools over the same backend the dashboard uses, so the plugin can
never disagree with the screen.

Refusal behaviours (docs/Plugin-Use-Cases.md), enforced here, not hoped for:
  - never score our own messages
  - never emit a tone label without the quote behind it
  - always stamp the answer with the last-scan time
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.getenv("RADAR_API_BASE", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = float(os.getenv("RADAR_TIMEOUT", "180"))

TONES = {"positive", "neutral", "concerned", "frustrated", "escalating"}


def api(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read() or "null"), None
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read() or "{}").get("detail", "")
        except Exception:
            pass
        return None, f"backend returned {e.code}. {detail}"
    except Exception as e:
        return None, f"cannot reach the radar backend at {BASE}: {e}"


def stamp(d):
    ts = (d or {}).get("last_scan")
    return f"\n\n_Last scan: {ts}_" if ts else "\n\n_Last scan: never - the radar has not run yet._"


def tone_line(m):
    """Never a tone without the quote behind it."""
    tone, quote = m.get("tone"), m.get("quote")
    if tone and tone in TONES and quote:
        return f"{tone} ({m.get('score')}) - \"{quote}\""
    if tone and not quote:
        return f"{tone} (score {m.get('score')}) - no quote recorded, so this label is not evidenced"
    return "unscored"


# --- tools ------------------------------------------------------------------

def radar_status(args):
    contact = (args.get("contact") or "").strip().lower()
    radar, err = api("GET", "/radar")
    if err:
        return err
    health, _ = api("GET", "/health")

    rows = radar["contacts"]
    if contact:
        rows = [c for c in rows if contact in c["name"].lower()]
        if not rows:
            known = ", ".join(c["name"] for c in radar["contacts"])
            return f"No contact matching '{args.get('contact')}'. Known contacts: {known}."

    out = ["**Client sentiment**", ""]
    for c in rows:
        q = f' - "{c["last_quote"]}"' if c.get("last_quote") else " - no quote on file"
        out.append(f"- **{c['name']}** ({c['role']}): {c['temperature']:+.2f}{q}")

    if not contact and radar.get("trend"):
        t = radar["trend"]
        out += ["", f"Trend: {t[0]['week']} {t[0]['avg_score']:+.2f} -> "
                    f"{t[-1]['week']} {t[-1]['avg_score']:+.2f} over {len(t)} weeks."]
        at_risk = [d for d in radar.get("deadlines", []) if d.get("at_risk")]
        if at_risk:
            out.append("At-risk deadlines: " + ", ".join(f"{d['title']} (due {d['due']})" for d in at_risk))
    return "\n".join(out) + stamp(health)


def radar_brief(args):
    brief, err = api("POST", "/brief")
    if err:
        return err
    health, _ = api("GET", "/health")
    out = ["**Account brief**", "", brief["summary"], "", "**Recommended actions**"]
    if not brief.get("actions"):
        out.append("- No action could be evidenced against a specific message, so none is offered.")
    for i, a in enumerate(brief["actions"], 1):
        out.append(f"{i}. {a['text']}  [{', '.join(a['cites'])}]")
    return "\n".join(out) + stamp(health)


def radar_ingest(args):
    text = (args.get("text") or "").strip()
    if not text:
        return "Nothing to ingest: 'text' is required."

    direction = (args.get("direction") or "inbound").lower()
    if direction != "inbound":
        return ("Refused: the radar scores only what the client says. Our own "
                "messages are context for the brief, never signal for the score.")

    payload = {
        "direction": "inbound",
        "kind": args.get("kind") or "email",
        "date": args.get("date") or "2026-09-10",
        "subject": args.get("subject"),
        "text": text,
        "contact": {
            "name": args.get("contact_name") or "Unknown client contact",
            "role": args.get("contact_role") or "Client contact",
            "org": args.get("contact_org") or "Client",
        },
    }
    res, err = api("POST", "/ingest", payload)
    if err:
        return err
    m = res["message"]
    lines = [f"Scored **{m['id']}** from {m['contact']['name']}: {tone_line(m)}"]
    radar = res.get("radar") or {}
    if radar.get("trend"):
        lines.append(f"Latest week now {radar['trend'][-1]['avg_score']:+.2f}.")
    hot = [c for c in radar.get("contacts", []) if c["temperature"] <= -0.6]
    if hot:
        lines.append("Cold contacts: " + ", ".join(f"{c['name']} ({c['temperature']:+.2f})" for c in hot))
    return "\n".join(lines) + stamp(res)


TOOLS = [
    {
        "name": "radar_status",
        "description": "How the client feels right now: per-contact temperature with the "
                       "quote driving it, the multi-week trend, and any at-risk deadlines. "
                       "Optionally narrow to one contact.",
        "inputSchema": {
            "type": "object",
            "properties": {"contact": {"type": "string",
                                       "description": "Optional contact name or partial name."}},
        },
        "_fn": radar_status,
    },
    {
        "name": "radar_brief",
        "description": "The account brief: what the lead should know, plus recommended "
                       "actions, each citing the message ids behind it.",
        "inputSchema": {"type": "object", "properties": {}},
        "_fn": radar_brief,
    },
    {
        "name": "radar_ingest",
        "description": "Add one new client message, score it, and report how the radar "
                       "moved. Refuses our own outbound messages by design.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The message body."},
                "contact_name": {"type": "string"},
                "contact_role": {"type": "string"},
                "contact_org": {"type": "string"},
                "subject": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "kind": {"type": "string", "enum": ["email", "transcript_turn"]},
                "direction": {"type": "string", "enum": ["inbound", "outbound"]},
            },
            "required": ["text"],
        },
        "_fn": radar_ingest,
    },
]


# --- JSON-RPC over stdio ----------------------------------------------------

def reply(rid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": rid}
    msg["error" if error else "result"] = error or result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method, rid = req.get("method"), req.get("id")

        if method == "initialize":
            reply(rid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "client-sentiment-radar", "version": "0.1"},
            })
        elif method in ("notifications/initialized", "initialized"):
            continue                      # notification: no id, no reply
        elif method == "tools/list":
            reply(rid, {"tools": [{k: v for k, v in t.items() if not k.startswith("_")}
                                  for t in TOOLS]})
        elif method == "tools/call":
            params = req.get("params") or {}
            tool = next((t for t in TOOLS if t["name"] == params.get("name")), None)
            if not tool:
                reply(rid, error={"code": -32602, "message": f"unknown tool {params.get('name')}"})
                continue
            try:
                text = tool["_fn"](params.get("arguments") or {})
            except Exception as e:
                text = f"Tool failed: {type(e).__name__}: {e}"
            reply(rid, {"content": [{"type": "text", "text": text}]})
        elif method == "ping":
            reply(rid, {})
        elif rid is not None:
            reply(rid, error={"code": -32601, "message": f"method not found: {method}"})


if __name__ == "__main__":
    main()
