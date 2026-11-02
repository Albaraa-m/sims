import { countOutcomes, passRate } from '@/dashboard'
import type { RunRow } from '@/types'

// Expects runs the judge passed or failed; anything else would skew the rate.
export default function PassRateChart({ runs, agentVersions }: { runs: RunRow[]; agentVersions: string[] }) {
  return (
    <figure className="space-y-2">
      <figcaption className="text-sm font-medium">Pass rate by agent version</figcaption>
      <div className="grid grid-cols-[max-content_1fr_max-content] items-center gap-x-3 gap-y-2 text-sm">
        {agentVersions.map((agentVersion) => {
          const counts = countOutcomes(runs.filter((run) => run.agent_version === agentVersion))
          const rate = passRate(counts) ?? 0
          const graded = counts.pass + counts.fail
          const label = `${counts.pass}/${graded} pass · ${Math.round(rate * 100)}%`
          return (
            <div key={agentVersion} className="contents">
              <span>Agent {agentVersion}</span>
              <div className="h-3 rounded-sm bg-muted" title={label}>
                <div className="h-full rounded-sm bg-[#2a78d6]" style={{ width: `${rate * 100}%` }} />
              </div>
              <span className="tabular-nums text-muted-foreground">{label}</span>
            </div>
          )
        })}
      </div>
    </figure>
  )
}
