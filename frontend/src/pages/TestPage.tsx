import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { readTest } from '@/api'
import SpecField from '@/components/SpecField'
import { Badge } from '@/components/ui/badge'
import type { TestDetail } from '@/types'

function FactsList({ facts }: { facts: Record<string, string> }) {
  const entries = Object.entries(facts)
  if (entries.length === 0) return <p className="text-muted-foreground">None</p>
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
      {entries.map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="text-muted-foreground">{key}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export default function TestPage() {
  const { testId } = useParams()
  const [test, setTest] = useState<TestDetail | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    if (testId) readTest(testId).then(setTest, (error: Error) => setLoadError(error.message))
  }, [testId])

  if (loadError) return <p className="text-sm text-destructive">Couldn't load the test: {loadError}</p>
  if (!test) return null

  const { spec, inferred } = test
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
          Tests
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">{test.name}</h1>
          <Badge variant={test.status === 'ready' ? 'default' : 'secondary'}>{test.status}</Badge>
        </div>
        <p className="font-mono text-sm text-muted-foreground">
          {test.id} · v{test.version}
        </p>
      </div>

      <div className="space-y-5">
        <SpecField label="Goal" value={spec.goal} inferredValue={inferred?.goal} />
        <SpecField
          label="Facts"
          value={<FactsList facts={spec.facts} />}
          inferredValue={inferred && <FactsList facts={inferred.facts} />}
          isEdited={inferred !== null && JSON.stringify(spec.facts) !== JSON.stringify(inferred.facts)}
        />
        <SpecField label="Behavior" value={spec.behavior} inferredValue={inferred?.behavior} />
        <SpecField
          label="Policy under test"
          value={spec.policy_under_test}
          inferredValue={inferred?.policy_under_test}
        />
        <SpecField
          label="Expected outcome"
          value={spec.expected_outcome}
          inferredValue={inferred?.expected_outcome}
        />
      </div>
    </section>
  )
}
