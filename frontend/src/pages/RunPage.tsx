import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { readRun, recordingUrl } from '@/api'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import Verdict from '@/components/Verdict'
import {
  ATTEMPT_STATUS_LABEL,
  formatRunDuration,
  isActive,
  isAwaitingGrade,
  RUN_STATUS_BADGE_VARIANT,
  RUN_STATUS_LABEL,
  startedAtFormat,
  turnElementId,
} from '@/runs'
import type { ConversationEntry, RunDetail } from '@/types'

const POLL_INTERVAL_MS = 3000

type ConversationLineProps = { entry: ConversationEntry; turn: number; isCited: boolean }

function ConversationLine({ entry, turn, isCited }: ConversationLineProps) {
  return (
    <div
      id={turnElementId(turn)}
      className={`grid grid-cols-[1.5rem_4rem_1fr] gap-3 rounded-md px-2 py-1 ${isCited ? 'bg-amber-100 dark:bg-amber-950' : ''}`}
    >
      <span className="text-right tabular-nums text-muted-foreground">{turn}</span>
      {entry.kind === 'speech' ? (
        <>
          <span className="text-muted-foreground">{entry.speaker}</span>
          <p>{entry.text}</p>
        </>
      ) : (
        <div className="col-span-2 rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
          {entry.name}({entry.arguments}){entry.output !== null && <> → {entry.output}</>}
        </div>
      )}
    </div>
  )
}

export default function RunPage() {
  const { runId } = useParams()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loadedAt, setLoadedAt] = useState(0)

  const loadRun = useCallback(() => {
    if (!runId) return
    readRun(runId).then(
      (loadedRun) => {
        setRun(loadedRun)
        setLoadedAt(Date.now())
      },
      (error: Error) => setLoadError(error.message),
    )
  }, [runId])

  const isRunning = run !== null && isActive(run)
  const outcome = run?.evaluations[0]?.outcome ?? null
  const isPolling = isRunning || (run !== null && isAwaitingGrade({ outcome, ended_at: run.ended_at }, loadedAt))

  useEffect(loadRun, [loadRun])

  useEffect(() => {
    if (!isPolling) return
    const interval = setInterval(loadRun, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [isPolling, loadRun])

  if (loadError) return <p className="text-sm text-destructive">Couldn't load the run: {loadError}</p>
  if (!run) return null

  const citedTurns = new Set(run.evaluations[0]?.cited_turns)
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        {run.test_id ? (
          <Link to={`/tests/${run.test_id}`} className="text-sm text-muted-foreground hover:text-foreground">
            {run.test_name}, v{run.test_version}
          </Link>
        ) : (
          <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
            Tests
          </Link>
        )}
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">
            Simulation <span className="font-mono">{run.id}</span>
          </h1>
          <Badge variant={RUN_STATUS_BADGE_VARIANT[run.status]}>{RUN_STATUS_LABEL[run.status]}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Agent {run.agent_version} · {startedAtFormat.format(new Date(run.started_at))} ·{' '}
          {formatRunDuration(run, loadedAt)}
          {run.attempt > 0 && (
            <>
              {' '}
              ·{' '}
              {run.status === 'queued'
                ? `Waiting for attempt ${run.attempt + 1} of ${run.max_attempts}`
                : `Attempt ${run.attempt} of ${run.max_attempts}`}
            </>
          )}
        </p>
        {run.attempts
          .filter((entry) => entry.status !== 'completed')
          .map((entry) => (
            <p key={entry.attempt} className="text-sm text-muted-foreground">
              Attempt {entry.attempt}: {ATTEMPT_STATUS_LABEL[entry.status]}
              {entry.reason && <> ({entry.reason})</>}
            </p>
          ))}
      </div>

      {run.error && (
        <Alert variant="destructive">
          <AlertTitle>{run.status === 'failed' ? "The call couldn't run" : 'The last attempt failed'}</AlertTitle>
          <AlertDescription>{run.error}</AlertDescription>
        </Alert>
      )}

      <Verdict run={run} now={loadedAt} onRegraded={loadRun} />

      {run.has_recording && <audio controls src={recordingUrl(run.id)} className="w-full" />}

      <div className="space-y-3 text-sm">
        <h2 className="text-base font-semibold">Conversation</h2>
        {run.conversation.length === 0 ? (
          <p className="text-muted-foreground">{run.status === 'queued' ? 'Waiting for a worker to place the call.' : isRunning ? 'The call is in progress.' : 'Nothing was said.'}</p>
        ) : (
          run.conversation.map((entry, turn) => (
            <ConversationLine key={turn} entry={entry} turn={turn} isCited={citedTurns.has(turn)} />
          ))
        )}
      </div>
    </section>
  )
}
