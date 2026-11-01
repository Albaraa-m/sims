# Benchmark: conversion fidelity

Converter `openai/gpt-5.4-mini`, judge `openai/gpt-5.4`. Facts and the clean control are checked in code; the other criteria by the judge.

## Failure cases

| Case | goal_kept | facts_kept | situation_kept | policy_right | leak_free |
|---|---|---|---|---|---|
| 01_no_confirmation | ✅ | ❌ | ✅ | ✅ | ✅ |
| 02_party_over_limit | ✅ | ❌ | ❌ | ✅ | ❌ |
| 03_after_last_slot | ❌ | ❌ | ❌ | ✅ | ❌ |
| 04_wrong_cancellation_policy | ✅ | ❌ | ✅ | ❌ | ❌ |
| 05_invented_menu_item | ❌ | ✅ | ❌ | ✅ | ❌ |
| 06_next_day_booking | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Passed** | 3/6 | 1/6 | 2/6 | 5/6 | 2/6 |

**Overall: 13/30 checks (43%).**

## Clean control

| Case | No test created |
|---|---|
| 07_clean_confirmed | ✅ no test was created |

## Why each check failed

- **01_no_confirmation / facts_kept**: missing: name=Khalid
- **02_party_over_limit / facts_kept**: missing: name=Noura
- **02_party_over_limit / situation_kept**: The spec leads the caller to accept and confirm a booking if offered, but it does not encode the key situation that parties over 8 must be refused and redirected to the events team. So it does not reliably recreate the answer key's failure scenario.
- **02_party_over_limit / leak_free**: The behavior leaks the expected success path by saying to end the call once they confirm the booking, which hints at what the agent should do and the tested outcome. Caller fields should stay neutral about whether a booking will be completed.
- **03_after_last_slot / goal_kept**: The spec omits the key aim of getting a late table after a flight, specifically around 22:00. 'For tonight for two people' is too broad and could match many different booking requests.
- **03_after_last_slot / facts_kept**: missing: name=Faisal
- **03_after_last_slot / situation_kept**: The spec does not include the key behavior of asking again if 22:00 is refused; instead it assumes the booking succeeds and ends after confirmation. A caller following only this spec would not recreate the answer key’s refusal-and-pushback situation.
- **03_after_last_slot / leak_free**: The behavior says "Once they say the table is booked," which reveals the expected successful outcome and thus hints at the failure being tested. It should stay caller-only and not assume the booking succeeds.
- **04_wrong_cancellation_policy / facts_kept**: missing: name=Reem
- **04_wrong_cancellation_policy / policy_right**: The answer key’s policy is the specific rule that free cancellation is allowed only up to 2 hours before the booking. The spec’s policy_under_test describes how to state a policy, not the same cancellation rule itself.
- **04_wrong_cancellation_policy / leak_free**: The caller fields leak the tested restaurant policy by asking specifically when a reservation can be canceled without paying, which reveals the free-cancellation rule under test. They otherwise stay in caller perspective, but this policy detail makes it fail.
- **05_invented_menu_item / goal_kept**: The shared part about checking whether the restaurant serves shawarma matches, but the spec adds a separate goal about dessert pricing. That changes the aim beyond the answer key's single goal, so it should not pass.
- **05_invented_menu_item / situation_kept**: The generated spec changes the scenario by adding a second goal about dessert pricing, which is not in the answer key’s situation. Because the caller is instructed they may continue past the shawarma question, it does not cleanly recreate the same situation from the answer key.
- **05_invented_menu_item / leak_free**: The goal adds a second test target about dessert pricing that is not caller-natural and hints at what is being checked beyond the caller’s simple intent. It also shifts away from the answer key’s caller-only objective of asking whether shawarma is served.
- **06_next_day_booking / goal_kept**: The answer key's goal is specifically to book a table for tomorrow evening, while the spec only says an evening meal and omits the key intent that it is for tomorrow. That makes the aim less specific and not clearly the same request.
- **06_next_day_booking / facts_kept**: missing: name=Saud, day=tomorrow
- **06_next_day_booking / situation_kept**: The key failure depends on the caller requesting a booking for tomorrow when the restaurant only accepts same-day reservations. The generated spec instead fixes the day to Thursday and omits the crucial tomorrow-vs-today situation, so a caller following it would not reliably recreate the same failure.

<!-- Written by hand below; kept when the report is regenerated. -->

## Hand check of the judge

I re-labelled all 24 judged checks (goal, situation, policy and leaks for the 6 failure cases) by reading each spec against its answer key. These labels are Claude's and still need the user's review.

| Case | goal | situation | policy | leaks | Disagreements |
|---|---|---|---|---|---|
| 01 | ✅ | ✅ | ✅ | ✅ | none |
| 02 | ✅ | ✅ | ✅ | ✅ | situation, leaks: the caller still asks for 10; "end the call once they confirm the booking" is an allowed caller-only line |
| 03 | ✅ | ✅ | ✅ | ✅ | goal, situation, leaks: 22:00 is in the facts, so the failure is recreated; the missing "push back once" is extra, not the trigger |
| 04 | ✅ | ✅ | ❌ | ✅ | leaks: asking about free cancellation *is* the caller's goal |
| 05 | ❌ | ✅ | ✅ | ✅ | situation, leaks: the shawarma question is still asked; a dessert question is natural caller talk |
| 06 | ❌ | ❌ | ✅ | ✅ | none |

**Agreement: 16/24 (67%).** Every disagreement is the judge failing a check that passes by hand: the judge is strict, not lenient, so it under-reports quality rather than hiding misses. Its leak checks are the least reliable (agreement 2/6): it reads the allowed "once they say it's booked, end the call" as a leak, despite the examples in its prompt. By hand the judged criteria pass 20/24.

## One hit, one miss

- **Hit, 01 no confirmation (v1's bug):** goal, situation, policy and leaks all pass. The behavior has the caller confirm a read-back and hang up once booked, so a v1 agent can book without confirming and a v2 agent reads back first; the test separates the two without telling the caller what is tested.
- **Miss, 06 next-day booking:** the converter turned "tomorrow, Thursday" into the fact `day: Thursday` and the goal "an evening meal". Run on a Thursday, the caller asks for today and the failure can't happen. Relative dates must stay relative; a converter prompt rule ("keep days relative to the call, like tomorrow") should fix it.

## Findings for the converter

1. **Names dropped in 5 of 5 booking cases.** The prompt keeps only "facts the failure depended on", so names go. The caller then invents a name, which doesn't change the failure; the answer keys were stricter than needed. Facts kept is 5/6 if names are ignored.
2. **Relative dates become weekdays** (case 06, above).
3. **Vague policy** (case 04): "state the deadline exactly as given in the policy" doesn't say the rule is 2 hours; the evaluator has to find it in `expected_outcome`.
4. **Extra goals** (case 05): the caller also asks about dessert, copied from the transcript's second question.
5. **Clean call recognised:** no test was created for the clean control.

## Limits

- 6 failure cases and 1 clean control, all self-written; one run each, so results can change between runs.
- No reported issue was given, the harder setting; the website lets reviewers add one.
- Scores the spec only, not whether the live caller acts it out, and not whether v1 fails and v2 passes (Task 2).
- The judge (`openai/gpt-5.4`) is stricter than the hand labels; the hand labels are one reviewer's.
