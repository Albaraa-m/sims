import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { listSwarms } from '@/api'
import CreateSwarmDialog from '@/components/CreateSwarmDialog'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { startedAtFormat } from '@/runs'
import type { SwarmRow } from '@/types'

export default function SwarmsPage() {
  const [swarms, setSwarms] = useState<SwarmRow[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    listSwarms().then(setSwarms, (error: Error) => setLoadError(error.message))
  }, [])

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Swarms</h1>
        <Button onClick={() => setIsCreateOpen(true)}>Create swarm</Button>
      </div>
      <CreateSwarmDialog open={isCreateOpen} onOpenChange={setIsCreateOpen} />
      {loadError && <p className="text-sm text-destructive">Couldn't load swarms: {loadError}</p>}
      {swarms && swarms.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No swarms yet. Create one to generate tests for every policy of an agent.
        </p>
      )}
      {swarms && swarms.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead>Tests</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {swarms.map((swarm) => (
              <TableRow key={swarm.id} onClick={() => navigate(`/swarms/${swarm.id}`)} className="cursor-pointer">
                <TableCell className="font-medium">
                  <Link to={`/swarms/${swarm.id}`}>{swarm.name}</Link>
                </TableCell>
                <TableCell>{swarm.agent_version}</TableCell>
                <TableCell>{swarm.test_count}</TableCell>
                <TableCell className="text-muted-foreground">
                  {startedAtFormat.format(new Date(swarm.created_at))}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  )
}
