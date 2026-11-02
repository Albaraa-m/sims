# Benchmark: Can we trust the evaluator?

**Question:** does each simulated call get the right verdict, and does a call that shouldn't pass ever pass?

## Criteria (set before measuring)

| Metric | Measures |
|---|---|
| Precision per verdict | Of the calls graded X, how many really were X. Pass precision is the key one: a pass must be trustworthy |
| Recall per verdict | Of the calls that really were X, how many were graded X |
| Accuracy | Verdicts that match the label |
| Evidence hit rate | Verdicts citing at least one turn that proves them |
| Consistency | Calls getting the same verdict in 3 gradings |

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
| 23\* | Caller declines at the confirmation; nothing booked | Confirm before booking | inconclusive ² |
| 24\* | Caller declines; agent books anyway | Confirm before booking | fail |

¹ A test checks only its own policy. The false "confirmed" breaks a different rule, so failing here would mean the judge grades beyond its scope.

² No booking happened, so "confirm before booking" was never tested. Case 24, where the agent books anyway, is the one that can fail.

## Results

24 cases × 3 gradings = 72 verdicts, judge `openai/gpt-5.4`, prompt `da9eed8d`.

| Verdict | Precision | Recall |
|---|---|---|
| pass | **15/15 (100%)** | 15/18 (83%) |
| fail | 25/28 (89%) | 25/27 (93%) |
| inconclusive | 15/17 (88%) | 15/15 (100%) |
| execution failure | 12/12 (100%) | 12/12 (100%) |

Accuracy 67/72 (93%) · evidence hit rate 43/43 (100%) · consistency 23/24 cases (96%).

| Expected ↓ / Got → | pass | fail | inconclusive | execution failure |
|---|---|---|---|---|
| pass | 15 | 3 | 0 | 0 |
| fail | 0 | 25 | 2 | 0 |
| inconclusive | 0 | 0 | 15 | 0 |
| execution failure | 0 | 0 | 0 | 12 |

**Every pass was right**, and every miss leans cautious: to fail or inconclusive, never to pass.

| Case | Got | Why |
|---|---|---|
| 10 | fail ×3 | The judge goes beyond the policy and fails the false "confirmed" after the tool error (an earlier run gave pass, fail, fail) |
| 12 | fail, inconclusive ×2 | Unsure whether refusing without the events contact breaks the policy; never a pass |

**Works:** all real v1/v2 calls, subtle failures (booked before the yes, partial confirmation, wrong time after a correction), off-script and declining callers, and every injected fault, each citing the right turns.

## Limits

- 24 cases, one labeler (the author), no second opinion on labels.
- Synthetic cases are cleaner than real speech-to-text, and the author chose where they are hard.
- One judge model and prompt; results may not carry over to others.
- The evaluator checks only the test's policy; other mistakes in the same call go unreported (case 10).

---

**Implementation.** Each folder in `cases/` is `<number>_<expected>_<scenario>` with `report.json` (the call's `chat_history`), `run.json` (spec, agent version, status, recording, a flag that breaks the judge) and `label.json` (expected verdict, key turns, reason). Specs are in `specs/`. The script loads each case into an in-memory database and calls the real `evaluate_simulation` 3 times.
