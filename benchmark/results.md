# Benchmark: conversion fidelity

Converter `openai/gpt-5.4-mini`, judge `openai/gpt-5.4`. Facts and the clean control are checked in code; the other criteria by the judge.

## Failure cases

| Case | goal_kept | facts_kept | trigger_kept | policy_right |
|---|---|---|---|---|
| 01_no_confirmation | ✅ | ❌ | ❌ | ✅ |
| 02_party_over_limit | ❌ | ❌ | ✅ | ✅ |
| 03_after_last_slot | ❌ | ❌ | ✅ | ✅ |
| 04_wrong_cancellation_policy | ✅ | ❌ | ✅ | ❌ |
| 05_invented_menu_item | ❌ | ✅ | ✅ | ✅ |
| 06_next_day_booking | ❌ | ❌ | ❌ | ✅ |
| **Passed** | 2/6 | 1/6 | 4/6 | 5/6 |
| *Baseline* | 2/6 | 1/6 | 4/6 | 5/6 |

**Overall: 12/24 checks (50%).**

## Clean control

| Case | No test created |
|---|---|
| 07_clean_confirmed | ✅ no test was created |

## Why each check failed

- **01_no_confirmation / facts_kept**: missing: name=Khalid
- **01_no_confirmation / trigger_kept**: The trigger requires the caller to provide name, time, and party size and stay on until the booking is confirmed. This spec omits the caller’s name from the facts, so following only it would not reliably cause the trigger.
- **02_party_over_limit / goal_kept**: The generated goal matches the family celebration and large-party reservation intent, but it omits the key same-day timing in the answer key ('this afternoon'). Because the target aim is less specific on an important part of the request, it should not pass.
- **02_party_over_limit / facts_kept**: missing: name=Noura
- **03_after_last_slot / goal_kept**: The generated goal omits the key aim of a late booking after a flight, which is central to the answer key. It only mentions a generic table for tonight for two people, so it does not clearly describe the same caller intent.
- **03_after_last_slot / facts_kept**: missing: name=Faisal
- **04_wrong_cancellation_policy / facts_kept**: missing: name=Reem
- **04_wrong_cancellation_policy / policy_right**: The answer key’s policy is the specific rule that free cancellation is allowed only up to 2 hours before the booking. The spec’s policy_under_test instead describes how to state the deadline, not the same underlying cancellation rule.
- **05_invented_menu_item / goal_kept**: The answer key's goal is only to check whether the restaurant serves shawarma. The spec adds a different aim about dessert pricing, so it does not describe the same goal.
- **06_next_day_booking / goal_kept**: The answer key’s goal is specifically to book for tomorrow evening, while the spec only says an evening meal with no mention of tomorrow. That changes a key part of the caller’s aim, so it does not match.
- **06_next_day_booking / facts_kept**: missing: name=Saud, day=tomorrow
- **06_next_day_booking / trigger_kept**: The trigger requires explicitly asking for tomorrow rather than today, but the test spec only says Thursday and does not ensure that this is tomorrow relative to the call. A caller following only this spec would not necessarily cause the same failure.

<!-- Written by hand below; kept when the report is regenerated. -->
