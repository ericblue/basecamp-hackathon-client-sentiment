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
from models import Brief, IngestRequest, Message, Radar

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
    return {"ok": True, "last_scan": scoring.last_scan()}


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
