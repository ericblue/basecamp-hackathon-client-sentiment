"""Canned data for GET /stub/* — byte-compatible with the live shapes.

This exists so the UI lane is never blocked on the model or on the dataset.
It is deployed at minute 10 and must keep answering the frozen contract even
after the live handlers land: a failure here is someone else's lane broken.

The arc matches the demo script in the README — Northwind Retail, a Workday
rollout, warm for two weeks, a dip after the missed May 19 migration
deadline, the CFO in red, a partial recovery.
"""

ENGAGEMENT = {
    "client": "Northwind Retail",
    "project": "Workday HCM rollout",
    "contacts": [
        {"name": "Dana Whitfield", "role": "CFO", "org": "Northwind Retail"},
        {"name": "Marcus Reyes", "role": "Program Director", "org": "Northwind Retail"},
        {"name": "Priya Nair", "role": "HR Operations Lead", "org": "Northwind Retail"},
    ],
    "deadlines": [
        {"id": "D-1", "title": "Payroll data migration", "due": "2026-05-19", "status": "missed"},
        {"id": "D-2", "title": "Phase 1 go-live", "due": "2026-06-15", "status": "at_risk"},
        {"id": "D-3", "title": "Parallel payroll run", "due": "2026-06-01", "status": "on_track"},
    ],
    "risks": [
        {"id": "R-1", "title": "Legacy payroll data quality", "severity": "high"},
        {"id": "R-2", "title": "Client-side testing capacity", "severity": "medium"},
    ],
}

TIMELINE = [
    {
        "id": "E-1", "thread_id": "TH-1", "kind": "email", "direction": "inbound",
        "contact": {"name": "Priya Nair", "role": "HR Operations Lead", "org": "Northwind Retail"},
        "date": "2026-04-14", "subject": "Kickoff went well",
        "text": "Thanks for yesterday — the team walked out genuinely excited, which is not "
                "how our last vendor kickoff went. Looking forward to this.",
        "score": 0.75, "tone": "positive",
        "quote": "the team walked out genuinely excited", "refs": [],
    },
    {
        "id": "E-2", "thread_id": "TH-1", "kind": "email", "direction": "outbound",
        "contact": {"name": "Account Team", "role": "Engagement Lead", "org": "Us"},
        "date": "2026-04-15", "subject": "Re: Kickoff went well",
        "text": "Glad it landed. Sending the data-mapping workbook today; we will need "
                "sign-off on the payroll fields by the 24th to hold the May 19 migration.",
    },
    {
        "id": "E-5", "thread_id": "TH-2", "kind": "email", "direction": "inbound",
        "contact": {"name": "Marcus Reyes", "role": "Program Director", "org": "Northwind Retail"},
        "date": "2026-04-28", "subject": "Payroll field mapping",
        "text": "Workbook is back with you. Two of the legacy earning codes have no clean "
                "target — can you confirm the May 19 migration is still realistic once you "
                "have looked at them?",
        "score": 0.05, "tone": "neutral",
        "quote": "can you confirm the May 19 migration is still realistic",
        "refs": ["D-1", "R-1"],
    },
    {
        "id": "T-3", "thread_id": "M-2", "kind": "transcript_turn", "direction": "inbound",
        "contact": {"name": "Marcus Reyes", "role": "Program Director", "org": "Northwind Retail"},
        "date": "2026-05-07", "meeting": {"title": "Weekly status call", "date": "2026-05-07"},
        "seq": 3,
        "text": "I want to flag that we are three weeks out and my team still has not seen a "
                "cutover runbook. I am not raising an alarm yet, but I would like a date.",
        "score": -0.3, "tone": "concerned",
        "quote": "we are three weeks out and my team still has not seen a cutover runbook",
        "refs": ["D-1"],
    },
    {
        "id": "E-11", "thread_id": "TH-3", "kind": "email", "direction": "inbound",
        "contact": {"name": "Marcus Reyes", "role": "Program Director", "org": "Northwind Retail"},
        "date": "2026-05-20", "subject": "Migration date",
        "text": "So we have missed the 19th. I asked about this on the 28th and again on the "
                "call. What I need now is not reassurance, it is a dated plan I can take to "
                "Dana.",
        "score": -0.65, "tone": "frustrated",
        "quote": "What I need now is not reassurance, it is a dated plan",
        "refs": ["D-1", "D-2"],
    },
    {
        "id": "E-14", "thread_id": "TH-3", "kind": "email", "direction": "inbound",
        "contact": {"name": "Dana Whitfield", "role": "CFO", "org": "Northwind Retail"},
        "date": "2026-05-21", "subject": "Thursday's steering call",
        "text": "I have asked our COO to join Thursday. Before that call I want a written "
                "view on whether the June 15 go-live is still credible, and what the "
                "contractual position is if it is not.",
        "score": -0.88, "tone": "escalating",
        "quote": "what the contractual position is if it is not",
        "refs": ["D-2"],
    },
    {
        "id": "E-17", "thread_id": "TH-3", "kind": "email", "direction": "inbound",
        "contact": {"name": "Marcus Reyes", "role": "Program Director", "org": "Northwind Retail"},
        "date": "2026-05-24", "subject": "Re: Recovery plan",
        "text": "This is the first thing I have been able to forward to Dana without "
                "caveating it. Still tight, but it is a plan. Let us hold the Thursday call "
                "as a working session.",
        "score": -0.1, "tone": "concerned",
        "quote": "the first thing I have been able to forward to Dana without caveating it",
        "refs": ["D-2"],
    },
]

