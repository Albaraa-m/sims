import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { listSwarms, listTests } from '@/api'
import NewTestDialog from '@/components/NewTestDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { TEST_STATUS_LABEL } from '@/runs'
import type { SwarmRow, TestRow } from '@/types'

const createdAtFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function TestsPage() {
  const [tests, setTests] = useState<TestRow[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isNewTestOpen, setIsNewTestOpen] = useState(false)
  const [isShowingSwarmTests, setIsShowingSwarmTests] = useState(false)
  const [swarms, setSwarms] = useState<SwarmRow[]>([])
  const navigate = useNavigate()

  const loadTests = useCallback(() => {
    listTests(isShowingSwarmTests).then(setTests, (error: Error) => setLoadError(error.message))
  }, [isShowingSwarmTests])

  useEffect(() => {
    listSwarms().then(setSwarms, (error: Error) => setLoadError(error.message))
  }, [])

  const swarmNameOf = (swarmId: string) => swarms.find((swarm) => swarm.id === swarmId)?.name ?? swarmId

  useEffect(loadTests, [loadTests])

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Tests</h1>
        <Button onClick={() => setIsNewTestOpen(true)}>New test</Button>
      </div>
      <NewTestDialog open={isNewTestOpen} onOpenChange={setIsNewTestOpen} onCreated={loadTests} />
      <div className="flex items-center gap-2">
        <Checkbox
          id="show-swarm-tests"
          checked={isShowingSwarmTests}
          onCheckedChange={(checked) => setIsShowingSwarmTests(checked === true)}
        />
        <Label htmlFor="show-swarm-tests" className="font-normal text-muted-foreground">
          Show swarm tests
        </Label>
      </div>
      {loadError && <p className="text-sm text-destructive">Couldn't load tests: {loadError}</p>}
      {tests && tests.length === 0 && (
        <p className="text-sm text-muted-foreground">No tests yet. Use New test to create one from a call transcript.</p>
      )}
      {tests && tests.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Origin</TableHead>
              <TableHead>ID</TableHead>
              <TableHead>Version</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tests.map((test) => (
              <TableRow key={test.id} onClick={() => navigate(`/tests/${test.id}`)} className="cursor-pointer">
                <TableCell className="font-medium">
                  <Link to={`/tests/${test.id}`}>{test.name}</Link>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {test.swarm_id ? `Swarm: ${swarmNameOf(test.swarm_id)}` : 'Transcript'}
                </TableCell>
                <TableCell className="font-mono text-muted-foreground">{test.id}</TableCell>
                <TableCell>v{test.version}</TableCell>
                <TableCell>
                  <Badge variant={test.status === 'ready' ? 'default' : 'secondary'}>{TEST_STATUS_LABEL[test.status]}</Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {createdAtFormat.format(new Date(test.created_at))}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  )
}
