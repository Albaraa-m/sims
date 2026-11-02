# Benchmark: Can we trust the evaluator?

**Question:** does each simulated call get the right verdict, and does a call that shouldn't pass ever pass?

## Criteria (set before measuring)

| Metric | Measures |
|---|---|
| False-pass rate | Calls graded pass that should not pass |
| Accuracy | Verdicts that match the label |
| Evidence hit rate | Verdicts citing at least one turn that proves them |
| Consistency | Calls getting the same verdict in 3 gradings |
| Fault handling | Broken calls never graded as agent behavior |

**Verdicts:** *pass* / *fail*: the agent followed or broke the policy. *Inconclusive*: the situation never came up, or the judge couldn't decide. *Execution failure*: the call itself broke.

## Cases

24 calls, labeled by hand before grading. \* = synthetic (a real call edited by hand, or written from scratch); the rest are real voice calls.

| # | Scenario | Policy under test | Expected |
|---|---|---|---|
| 01 | v1 books without confirming | Confirm before booking | fail |
| 02 | v1 books without confirming | Confirm before booking | fail |
| 03 | v2 confirms, then books | Confirm before booking | pass |
| 04 | v2 asks for the name, confirms, then books | Confirm before booking | pass |
| 05 | v1 refuses 12 guests, gives the events email | Parties over 8 go to events | pass |
| 06 | v2 refuses 12 guests, gives the events email | Parties over 8 go to events | pass |
| 07\* | Asks to confirm, but books before the caller answers | Confirm before booking | fail |
| 08\* | Confirms time and party size, not the name | Confirm before booking | fail |
| 09\* | Repeats the details but never asks | Confirm before booking | fail |
| 10\* | Confirms properly; the booking then errors and the agent still says "confirmed" | Confirm before booking | pass ¹ |
| 11\* | Mentions the limit, then books 12 anyway | Parties over 8 go to events | fail |
| 12\* | Refuses 12 guests without the events contact | Parties over 8 go to events | fail |
| 13\* | Caller only asks about the menu | Confirm before booking | inconclusive |
| 14\* | Caller hangs up before giving details | Confirm before booking | inconclusive |
| 15\* | Caller asks for 6 guests, within the limit | Parties over 8 go to events | inconclusive |
| 16\* | Call times out | Confirm before booking | execution failure |
| 17\* | No session report saved | Confirm before booking | execution failure |
| 18\* | No audio recording | Confirm before booking | execution failure |
| 19\* | Caller never speaks | Confirm before booking | execution failure |
| 20\* | Judge returns invalid replies | Confirm before booking | inconclusive |
| 21\* | Caller corrects the time; agent confirms again, books the new time | Confirm before booking | pass |
| 22\* | Caller corrects the time; agent books the old time | Confirm before booking | fail |
| 23\* | Caller declines at the confirmation; nothing booked | Confirm before booking | pass |
| 24\* | Caller declines; agent books anyway | Confirm before booking | fail |

¹ A test checks only its own policy. The false "confirmed" breaks a different rule, so failing here would mean the judge grades beyond its scope.

## Results

24 cases × 3 gradings = 72 verdicts, judge `openai/gpt-5.4`, prompt `da9eed8d`.

| Metric | Result |
|---|---|
| False-pass rate | **0/51 (0%)** |
| Accuracy | 66/72 (92%) |
| Evidence hit rate | 44/44 (100%) |
| Consistency | 22/24 cases (92%) |
| Fault handling | 12/12 (100%) |

| Expected ↓ / Got → | pass | fail | inconclusive | execution failure |
|---|---|---|---|---|
| pass | 16 | 2 | 3 | 0 |
| fail | 0 | 26 | 1 | 0 |
| inconclusive | 0 | 0 | 12 | 0 |
| execution failure | 0 | 0 | 0 | 12 |

Every miss leans cautious: nothing that should fail or be set aside was ever passed.

| Case | Got | Why |
|---|---|---|
| 10 | pass, fail, fail | The judge drifted outside the policy and failed the false "confirmed" after the tool error. Inconsistent grading on calls that break a second rule |
| 12 | fail, fail, inconclusive | Once unsure whether refusing without the events contact counts; still never a pass |
| 23 | inconclusive ×3 | The caller declined, so nothing was booked; the judge reads "confirm before booking" as untested when no booking happens. Arguably a label question: does "nothing booked after a no" prove the policy? |

**Works:** all real v1/v2 calls, subtle failures (booked before the yes, partial confirmation, wrong time after a correction), off-script callers and every injected fault were graded correctly in all 3 gradings, each citing the right turns.

## Limits

- 24 cases, one labeler (the author), no second opinion on labels.
- Synthetic cases are cleaner than real speech-to-text, and the author chose where they are hard.
- One judge model and prompt; results may not carry over to others.
- The evaluator checks only the test's policy; other mistakes in the same call go unreported (case 10).

---

**Implementation.** Each folder in `cases/` is `<number>_<expected>_<scenario>` with `report.json` (the call's `chat_history`), `run.json` (spec, agent version, status, recording, a flag that breaks the judge) and `label.json` (expected verdict, key turns, reason). Specs are in `specs/`. The script loads each case into an in-memory database and calls the real `evaluate_simulation` 3 times.
