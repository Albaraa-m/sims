import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { listTests } from '@/api'
import NewTestDialog from '@/components/NewTestDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { TestRow } from '@/types'

const createdAtFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function TestsPage() {
  const [tests, setTests] = useState<TestRow[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isNewTestOpen, setIsNewTestOpen] = useState(false)
  const navigate = useNavigate()

  const loadTests = useCallback(() => {
    listTests().then(setTests, (error: Error) => setLoadError(error.message))
  }, [])

  useEffect(loadTests, [loadTests])

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Tests</h1>
        <Button onClick={() => setIsNewTestOpen(true)}>New test</Button>
      </div>
      <NewTestDialog open={isNewTestOpen} onOpenChange={setIsNewTestOpen} onCreated={loadTests} />
      {loadError && <p className="text-sm text-destructive">Couldn't load tests: {loadError}</p>}
      {tests && tests.length === 0 && (
        <p className="text-sm text-muted-foreground">No tests yet. Use New test to create one from a call transcript.</p>
      )}
      {tests && tests.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
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
                <TableCell className="font-mono text-muted-foreground">{test.id}</TableCell>
                <TableCell>v{test.version}</TableCell>
                <TableCell>
                  <Badge variant={test.status === 'ready' ? 'default' : 'secondary'}>{test.status}</Badge>
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
