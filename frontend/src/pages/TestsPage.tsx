import { useEffect, useState } from 'react'

import { listTests } from '@/api'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { TestRow } from '@/types'

const createdAtFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function TestsPage() {
  const [tests, setTests] = useState<TestRow[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    listTests().then(setTests, (error: Error) => setLoadError(error.message))
  }, [])

  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Tests</h1>
      {loadError && <p className="text-sm text-destructive">Couldn't load tests: {loadError}</p>}
      {tests && tests.length === 0 && (
        <p className="text-sm text-muted-foreground">No tests yet. Create one from a call transcript.</p>
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
              <TableRow key={test.id}>
                <TableCell className="font-medium">{test.name}</TableCell>
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
