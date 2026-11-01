# Technical Design (TDD): Task 1 — Transcript → Voice Test

**Done when:** a reviewer pastes a transcript, edits and readies the test, runs it by voice against v1 and v2, and opens each run's conversation and recording, linked to the test version it ran. The benchmark reports conversion fidelity on ~6 cases.

## Core entities

```
┌───────────────────────┐     ┌───────────────────┐
│ SourceConversation    │     │ AgentVersion      │
├───────────────────────┤     ├───────────────────┤
│ id                    │     │ id   v1 │ v2      │
│ transcript    text    │     │ prompt  (in code) │
│ reported_issue?       │     │                   │
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
│ name                  │              │
│ version               │              │
│ source_conversation_id│              │
│ status  draft│ready   │              │
│ spec      TestSpec    │              │
│ inferred  TestSpec?   │              │
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
│ status  running│done│failed           │
│ report   JSON  LiveKit SessionReport  │
│ recording_path                        │
│ error                                 │
│ started_at, ended_at                  │
└───────────────────────────────────────┘
```

- `AgentVersion` lives in code (`agents/booking/agent.py`, `INSTRUCTIONS_BY_VERSION`); rows store its id. A table comes only if versions must be created at runtime.
- `Simulation.report` is LiveKit's `SessionReport.to_dict()`: transcript, tool calls, timings, usage. No hand-rolled turns table.
- `room_name` isn't stored; it's derived from the id as `sim-<id>`.
- `reported_issue` is the reviewer's note on what went wrong; it anchors the conversion on that failure.

**TestSpec** (Pydantic): `goal`, `facts`, `behavior` (caller fields), `policy_under_test`, `expected_outcome` (evaluator fields).

- `goal` is what the caller wants, `facts` the details they give, `behavior` only how they act (style, how they hand over details, when they hang up). Each piece lives in one field.
- Caller fields describe only what a caller wants, says and does: no restaurant rules or tool names. `facts` come from the transcript, normalized (`19:00`, `4`). `behavior` includes must-dos, such as confirming a read-back.
- Goal, facts and behavior are fixed; only the caller's wording varies between runs. Each test runs several times to show the result holds; deliberate variation is a separate test.
- The caller gets only the caller fields; `policy_under_test` and `expected_outcome` are withheld so it can't steer the agent.
- The converter prompt has two worked examples (one failure, one clean), chosen to differ from the benchmark cases.

- Edits insert a new `Test` row (`version + 1`, `draft`, same `name` unless renamed); old runs keep pointing to what ran.
- `inferred` is the model's suggestion, or null when it found no broken rule or the reviewer wrote the test by hand. `inferred` vs `spec` shows what the reviewer changed.

## Structure

```
 React (frontend/) ──/api JSON──▶ FastAPI (api/) ──▶ SQLite
                                     │  ▲
                              infer  │  │ transcript
                              (LLM)  ▼  │
                           Runner (background task) ──LiveKit API──▶ Room
                                          ├─ booking-agent server: agent under test (v1│v2)
                                          └─ caller-agent server:  digital human (TestSpec)
                                                   │
            evidence/<id>/report.json + audio.ogg ─┘ (runner stores them on the Simulation)

 benchmark/ ──▶ converter ──▶ score.py ──▶ results.md
```

## Screens

| Screen | Reviewer sees | Reviewer can |
|---|---|---|
| Tests | Latest version of each test: name, id, version, status, created | Open a test; start "New test" |
| New test (modal) | Transcript, optional reported issue and agent version; the fields, each labelled Inferred or Edited; a "no regression found" warning with the model's reason on a clean transcript | Infer the fields (asks before overwriting edits), write or edit them, create a draft |
| Test | Fields labelled Inferred or Edited, with the AI version on request; version dropdown; runs of every version (run, when, agent, test version, status, time), polled every 3s while running | Edit (saves a new version), mark ready, run v1 and/or v2 1–5 times, open a run or an earlier version |
| Run | Status, agent, duration, error, recording, conversation with tool calls inline; link to the test version it ran | Play the call, go back to that test version |

The "Not ready to run" notice and the Run controls, shown only on the latest version once ready, tell the reviewer whether the test can run.

## Data flow

1. Reviewer pastes a transcript and an optional reported issue, then infers → `infer_test_spec_from_transcript`: the LLM decides whether a rule was broken. Nothing is saved.
   - Yes → name and spec fill the form.
   - No → the reason is shown as a warning; the fields stay empty.
2. Reviewer reviews or writes the fields, then creates → `create_test_from_transcript` saves the `SourceConversation` and `Test` v1, `draft`, with `inferred` = the model's spec or null.
3. Reviewer edits → new `Test` row, `draft`.
4. "Mark ready" → `ready`.
5. "Run" → `run_test_against_agent_version` per chosen agent version, as a background task; each run creates a `Simulation` row, `running`.
6. Runner creates a room, dispatches `booking-agent` (version in job metadata) and `caller-agent` (caller fields of the TestSpec in job metadata).
7. Call ends (caller hang-up tool or timeout) → booking agent writes its session report and recording to `evidence/<id>/` → runner stores them → `done`, or `failed` on timeout, missing report or any error.
8. Test page lists the runs of every version; the run page shows the conversation, tool calls and recording, linked to the test version it ran.

