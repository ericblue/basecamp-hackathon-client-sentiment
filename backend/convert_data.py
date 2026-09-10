"""Convert the data lane's format into the frozen contract, into data/.

Michael generates Meridian Holdings in his own shape (docs/data.json plus
engagement.json at the repo root). The contract everyone else builds against
is different in almost every field name, and its transcripts are pre-split
turn records rather than prose. Rather than teach the backend a second
schema, this converts once and writes contract-shaped files into data/.

Re-run it whenever the data lane pushes:  python convert_data.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DATA = ROOT / "docs" / "data.json"
SRC_ENGAGEMENT = ROOT / "engagement.json"
OUT = ROOT / "data"

CLIENT_DOMAIN = "meridianholdings.com"

SPEAKER = re.compile(r"(?:^|(?<=\s))((?:[A-Z][A-Z'.\-]*)(?:\s[A-Z][A-Z'.\-]*)*):\s")


def _name_from_email(addr: str) -> str:
    local = addr.split("@")[0]
    return " ".join(p.capitalize() for p in re.split(r"[._]", local) if p)


def _is_client(addr: str) -> bool:
    return CLIENT_DOMAIN in (addr or "").lower()


def convert() -> dict:
    src = json.loads(SRC_DATA.read_text())
    eng_src = json.loads(SRC_ENGAGEMENT.read_text())

    # Only CLIENT-side contacts count. engagement.json also lists our own
    # people ("Engagement Lead", "Engagement Team"); if those land in the
    # lookup, our own transcript turns get scored as the client's words -
    # which is the one thing this system must never do.
    roles = {
        c["name"]: c.get("title", "Client contact")
        for c in eng_src.get("contacts", []) if c.get("org") == "client"
    }

    def contact_for(name: str, client: bool) -> dict:
        if not client:
            return {"name": name or "Engagement Team", "role": "Engagement Lead", "org": "Us"}
        return {"name": name, "role": roles.get(name, "Client contact"), "org": eng_src["client"]}

    emails: list[dict] = []
    turns: list[dict] = []
    e_no = t_no = 0

    for w in src["workstreams"]:
        ws = w["id"]

        for mail in w.get("emails", []):
            e_no += 1
            client = _is_client(mail.get("from", ""))
            emails.append({
                "id": f"E-{e_no}",
                "thread_id": f"TH-{ws}",
                "kind": "email",
                "direction": "inbound" if client else "outbound",
                "contact": contact_for(_name_from_email(mail.get("from", "")), client),
                "date": mail["date"],
                "subject": mail.get("subject"),
                "text": mail.get("body", ""),
            })

        for meeting in w.get("meetings", []):
            # Prose transcript -> turn records. Speakers are "NAME:" at the
            # start or mid-string; split on that boundary and keep order.
            excerpt = meeting.get("transcript_excerpt", "")
            # A speaker label is a run of ALL-CAPS words followed by a colon,
            # and must start the string or follow whitespace - without the
            # lookbehind, "OKAFOR:" also matches at "FOR:".
            labels = list(SPEAKER.finditer(excerpt))
            seq = 0
            for i, mt in enumerate(labels):
                speaker = mt.group(1).strip()
                end = labels[i + 1].start() if i + 1 < len(labels) else len(excerpt)
                said = excerpt[mt.end():end].strip()
                if not said:
                    continue
                seq += 1
                t_no += 1
                # Our side is labelled by role ("ENGAGEMENT LEAD"), the client
                # by surname. Anything matching a known client surname is theirs.
                match = next((n for n in roles if speaker.title() in n or n.split()[-1].upper() == speaker), None)
                client = match is not None
                turns.append({
                    "id": f"T-{t_no}",
                    "thread_id": f"M-{ws}-{meeting['date']}",
                    "kind": "transcript_turn",
                    "direction": "inbound" if client else "outbound",
                    "contact": contact_for(match or speaker.title(), client),
                    "date": meeting["date"],
                    "meeting": {"title": meeting.get("title", "Meeting"), "date": meeting["date"]},
                    "seq": seq,
                    "text": said,
                })

    engagement = {
        "client": eng_src["client"],
        "project": eng_src.get("engagement_name", eng_src["client"]),
        "contacts": [
            {"name": c["name"], "role": c.get("title", ""), "org": eng_src["client"]}
            for c in eng_src.get("contacts", []) if c.get("org") == "client"
        ],
        "deadlines": [
            {"id": d["id"], "title": d["title"],
             "due": d.get("due_date") or d.get("due", ""), "status": d.get("status", "open")}
            for d in eng_src.get("deadlines", [])
        ],
        "risks": [
            {"id": r["id"], "title": r["title"], "severity": r.get("severity", r.get("status", "open"))}
            for r in eng_src.get("risks", [])
        ],
    }

    (OUT / "emails").mkdir(parents=True, exist_ok=True)
    (OUT / "transcripts").mkdir(parents=True, exist_ok=True)
    (OUT / "engagement.json").write_text(json.dumps(engagement, indent=2))
    (OUT / "emails" / "all.json").write_text(json.dumps(emails, indent=2))
    (OUT / "transcripts" / "all.json").write_text(json.dumps(turns, indent=2))

    return {
        "emails": len(emails),
        "inbound_emails": sum(e["direction"] == "inbound" for e in emails),
        "turns": len(turns),
        "inbound_turns": sum(t["direction"] == "inbound" for t in turns),
        "contacts": len(engagement["contacts"]),
        "deadlines": len(engagement["deadlines"]),
        "risks": len(engagement["risks"]),
    }


if __name__ == "__main__":
    for k, v in convert().items():
        print(f"  {k:16} {v}")
