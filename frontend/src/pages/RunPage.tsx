import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { readRun, recordingUrl } from '@/api'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { formatRunDuration, RUN_STATUS_BADGE_VARIANT, startedAtFormat } from '@/runs'
import type { ConversationEntry, RunDetail } from '@/types'

const POLL_INTERVAL_MS = 3000

function ConversationLine({ entry }: { entry: ConversationEntry }) {
  if (entry.kind === 'speech') {
    return (
      <div className="grid grid-cols-[4rem_1fr] gap-3">
        <span className="text-muted-foreground">{entry.speaker}</span>
        <p>{entry.text}</p>
      </div>
    )
  }
  return (
    <div className="ml-[4.75rem] rounded-md bg-muted px-3 py-2 font-mono text-xs text-muted-foreground">
      {entry.name}({entry.arguments}){entry.output !== null && <> → {entry.output}</>}
    </div>
  )
}

export default function RunPage() {
  const { runId } = useParams()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loadedAt, setLoadedAt] = useState(0)

  const isRunning = run?.status === 'running'

  useEffect(() => {
    if (!runId) return
    const loadRun = () =>
      readRun(runId).then(
        (loadedRun) => {
          setRun(loadedRun)
          setLoadedAt(Date.now())
        },
        (error: Error) => setLoadError(error.message),
      )
    loadRun()
    if (!isRunning) return
    const interval = setInterval(loadRun, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [runId, isRunning])

  if (loadError) return <p className="text-sm text-destructive">Couldn't load the run: {loadError}</p>
  if (!run) return null

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
          <h1 className="font-mono text-xl font-semibold">{run.id}</h1>
          <Badge variant={RUN_STATUS_BADGE_VARIANT[run.status]}>{run.status}</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Agent {run.agent_version} · {startedAtFormat.format(new Date(run.started_at))} ·{' '}
          {formatRunDuration(run, loadedAt)}
        </p>
      </div>

      {run.error && (
        <Alert variant="destructive">
          <AlertTitle>The run failed</AlertTitle>
          <AlertDescription>{run.error}</AlertDescription>
        </Alert>
      )}

      {run.has_recording && <audio controls src={recordingUrl(run.id)} className="w-full" />}

      <div className="space-y-3 text-sm">
        <h2 className="text-base font-semibold">Conversation</h2>
        {run.conversation.length === 0 ? (
          <p className="text-muted-foreground">{isRunning ? 'The call is in progress.' : 'Nothing was said.'}</p>
        ) : (
          run.conversation.map((entry, index) => <ConversationLine key={index} entry={entry} />)
        )}
      </div>
    </section>
  )
}
