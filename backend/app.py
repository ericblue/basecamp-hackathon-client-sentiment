"""Client Sentiment Radar — API. Owned by the backend lane.

Layout of this file: stubs first, then live handlers, because that is the
build order and the stubs are the contract everyone else builds against.

Boot does no work: no model calls, no data loading, no scoring at import
time. Render's health check hits /health and must get an answer immediately.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import scoring
import stub_data
from models import Alert, Brief, IngestRequest, Message, Radar, RunRecord, ScanResult

app = FastAPI(title="Client Sentiment Radar", version="0.1")

# Wide open on purpose: Vite's dev port, someone else's laptop, and whatever
# host the UI ends up deployed on. There is no auth and no private data here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Render's health check. Never touches data or the model."""
    return {
        "ok": True,
        "last_scan": scoring.last_scan(),
        "next_scan": scoring.next_scan(),
        "runs": len(scoring.runs()),
    }


# --- stubs (live from minute 10) -------------------------------------------

@app.get("/stub/timeline")
def stub_timeline() -> dict:
    return {"engagement": stub_data.ENGAGEMENT, "messages": stub_data.TIMELINE}


@app.get("/stub/radar")
def stub_radar() -> dict:
    return stub_data.RADAR


@app.post("/stub/brief")
def stub_brief() -> dict:
    return stub_data.BRIEF


@app.post("/stub/ingest")
def stub_ingest(msg: IngestRequest) -> dict:
    """Echoes back a plausibly scored message so the UI can build the ingest
    box before scoring is live. Outbound is refused here exactly as it is on
    the live endpoint — the one rule holds in the stub too."""
    if msg.direction != "inbound":
        raise HTTPException(422, "outbound messages are never scored")
    return {
        "message": {
            **msg.model_dump(exclude_none=True),
            "id": msg.id or "E-99",
            "score": -0.82,
            "tone": "escalating",
            "quote": msg.text.strip()[:120],
            "refs": ["D-2"],
        },
        "radar": stub_data.RADAR,
    }


@app.post("/stub/scan")
def stub_scan() -> dict:
    """A canned scan that always looks like the demo moment: one new
    escalating message from the CFO, one alert, the line moving."""
    return stub_data.SCAN


@app.get("/stub/alerts")
def stub_alerts() -> dict:
    return {"alerts": stub_data.SCAN["alerts"],
            "last_scan": stub_data.SCAN["last_scan"],
            "next_scan": stub_data.SCAN["next_scan"]}


@app.get("/stub/runs")
def stub_runs() -> dict:
    return {"runs": [stub_data.SCAN["run"]]}


# --- live ------------------------------------------------------------------

def _timeline():
    try:
        return scoring.scored_timeline()
    except scoring.DataUnavailable as e:
        # Lane A has not landed yet. Say so plainly instead of 500ing — the UI
        # should stay on /stub/* until this stops firing.
        raise HTTPException(503, f"{e}. Use /stub/* until the dataset lands.")


@app.get("/timeline")
def timeline() -> dict:
    engagement, messages = _timeline()
    return {
        "engagement": engagement.model_dump(),
        "messages": [m.model_dump(exclude_none=True) for m in messages],
        "last_scan": scoring.last_scan(),
    }


@app.get("/radar", response_model=Radar)
def radar() -> Radar:
    engagement, messages = _timeline()
    return scoring.build_radar(engagement, messages)


@app.post("/brief", response_model=Brief)
def brief() -> Brief:
    engagement, messages = _timeline()
    return scoring.build_brief(engagement, messages)


@app.post("/ingest")
def ingest(msg: IngestRequest) -> dict:
    """The always-on story in miniature: one message in, re-score, roll-ups
    move. Outbound is refused — scoring our own words is a bug, not a
    feature."""
    if msg.direction != "inbound":
        raise HTTPException(422, "outbound messages are never scored")

    message = Message(
        **{**msg.model_dump(exclude_none=True),
           "id": msg.id or f"E-{uuid.uuid4().hex[:4]}"}
    )
    scoring.add_message(message)
    engagement, messages = _timeline()
    scored = next((m for m in messages if m.id == message.id), message)
    return {
        "message": scored.model_dump(exclude_none=True),
        "radar": scoring.build_radar(engagement, messages).model_dump(),
        "last_scan": scoring.last_scan(),
    }


# --- the always-on half (§5a) ----------------------------------------------

@app.post("/scan", response_model=ScanResult)
def scan() -> ScanResult:
    """What the Claude Routine calls on each run. Pulls anything new out of
    data/, scores it, diffs the radar against the previous scan, and returns
    the alerts worth reaching out about. Idempotent: a scan with nothing new
    returns no alerts rather than repeating the last ones."""
    try:
        return scoring.scan()
    except scoring.DataUnavailable as e:
        raise HTTPException(503, f"{e}. Use /stub/scan until the dataset lands.")


@app.get("/alerts")
def alerts() -> dict:
    """What the UI banner reads. Most recent first."""
    return {
        "alerts": [a.model_dump() for a in scoring.alerts()],
        "last_scan": scoring.last_scan(),
        "next_scan": scoring.next_scan(),
    }


@app.get("/runs")
def runs() -> dict:
    """The run log — §5a step 5, the source for 'last scan 07:02, next 08:00'."""
    return {
        "runs": [r.model_dump() for r in scoring.runs()],
        "last_scan": scoring.last_scan(),
        "next_scan": scoring.next_scan(),
    }