RADAR = {
    "trend": [
        {"week": "2026-W16", "avg_score": 0.75, "n": 2},
        {"week": "2026-W17", "avg_score": 0.52, "n": 3},
        {"week": "2026-W18", "avg_score": 0.05, "n": 4},
        {"week": "2026-W19", "avg_score": -0.30, "n": 3},
        {"week": "2026-W20", "avg_score": -0.68, "n": 5},
        {"week": "2026-W21", "avg_score": -0.35, "n": 4},
    ],
    "contacts": [
        {"name": "Dana Whitfield", "role": "CFO", "temperature": -0.88,
         "last_quote": "what the contractual position is if it is not"},
        {"name": "Marcus Reyes", "role": "Program Director", "temperature": -0.25,
         "last_quote": "the first thing I have been able to forward to Dana without caveating it"},
        {"name": "Priya Nair", "role": "HR Operations Lead", "temperature": 0.45,
         "last_quote": "the team walked out genuinely excited"},
    ],
    "deadlines": [
        {"id": "D-1", "title": "Payroll data migration", "due": "2026-05-19",
         "status": "missed", "at_risk": True, "mentions": ["E-5", "T-3", "E-11"]},
        {"id": "D-2", "title": "Phase 1 go-live", "due": "2026-06-15",
         "status": "at_risk", "at_risk": True, "mentions": ["E-11", "E-14", "E-17"]},
        {"id": "D-3", "title": "Parallel payroll run", "due": "2026-06-01",
         "status": "on_track", "at_risk": False, "mentions": []},
    ],
    "risks": [
        {"id": "R-1", "title": "Legacy payroll data quality", "severity": "high",
         "mentions": ["E-5"]},
        {"id": "R-2", "title": "Client-side testing capacity", "severity": "medium",
         "mentions": []},
    ],
}

BRIEF = {
    "summary": "Northwind has gone from warm to escalating in three weeks, and the trigger "
               "is a single missed date. The May 19 payroll migration slipped after Marcus "
               "flagged the earning-code gap on April 28 and again on the May 7 call; he "
               "escalated on May 20, and Dana Whitfield has now pulled her COO into "
               "Thursday's steering call and asked about the contractual position on the "
               "June 15 go-live. The recovery plan has partially stabilised Marcus, but "
               "Dana has not softened and is the relationship to repair.",
    "actions": [
        {"text": "Send Dana a written go-live assessment before Thursday that answers the "
                 "credibility question directly rather than defending the slip.",
         "cites": ["E-14"]},
        {"text": "Call Marcus to confirm the Thursday call is a working session, and bring "
                 "the dated cutover plan he asked for twice.",
         "cites": ["E-11", "E-17"]},
        {"text": "Close out the two unmapped legacy earning codes this week — they are the "
                 "root of the missed date and are still open.",
         "cites": ["E-5"]},
    ],
}
