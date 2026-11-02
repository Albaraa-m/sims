import { useEffect, useState } from 'react'

import { listSwarms } from '@/api'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { REGRESSION_SCOPE, swarmScope } from '@/scopes'
import type { SwarmRow } from '@/types'

type ScopeSelectProps = {
  value: string
  onChange: (scope: string) => void
}

// Picks which tests a page counts: the regression suite, or one swarm.
export default function ScopeSelect({ value, onChange }: ScopeSelectProps) {
  const [swarms, setSwarms] = useState<SwarmRow[]>([])

  useEffect(() => {
    listSwarms().then(setSwarms, () => setSwarms([]))
  }, [])

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger size="sm" aria-label="Scope" className="min-w-48">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={REGRESSION_SCOPE}>Regression tests</SelectItem>
        {swarms.map((swarm) => (
          <SelectItem key={swarm.id} value={swarmScope(swarm.id)}>
            Swarm: {swarm.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
