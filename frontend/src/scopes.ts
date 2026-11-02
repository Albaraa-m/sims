import type { TestRow } from '@/types'

// Regression tests and swarm tests are never counted together; a page shows one scope.
export const REGRESSION_SCOPE = 'regression'

export function swarmScope(swarmId: string): string {
  return `swarm:${swarmId}`
}

export function isTestInScope(test: TestRow, scope: string): boolean {
  if (scope === REGRESSION_SCOPE) return test.swarm_id === null
  const swarmId = scope.replace('swarm:', '')
  return test.swarm_id === swarmId || test.promoted_from_swarm_id === swarmId
}
