export type TestStatus = 'draft' | 'ready'

export type TestRow = {
  id: string
  name: string
  version: number
  status: TestStatus
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

export type RunRow = {
  id: string
  test_id: string
  test_version: number
  agent_version: string
  status: RunStatus
  started_at: string
  ended_at: string | null
}
