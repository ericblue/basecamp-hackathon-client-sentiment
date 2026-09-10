---
spec_version: 0.5
engine:   adhoc
tracking: claude-tasks
verify:   none
review:   none
test_cmd: "curl -fsS http://localhost:8000/stub/radar > /dev/null"
e2e:      none
merge:    ask
---

## Why these choices

**engine=** — four people own four lanes for sixty minutes (`docs/Workstreams.md`);
the parallelism is human, not worktree-per-task, so no formal engine drives it.
The method that *does* apply is the clock: freeze the contract at minute 5, stubs
live at minute 10, live scoring at 30, UI flips to live at 40, freeze at 50. Work
the current minute's deliverable, not the backlog.

**verify=** — no test suite exists and none is worth building against a two-minute
demo deadline. The bar the PRD actually sets is *"demoing by minute 45"*; anything
that isn't is cut rather than fixed, and a test gate would not have caught that
call anyway.

**test_cmd=** — a liveness probe, not a suite. The stub endpoint is the one shared
dependency in the build: the UI lane is blocked the moment it stops answering, and
it must keep answering the frozen contract shape even after the live handlers land.
Treat a failure as "you just broke someone else's lane."

**merge=** — three other people are pushing to `main` under time pressure, and the
merge points are scheduled (minutes 10, 30, 40) rather than continuous. A human
picks the moment; unattended merging would land a lane's half-finished branch in
the middle of someone else's integration.

<!-- TODO (Eric): add anything lane-specific the team agrees at the table — in
     particular who owns the merge call at each handoff minute, and whether the
     plugin lane gets its own branch or rides on Lane D's. -->
