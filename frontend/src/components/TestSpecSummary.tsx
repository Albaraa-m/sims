import type { TestSpec } from '@/types'

function factsInline(facts: Record<string, string>): string {
  return Object.entries(facts)
    .map(([name, value]) => `${name.replaceAll('_', ' ')}: ${value}`)
    .join(' · ')
}

export default function TestSpecSummary({ spec }: { spec: TestSpec }) {
  const facts = factsInline(spec.facts)
  return (
    <>
      <p className="text-muted-foreground">
        <span className="text-foreground">Scenario:</span> {spec.goal}
        {facts && <span> ({facts})</span>}
      </p>
      <p className="text-muted-foreground">
        <span className="text-foreground">Expected:</span> {spec.expected_outcome}
      </p>
    </>
  )
}
