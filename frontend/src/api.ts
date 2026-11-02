import type {
  CreateTestRequest,
  EvaluationDetail,
  FoundPolicies,
  InferredTest,
  Policy,
  QueueState,
  RunDetail,
  RunRow,
  SaveSwarmRequest,
  SwarmDetail,
  SwarmProposal,
  SwarmRow,
  TestDetail,
  TestRow,
  TestSpec,
} from '@/types'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    // FastAPI explains refusals (e.g. a full queue) in detail; show that when there is one.
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : null
    throw new Error(detail ?? `${init?.method ?? 'GET'} ${path} failed with ${response.status}`)
  }
  return response.json()
}

export function listTests(includeSwarmTests = false): Promise<TestRow[]> {
  return requestJson(`/api/tests?include_swarm_tests=${includeSwarmTests}`)
}

export function readTest(testId: string): Promise<TestDetail> {
  return requestJson(`/api/tests/${testId}`)
}

export function listTestVersions(testId: string): Promise<TestRow[]> {
  return requestJson(`/api/tests/${testId}/versions`)
}

export function inferTest(transcript: string, reportedIssue: string | null): Promise<InferredTest> {
  return requestJson('/api/tests/infer', {
    method: 'POST',
    body: JSON.stringify({ transcript, reported_issue: reportedIssue }),
  })
}

export function createTest(request: CreateTestRequest): Promise<TestRow> {
  return requestJson('/api/tests', { method: 'POST', body: JSON.stringify(request) })
}

export function editTest(testId: string, name: string, spec: TestSpec): Promise<TestDetail> {
  return requestJson(`/api/tests/${testId}`, { method: 'PUT', body: JSON.stringify({ name, spec }) })
}

export function markTestReady(testId: string): Promise<TestDetail> {
  return requestJson(`/api/tests/${testId}/ready`, { method: 'POST' })
}

export function startRuns(testId: string, agentVersions: string[], runsPerVersion: number): Promise<null> {
  return requestJson(`/api/tests/${testId}/runs`, {
    method: 'POST',
    body: JSON.stringify({ agent_versions: agentVersions, runs_per_version: runsPerVersion }),
  })
}

export function listRuns(testId: string): Promise<RunRow[]> {
  return requestJson(`/api/tests/${testId}/runs`)
}

export function readRun(runId: string): Promise<RunDetail> {
  return requestJson(`/api/runs/${runId}`)
}

export function recordingUrl(runId: string): string {
  return `/api/runs/${runId}/recording`
}

export function regradeRun(runId: string): Promise<EvaluationDetail> {
  return requestJson(`/api/runs/${runId}/evaluate`, { method: 'POST' })
}

export type RunFilters = { test_id?: string; agent_version?: string; outcome?: string }

export function listRunsOfAllTests(filters: RunFilters): Promise<RunRow[]> {
  const definedFilters = Object.entries(filters).filter((entry): entry is [string, string] => Boolean(entry[1]))
  return requestJson(`/api/runs?${new URLSearchParams(definedFilters)}`)
}

export function findPolicies(agentVersion: string): Promise<FoundPolicies> {
  return requestJson('/api/swarms/policies', {
    method: 'POST',
    body: JSON.stringify({ agent_version: agentVersion }),
  })
}

export function generateSwarm(agentVersion: string, policies: Policy[]): Promise<SwarmProposal> {
  return requestJson('/api/swarms/generate', {
    method: 'POST',
    body: JSON.stringify({ agent_version: agentVersion, policies }),
  })
}

export function saveSwarm(request: SaveSwarmRequest): Promise<SwarmRow> {
  return requestJson('/api/swarms', { method: 'POST', body: JSON.stringify(request) })
}

export function listSwarms(): Promise<SwarmRow[]> {
  return requestJson('/api/swarms')
}

export function readSwarm(swarmId: string): Promise<SwarmDetail> {
  return requestJson(`/api/swarms/${swarmId}`)
}

export function startSwarmRuns(swarmId: string, agentVersions: string[], runsPerTest: number): Promise<{ queued: number }> {
  return requestJson(`/api/swarms/${swarmId}/runs`, {
    method: 'POST',
    body: JSON.stringify({ agent_versions: agentVersions, runs_per_version: runsPerTest }),
  })
}

export function listRunsOfSwarm(swarmId: string): Promise<RunRow[]> {
  return requestJson(`/api/swarms/${swarmId}/runs`)
}

export function cancelSwarmRuns(swarmId: string): Promise<null> {
  return requestJson(`/api/swarms/${swarmId}/cancel`, { method: 'POST' })
}

export function readQueueState(): Promise<QueueState> {
  return requestJson('/api/system/queue')
}

export function killWorker(workerId: string): Promise<null> {
  return requestJson(`/api/system/workers/${workerId}/kill`, { method: 'POST' })
}

export function setFailRate(failRate: number): Promise<{ fail_rate: number }> {
  return requestJson('/api/system/fail-rate', { method: 'PUT', body: JSON.stringify({ fail_rate: failRate }) })
}
