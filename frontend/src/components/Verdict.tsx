import { useState } from 'react'

import { regradeRun } from '@/api'
import OutcomeBadge from '@/components/OutcomeBadge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { OUTCOME_BADGE_VARIANT, OUTCOME_LABEL, startedAtFormat, turnElementId } from '@/runs'
import type { EvaluationDetail, RunDetail } from '@/types'

function scrollToTurn(turn: number) {
  document.getElementById(turnElementId(turn))?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function JudgeSettings({ evaluation }: { evaluation: EvaluationDetail }) {
  return (
    <p className="text-xs text-muted-foreground">
      {startedAtFormat.format(new Date(evaluation.created_at))}
      {evaluation.judge_model && (
        <>
          {' '}
          · judge {evaluation.judge_model}, prompt {evaluation.judge_prompt_version}
        </>
      )}
      {!evaluation.judge_model && ' · decided in code, without the judge'}
    </p>
  )
}

type VerdictProps = {
  run: RunDetail
  now: number
  onRegraded: () => void
}

export default function Verdict({ run, now, onRegraded }: VerdictProps) {
  const [isRegrading, setIsRegrading] = useState(false)
  const [regradeError, setRegradeError] = useState<string | null>(null)
  const [latest, ...earlier] = run.evaluations

  const regrade = () => {
    setIsRegrading(true)
    setRegradeError(null)
    regradeRun(run.id)
      .then(onRegraded, (error: Error) => setRegradeError(error.message))
      .finally(() => setIsRegrading(false))
  }

  return (
    <div className="space-y-3 rounded-lg border p-4 text-sm">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold">Verdict</h2>
        <OutcomeBadge run={{ outcome: latest?.outcome ?? null, ended_at: run.ended_at, status: run.status }} now={now} />
        {run.status === 'done' && (
          <Button variant="outline" size="sm" className="ml-auto" onClick={regrade} disabled={isRegrading}>
            {isRegrading ? 'Grading…' : 'Regrade'}
          </Button>
        )}
      </div>
      {regradeError && <p className="text-destructive">Couldn't regrade: {regradeError}</p>}
      {latest && (
        <>
          <p>{latest.reason}</p>
          {latest.error && <p className="text-muted-foreground">Error: {latest.error}</p>}
          {latest.cited_turns.length > 0 && (
            <p className="flex flex-wrap items-center gap-2 text-muted-foreground">
              Evidence:
              {latest.cited_turns.map((turn) => (
                <Button key={turn} variant="link" size="sm" className="h-auto p-0" onClick={() => scrollToTurn(turn)}>
                  turn {turn}
                </Button>
              ))}
            </p>
          )}
          <JudgeSettings evaluation={latest} />
        </>
      )}
      {earlier.length > 0 && (
        <details className="text-muted-foreground">
          <summary className="cursor-pointer">Earlier grades ({earlier.length})</summary>
          <ul className="mt-2 space-y-3">
            {earlier.map((evaluation) => (
              <li key={evaluation.created_at} className="space-y-1">
                <Badge variant={OUTCOME_BADGE_VARIANT[evaluation.outcome]}>{OUTCOME_LABEL[evaluation.outcome]}</Badge>
                <p>{evaluation.reason}</p>
                <JudgeSettings evaluation={evaluation} />
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
