"""Scoring, caching and roll-ups. Owned by the backend lane.

Two rules this module enforces and must never break:

1. Only direction == "inbound" is scored. Outbound messages pass through
   untouched, with score/tone/quote left as None.
2. Nothing is scored at import time or at startup. Render's health check has
   to pass before any model call happens, so scoring is lazy: the first
   request that needs scores pays for them, everything after reads the cache.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv

import prompts
from models import (
    Action,
    Alert,
    Brief,
    BriefResult,
    ContactTemperature,
    DeadlineStatus,
    Engagement,
    Message,
    Radar,
    RadarDiff,
    RiskStatus,
    RunRecord,
    ScanResult,
    ScoreResult,
    TrendPoint,
)

load_dotenv()

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
SCORING_MODEL = os.getenv("SCORING_MODEL", "claude-sonnet-5")
BRIEF_MODEL = os.getenv("BRIEF_MODEL", "claude-sonnet-5")
SCAN_INTERVAL_MIN = int(os.getenv("SCAN_INTERVAL_MIN", "60"))

# Alert thresholds — §5a step 4.
TREND_DROP = float(os.getenv("TREND_DROP", "0.3"))

# The SDK picks up ANTHROPIC_API_KEY and, if set, ANTHROPIC_BASE_URL — the
# latter matters only if the Base Camp key is a gateway key rather than a
# direct sk-ant-... one. Constructed lazily so an unset key cannot break boot.
_client: anthropic.Anthropic | None = None
_client_lock = threading.Lock()


def client() -> anthropic.Anthropic:
    global _client
    with _client_lock:
        if _client is None:
            _client = anthropic.Anthropic()
        return _client


class DataUnavailable(RuntimeError):
    """data/ has no engagement yet — Lane A has not landed."""


# --- loading ---------------------------------------------------------------

def load_engagement() -> Engagement:
    path = DATA_DIR / "engagement.json"
    if not path.exists():
        raise DataUnavailable(f"no engagement.json under {DATA_DIR}")
    return Engagement.model_validate_json(path.read_text())


def load_messages() -> list[Message]:
    """emails/*.json (one message or a list) plus transcripts/*.json (arrays
    of turn records). Both are already in the Message shape."""
    out: list[Message] = []
    for sub in ("emails", "transcripts"):
        d = DATA_DIR / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            raw = json.loads(f.read_text())
            for item in raw if isinstance(raw, list) else [raw]:
                out.append(Message.model_validate(item))
    if not out:
        raise DataUnavailable(f"no messages under {DATA_DIR}")
    out.sort(key=lambda m: (m.date, m.seq or 0, m.id))
    return out


# --- the cache -------------------------------------------------------------

_scores: dict[str, ScoreResult] = {}      # message id -> score
_extra: list[Message] = []                # messages added via /ingest
_lock = threading.Lock()
_last_scan: str | None = None

# Scan state. Process memory, like everything else here: a Render restart
# resets the baseline and the next scan will see every message as new. The
# durable copy is whatever the routine writes back to the repo.
_seen: set[str] = set()
_prev_radar: Radar | None = None
_alerts: list[Alert] = []
_runs: list[RunRecord] = []


def last_scan() -> str | None:
    return _last_scan


def next_scan() -> str | None:
    if not _last_scan:
        return None
    return (datetime.fromisoformat(_last_scan)
            + timedelta(minutes=SCAN_INTERVAL_MIN)).isoformat(timespec="seconds")


def alerts() -> list[Alert]:
    with _lock:
        return list(reversed(_alerts))


def runs() -> list[RunRecord]:
    with _lock:
        return list(reversed(_runs))


def score_message(m: Message, ref_ids: list[str]) -> ScoreResult | None:
    """Score one message. Returns None for outbound — that is the one rule."""
    if m.direction != "inbound":
        return None
    with _lock:
        cached = _scores.get(m.id)
    if cached:
        return cached

    system = prompts.SCORING_SYSTEM
    if ref_ids:
        system += "\n\nDeadline and risk ids you may cite in refs: " + ", ".join(ref_ids)

    resp = client().messages.parse(
        model=SCORING_MODEL,
        max_tokens=1024,
        output_config={"effort": "low"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{
            "role": "user",
            "content": prompts.scoring_user_prompt(m.text, m.contact.name, m.contact.role),
        }],
        output_format=ScoreResult,
    )
    result = resp.parsed_output
    with _lock:
        _scores[m.id] = result
    return result


def scored_timeline() -> tuple[Engagement, list[Message]]:
    """Every message, scored where inbound. Lazy: this is where the model
    calls actually happen, on the first request that needs them."""
    global _last_scan
    engagement = load_engagement()
    messages = load_messages() + list(_extra)
    ref_ids = [d.id for d in engagement.deadlines] + [r.id for r in engagement.risks]

    for m in messages:
        if m.direction != "inbound":
            continue
        result = score_message(m, ref_ids)
        if result:
            m.score, m.tone, m.quote, m.refs = (
                result.score, result.tone, result.quote, result.refs
            )
    _last_scan = datetime.now().astimezone().isoformat(timespec="seconds")
    return engagement, messages


def add_message(m: Message) -> None:
    with _lock:
        _extra.append(m)


# --- roll-ups --------------------------------------------------------------

def _week_of(d: str) -> str:
    try:
        parsed = date.fromisoformat(d[:10])
    except ValueError:
        return d[:10]
    y, w, _ = parsed.isocalendar()
    return f"{y}-W{w:02d}"


def build_radar(engagement: Engagement, messages: list[Message]) -> Radar:
    scored = [m for m in messages if m.score is not None]

    by_week: dict[str, list[float]] = defaultdict(list)
    for m in scored:
        by_week[_week_of(m.date)].append(m.score)
    trend = [
        TrendPoint(week=w, avg_score=round(statistics.fmean(v), 3), n=len(v))
        for w, v in sorted(by_week.items())
    ]

    by_contact: dict[str, list[Message]] = defaultdict(list)
    for m in scored:
        by_contact[m.contact.name].append(m)
    contacts = []
    for name, ms in by_contact.items():
        ms.sort(key=lambda m: m.date)
        contacts.append(ContactTemperature(
            name=name,
            role=ms[-1].contact.role,
            temperature=round(statistics.fmean(m.score for m in ms), 3),
            last_quote=ms[-1].quote,
        ))
    contacts.sort(key=lambda c: c.temperature)

    def mentions_of(ref_id: str) -> list[str]:
        return [m.id for m in scored if m.refs and ref_id in m.refs]

    deadlines = []
    for d in engagement.deadlines:
        ms = mentions_of(d.id)
        negative = [m for m in scored if m.id in ms and m.score is not None and m.score < -0.2]
        # at_risk if the client is unhappy about it, or the engagement file
        # already says so. "on_track" is the only status that is not a warning.
        flagged = d.status.lower().replace(" ", "_") in {"missed", "at_risk", "slipped", "late"}
        deadlines.append(DeadlineStatus(
            **d.model_dump(), at_risk=bool(negative) or flagged, mentions=ms
        ))

    risks = [RiskStatus(**r.model_dump(), mentions=mentions_of(r.id)) for r in engagement.risks]
    return Radar(trend=trend, contacts=contacts, deadlines=deadlines, risks=risks)


def build_brief(engagement: Engagement, messages: list[Message]) -> Brief:
    """One Sonnet call. The engagement context is cached; the messages are not,
    because they change on every ingest."""
    engagement_json = engagement.model_dump_json(indent=None)
    slim = [
        {k: v for k, v in {
            "id": m.id, "date": m.date, "direction": m.direction,
            "contact": m.contact.name, "subject": m.subject,
            "text": m.text[:600], "score": m.score, "tone": m.tone, "refs": m.refs,
        }.items() if v is not None}
        for m in messages
    ]
    resp = client().messages.parse(
        model=BRIEF_MODEL,
        # Not 2048: with a full dataset the summary plus three cited actions
        # ran past it and the structured output was truncated mid-JSON, which
        # surfaces as a parse error, not as a short brief.
        max_tokens=16000,
        system=[{
            "type": "text",
            "text": prompts.BRIEF_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": prompts.brief_user_prompt(engagement_json, json.dumps(slim)),
        }],
        output_format=BriefResult,
    )
    parsed = resp.parsed_output

    # Guardrails on model output, both seen in testing:
    #  - a stray XML-ish tag leaking into the prose
    #  - an action citing a deadline/risk id instead of a message id
    valid_ids = {m.id for m in messages}
    summary = _strip_tags(parsed.summary)
    actions = []
    for a in parsed.actions:
        cites = [c for c in a.cites if c in valid_ids]
        if not cites:
            # An action we cannot cite is an action we do not show.
            continue
        actions.append(Action(text=_strip_tags(a.text), cites=cites))
    return Brief(summary=summary, actions=actions)


_TAG = re.compile(r"</?[A-Za-z_][\w:-]*\s*/?>")


