import { OUTCOME_LABEL } from '@/runs'
import type { Outcome, RunRow } from '@/types'

const OUTCOMES: Outcome[] = ['pass', 'fail', 'inconclusive', 'execution_failed']

type OutcomeSummaryProps = {
  runs: RunRow[]
  // Only this test version's runs are counted, so the versions compare like for like.
  testId: string
  testVersion: number
}

export default function OutcomeSummary({ runs, testId, testVersion }: OutcomeSummaryProps) {
  const gradedRuns = runs.filter((run) => run.test_id === testId && run.outcome !== null)
  if (gradedRuns.length === 0) return null
  const agentVersions = [...new Set(gradedRuns.map((run) => run.agent_version))].sort()

  return (
    <div className="space-y-2 rounded-lg border p-4 text-sm">
      <h3 className="font-medium">Outcomes of test v{testVersion}</h3>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
        {agentVersions.map((agentVersion) => {
          const runsOfVersion = gradedRuns.filter((run) => run.agent_version === agentVersion)
          const counts = OUTCOMES.map(
            (outcome) => `${runsOfVersion.filter((run) => run.outcome === outcome).length} ${OUTCOME_LABEL[outcome]}`,
          )
          return (
            <div key={agentVersion} className="contents">
              <dt className="font-medium">Agent {agentVersion}</dt>
              <dd className="tabular-nums">
                {counts.join(' / ')} <span className="text-muted-foreground">(n={runsOfVersion.length})</span>
              </dd>
            </div>
          )
        })}
      </dl>
      <p className="text-xs text-muted-foreground">
        Covers only this test's policy over n graded runs. Small samples can't show a version is better overall, and
        inconclusive runs and execution failures say nothing about the agent.
      </p>
    </div>
  )
}
