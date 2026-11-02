# Technical Design (TDD): Task 2 — Evaluator, Results and Dashboards (M10–M12)

**Done when:** every finished run gets an outcome (pass, fail, execution failure or inconclusive) with the cited turns that justify it. The reviewer reads the grading criteria before running, filters results, and drills from a result into its evidence. The dashboard (M12) compares agent versions and shows system health. The evaluator benchmark (M13) has its own results in `benchmark/`.

## Outcomes

| Outcome | Meaning | Decided by |
|---|---|---|
| Pass | The situation happened and the agent followed the policy | Judge |
| Fail | The situation happened and the agent broke the policy | Judge |
| Execution failure | No usable call: call failed (crash, timeout), unfinished, no report, no recording, agent or caller never spoke | Code, before the judge |
| Inconclusive | The call ran, but the policy can't be graded: the caller never pursued the goal, the call ended before the situation came up, the judge errored or cited turns that don't exist | Judge or code |

Only pass and fail count towards a pass rate. The other two are always shown, never counted as passes.

## Core entities

```
┌──────────────┐ 1   N ┌──────────────┐ 1   N ┌──────────────────────────┐
│ Test         │──────▶│ Simulation   │──────▶│ Evaluation (immutable)   │
│ (version)    │       │ (one call)   │       ├──────────────────────────┤
│ spec:        │       │ agent_version│       │ id                       │
│  policy_     │       │ status       │       │ simulation_id            │
│  under_test  │       │ report       │       │ outcome                  │
│  expected_   │       └──────────────┘       │ situation_happened?      │
│  outcome     │                              │ cited_turns  [int]       │
└──────────────┘                              │ reason                   │
                                              │ judge_model              │
                                              │ judge_prompt_version     │
                                              │ error?                   │
                                              │ created_at               │
                                              └──────────────────────────┘
```

- One `Evaluation` per grading. Regrading adds a row; the newest is shown and earlier ones stay in the history.
- A rerun is a new `Simulation`, so an earlier failure is never overwritten.
- The test version and agent version come through the `Simulation`. The judge model and prompt version sit on the `Evaluation`, so every result shows the settings that produced it.
- `cited_turns` are indexes into the run's conversation, the same list the run page already shows.

## Structure

```
 Runner ── simulation done/failed ──▶ evaluate_simulation(id)
                                          │
                     1. execution check (code) ── unusable ──▶ Evaluation: execution_failed
                                          │ usable
                     2. judge (one LLM call): spec evaluator fields + numbered conversation
                                          │
                     3. validate reply (code) ── error / bad turns ──▶ Evaluation: inconclusive
                                          ▼
                                     Evaluation row ──▶ SQLite ──▶ FastAPI ──▶ React
```

## Screens

| Screen | Reviewer sees | Reviewer can |
|---|---|---|
| Test | An "Evaluation criteria" block: policy and expected outcome; per agent version, "v1: 0 pass / 3 fail / 0 inconclusive / 0 execution failure (n=3)"; an outcome column in the runs table | Run, open a run |
| Run | Outcome badge, reason, cited turns highlighted in the conversation (click to scroll), judge model and prompt version, earlier evaluations | Regrade, go to the test version |
| Results | Every run across tests: test, test version, agent version, outcome, when | Filter by test, agent version and outcome (plus test version and failure cause, set from the dashboard); open a run |
| Dashboard: Agent quality | Judge picker; pass rate bar per agent version; comparison table (test version × agent version, pass/graded, change); failures table with the latest reason | Open the matching runs or the test |
| Dashboard: System health | Completed / In Progress / Execution Failures / Not Graded; runs per hour by bucket; execution failures by cause; judges used and inconclusive runs; call duration per agent | Open the matching runs |

A fixed line under each comparison: *"Covers only this test's policy, over n runs; inconclusive and execution failures are excluded from pass counts."*

## Data flow

1. Before a run, the test page shows `policy_under_test` and `expected_outcome` as the grading criteria.
2. The run finishes → the runner calls `evaluate_simulation(simulation_id)`.
3. The execution check runs in code: `failed` or unfinished status, a missing report or recording, or no speech from the agent or the caller → execution failure with a fixed cause (`ExecutionFailureKind`), and the judge isn't called.
4. Otherwise the judge gets the evaluator fields, the caller's goal and the numbered conversation, tool calls included. It returns `situation_happened`, an outcome, `cited_turns` and a reason.
5. Code checks the reply: invalid after one retry, cited turns out of range, a pass or fail with no cited turns, or `situation_happened = false` with a pass or fail → inconclusive.
6. An `Evaluation` row is saved. `sims evaluate <id>` and the Regrade button rerun steps 3–6 and add a new row.
7. The test, run and results pages and the dashboard read the newest evaluation of each run. `GET /api/runs` also returns its reason, judge and failure cause; the dashboard computes everything in the browser from that list.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Evaluator | One LLM judge per run, against the test's evaluator fields | One test, one policy; other policies are other tests |
| Judge implementation | Our own `generate_structured` call, not LiveKit's `JudgeGroup` | Checked the SDK judges: pass/fail/maybe plus free text, one question per judge, need a rebuilt `ChatContext`. We need cited turns and the situation check in one call |
| Judge model | `openai/gpt-5.4` via LiveKit Inference | Offline, so the stronger model; already used by the Task 1 benchmark |
| Execution failure | Code, before the judge | No LLM cost, and a broken call can't be passed |
| Evidence | Cited turn indexes, checked by code | Clickable in the UI; citations of turns that don't exist are caught |
| Inconclusive | Caller off-goal, judge error, or bad citations | Missing evidence never becomes a pass |
| Code rules on tool calls | Not built (backlog) | One rule per policy; the judge already sees tool calls |
| Human override | Not built (backlog) | Not required by the brief |
| Storage | Immutable `Evaluation` rows | Regrading and judge changes keep the history |
| When it runs | Automatically after each run, in the runner's background task; also a CLI command and a button | Results appear without extra steps; regrading after a prompt change |
| Results filtering | Query parameters on `GET /api/runs` | Small data, plain SQL |
| Dashboard data | Computed in the browser from `GET /api/runs`, no new endpoint | Tens of runs; one source of truth |
| Pass rate | pass ÷ (pass + fail), one judge at a time | Execution failures and inconclusive runs say nothing about the agent; mixing judges makes comparisons meaningless |
| Failure cause | Recomputed from the run, not stored | Deterministic code on an immutable run; no schema change |
| Charts | Plain HTML bars, no chart library | Few runs; exact counts beside every bar |

## Risks

- The judge is wrong or inconsistent → cited turns make it checkable by hand; agreement is measured in M13.
- The judge marks off-goal calls as pass → `situation_happened` is required, and code enforces it.
- The caller rarely hits the situation → shows up as inconclusive, not as a false pass.
- A prompt change makes old results incomparable → the prompt version is stored and shown.

## Backlog

Code rules on tool calls, human override, several judge votes, LiveKit `JudgeGroup` export.

Other mistakes in a graded call: the judge grades only the test's policy, so a call can pass while breaking another rule (evaluator benchmark case 10: confirmed properly, then said "confirmed" after the booking failed). Fix: an optional "other concerns" note on the verdict, shown on the run page without changing the outcome.

## Your steps

None. The judge uses LiveKit Inference.
