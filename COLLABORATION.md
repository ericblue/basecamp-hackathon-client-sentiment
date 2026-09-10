# How we collaborate for the hour

Three places, no signups. Use them for what they are good at and nothing else.

## Canvas: Excalidraw (live)

https://excalidraw.com/#room=ff2dd40f981511818ca9,YPzyHAapS-j56uqijCuD3g

The shared board. Open the link in any browser; you are in the room immediately, no account. Put your name on your cursor (top right, once you are in). Use it for:

- the architecture picture (data, backend, UI, plugin) and the arrows between them
- the lane board: four columns (Data, Backend, UI, Demo and plugin), one sticky per task, move it right when done
- the demo storyboard: six frames, one per step in the README

Do not put code or long text here. If it needs to be typed, it goes in the repo.

## Chat: WhatsApp group

Group name: Sentiment Radar hackathon. Eric's WhatsApp: +1 310 699 9664 (or https://wa.me/13106999664). Message Eric there and he will add you to the group, or scan the group QR off his screen at the table. Use it for:

- handoff pings at the clock minutes (10, 30, 40, 50): "stub endpoints live", "dataset final", "UI on live API"
- contract changes, one line with the reason, only before minute 30
- "I am blocked on X" the moment it happens, not five minutes later

## Code and docs: GitHub

Repo: `basecamp-hackathon-client-sentiment` (Eric's account; collaborators added at the table, or fork and PR).

- `README.md` carries the contract; it is the thing every lane builds against
- `docs/` has the PRD, the workstreams, the plugin use cases and the two mockups
- one branch per lane (`lane-data` Mike, `lane-backend` Eric, `lane-ui` Aditya, `lane-agent` Alex), merge to `main` at the handoff minutes
- one issue per lane, so handoff notes and known gaps have a place to land
- lanes backend and agent share `backend/`: Alex owns `prompts.py`, Eric owns everything else in it
- the Anthropic key comes from https://basecamp-key-server.onrender.com/ and never lands in the repo; `.env` is gitignored

## The clock

| Minute | Milestone |
|---|---|
| 0 to 5 | Everyone in the three links; lanes assigned; contract read |
| 10 | Stub endpoints live; UI starts; first ten messages committed |
| 30 | Scoring live on real data; dataset final; UI end to end on stub |
| 40 | UI on the live API; integration fixes only |
| 50 | Freeze; rehearse the demo twice |
| 60 | Demo |

## Two rules

Anything not demoing by minute 45 is cut, not fixed. Anything not in the contract is decided by the lane that needs it and announced in the chat.
