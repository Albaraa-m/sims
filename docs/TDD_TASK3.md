# Technical Design (TDD): Task 3 — Swarm Generation (M14) and Reliable Queue (M16)

**Done when:** a reviewer creates a swarm in the browser (agent version, then which policies to test), reviews the generated tests, one per policy, edits or removes some, and saves. The swarm and its Ready tests are stored; nothing runs. Running a swarm (queue, admission cap, retries) is a later milestone.

## Core entities

```
┌──────────────────────┐ 1   N ┌──────────────────────────────┐
│ Swarm                │──────▶│ Test (existing)              │
├──────────────────────┤       ├──────────────────────────────┤
│ id, name             │       │ swarm_id?          (new)     │
│ agent_version        │       │ source_conversation_id?      │
│ policies  [str]      │       │   (now optional)             │
│ created_at           │       │ name, spec, status, …        │
└──────────────────────┘       └──────────────────────────────┘
```

- A **scenario** is an ordinary `Test`, one per policy: `name` is the policy's name, read like a test name ("Agent refers parties over 8 to the events team"), `spec.behavior` is the caller instruction, `spec.policy_under_test` is the policy copied verbatim from `Swarm.policies`.
- A policy has a `name` (the test name) and a `rule` (the full text, copied into `policy_under_test`).
- `Swarm.policies` holds the rules of the policies the reviewer kept.
- Generated tests have no source conversation; their fields are labelled Generated.

## Structure

```
 Create swarm (agent version) ─▶ POST /api/swarms/policies ─▶ extract policies (1 LLM call)
        │ reviewer unticks any policies
        ▼
 POST /api/swarms/generate ─▶ one test per policy (1 LLM call each, in parallel)   nothing saved
        │ proposal
        ▼
 Review page (browser state): edit / remove ─▶ Save ─▶ POST /api/swarms ─▶ Swarm + Ready Tests in SQLite
```

## Data flow

1. The reviewer opens Swarms → Create swarm and picks an agent version → Find policies.
2. `find_policies_of_agent_version` reads the restaurant's rules (`RESTAURANT_POLICIES`, knowledge base included), the same for every version, and the tool descriptions, and returns one policy per topic (about 8 for v2), each with a test-like name and its full rule.
3. The same dialog lists them, all ticked; the reviewer unticks any to skip, then Generate N tests (N = ticked policies).
4. `propose_swarm` writes one test per policy, one call each, choosing the caller behavior most likely to expose a breach; the test is named after the policy and its rule is copied verbatim for the judge.
5. The review page lists the tests: name, policy, caller behavior; Edit opens the full spec (labelled Generated / Edited); Remove drops it, and its policy with it.
6. Save stores the swarm and its tests as Ready in one transaction and opens the saved swarm page; each row links to its test page.
7. The Tests tab hides swarm tests unless "Show swarm tests" is on; an Origin column says where each test came from.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Scenario | An ordinary `Test` with `swarm_id` | Editing, versioning, running and grading are reused |
| Source | `RESTAURANT_POLICIES` (rules + knowledge base) plus the tools, for every version | Tests must expect what the restaurant wants, not what the tested prompt says: generated from v1's prompt, they would expect v1's bug |
| Test count | One test per policy; the reviewer only chooses policies | No counts to balance; no policy left untested |
| Policies | One per topic, found before generating | The reviewer decides coverage seeing what there is to cover |
| Test names | The policy's name, "Agent <does what>" | Readable from the list, like a test function name |
| Saving | Only on Save, as Ready | The reviewer confirms before anything is stored, as with New test |
| Policy grouping | Verbatim policy text, no extra field | One less field; the policy list on the swarm shows untested ones |
| Model | `openai/gpt-5.4`, as the judge | Offline, and the mini model dropped constraints on abstract rules (turned "answer only from the knowledge base" into a booking) |
| Tests tab | Swarm tests hidden by default | Keeps the curated regression suite readable |