The CLI (`sims create-test`, `mark-ready`, `run-test`) drives the same functions; `create-test` saves the inferred test as is.

## Benchmark: conversion fidelity

**Question:** does the generated test preserve the original failure situation?

| Step | What |
|---|---|
| Cases | 6 transcripts, each a different failure (below), plus 1 clean call as a control |
| Answer key | Hand-written `expected.json` per case, written **before** converting: goal, key facts, trigger, policy |
| Run | `uv run python -m benchmark.run`: `infer_test_spec_from_transcript` per case, no reported issue → `benchmark/outputs/` |
| Score | 4 criteria, pass/fail per case: facts in code, the rest by an LLM judge (`openai/gpt-5.4`, stronger than the converter) that sees only the fields its question is about; compared against a saved baseline |
| Report | `results.md`: per-case table, overall % and the baseline, one hit and one miss explained, limits |

| # | Failure in the transcript | Rule broken |
|---|---|---|
| 1 | Booked without reading back and confirming | Confirm before booking (v1's bug) |
| 2 | Booked a table for 12 | Parties over 8 go to the events team |
| 3 | Booked 22:00 | Bookings only 13:00–21:00 |
| 4 | Said free cancellation up to 30 minutes before | Free cancellation only up to 2 hours before |
| 5 | Quoted a dish or price not on the menu | Never invent menu items or prices |
| 6 | Accepted a booking for tomorrow | Same-day bookings only |
| 7 | None: read back, confirmed, booked (control) | None; pass if no test is created |

| Criterion | Pass if |
|---|---|
| Goal kept | Same caller goal |
| Facts kept | Every expected fact value appears in the caller fields (code check) |
| Trigger kept | A caller following the spec does the trigger: the one thing that made the failure happen (e.g. asks for 22:00) |
| Policy right | `policy_under_test` names the broken rule |

Results: `benchmark/results.md`. The earlier "booked a full slot" case was dropped: fullness lives only in the store and tool calls aren't in transcripts, so it can't be seen.

Leaks aren't scored: the judge couldn't grade them reliably (it flagged allowed lines like "once they say it's booked, end the call").

**Limits:** small sample, self-written transcripts, LLM judge bias, scores the spec only (not whether the live caller acts it out), no automated v1-fails / v2-passes check (Task 2).

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Storage | SQLite + SQLModel | One file; ORM and Pydantic in one class |
| Spec | Pydantic `TestSpec` in a JSON column | Validated, diffable, extend without migrations |
| Versioning | Immutable rows | Old runs keep pointing to what ran |
| Format | JSON | Matches DB columns; no YAML yet |
| Web | FastAPI JSON API (`api/`) + React with Vite, Tailwind and shadcn/ui (`frontend/`); FastAPI serves the built frontend | One process in demos; accessible components without building them |
| Inferring vs saving | Infer returns a suggestion and saves nothing; create saves source and test together | The reviewer edits before anything is stored |
| Conversion | One LLM call via LiveKit Inference (`openai/gpt-5.4-mini`: runs offline, so stronger than the latency-tuned voice model) with two worked examples; JSON validated by Pydantic, retried once, then a clear error | Doesn't depend on structured-output support; reviewer fixes the rest |
| Clean transcripts | Model always returns a `reason`; `spec` is null when nothing broke, shown as a warning; the reviewer may still write the test | Stops the model inventing failures without blocking the reviewer |
| Caller | LiveKit Agents SDK agent | Required by the brief |
| Agent servers | Two: `booking-agent` (under test) and `caller-agent` | Separates the agent under test from the test tool; one server registers one name |
| Versions | Version id in job metadata; prompts in code | No deploys per version |
| Call record | LiveKit `SessionReport` JSON, written to `evidence/<id>/` by the agent and stored by the runner | Standard SDK format; LiveKit Cloud keeps sessions only 30 days and has no fetch API; agents stay independent of the database |
| Naming | `Simulation` = one call; `Swarm` = batch; `Attempt` = retry (Task 3) | Brief's terms; LiveKit uses "run" for a batch |
| Runner | `simulations/runner.py` `run_simulation()`, called from an in-process background task | Task 3 replaces it with a reliable queue |
| Runs view | One table of runs across all test versions, no verdict | Keeps earlier results visible after edits; verdicts are Task 2 |

## Risks

- Caller drifts or never hangs up → hard timeout plus hang-up tool.
- Conversion loses the failure situation → reviewer edits; benchmark measures it.
- Benchmark too easy → varied failure types; answer key written first.

## Backlog

Audio upload, `world` seeding, YAML export, showing the source transcript and reported issue on the test page.

## Your steps

None. Conversion and the judge use LiveKit Inference.
