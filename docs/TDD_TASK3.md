# Technical Design (TDD): Task 3 — Swarm Generation (M14)

**Done when:** a reviewer creates a swarm in the browser (agent version, then which policies to test and how many tests each, within a maximum), reviews the generated scenarios grouped by policy, edits or removes some, and saves. The swarm and its Ready tests are stored; nothing runs. Running a swarm (queue, admission cap, retries) is a later milestone.

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

- A **scenario** is an ordinary `Test`: `name` reads "Caller <does what> → agent <does what>", `spec.behavior` is the caller instruction, `spec.policy_under_test` is the policy copied verbatim from `Swarm.policies`.
- Grouping by policy is grouping by `policy_under_test`; a test whose policy the reviewer edited shows under its own heading.
- `Swarm.policies` holds only the policies the reviewer chose, each with at least one test.
- Generated tests have no source conversation; their fields are labelled Generated.

## Structure

```
 Create swarm (agent version) ─▶ POST /api/swarms/policies ─▶ extract policies (1 LLM call)
        │ reviewer ticks policies, sets tests per policy (1–3) within a maximum
        ▼
 POST /api/swarms/generate ─▶ tests per policy (1 LLM call each, in parallel)     nothing saved
        │ proposal
        ▼
 Review page (browser state): edit / remove ─▶ Save ─▶ POST /api/swarms ─▶ Swarm + Ready Tests in SQLite
```

## Data flow

1. The reviewer opens Swarms → Create swarm and picks an agent version → Find policies.
2. `find_policies_of_agent_version` reads that version's instructions (restaurant policies and knowledge base included) and its tool descriptions, and returns one policy per topic (about 8 for v2).
3. The same dialog lists them, all ticked, with a **maximum tests** field. Each ticked policy gets at least 1 test and at most 3; the maximum is spread over them, and counts the reviewer types are kept. If the ticked policies need more than the maximum, a warning offers "Raise maximum to N", or the reviewer unticks policies; Generate stays disabled until the total fits.
4. `propose_swarm` writes exactly the chosen number of tests per policy, one call per policy; code copies the policy text verbatim, trims extras and tops up once if short.
5. The review page shows the proposal grouped by policy: each row is the name and behavior; Edit opens the full spec (labelled Generated / Edited); Remove drops it. A policy whose tests are all removed isn't saved.
6. Save stores the swarm and its tests as Ready in one transaction and opens the saved swarm page; each row links to its test page.
7. The Tests tab hides swarm tests unless "Show swarm tests" is on; an Origin column says where each test came from.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Scenario | An ordinary `Test` with `swarm_id` | Editing, versioning, running and grading are reused |
| Source | The chosen version's prompt plus its tools | The brief: the swarm uses the agent's instructions, policies, knowledge and tools |
| Test count | Reviewer picks policies and tests per policy (1–3) within a maximum of up to 40 | No policy is left untested; the LLM doesn't decide how much runs |
| Policies | One per topic, found before generating | The reviewer decides coverage seeing what there is to cover |
| Test names | "Caller <does what> → agent <does what>" | Readable from the list, like a test function name |
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
