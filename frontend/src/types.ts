export type TestStatus = 'draft' | 'ready'

export type TestRow = {
  id: string
  name: string
  version: number
  status: TestStatus
  // Set for generated tests; null for tests made from a transcript.
  swarm_id: string | null
  created_at: string
}

export type TestSpec = {
  goal: string
  facts: Record<string, string>
  behavior: string
  policy_under_test: string
  expected_outcome: string
}

export type InferredTest = {
  reason: string
  name: string | null
  spec: TestSpec | null
}

export type CreateTestRequest = {
  transcript: string
  reported_issue: string | null
  agent_version: string | null
  name: string
  spec: TestSpec
  inferred_spec: TestSpec | null
}

export type TestDetail = TestRow & {
  spec: TestSpec
  inferred: TestSpec | null
}

export type RunStatus = 'running' | 'done' | 'failed'

export type Outcome = 'pass' | 'fail' | 'execution_failed' | 'inconclusive'

export type RunRow = {
  id: string
  test_id: string
  test_name: string
  test_version: number
  agent_version: string
  status: RunStatus
  started_at: string
  ended_at: string | null
  // Null until the run is graded.
  outcome: Outcome | null
  reason: string | null
  judge_model: string | null
  judge_prompt_version: string | null
  // Set only for execution failures, so they can be grouped.
  execution_failure_kind: ExecutionFailureKind | null
}

export type ExecutionFailureKind =
  | 'call_failed'
  | 'call_unfinished'
  | 'no_report'
  | 'no_recording'
  | 'agent_silent'
  | 'caller_silent'

export type EvaluationDetail = {
  outcome: Outcome
  situation_happened: boolean | null
  cited_turns: number[]
  reason: string
  judge_model: string | null
  judge_prompt_version: string | null
  error: string | null
  created_at: string
}

export type ConversationEntry =
  | { kind: 'speech'; speaker: string; text: string }
  | { kind: 'tool_call'; name: string; arguments: string; output: string | null }

export type RunDetail = {
  id: string
  agent_version: string
  status: RunStatus
  started_at: string
  ended_at: string | null
  error: string | null
  test_id: string | null
  test_name: string | null
  test_version: number | null
  conversation: ConversationEntry[]
  has_recording: boolean
  // Newest first; the first one is the run's current outcome.
  evaluations: EvaluationDetail[]
}

export type Scenario = {
  name: string
  spec: TestSpec
}

// A rule found in the agent's instructions; each becomes one test, named by name.
export type Policy = {
  name: string
  rule: string
}

export type FoundPolicies = {
  agent_version: string
  policies: Policy[]
}

export type SwarmProposal = {
  agent_version: string
  policies: string[]
  scenarios: Scenario[]
}

export type SaveSwarmRequest = {
  name: string
  agent_version: string
  policies: string[]
  scenarios: Scenario[]
}

export type SwarmRow = {
  id: string
  name: string
  agent_version: string
  test_count: number
  created_at: string
}

export type SwarmTest = {
  id: string
  name: string
  version: number
  status: TestStatus
  spec: TestSpec
}

export type SwarmDetail = SwarmRow & {
  // Every policy found, so untested ones show too; tests group by policy_under_test.
  policies: string[]
  tests: SwarmTest[]
}
