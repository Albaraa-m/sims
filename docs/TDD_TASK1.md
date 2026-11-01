# Technical Design (TDD): Task 1 — Transcript → Voice Test

**Done when:** a reviewer pastes a transcript, edits and readies the test, runs it by voice against v1 and v2, and compares both runs side by side, linked to the source. The benchmark reports conversion fidelity on ~6 cases.

## Core entities

```
┌───────────────────────┐     ┌───────────────────┐
│ SourceConversation    │     │ AgentVersion      │
├───────────────────────┤     ├───────────────────┤
│ id                    │     │ id   v1 │ v2      │
│ transcript    JSON    │     │ prompt  (in code) │
│ agent_version? ───────┼────▶│                   │
│ created_at            │     └───────────────────┘
└───────────────────────┘              ▲
          ▲ 1                          │ 1
          │ N                          │
┌───────────────────────┐              │
│ Test (immutable)      │              │
├───────────────────────┤              │
│ id                    │              │
│ lineage_id            │              │
│ version               │              │
│ source_conv_id        │              │
│ status  draft│ready   │              │
│ spec      TestSpec    │              │
│ inferred  TestSpec    │              │
│ created_at            │              │
└───────────────────────┘              │
          ▲ 1                          │ N
          │ N                          │
┌──────────────────────────────────────┴┐
│ Simulation                            │
├───────────────────────────────────────┤
│ id                                    │
│ test_id?        (empty for ad-hoc)    │
│ agent_version                         │
│ status  running│done│failed (+queued) │
│ report   JSON  LiveKit SessionReport  │
│ recording_path                        │
│ room_name, error                      │
│ started_at, ended_at                  │
└───────────────────────────────────────┘
```

- `AgentVersion` lives in code (`agents/booking/agent.py`, `INSTRUCTIONS_BY_VERSION`); rows store its id. A table comes only if versions must be created at runtime.
- `Simulation.report` is LiveKit's `SessionReport.to_dict()`: transcript, tool calls, timings, usage. No hand-rolled turns table.
- `queued` is added in this task, when the API starts simulations in the background.

**TestSpec** (Pydantic): `goal`, `facts`, `caller_instructions`, `policy_under_test`, `expected_outcome`, `fixed`, `varying`.

- Edits insert a new `Test` row (`version + 1`, `draft`); old runs keep pointing to what ran.
- `inferred` vs `spec` shows what the model inferred and what the reviewer changed.

## Structure

```
 Browser ──HTTP──▶ FastAPI ──▶ SQLite
                     │  ▲
           convert   │  │ transcript
            (LLM)    ▼  │
                  Runner ──LiveKit API──▶ Room
                                          ├─ booking-agent server: agent under test (v1│v2)
                                          └─ caller-agent server:  digital human (TestSpec)
                                                   │
            evidence/<id>/report.json + audio.ogg ─┘ (runner stores them on the Simulation)

 benchmark/ ──▶ converter ──▶ score.py ──▶ results.md
```

## Screens

| Screen | Reviewer sees | Reviewer can |
|---|---|---|
| Paste | Transcript box | Paste and convert |
| Review | Spec fields; edited fields marked against `inferred`; status badge | Edit fields, toggle fixed/varying, mark ready |
| Runs | v1 and v2 side by side; tool calls inline; status polled every 2s | Run, rerun, open source and earlier versions |

"Ready" badge and an enabled Run button tell the reviewer the test can run.

## Data flow

1. Reviewer pastes a transcript → `SourceConversation`.
2. LLM extracts a `TestSpec` → `Test` v1, `draft`, `inferred = spec`.
3. Reviewer edits → new `Test` row, `draft`.
4. "Mark ready" → `ready`.
5. "Run vs v1 and v2" → two `Simulation` rows, `queued`.
6. Runner creates a room, dispatches `booking-agent` (version in job metadata) and `caller-agent` (TestSpec in job metadata; today the caller's goal is hardcoded) → `running`.
7. Call ends (caller hang-up tool or timeout) → booking agent writes its session report and recording to `evidence/<id>/` → runner stores them → `done`, or `failed` on timeout, missing report or any error.
8. UI shows source, test version and both simulations side by side, tool calls inline.

## Benchmark: conversion fidelity

**Question:** does the generated test preserve the original failure situation?

| Step | What |
|---|---|
| Cases | 6 transcripts, each a different failure (below) |
| Answer key | Hand-written `expected.json` per case, written **before** converting: goal, key facts, situation, policy |
| Run | `benchmark/run.py` converts each transcript → `TestSpec` |
| Score | 5 criteria, pass/fail per case; LLM judge with the rubric, spot-checked by hand |
| Report | `results.md`: per-case table, overall %, one hit and one miss explained, limits |

| # | Failure in the transcript | Rule broken |
|---|---|---|
| 1 | Booked without reading back and confirming | Confirm before booking (v1's bug) |
| 2 | Booked a table for 12 | Parties over 8 go to the events team |
| 3 | Booked 22:00 | Bookings only 13:00–21:00 |
| 4 | Said 20:00 was booked, but it's full | Check availability before booking |
| 5 | Quoted a dish or price not on the menu | Never invent menu items or prices |
| 6 | Accepted a booking for tomorrow | Same-day bookings only |

| Criterion | Pass if |
|---|---|
| Goal kept | Same caller goal |
| Facts kept | All key facts present |
| Situation kept | Caller still creates the conditions that expose the failure |
| Policy right | `policy_under_test` names the broken rule |
| Fixed/varying | Essentials are fixed |

**Limits:** small sample, self-written transcripts, LLM judge bias, scores the spec only (not whether the live caller acts it out), no automated v1-fails / v2-passes check (Task 2).

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Storage | SQLite + SQLModel | One file; ORM and Pydantic in one class |
| Spec | Pydantic `TestSpec` in a JSON column | Validated, diffable, extend without migrations |
| Versioning | Immutable rows | Old runs keep pointing to what ran |
| Format | JSON | Matches DB columns; no YAML yet |
| Web | FastAPI + server-rendered HTML | Fewest moving parts |
| Conversion | One LLM call, structured output | Simple; reviewer fixes the rest |
| Caller | LiveKit Agents SDK agent | Required by the brief |
| Agent servers | Two: `booking-agent` (under test) and `caller-agent` | Separates the agent under test from the test tool; one server registers one name |
| Versions | Version id in job metadata; prompts in code | No deploys per version |
| Call record | LiveKit `SessionReport` JSON, written to `evidence/<id>/` by the agent and stored by the runner | Standard SDK format; LiveKit Cloud keeps sessions only 30 days and has no fetch API; agents stay independent of the database |
| Naming | `Simulation` = one call; `Swarm` = batch; `Attempt` = retry (Task 3) | Brief's terms; LiveKit uses "run" for a batch |
| Runner | `simulations/runner.py` `run_simulation()`, called from an in-process background task | Task 3 replaces it with a reliable queue |
| Comparison | Side-by-side view, no verdict | Verdicts are Task 2 |

## Risks

- Caller drifts or never hangs up → hard timeout plus hang-up tool.
- Conversion loses the failure situation → reviewer edits; benchmark measures it.
- Benchmark too easy → varied failure types; answer key written first.

## Backlog

Audio upload, `world` seeding, recording URL, YAML export.

## Your steps

None. Conversion and the judge use LiveKit Inference.