def _strip_tags(text: str) -> str:
    return _TAG.sub("", text).strip()


# --- the always-on half (§5a) ----------------------------------------------

def diff_radar(prev: Radar | None, now: Radar, new_msgs: list[Message]) -> RadarDiff:
    """What moved since the previous scan. §5a step 3."""
    if prev is None:
        return RadarDiff(
            first_run=True,
            latest_week=now.trend[-1].week if now.trend else None,
        )

    latest_week = now.trend[-1].week if now.trend else None
    delta = None
    if now.trend:
        before = next((t.avg_score for t in prev.trend if t.week == latest_week), None)
        if before is None and prev.trend:
            before = prev.trend[-1].avg_score          # the week is itself new
        if before is not None:
            delta = round(now.trend[-1].avg_score - before, 3)

    # Any NEW escalating message is news — including from a contact who was
    # already cold. A CFO escalating a second time, harder, is exactly the
    # thing to wake someone for; comparing against her prior temperature
    # suppressed the alert and made the demo moment silent. Repetition is
    # already prevented upstream: a message is only ever new once.
    crossed = sorted({m.contact.name for m in new_msgs if m.tone == "escalating"})

    prev_at_risk = {d.id for d in prev.deadlines if d.at_risk}
    newly = sorted({d.id for d in now.deadlines if d.at_risk and d.id not in prev_at_risk})

    return RadarDiff(
        avg_score_delta=delta,
        latest_week=latest_week,
        contacts_crossed_escalating=crossed,
        deadlines_newly_at_risk=newly,
    )


