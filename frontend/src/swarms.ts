export type PolicyGroup<Item> = { policy: string; items: Item[] }

// Groups by policy text in the swarm's order, keeping untested policies and adding any
// policy a reviewer reworded, so nothing is hidden.
export function groupByPolicy<Item>(
  policies: string[],
  items: Item[],
  policyOf: (item: Item) => string,
): PolicyGroup<Item>[] {
  const reworded = [...new Set(items.map(policyOf))].filter((policy) => !policies.includes(policy))
  return [...policies, ...reworded].map((policy) => ({
    policy,
    items: items.filter((item) => policyOf(item) === policy),
  }))
}

// Past about 3, tests for one policy start repeating each other; matches the backend.
export const MAX_TESTS_PER_POLICY = 3
export const MAX_TESTS_PER_SWARM = 40

// Every chosen policy gets at least 1 test and at most 3. Counts the reviewer typed are
// kept; the rest of the maximum is spread over the other policies.
export function spreadTestsAcrossPolicies(
  maximum: number,
  policies: string[],
  typedCounts: Record<string, number>,
): Record<string, number> {
  const counts: Record<string, number> = {}
  const untouched = policies.filter((policy) => !(policy in typedCounts))
  for (const policy of policies) counts[policy] = typedCounts[policy] ?? 1
  let left = maximum - Object.values(counts).reduce((sum, count) => sum + count, 0)
  while (left > 0 && untouched.some((policy) => counts[policy] < MAX_TESTS_PER_POLICY)) {
    for (const policy of untouched) {
      if (left > 0 && counts[policy] < MAX_TESTS_PER_POLICY) {
        counts[policy] += 1
        left -= 1
      }
    }
  }
  return counts
}
