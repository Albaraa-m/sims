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
