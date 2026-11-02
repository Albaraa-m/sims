import { StatusPill } from '@/components/SuiteStatus'
import { Badge } from '@/components/ui/badge'
import { suiteStatusOf } from '@/dashboard'
import { OUTCOME_BADGE_VARIANT, OUTCOME_LABEL } from '@/runs'
import type { Outcome, RunRow } from '@/types'

const OUTCOMES: Outcome[] = ['pass', 'fail', 'inconclusive', 'execution_failed']

type OutcomeSummaryProps = {
  runs: RunRow[]
  // Only this test version's runs are counted, so the versions compare like for like.
  testId: string
  testVersion: number
}

// Per agent version: the test's status (as on the dashboard), then every graded run by outcome.
export default function OutcomeSummary({ runs, testId, testVersion }: OutcomeSummaryProps) {
  const gradedRuns = runs.filter((run) => run.test_id === testId && run.outcome !== null)
  if (gradedRuns.length === 0) return null
  const agentVersions = [...new Set(gradedRuns.map((run) => run.agent_version))].sort()

  return (
    <div className="space-y-3 rounded-lg border p-4 text-sm">
      <div>
        <h3 className="text-base font-semibold">Run summary</h3>
        <p className="text-muted-foreground">All graded runs of test v{testVersion}, by agent version.</p>
      </div>
      <div className="grid grid-cols-[max-content_max-content_1fr] items-center gap-x-4 gap-y-2">
        {agentVersions.map((agentVersion) => {
          const runsOfVersion = gradedRuns.filter((run) => run.agent_version === agentVersion)
          const count = (outcome: Outcome) => runsOfVersion.filter((run) => run.outcome === outcome).length
          const pass = count('pass')
          const fail = count('fail')
          return (
            <div key={agentVersion} className="contents">
              <span className="font-medium">Agent {agentVersion}</span>
              <StatusPill cell={{ pass, fail, status: suiteStatusOf(pass, fail), testId }} />
              <span className="flex flex-wrap items-center gap-1.5">
                {OUTCOMES.filter((outcome) => count(outcome) > 0).map((outcome) => (
                  <Badge key={outcome} variant={OUTCOME_BADGE_VARIANT[outcome]}>
                    {count(outcome)} {OUTCOME_LABEL[outcome]}
                  </Badge>
                ))}
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-muted-foreground">
        Covers only this test's policy. Passing: every graded run passed; Flaky: some did; Failing: none did. Small
        samples can't show a version is better overall, and inconclusive runs and execution failures say nothing about
        the agent.
      </p>
    </div>
  )
}
