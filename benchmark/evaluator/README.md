# Benchmark: Can we trust the evaluator?

**Question:** does each simulated call get the right verdict, and can a reviewer rely on a pass?

## Criteria (set before measuring)

| Metric | Measures | Why it matters |
|---|---|---|
| Pass precision | Of the calls graded pass, how many really passed | A wrong pass lets a regression ship unnoticed: the costliest error in testing |
| Accuracy | Verdicts that match the label | Overall correctness, including fails, inconclusive calls and execution failures |
| Evidence hit rate | Pass or fail verdicts citing a turn that proves them | Reviewers can check a verdict instead of trusting it |
| Consistency | Cases given the same verdict in all 3 gradings | One grading per call is enough |

**Verdicts:** *pass* / *fail*: the agent followed or broke the policy. *Inconclusive*: the situation never came up, or the judge couldn't decide. *Execution failure*: the call itself broke.

## Cases and results

25 calls labeled by hand before grading, each graded 3 times (judge `openai/gpt-5.4`, prompt `09737e76`). \* = synthetic (a real call edited by hand, or written from scratch); the rest are real voice calls. ¹ = gray area, see below.

| # | Scenario | Policy under test | Expected | Graded (3 runs) |
|---|---|---|---|---|
| 01 | v1 books without confirming | Confirm before booking | fail | ✓ fail, fail, fail |
| 02 | v1 books without confirming | Confirm before booking | fail | ✓ fail, fail, fail |
| 03 | v2 confirms, then books | Confirm before booking | pass | ✓ pass, pass, pass |
| 04 | v2 asks for the name, confirms, then books | Confirm before booking | pass | ✓ pass, pass, pass |
| 05 | v1 refuses 12 guests, gives the events email | Parties over 8 go to events | pass | ✓ pass, pass, pass |
| 06 | v2 refuses 12 guests, gives the events email | Parties over 8 go to events | pass | ✓ pass, pass, pass |
| 07\* | Asks to confirm, but books before the caller answers | Confirm before booking | fail | ✓ fail, fail, fail |
| 08\* | Confirms time and party size, not the name | Confirm before booking | fail | ✓ fail, fail, fail |
| 09\* | Repeats the details but never asks | Confirm before booking | fail | ✓ fail, fail, fail |
| 10\* | Confirms properly; the booking then errors and the agent still says "confirmed" | Confirm before booking | pass ¹ | ✓ pass, pass, pass |
| 11\* | Mentions the limit, then books 12 anyway | Parties over 8 go to events | fail | ✓ fail, fail, fail |
| 12\* | Refuses 12 guests without the events contact | Parties over 8 go to events | fail ¹ | ✓ fail, fail, fail |
| 13\* | Caller only asks about the menu | Confirm before booking | inconclusive | ✓ inconcl., inconcl., inconcl. |
| 14\* | Caller hangs up before giving details | Confirm before booking | inconclusive | ✓ inconcl., inconcl., inconcl. |
| 15\* | Caller asks for 6 guests, within the limit | Parties over 8 go to events | inconclusive | ✓ inconcl., inconcl., inconcl. |
| 16\* | Call times out | Confirm before booking | execution failure | ✓ exec. fail, exec. fail, exec. fail |
| 17\* | No session report saved | Confirm before booking | execution failure | ✓ exec. fail, exec. fail, exec. fail |
| 18\* | No audio recording | Confirm before booking | execution failure | ✓ exec. fail, exec. fail, exec. fail |
| 19\* | Caller never speaks | Confirm before booking | execution failure | ✓ exec. fail, exec. fail, exec. fail |
| 20\* | Judge returns invalid replies | Confirm before booking | inconclusive | ✓ inconcl., inconcl., inconcl. |
| 21\* | Caller corrects the time; agent confirms again, books the new time | Confirm before booking | pass | ✓ pass, pass, pass |
| 22\* | Caller corrects the time; agent books the old time | Confirm before booking | fail | ✓ fail, fail, fail |
| 23\* | Caller declines at the confirmation; nothing booked | Confirm before booking | inconclusive ¹ | ✗ pass, pass, pass |
| 24\* | Caller declines; agent books anyway | Confirm before booking | fail | ✓ fail, fail, fail |
| 25 | v2 quotes the 2-hour cancellation rule, then says a 17:05 cancel of a 19:00 booking is free | Free cancellation up to 2 hours before | fail | ✓ fail, fail, fail |

| Pass precision | Accuracy | Evidence hit rate | Consistency |
|---|---|---|---|
| **18/21 (86%)** | 72/75 (96%) | 48/48 (100%) | 25/25 (100%) |

All 3 wrong passes are case 23, a gray area (below). Outside it, every pass was right.

**Judge changes in this run** (prompt `09737e76`; the last change splits the judge's working from a short reason for reviewers, after the swarm showed an agent quoting the cancellation rule and then misapplying it): the judge now checks the policy is *applied correctly to this caller*, not just stated (case 25); counts a call as untested when the policy never came into play, whatever the caller's goal; and writes its reasoning, including any arithmetic, before the verdict. Without the last change it repeated the agent's mistake and passed case 25.

## Gray areas

| Case | Question | Our call | What the judge did |
|---|---|---|---|
| 10 | A call follows the tested policy but breaks another rule. Pass or fail? | Pass: a test grades only its own policy; other rules need their own tests | Pass, as labeled |
| 12 | The agent refuses the large party but never refers it to events. Is the policy broken? | Fail: the referral is part of the policy | Fail, as labeled |
| 23 | The caller says no at the confirmation and nothing is booked. Did the agent confirm before booking? | Inconclusive: no booking, so the policy was never tested. Case 24 is the one that can fail | Pass every time: it reads "confirmed, then didn't book after a no" as following the policy. All 3 false passes come from this case |

## Limits

- 25 cases, one labeler (the author), no second opinion on labels.
- Synthetic cases are cleaner than real speech-to-text, and the author chose where they are hard.
- One judge model and prompt; verdicts on gray areas shift between runs.
- The evaluator reports nothing about mistakes outside the tested policy (case 10).

---

**Implementation.** Each folder in `cases/` is `<number>_<expected>_<scenario>` with `report.json` (the call's `chat_history`), `run.json` (spec, agent version, status, recording, a flag that breaks the judge) and `label.json` (expected verdict, key turns, reason). Specs are in `specs/`. `python -m benchmark.evaluator.run` loads each case into an in-memory database, calls the real `evaluate_simulation` 3 times, and saves `results.json`; `score.py` computes the metrics.
