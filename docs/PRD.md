# PRD: Voice-Agent Simulations

Requirements source: `docs/TAKEHOME.local.md`.

## Problem

A fix to one call can break another. Reviewers need repeatable voice tests, broad coverage, and trustworthy results.

## Use case

A restaurant booking agent with a knowledge base (hours, menu, policies) and two tools: `check_availability` and `create_booking`.

**Reported failure:** v1 books without confirming. v2 reads back the details and waits for a yes.

## Core entities

| Entity | Meaning |
|---|---|
| AgentVersion | A prompt and tools. Immutable. |
| Test | Caller goal, facts, fixed and varying parts, expected behavior. Editing creates a new version. |
| Run | One test version × one agent version. Retries never erase earlier results. |
| Evaluation | Checks with evidence and an outcome. |

**Outcomes:** `pass`, `behavioral_fail`, `execution_fail`, `inconclusive`. Missing evidence or an evaluator error is never a pass.

## Requirements

- **Task 1:** a transcript becomes a test the reviewer can edit, which then runs by voice against v1 and v2. The test stays linked to its source conversation.
- **Task 2:** fixed-rule checks plus a model judge, each with evidence. A results view drills down into a single run. Dashboards show v1 vs v2 and system health.
- **Task 3:** the agent's prompt, knowledge base and tools produce a coverage grid. The reviewer adjusts it, which generates a swarm. A reliable queue limits concurrency and handles retries, cancellation and recovery. Every run is accounted for.
- **Task 4 (bonus):** a command-line tool or MCP server for coding agents.

## Reliability targets

- 0 lost or double-counted runs.
- No run stuck `running` past its timeout.
- Recovery after a worker is killed.
- Capacity is measured and stated.

## Benchmarks

| Task | Measures |
|---|---|
| 1 | Does the test keep the original goal, facts and failure situation? Does v1 fail it and v2 pass it? |
| 2 | Agreement with hand labels; false-pass rate |
| 3 | Share of planted bugs caught; coverage of the grid |

## Out of scope

Authentication, multiple tenants, Kubernetes, a large scenario library, polished visual design.

## Milestones

### Foundation

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M0 | A basic LiveKit voice agent | You talk to it in console mode and it answers |
| [ ] | M1 | Restaurant prompt and knowledge base | It answers questions about hours and the menu correctly |
| [ ] | M2 | Booking tools with a fake store | It checks availability and creates a booking |
| [ ] | M3 | Two prompt versions, v1 and v2 | v1 books without confirming, v2 confirms first |
| [ ] | M4 | Caller agent | Two agents complete a booking call by voice |
| [ ] | M5 | Save each call | Transcript and tool calls are stored in SQLite |

### Task 1: Targeted voice tests

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M6 | Transcript → test | A pasted transcript becomes a saved test |
| [ ] | M7 | Run a test against v1 and v2 | Both runs are stored, linked to the test |
| [ ] | M8 | Website: tests | You can create, edit and run a test in the browser |
| [ ] | M9 | Benchmark: conversion fidelity | Score on ~6 failure transcripts against a rubric written beforehand, plus the share where v1 fails and v2 passes |

### Task 2: Evaluation and dashboards

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M10 | Evaluator | Each run gets an outcome with evidence |
| [ ] | M11 | Website: results | You can filter results and drill into a run's evidence |
| [ ] | M12 | Dashboards | Version comparison and system health views |
| [ ] | M13 | Benchmark: evaluator trust | Agreement with hand labels and the false-pass rate on ~20 runs, including injected faults |

### Task 3: Reliable swarm

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M14 | Swarm generation | Agent prompt → reviewed coverage grid → tests |
| [ ] | M15 | Benchmark: swarm quality | Share of planted bugs caught and coverage of the grid |
| [ ] | M16 | Reliable queue | Kill a worker mid-swarm, and every run is still accounted for (load and recovery evidence) |

### Delivery

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M17 | README and Loom | Submitted |

### Bonus: Task 4

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M18 | Coding-agent interface and benchmark | Claude Code fixes v1 using results |

M18 is optional. M16 is never cut.
