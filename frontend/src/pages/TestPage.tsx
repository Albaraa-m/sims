import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { listRuns, listTestVersions, markTestReady, readSwarm, readTest, startRuns } from '@/api'
import EditTestDialog from '@/components/EditTestDialog'
import RunControls from '@/components/RunControls'
import OutcomeSummary from '@/components/OutcomeSummary'
import RunsTable from '@/components/RunsTable'
import SpecField from '@/components/SpecField'
import { Alert, AlertAction, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { isActive, isAwaitingGrade, TEST_STATUS_BADGE_VARIANT, TEST_STATUS_LABEL } from '@/runs'
import type { RunRow, SwarmDetail, TestDetail, TestRow } from '@/types'

const POLL_INTERVAL_MS = 3000
// Started runs take a moment to appear, so keep polling briefly even if none is running yet.
const POLL_AFTER_START_MS = 15000

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
  const [versions, setVersions] = useState<TestRow[]>([])
  const [swarm, setSwarm] = useState<SwarmDetail | null>(null)
  const [runs, setRuns] = useState<RunRow[]>([])
  const [lastStartedAt, setLastStartedAt] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!testId) return
    readTest(testId).then(setTest, (error: Error) => setLoadError(error.message))
    listTestVersions(testId).then(setVersions, (error: Error) => setLoadError(error.message))
  }, [testId])

  const swarmId = test?.swarm_id
  useEffect(() => {
    if (swarmId) readSwarm(swarmId).then(setSwarm, (error: Error) => setLoadError(error.message))
  }, [swarmId])

  const loadRuns = useCallback(() => {
    if (testId) listRuns(testId).then(setRuns, (error: Error) => setLoadError(error.message))
  }, [testId])

  useEffect(loadRuns, [loadRuns])

  const isPolling =
    runs.some((run) => isActive(run) || isAwaitingGrade(run, now)) ||
    now - lastStartedAt < POLL_AFTER_START_MS

  useEffect(() => {
    if (!isPolling) return
    const interval = setInterval(() => {
      setNow(Date.now())
      loadRuns()
    }, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [isPolling, loadRuns])

  if (loadError) return <p className="text-sm text-destructive">Couldn't load the test: {loadError}</p>
  if (!test) return null

  const { spec, inferred } = test
  const latestVersion = versions.at(-1)
  const aiLabel = test.swarm_id ? 'Generated' : 'Inferred'
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
          Tests
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">{test.name}</h1>
          <Badge variant={TEST_STATUS_BADGE_VARIANT[test.status]}>{TEST_STATUS_LABEL[test.status]}</Badge>
          <Button variant="outline" className="ml-auto" onClick={() => setIsEditing(true)}>
            Edit
          </Button>
        </div>
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Select value={test.id} onValueChange={(versionId) => navigate(`/tests/${versionId}`)}>
            <SelectTrigger size="sm" aria-label="Version">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {versions.map((version) => (
                <SelectItem key={version.id} value={version.id}>
                  v{version.version}
                  {version.id === latestVersion?.id ? ' (latest)' : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="font-mono">{test.id}</span>
          {swarm && (
            <span>
              · From swarm{' '}
              <Link to={`/swarms/${swarm.id}`} className="underline">
                {swarm.name}
              </Link>
            </span>
          )}
        </div>
        {latestVersion && latestVersion.id !== test.id && (
          <p className="text-sm text-muted-foreground">
            This is v{test.version}, kept for its runs. The latest is{' '}
            <Link to={`/tests/${latestVersion.id}`} className="underline">
              v{latestVersion.version}
            </Link>
            .
          </p>
        )}
      </div>

      {test.status === 'draft' && (
        <Alert>
          <AlertTitle>Not ready to run</AlertTitle>
          <AlertDescription>Review the fields, then mark the test ready.</AlertDescription>
          <AlertAction>
            <Button
              size="sm"
              onClick={() => markTestReady(test.id).then(setTest, (error: Error) => setLoadError(error.message))}
            >
              Mark ready
            </Button>
          </AlertAction>
        </Alert>
      )}

      {isEditing && (
        <EditTestDialog
          test={test}
          open={isEditing}
          onOpenChange={setIsEditing}
          onSaved={(newVersion) => {
            setIsEditing(false)
            navigate(`/tests/${newVersion.id}`)
          }}
        />
      )}

      <section className="space-y-4 rounded-lg border p-4">
        <div>
          <h2 className="text-base font-semibold">Scenario</h2>
          <p className="text-sm text-muted-foreground">What the simulated caller is told.</p>
        </div>
        <SpecField aiLabel={aiLabel} label="Goal" value={spec.goal} inferredValue={inferred?.goal} />
        <SpecField
          aiLabel={aiLabel}
          label="Facts"
          value={<FactsList facts={spec.facts} />}
          inferredValue={inferred && <FactsList facts={inferred.facts} />}
          isEdited={inferred !== null && JSON.stringify(spec.facts) !== JSON.stringify(inferred.facts)}
        />
        <SpecField aiLabel={aiLabel} label="Behavior" value={spec.behavior} inferredValue={inferred?.behavior} />
      </section>

      <section className="space-y-4 rounded-lg border bg-muted/40 p-4">
        <div>
          <h2 className="text-base font-semibold">Evaluation criteria</h2>
          <p className="text-sm text-muted-foreground">Hidden from the caller. Used to grade each call.</p>
        </div>
        <SpecField
          aiLabel={aiLabel}
          label="Policy under test"
          value={spec.policy_under_test}
          inferredValue={inferred?.policy_under_test}
        />
        <SpecField
          aiLabel={aiLabel}
          label="Expected outcome"
          value={spec.expected_outcome}
          inferredValue={inferred?.expected_outcome}
        />
      </section>

      <div className="space-y-3">
        <h2 className="text-base font-semibold">Runs</h2>
        {test.status === 'ready' && latestVersion?.id === test.id && (
          <RunControls
            startRuns={(agentVersions, runsPerVersion) => startRuns(test.id, agentVersions, runsPerVersion)}
            onStarted={() => {
              const startedAt = Date.now()
              setLastStartedAt(startedAt)
              setNow(startedAt)
              loadRuns()
            }}
          />
        )}
        {latestVersion && latestVersion.id !== test.id && (
          <p className="text-sm text-muted-foreground">Runs use the latest version.</p>
        )}
        <OutcomeSummary runs={runs} testId={test.id} testVersion={test.version} />
        <RunsTable runs={runs} viewedTestId={test.id} now={now} />
      </div>
    </section>
  )
}
