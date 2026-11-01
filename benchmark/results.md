# Benchmark: does a converted test keep the original failure?

A reviewer pastes a failed call with the restaurant booking agent. A model turns it
into a voice test: what the simulated caller wants and does, plus the rule the agent
broke. This benchmark checks whether that test still reproduces the original failure.

**Setup.** 6 call transcripts, each breaking a different agent rule, plus 1 clean
call. For each, an answer key (goal, facts, trigger, rule) was written by hand before
any conversion ran. Each generated test gets 4 pass/fail checks:

| Check | Passes if | Graded by |
|---|---|---|
| Goal | The caller wants the same thing as in the original call | LLM judge |
| Facts | Every key detail (name, time, party size, day) is kept | Code |
| Trigger | The caller still does what made the agent fail (e.g. asks for 22:00) | LLM judge |
| Policy | The test names the rule the agent actually broke | LLM judge |

The clean call passes if no test is created, so the converter can't score by
inventing failures. The judge is a stronger model than the converter, sees only the
fields it grades, and fails when unsure. Run it with `uv run python -m benchmark.run`.

## Results

Converter `openai/gpt-5.4-mini`; judge `openai/gpt-5.4`.

| What the agent did wrong | Goal | Facts | Trigger | Policy | Total |
|---|---|---|---|---|---|
| Booked without reading the details back for a yes | ✅ | ✅ | ✅ | ✅ | 4/4 |
| Booked 10 guests; parties over 8 go to the events team | ✅ | ✅ | ✅ | ✅ | 4/4 |
| Booked 22:00; the last slot is 21:00 | ❌ | ✅ | ✅ | ❌ | 2/4 |
| Said free cancellation up to 30 min before; the rule is 2 hours | ✅ | ✅ | ✅ | ✅ | 4/4 |
| Invented a shawarma dish and its price | ✅ | ✅ | ✅ | ✅ | 4/4 |
| Booked for tomorrow; bookings are same-day only | ✅ | ✅ | ✅ | ✅ | 4/4 |
| **After fixes** | 5/6 | 6/6 | 6/6 | 5/6 | **22/24** |
| *Before fixes* | 2/6 | 1/6 | 4/6 | 5/6 | **12/24** |

**Clean call** (none: the agent read back, got a yes, then booked): ✅ no test was created.

Each judgement's reason: `benchmark/results.json`; each generated test: `benchmark/outputs/`.

<!-- Written by hand below; kept when the report is regenerated. -->

## What the benchmark found, and the fixes

The first run (before fixes) exposed four converter problems. Each became one rule in the converter prompt:

| Problem in the generated tests | Fix |
|---|---|
| The caller asked for "Thursday" instead of "tomorrow", so the test can't fail when it runs on a Thursday | Keep days relative to the call |
| The caller's name was dropped from every booking | Keep the caller's name |
| A second, unrelated question (dessert) became part of the goal | Only the request that exposed the failure |
| The rule read "state the deadline exactly as given" instead of the rule itself | State the rule with its numbers |

**Remaining misses (late-slot case):** the goal leaves 22:00 to the facts, and the rule adds "only for today". Both are wording; the caller still asks for 22:00, so the failure still triggers.

## Limits

- **Small and self-written:** 7 cases, one run each; results can vary between runs.
- **Tuned on the same cases:** the fixes came from these misses, so part of the gain is tuning.
- **Leaks not scored:** whether the caller is told what's being tested. The LLM judge flagged allowed lines ("once they say it's booked, end the call"), so leaks are left to the converter's rules and the reviewer.
- **Spec only:** doesn't check that the live caller acts it out, or that v1 fails and v2 passes (Task 2).
- **One later prompt fix not re-run:** dropping unrelated questions from the caller's behavior (the dessert follow-up still in the menu case's output).
