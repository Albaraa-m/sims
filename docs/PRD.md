# PRD: Voice-Agent Simulations

Requirements source: `docs/TAKEHOME.local.md`.

## Problem

A fix to one call can break another. Reviewers need repeatable voice tests, broad coverage, and trustworthy results.

## Use case

A restaurant booking agent with a knowledge base (hours, menu, policies) and two tools: `check_availability` and `create_booking`.

**Reported failure:** v1 has the confirmation rule, but a conflicting "keep calls short" line makes it book without confirming. v2 removes the conflict, so it reads back the details and waits for a yes.

## Core entities

| Entity | Meaning |
|---|---|
| SourceConversation | The reported conversation, plus the reviewer's note on what went wrong. |
| AgentVersion | A prompt and tools. Immutable. |
| Test | One broken rule to check: a name, caller goal, facts, behavior, policy under test, expected outcome. Editing creates a new version. |
| Simulation | One call: test version × agent version. Retries never erase earlier results. |
| Evaluation | An outcome with a reason and cited turns, plus the judge that produced it. Regrading adds a row. |

**Outcomes:** `pass`, `fail`, `execution_failed`, `inconclusive`. Missing evidence or an evaluator error is never a pass.

## Requirements

- **Task 1:** a transcript becomes a test the reviewer can edit, which then runs by voice against v1 and v2. The test stays linked to its source conversation.
- **Task 2:** an execution check in code, then a model judge that cites turns as evidence. A results view drills down into a single run. Dashboards show v1 vs v2 and system health.
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
| [x] | M0 | A basic LiveKit voice agent | You talk to it in console mode and it answers |
| [x] | M1 | Restaurant prompt and knowledge base | It answers questions about hours and the menu correctly |
| [x] | M2 | Booking tools with a fake store | It checks availability and creates a booking |
| [x] | M3 | Two prompt versions, v1 and v2 | v1 books without confirming, v2 confirms first |
| [x] | M4 | Caller agent | Two agents complete a booking call by voice |
| [x] | M5 | Save each call | Transcript and tool calls are stored in SQLite |

### Task 1: Targeted voice tests

| | # | Milestone | Done when |
|---|---|---|---|
| [x] | M6 | Transcript → test | A pasted transcript becomes a saved test |
| [x] | M7 | Run a test against v1 and v2 | Both simulations are stored, linked to the test |
| [x] | M8 | Website: tests | You can create, edit and run a test in the browser |
| [x] | M9 | Benchmark: conversion fidelity | Score on ~6 failure transcripts against a rubric written beforehand |

### Task 2: Evaluation and dashboards

| | # | Milestone | Done when |
|---|---|---|---|
| [x] | M10 | Evaluator | Each run gets an outcome with evidence |
| [x] | M11 | Website: results | You can filter results and drill into a run's evidence |
| [x] | M12 | Dashboards | Version comparison and system health views |
| [x] | M13 | Benchmark: evaluator trust | Agreement with hand labels and the false-pass rate on ~20 runs, including injected faults |

### Task 3: Reliable swarm

| | # | Milestone | Done when |
|---|---|---|---|
| [x] | M14 | Swarm generation | Agent prompt → tests per policy, reviewed and saved as a swarm |
| [x] | M15 | Benchmark: swarm quality | Share of planted bugs caught and coverage of the grid |
| [x] | M16 | Reliable queue | Kill a worker mid-swarm, and every run is still accounted for (load and recovery evidence) |

### Delivery

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M17 | README and Loom | Submitted |

### Bonus: Task 4

| | # | Milestone | Done when |
|---|---|---|---|
| [ ] | M18 | Coding-agent interface and benchmark | Claude Code fixes v1 using results |

M18 is optional. M16 is never cut.
