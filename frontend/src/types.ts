export type TestStatus = 'draft' | 'ready'

export type TestRow = {
  id: string
  name: string
  version: number
  status: TestStatus
  // Set for generated tests; null for tests made from a transcript.
  swarm_id: string | null
  // Set for swarm tests promoted into the regression suite.
  promoted_from_swarm_id: string | null
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

export type RunStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled'

export type AttemptLogEntry = {
  attempt: number
  status: 'completed' | 'failed' | 'interrupted'
  reason: string | null
  started_at: string | null
  ended_at: string | null
}

export type Outcome = 'pass' | 'fail' | 'execution_failed' | 'inconclusive'

export type RunRow = {
  id: string
  test_id: string
  // Shared by every version of the test, so a test can be counted once.
  test_lineage_id: string
  // The swarm that queued the run, if any.
  swarm_id: string | null
  test_name: string
  test_version: number
  agent_version: string
  status: RunStatus
  // The current attempt, 0 while queued for the first time; past ones are in attempts.
  attempt: number
  attempts: AttemptLogEntry[]
  // When the run was requested; call_started_at is when its current attempt began.
  started_at: string
  call_started_at: string | null
  ended_at: string | null
  // Null until the latest attempt is done and graded.
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
  // The judge's step-by-step working behind reason; null when no judge was asked.
  reasoning: string | null
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
  attempt: number
  max_attempts: number
  attempts: AttemptLogEntry[]
  started_at: string
  call_started_at: string | null
  ended_at: string | null
  error: string | null
  test_id: string | null
  test_name: string | null
  test_version: number | null
  // What the judge grades against, from the test's spec.
  policy_under_test: string | null
  expected_outcome: string | null
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
  promoted_from_swarm_id: string | null
}

export type SwarmDetail = SwarmRow & {
  // Every policy found, so untested ones show too; tests group by policy_under_test.
  policies: string[]
  tests: SwarmTest[]
}

export type WorkerRow = {
  id: string
  pid: number
  max_calls: number
  calls_running: number
  heartbeat_seconds_ago: number
}

// A worker that stopped heartbeating while its simulations were still running.
export type StoppedWorkerRow = {
  id: string
  simulations_recovering: number
  seconds_until_requeued: number
}

export type QueueState = {
  queued: number
  running: number
  max_running: number
  max_queued: number
  longest_wait_seconds: number | null
  fail_rate: number
  // Kill and failure injection are offered only when the website was started for a demo.
  fault_injection_enabled: boolean
  refused_starts_last_hour: number
  refused_simulations: number
  workers: WorkerRow[]
  stopped_workers: StoppedWorkerRow[]
}

export type SwarmRunStatus = 'queued' | 'running' | 'completed' | 'cancelled'

// One press of Run swarm; id "earlier" groups calls queued before runs were numbered.
export type SwarmRunSummary = {
  id: string
  number: number
  created_at: string | null
  agent_versions: string[]
  status: SwarmRunStatus
  total: number
  status_counts: Partial<Record<RunStatus, number>>
  outcome_counts: Partial<Record<Outcome, number>>
}

export type QueuedRuns = {
  queued: number
  swarm_run_id: string | null
  swarm_run_number: number | null
}
