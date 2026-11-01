import type { CreateTestRequest, InferredTest, TestRow } from '@/types'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    throw new Error(`${init?.method ?? 'GET'} ${path} failed with ${response.status}`)
  }
  return response.json()
}

export function listTests(): Promise<TestRow[]> {
  return requestJson('/api/tests')
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
