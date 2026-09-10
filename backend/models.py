"""The frozen data contract, as Pydantic models.

Every lane builds against these shapes. See CLAUDE.md; do not change them
mid-build without announcing it in the shared thread.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Tone = Literal["positive", "neutral", "concerned", "frustrated", "escalating"]
Direction = Literal["inbound", "outbound"]
Kind = Literal["email", "transcript_turn"]


class Contact(BaseModel):
    name: str
    role: str
    org: str


class Meeting(BaseModel):
    title: str
    date: str


class Message(BaseModel):
    id: str
    thread_id: str
    kind: Kind
    direction: Direction
    contact: Contact
    date: str
    text: str
    subject: Optional[str] = None
    meeting: Optional[Meeting] = None      # transcript_turn only
    seq: Optional[int] = None              # transcript_turn only
    # The one rule: these are populated only when direction == "inbound".
    score: Optional[float] = None
    tone: Optional[Tone] = None
    quote: Optional[str] = None
    refs: Optional[list[str]] = None


class Deadline(BaseModel):
    id: str
    title: str
    due: str
    status: str


class Risk(BaseModel):
    id: str
    title: str
    severity: str


class Engagement(BaseModel):
    client: str
    project: str
    contacts: list[Contact] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)


class TrendPoint(BaseModel):
    week: str
    avg_score: float
    n: int


class ContactTemperature(BaseModel):
    name: str
    role: str
    temperature: float          # mean score of that contact's messages, -1..1
    last_quote: Optional[str] = None


class DeadlineStatus(Deadline):
    at_risk: bool = False
    mentions: list[str] = Field(default_factory=list)


class RiskStatus(Risk):
    mentions: list[str] = Field(default_factory=list)


class Radar(BaseModel):
    trend: list[TrendPoint] = Field(default_factory=list)
    contacts: list[ContactTemperature] = Field(default_factory=list)
    deadlines: list[DeadlineStatus] = Field(default_factory=list)
    risks: list[RiskStatus] = Field(default_factory=list)


class Action(BaseModel):
    text: str
    cites: list[str] = Field(default_factory=list)


class Brief(BaseModel):
    summary: str
    actions: list[Action] = Field(default_factory=list)


# --- model-facing shapes (structured output targets) ------------------------

class ScoreResult(BaseModel):
    """What the scorer returns for one client message."""
    score: float
    tone: Tone
    quote: str
    refs: list[str] = Field(default_factory=list)


class BriefResult(BaseModel):
    summary: str
    actions: list[Action]


class IngestRequest(BaseModel):
    """POST /ingest — one new message, contract-shaped, unscored."""
    id: Optional[str] = None
    thread_id: str = "T-ingest"
    kind: Kind = "email"
    direction: Direction = "inbound"
    contact: Contact
    date: str
    text: str
    subject: Optional[str] = None
