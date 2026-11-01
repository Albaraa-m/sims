import type { FactRow } from '@/components/FactsEditor'
import type { TestSpec } from '@/types'

function factRowsFromFacts(facts: Record<string, string>): FactRow[] {
  return Object.entries(facts).map(([key, value]) => ({ key, value }))
}

function factsFromFactRows(rows: FactRow[]): Record<string, string> {
  return Object.fromEntries(
    rows.filter((row) => row.key.trim()).map((row) => [row.key.trim(), row.value.trim()]),
  )
}

export type TestFields = {
  name: string
  goal: string
  facts: FactRow[]
  behavior: string
  policy_under_test: string
  expected_outcome: string
}

export const EMPTY_FIELDS: TestFields = {
  name: '',
  goal: '',
  facts: [],
  behavior: '',
  policy_under_test: '',
  expected_outcome: '',
}

export function fieldsFromSpec(name: string | null, spec: TestSpec | null): TestFields {
  if (!spec) return EMPTY_FIELDS
  return { ...spec, name: name ?? '', facts: factRowsFromFacts(spec.facts) }
}

export function factsAsText(rows: FactRow[]): string {
  return rows.map((row) => `${row.key}: ${row.value}`).join('\n') || 'None'
}

export function specFromFields(fields: TestFields): TestSpec {
  return {
    goal: fields.goal.trim(),
    facts: factsFromFactRows(fields.facts),
    behavior: fields.behavior.trim(),
    policy_under_test: fields.policy_under_test.trim(),
    expected_outcome: fields.expected_outcome.trim(),
  }
}

export function areFieldsComplete(fields: TestFields): boolean {
  const textFields = [fields.name, fields.goal, fields.behavior, fields.policy_under_test, fields.expected_outcome]
  const factsComplete = fields.facts.every((row) => !row.value.trim() || row.key.trim())
  return textFields.every((text) => text.trim()) && factsComplete
}
