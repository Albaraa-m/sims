import { useState } from 'react'

import { startRuns } from '@/api'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const AGENT_VERSIONS = ['v1', 'v2']

type RunControlsProps = {
  testId: string
  onStarted: () => void
}

export default function RunControls({ testId, onStarted }: RunControlsProps) {
  const [agentVersions, setAgentVersions] = useState<string[]>(AGENT_VERSIONS)
  const [runsPerVersion, setRunsPerVersion] = useState(1)
  const [isStarting, setIsStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  function toggleAgentVersion(agentVersion: string, isChecked: boolean) {
    setAgentVersions(AGENT_VERSIONS.filter((v) => (v === agentVersion ? isChecked : agentVersions.includes(v))))
  }

  async function startSelectedRuns() {
    setIsStarting(true)
    setStartError(null)
    try {
      await startRuns(testId, agentVersions, runsPerVersion)
      onStarted()
    } catch (error) {
      setStartError(`Couldn't start the runs: ${(error as Error).message}`)
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-5 text-sm">
        <span className="text-muted-foreground">Agent</span>
        {AGENT_VERSIONS.map((agentVersion) => (
          <Label key={agentVersion} className="font-normal">
            <Checkbox
              checked={agentVersions.includes(agentVersion)}
              onCheckedChange={(checked) => toggleAgentVersion(agentVersion, checked === true)}
            />
            {agentVersion}
          </Label>
        ))}
        <Label className="font-normal">
          Runs per version
          <Input
            type="number"
            min={1}
            max={5}
            value={runsPerVersion}
            onChange={(event) => setRunsPerVersion(Math.min(5, Math.max(1, Number(event.target.value) || 1)))}
            className="w-16"
          />
        </Label>
        <Button onClick={startSelectedRuns} disabled={agentVersions.length === 0 || isStarting}>
          {isStarting ? 'Starting…' : `Run ${agentVersions.length * runsPerVersion} simulation${agentVersions.length * runsPerVersion === 1 ? '' : 's'}`}
        </Button>
      </div>
      {startError && <p className="text-sm text-destructive">{startError}</p>}
    </div>
  )
}
