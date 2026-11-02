# Sawt Sims

A simulations product for voice agents: turn a reported failure into a repeatable test, stress the agent with a generated swarm of callers, and know whether a change can be trusted.

**Use case:** a restaurant booking agent. **Reported failure:** v1 books without confirming the details; v2 fixes it.
**Decisions it supports:** Is the bug real? Did the fix hold? Is it the agent or the system? What to fix next?

## How to start

```bash
cp .env.example .env               # add your LiveKit Cloud keys
uv sync && (cd frontend && npm install && npm run build)
uv run sims web --start-agents      # website + agents → http://localhost:8000
uv run sims worker --max-calls 2    # run in two terminals
```

1. **Task 1:** Tests → New test → paste [no_confirmation.txt](examples/transcripts/no_confirmation.txt) → run on v1 and v2.
2. **Task 2:** open a verdict and the Dashboard.
3. **Task 3:** Swarms → Create → Run, then on System health kill a worker or raise the fail rate.

## Architecture

```
Website ─▶ API ─▶ SQLite queue ─▶ workers ─▶ LiveKit room: agent ⇄ digital-human caller ─▶ judge ─▶ verdict
```

Workers claim simulations with leases; a dead worker's work is requeued, and failed attempts retry up to 3 times.

## How each task is answered

| Task | Question | Answer | Benchmark |
|---|---|---|---|
| 1. Targeted test | Does the test keep the failure without replaying it? | The goal, facts and trigger are fixed; the caller is a live agent, so wording and replies vary. The reviewer edits what the model inferred. | **19/24** checks kept the goal, facts, trigger and policy |
| 2. Evaluation | Can a reviewer trust a verdict? | Code checks the call happened, then a judge cites the turns behind every Pass or Fail. Four outcomes, so a broken system is never blamed on the agent. | **96%** accuracy, **86%** pass precision, **100%** cited evidence |
| 3. Swarm | Does the swarm find real problems? | Tests are generated from the restaurant's policies, one per rule, and reviewed before running. | **8/8** rules covered, **4/8** planted bugs caught, plus 1 real v2 bug |
| 3. Reliability | Does every simulation survive load and failure? | One queue row per simulation, leases, a concurrency cap, retries, refusing what doesn't fit. | **32/32** finished; a killed worker recovered in **63 s**; capacity **4** at once |

Details: [conversion](benchmark/conversion/results.md) · [evaluator](benchmark/evaluator/README.md) · [swarm](benchmark/swarm/README.md) · [reliability](docs/RELIABILITY.md)

## Key decisions

- **Own runner, not `lk agent simulate`:** we need four outcomes, cited evidence, retries and a website.
- **SQLite queue with leases:** survives crashes with no broker to run.
- **Strong model for grading (`gpt-5.4`):** grading runs offline, so accuracy wins over speed.

## Limitations

- Single machine; capacity is limited by laptop memory, not the design.
- One test per policy, so each rule is tested from one angle.
- The judge grades only the test's policy, with no human override.
- Left out on purpose: auth, multiple tenants, Kubernetes, polished visuals.
- Task 4 not attempted.