## Risks

- One test per policy tests each rule from one angle only → "Generate another" per policy is in the backlog.

- Generated behaviors leak the test → the converter's leak rules in the prompt; the reviewer edits.
- The swarm tests the agent against its own prompt → a wrong prompt gives wrong expectations (listed as a limit).
- Migrating `sims.db` → one table rebuild that keeps every row; back up first.

## Your steps

None.

---

# M16 — Reliable queue

**Done when:** every requested call is accounted for under load and failure: a worker killed mid-swarm leaves no run stuck, its calls are interrupted, requeued and finished, and the totals still add up. Results: [RELIABILITY.md](RELIABILITY.md).

## Core entities

| Entity | Change |
|---|---|
| `Simulation` | One row per requested call. Statuses Queued · Running · Done · Failed ("Couldn't Run") · Cancelled; `attempt`, `max_attempts` (3), `lease_until`, `worker_id`, `attempts` log (`{attempt, status, reason, started_at, ended_at}`), `swarm_id`, `call_started_at` |
| `Evaluation` | `attempt`: a run's grade counts only for its latest attempt |
| `WorkerProcess` | Each live worker: id, pid, calls running, heartbeat; lets the website list and stop workers |
| `QueueSettings` | One row: the injected failure rate every worker reads |
| `RefusedStart` | Each start the queue refused, so refusals are counted |

## Structure

```
 Website / CLI ── admit (all or nothing; refusals recorded) ─▶ Simulation rows: queued
                                     │ one atomic UPDATE: oldest queued, if running < cap
                     ┌───────────────┼───────────────┐
                sims worker      sims worker      (any number; each ≤ --max-calls)
                     │ renew lease every 10 s; heartbeat; read injected failure rate
                     └─ room sim-{id}-{attempt} ─▶ evidence/{id}/{attempt}/ ─▶ grade
                                     ▲
     reaper in every worker, every 15 s: lease expired ─▶ interrupted ─▶ queued (attempt+1) or failed after 3
```

## Data flow

1. Run (test or swarm) admits one row per call; if the queue would pass its limit, the whole start is refused and recorded.
2. A worker claims the oldest queued row with one UPDATE that also checks the global cap, raising the attempt and taking a 60 s lease.
3. The attempt places the call in its own room under a hard deadline; the booking agent saves evidence under the attempt's folder.
4. Done: the evidence is stored only if the row is still running that attempt; then the call is graded. An ungradable call (e.g. the caller never spoke) is retried.
5. An error, an injected failure or a hang logs the attempt and requeues the call, or marks it failed after the third attempt.
6. A worker that dies stops renewing its lease; every other worker's reaper requeues its calls and closes their rooms.
7. Cancel turns a swarm's queued and running calls to Cancelled and closes their rooms; a late write from the attempt is ignored.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Queue | SQLite rows plus leases, no broker | Already there; survives a crash; simplest thing that works |
| Exactly-once counting | One row per call; retries are attempts on it | Nothing lost or counted twice |
| Stale writes | Every finishing write checks status and attempt | A dead worker coming back can't overwrite a retry or a cancel |
| Retries | Errors and ungradable calls, up to 3 attempts; never a pass, fail or inconclusive | Retrying a real verdict would hide agent behavior |
| Hangs | A hard deadline around each attempt | The lease alone can't catch a hung attempt in a live worker |
| Admission | Refuse the whole start, and record it | A half-started swarm is confusing; refused work must be counted |
| Locking | Transactions take the write lock up front and wait | Several processes share one file |
| Fault controls | Kill a worker and inject failures from System Health, only with `SIMS_FAULT_INJECTION=1` | Shows recovery in the UI without a terminal |

## Risks

- A dead worker's calls hold the cap for up to 75 s (lease plus reaper interval) before they're requeued.
- One SQLite file limits the queue to one machine.
- Laptop memory, not the account, is the first capacity limit.
