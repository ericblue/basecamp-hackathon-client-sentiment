"""Contract smoke test. Not a unit suite - a liveness probe that answers
"did I just break someone else's lane?" Run it before any push that touches
backend/.

    python smoke_test.py [base_url]      default http://127.0.0.1:8000
"""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


def call(method, path, body=None):
    req = urllib.request.Request(
        BASE + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        return e.code, None


print(f"\n--- stub contract (the UI lane's dependency) --- {BASE}")
s, d = call("GET", "/stub/timeline")
check("GET /stub/timeline 200", s == 200)
check("stub timeline has messages", bool(d and d.get("messages")))
check("stub: no outbound carries a score",
      all(m.get("score") is None for m in (d or {}).get("messages", [])
          if m["direction"] == "outbound"))
check("stub: every scored message has a quote",
      all(m.get("quote") for m in (d or {}).get("messages", [])
          if m.get("score") is not None))

s, d = call("GET", "/stub/radar")
check("GET /stub/radar 200", s == 200)
check("stub radar has all four keys",
      bool(d) and all(k in d for k in ("trend", "contacts", "deadlines", "risks")))

s, d = call("POST", "/stub/brief")
check("POST /stub/brief 200", s == 200)
check("stub brief actions all cite", bool(d) and all(a["cites"] for a in d["actions"]))

s, _ = call("POST", "/stub/ingest", {"direction": "outbound", "date": "2026-05-25",
                                     "text": "ours",
                                     "contact": {"name": "Us", "role": "Lead", "org": "Us"}})
check("stub ingest REFUSES outbound (422)", s == 422, f"got {s}")

s, d = call("POST", "/stub/ingest", {"direction": "inbound", "date": "2026-05-25",
                                     "text": "I am copying our General Counsel.",
                                     "contact": {"name": "Dana", "role": "CFO", "org": "N"}})
check("stub ingest scores inbound", s == 200 and d["message"].get("score") is not None)

for p in ("/stub/scan", "/stub/alerts", "/stub/runs"):
    m = "POST" if p == "/stub/scan" else "GET"
    s, _ = call(m, p)
    check(f"{m} {p} 200", s == 200, f"got {s}")

print("\n--- live (first call scores the dataset; slow) ---")
s, d = call("GET", "/health")
check("GET /health 200", s == 200)
check("health exposes scan clock", bool(d) and "next_scan" in d)

s, d = call("GET", "/timeline")
if s == 503:
    print("  SKIP  live endpoints - no dataset under data/ (503)")
else:
    msgs = d["messages"]
    check("GET /timeline 200", s == 200)
    check("THE ONE RULE: no outbound message is scored",
          all(m.get("score") is None for m in msgs if m["direction"] == "outbound"),
          str([m["id"] for m in msgs if m["direction"] == "outbound" and m.get("score") is not None]))
    check("every scored message has a quote",
          all(m.get("quote") for m in msgs if m.get("score") is not None))
    check("every score is in range -1..1",
          all(-1.0 <= m["score"] <= 1.0 for m in msgs if m.get("score") is not None))
    check("every tone is a contract value",
          all(m["tone"] in {"positive", "neutral", "concerned", "frustrated", "escalating"}
              for m in msgs if m.get("tone")))
    ids = {m["id"] for m in msgs}
    check("message ids are unique", len(ids) == len(msgs))

    s, r = call("GET", "/radar")
    check("GET /radar 200", s == 200)
    check("radar mentions reference real message ids",
          all(mid in ids for dl in r["deadlines"] for mid in dl["mentions"])
          and all(mid in ids for rk in r["risks"] for mid in rk["mentions"]))
    check("trend weeks are ordered", [t["week"] for t in r["trend"]] == sorted(t["week"] for t in r["trend"]))

    s, b = call("POST", "/brief")
    check("POST /brief 200", s == 200)
    check("brief returns a summary", bool(b) and len(b.get("summary", "")) > 40)
    check("brief returns 3 actions", bool(b) and len(b.get("actions", [])) == 3,
          f"got {len(b.get('actions', [])) if b else 0}")
    check("brief cites resolve to real messages",
          bool(b) and all(c in ids for a in b["actions"] for c in a["cites"]))

    s, sc = call("POST", "/scan")
    check("POST /scan 200", s == 200)
    s, sc2 = call("POST", "/scan")
    check("scan is idempotent (no new, no alerts)",
          bool(sc2) and not sc2["new_messages"] and not sc2["alerts"])

    s, _ = call("POST", "/ingest", {"direction": "outbound", "date": "2026-05-25", "text": "ours",
                                    "contact": {"name": "Us", "role": "Lead", "org": "Us"}})
    check("live ingest REFUSES outbound (422)", s == 422, f"got {s}")

print(f"\n  {ok} passed, {fail} failed\n")
sys.exit(1 if fail else 0)
