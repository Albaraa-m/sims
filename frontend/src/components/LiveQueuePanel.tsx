import { useCallback, useEffect, useState } from 'react'

import { killWorker, readQueueState, setFailRate } from '@/api'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { QueueState } from '@/types'

const POLL_INTERVAL_MS = 2000
const FAIL_RATES = [0, 0.1, 0.3, 0.5]

// What the queue is doing right now, with the controls used to show it recovering.
export default function LiveQueuePanel() {
  const [state, setState] = useState<QueueState | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [killingWorkerId, setKillingWorkerId] = useState<string | null>(null)

  const loadState = useCallback(() => {
    readQueueState().then(setState, (error: Error) => setActionError(error.message))
  }, [])

  useEffect(() => {
    loadState()
    const interval = setInterval(loadState, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [loadState])

  if (!state) return null

  function kill(workerId: string) {
    setKillingWorkerId(workerId)
    setActionError(null)
    killWorker(workerId)
      .then(loadState, (error: Error) => setActionError(error.message))
      .finally(() => setKillingWorkerId(null))
  }

  function changeFailRate(value: string) {
    setActionError(null)
    setFailRate(Number(value)).then(loadState, (error: Error) => setActionError(error.message))
  }

  return (
    <div className="space-y-3 rounded-lg border p-4 text-sm">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 className="text-base font-semibold">Queue now</h2>
        <span>
          <span className="font-medium tabular-nums">{state.running}</span>
          <span className="text-muted-foreground"> of {state.max_running} running</span>
        </span>
        <span>
          <span className="font-medium tabular-nums">{state.queued}</span>
          <span className="text-muted-foreground"> queued (limit {state.max_queued})</span>
        </span>
        <span className="text-muted-foreground">
          {state.refused_starts_last_hour} {state.refused_starts_last_hour === 1 ? 'start' : 'starts'} refused in
          the last hour
        </span>
        {state.fault_injection_enabled && (
          <span className="ml-auto flex items-center gap-2">
            <span className="text-muted-foreground">Inject failures</span>
            <Select value={String(state.fail_rate)} onValueChange={changeFailRate}>
              <SelectTrigger size="sm" aria-label="Inject failures">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FAIL_RATES.map((rate) => (
                  <SelectItem key={rate} value={String(rate)}>
                    {Math.round(rate * 100)}% of attempts
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </span>
        )}
      </div>

      {state.workers.length === 0 ? (
        <p className="text-muted-foreground">No worker is running: queued calls wait until one starts.</p>
      ) : (
        <ul className="divide-y rounded-md border">
          {state.workers.map((worker) => (
            <li key={worker.id} className="flex items-center gap-4 px-3 py-2">
              <span className="font-mono">{worker.id}</span>
              <span className="tabular-nums">
                {worker.calls_running} of {worker.max_calls} calls
              </span>
              <span className="text-muted-foreground">heartbeat {Math.round(worker.heartbeat_seconds_ago)}s ago</span>
              {state.fault_injection_enabled && (
                <Button
                  variant="outline"
                  size="sm"
                  className="ml-auto"
                  disabled={killingWorkerId === worker.id}
                  onClick={() => kill(worker.id)}
                >
                  {killingWorkerId === worker.id ? 'Killing…' : 'Kill'}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {actionError && <p className="text-destructive">{actionError}</p>}
    </div>
  )
}
