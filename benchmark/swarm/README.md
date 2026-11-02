# Benchmark: Does the swarm catch broken rules?

## Summary

We scored the swarm on two things: **policy coverage** (does every rule get a test?) and **bug catching** (do those tests notice when the agent breaks a rule?). To measure bug catching, we broke the agent on purpose, one rule at a time.

| Policy coverage | Bug catching |
|---|---|
| **8/8** rules have a test | **4/8** broken agents caught |

Of the 4 misses, **2 are the swarm's fault**: the test asked a question that never exposes the bug. One is the benchmark's fault, and one is **a real bug in v2** the swarm found.

**Next fix:** have the generator double-check each test ("would a broken agent fail this?") and rewrite it if not.

## How it works

1. **Write down the rules** the agent must follow (8 of them), by hand, before scoring.
2. **Break each rule** in its own copy of the agent ([planted_bugs.py](../../agents/booking/planted_bugs.py)), e.g. "books parties of up to 12" instead of 8.
3. **Generate a swarm** from the agent's instructions, exactly as the website does.
4. **Run each rule's test twice**: on the broken copy and on the correct agent (v2), as real voice calls.

A test **catches** a bug when it **fails the broken agent and passes the correct one**. Any other result means the test couldn't tell them apart:

| Broken agent | Correct agent | Meaning |
|---|---|---|
| Fails | Passes | ✓ Caught the bug |
| Passes | Passes | Test too weak: it never ran into the bug |
| Fails | Fails | Test is wrong, or the "correct" agent has the bug too |
| No verdict | No verdict | The situation never came up in the call |

## Results

| # | Rule | How we broke it | Result | Why |
|---|---|---|---|---|
| 1 | Answer only from known information | Makes up dishes | ✗ Too weak | Asked about bread, not a dish, so the bug never showed |
| 2 | Bookings are for today only | Books up to 7 days ahead | ✓ Caught | |
| 3 | Bookings on the hour, 13:00 to 21:00 | Books 12:00 to 23:00 | ✗ Too weak | Benchmark's fault: we ran the "on the hour" test (19:30), not the "13:00 to 21:00" one |
| 4 | Check availability before booking | Skips the check | ✗ No verdict | Asked for 22:00, which was refused before any booking |
| 5 | Read back details, book only after a yes | v1 as is (the real bug) | ✓ Caught | |
| 6 | Parties over 8 go to the events team | Books up to 12 | ✓ Caught | |
| 7 | Tables held 15 minutes | Holds 30 minutes | ✓ Caught | |
| 8 | Free cancellation up to 2 hours before | Free up to 30 minutes | ✗ Both fail | **v2 has this bug too**: it quotes the rule but doesn't apply it to the caller's time |

## Limits

- Each test ran once per agent (16 calls) to keep it cheap. Voice calls vary, so a result can flip between runs.
- One generated swarm; another may ask different questions.
- The same person wrote the agent, the rules and the bugs; real bugs may be subtler.
- Pass and fail verdicts come from the evaluator, benchmarked separately (Task 2).

---

**Run it:** `SIMS_AGENT_NAME_SUFFIX=-bench uv run python -m benchmark.swarm.run`. Results, including every test and the judge's reasons, are saved to `results.json`. The benchmark starts its own agent servers, so a running website never takes its calls.
