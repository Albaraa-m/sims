# Technical Design (TDD): Task 3 — Swarm Generation (M14)

**Done when:** a reviewer creates a swarm in the browser (agent version + number of tests), reviews the generated scenarios grouped by policy, edits or removes some, and saves. The swarm and its Ready tests are stored; nothing runs. Running a swarm (queue, admission cap, retries) is a later milestone.

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

- A **scenario** is an ordinary `Test`: `name` is the short label ("Says 6, then actually 11"), `spec.behavior` is the caller instruction, `spec.policy_under_test` is the policy copied verbatim from `Swarm.policies`.
- Grouping by policy is grouping by `policy_under_test`; a test whose policy the reviewer edited shows under its own heading.
- Generated tests have no source conversation; their fields are labelled Generated.

## Structure

```
 Create swarm (agent version, N tests)
        │ POST /api/swarms/generate            nothing saved
        ▼
 extract policies (1 LLM call) ─▶ split N across policies (code) ─▶ scenarios per policy (1 LLM call each, in parallel)
        │ proposal
        ▼
 Review page (browser state): edit / remove ─▶ Save ─▶ POST /api/swarms ─▶ Swarm + Ready Tests in SQLite
```

## Data flow

1. The reviewer opens Swarms → Create swarm, picks an agent version and the number of tests.
2. `propose_swarm` reads that version's instructions (restaurant policies and knowledge base included) and its tool descriptions, and extracts the policies.
3. Code splits the number of tests evenly across policies, remainder to the first; if there are fewer tests than policies, a warning names the untested ones.
4. One call per policy writes exactly its share of scenarios with different caller behaviors; code copies the policy text verbatim, trims extras and retries once if short.
5. The review page shows the proposal grouped by policy: each row is the name and behavior; Edit opens the full spec; Remove drops it.
6. Save stores the swarm and its tests as Ready in one transaction and opens the saved swarm page; each row links to its test page.
7. The Tests tab hides swarm tests unless "Show swarm tests" is on; an Origin column says where each test came from.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Scenario | An ordinary `Test` with `swarm_id` | Editing, versioning, running and grading are reused |
| Source | The chosen version's prompt plus its tools | The brief: the swarm uses the agent's instructions, policies, knowledge and tools |
| Test count | Set by the reviewer, enforced in code | The LLM doesn't decide how much runs |
| Saving | Only on Save, as Ready | The reviewer confirms before anything is stored, as with New test |
| Policy grouping | Verbatim policy text, no extra field | One less field; the policy list on the swarm shows untested ones |
| Model | The converter's (`openai/gpt-5.4-mini`) | Offline generation, same leak rules as conversion |
| Tests tab | Swarm tests hidden by default | Keeps the curated regression suite readable |

## Risks

- Generated behaviors leak the test → the converter's leak rules in the prompt; the reviewer edits.
- The swarm tests the agent against its own prompt → a wrong prompt gives wrong expectations (listed as a limit).
- Migrating `sims.db` → one table rebuild that keeps every row; back up first.

## Your steps

None.
