# Benchmark: conversion fidelity

Converter `openai/gpt-5.4-mini`, judge `openai/gpt-5.4`. Facts and the clean control are checked in code; the other criteria by the judge.

## Failure cases

| Case | goal_kept | facts_kept | trigger_kept | policy_right |
|---|---|---|---|---|
| 01_no_confirmation | ✅ | ✅ | ✅ | ✅ |
| 02_party_over_limit | ✅ | ✅ | ✅ | ✅ |
| 03_after_last_slot | ❌ | ✅ | ✅ | ❌ |
| 04_wrong_cancellation_policy | ✅ | ✅ | ✅ | ✅ |
| 05_invented_menu_item | ✅ | ✅ | ✅ | ✅ |
| 06_next_day_booking | ✅ | ✅ | ✅ | ✅ |
| **Passed** | 5/6 | 6/6 | 6/6 | 5/6 |
| *Baseline* | 2/6 | 1/6 | 4/6 | 5/6 |

**Overall: 22/24 checks (92%).**

## Clean control

| Case | No test created |
|---|---|
| 07_clean_confirmed | ✅ no test was created |

## Why each check failed

- **03_after_last_slot / goal_kept**: The spec matches some details like today, party size, and name, but it omits the key aim of a late table after a flight. It also leaves out the crucial 22:00 request that defines the caller's goal.
- **03_after_last_slot / policy_right**: The answer key policy only states that bookings are on the hour from 13:00 to 21:00, while the spec adds an extra rule that bookings are only for today. Because the spec changes the rule rather than naming the same one exactly, it does not match.

<!-- Written by hand below; kept when the report is regenerated. -->

## What changed

The baseline row is the original converter outputs, scored with these criteria. The converter prompt then got four fixes, each from a miss in the baseline:

| Fix | Baseline miss | Now |
|---|---|---|
| Keep the caller's name in facts | Names dropped in all 5 booking cases | Kept in all |
| Keep days relative ("tomorrow", not "Thursday") | Case 06 became `day: Thursday`, so the test can't fail when run on a Thursday | `day: tomorrow` |
| One goal: the request that exposed the failure | Case 05 also asked about dessert | Shawarma only |
| State the rule with its numbers | Case 04 said "state the deadline exactly as given" | "free cancellation up to 2 hours before" |

**Caveat:** the fixes were made against these same 6 cases, so part of the gain is tuning. New cases written after the fixes would show how much carries over.

## Remaining misses

- **03 goal:** "Book a table for today for two people under Faisal." The 22:00 time is in the facts, so the failure still triggers; the judge wants it in the goal too. Borderline.
- **03 policy:** the spec adds "only for today" to the 13:00–21:00 rule. True, but not the rule that was broken. Borderline.

## One hit, one miss

- **Hit, 06 next-day booking:** the baseline's worst case (goal, facts and trigger all failed) now passes everything. With `day: tomorrow`, the caller asks for the day after the call whenever the test runs.
- **Miss, 03 after last slot:** see above; both failures are judgement calls on wording, not a lost trigger.

## Limits

- 6 failure cases and 1 clean control, all self-written; one run each, so results can change between runs.
- Fixes were tuned on the same cases (see caveat).
- No reported issue was given, the harder setting.
- Leaks aren't scored: the LLM judge couldn't grade them reliably. The converter prompt has the leak rules and the reviewer checks the caller fields.
- Scores the spec only, not whether the live caller acts it out, and not whether v1 fails and v2 passes (Task 2).
- The judge is strict; it fails when unsure.