def build_alerts(diff: RadarDiff, new_msgs: list[Message], stamp: str) -> list[Alert]:
    """§5a step 4: reach out only when something moved. Every alert carries
    the client's own quote and the message ids behind it — an alert we
    cannot evidence is an alert we do not send."""
    out: list[Alert] = []

    for name in diff.contacts_crossed_escalating:
        driver = next(
            (m for m in reversed(new_msgs) if m.contact.name == name and m.tone == "escalating"),
            None,
        )
        if not driver or not driver.quote:
            continue          # no quote, no alert
        out.append(Alert(
            id=f"A-{len(_alerts) + len(out) + 1}",
            at=stamp, kind="escalation", severity="high",
            text=f"{name} ({driver.contact.role}) has turned escalating.",
            contact=name, quote=driver.quote, message_ids=[driver.id],
        ))

    if diff.avg_score_delta is not None and diff.avg_score_delta <= -TREND_DROP:
        scored_new = [m for m in new_msgs if m.score is not None]
        worst = min(scored_new, key=lambda m: m.score, default=None)
        out.append(Alert(
            id=f"A-{len(_alerts) + len(out) + 1}",
            at=stamp, kind="trend_drop", severity="medium",
            text=(f"Weekly average fell {abs(diff.avg_score_delta)} "
                  f"in {diff.latest_week}."),
            contact=worst.contact.name if worst else None,
            quote=worst.quote if worst else None,
            message_ids=[m.id for m in scored_new],
        ))

    return out


def scan() -> ScanResult:
    """One call the routine can build on: pull, score, compare, decide.

    §5a has the routine call /ingest per message and diff /radar itself.
    Doing it in one endpoint keeps scoring in one place (which is what that
    instruction protects) and leaves the routine four HTTP calls instead of
    N+2.
    """
    global _prev_radar

    engagement, messages = scored_timeline()      # scores anything unscored
    stamp = _last_scan or datetime.now().astimezone().isoformat(timespec="seconds")

    with _lock:
        known = set(_seen)
    new_msgs = [m for m in messages if m.id not in known]

    radar = build_radar(engagement, messages)
    diff = diff_radar(_prev_radar, radar, new_msgs)
    fired = build_alerts(diff, new_msgs, stamp)

    record = RunRecord(
        at=stamp,
        new_messages=[m.id for m in new_msgs],
        alerts_fired=len(fired),
        note=("first run — baseline recorded, no alerts" if diff.first_run
              else f"{len(new_msgs)} new, {len(fired)} alert(s)"),
    )

    with _lock:
        _seen.update(m.id for m in messages)
        _alerts.extend(fired)
        _runs.append(record)
    _prev_radar = radar

    return ScanResult(
        new_messages=new_msgs, alerts=fired, diff=diff, radar=radar,
        last_scan=stamp, next_scan=next_scan() or stamp, run=record,
    )
