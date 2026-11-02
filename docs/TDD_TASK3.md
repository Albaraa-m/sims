# Technical Design (TDD): Task 3 — Swarm Generation (M14)

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
