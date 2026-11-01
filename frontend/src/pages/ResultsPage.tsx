import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { listRunsOfAllTests, listTests } from '@/api'
import OutcomeBadge from '@/components/OutcomeBadge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { OUTCOME_LABEL, startedAtFormat } from '@/runs'
import type { Outcome, RunRow, TestRow } from '@/types'

// Radix Select can't hold an empty value, so "no filter" needs its own.
const ANY = 'any'

type FilterProps = {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}

function Filter({ label, value, options, onChange }: FilterProps) {
  return (
    <Select value={value || ANY} onValueChange={(selected) => onChange(selected === ANY ? '' : selected)}>
      <SelectTrigger size="sm" aria-label={label}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ANY}>Any {label.toLowerCase()}</SelectItem>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export default function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [tests, setTests] = useState<TestRow[]>([])
  const [runs, setRuns] = useState<RunRow[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [loadedAt, setLoadedAt] = useState(0)
  const navigate = useNavigate()

  const filters = {
    test_id: searchParams.get('test_id') ?? '',
    agent_version: searchParams.get('agent_version') ?? '',
    outcome: searchParams.get('outcome') ?? '',
  }
  const setFilter = (name: keyof typeof filters, value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(name, value)
    else next.delete(name)
    setSearchParams(next)
  }

  useEffect(() => {
    listTests().then(setTests, (error: Error) => setLoadError(error.message))
  }, [])

  useEffect(() => {
    listRunsOfAllTests(Object.fromEntries(searchParams)).then(
      (loadedRuns) => {
        setRuns(loadedRuns)
        setLoadedAt(Date.now())
      },
      (error: Error) => setLoadError(error.message),
    )
  }, [searchParams])

  const outcomes = Object.entries(OUTCOME_LABEL) as [Outcome, string][]
  return (
    <section className="space-y-4">
      <h1 className="text-xl font-semibold">Results</h1>
      <div className="flex flex-wrap items-center gap-2">
        <Filter
          label="Test"
          value={filters.test_id}
          options={tests.map((test) => ({ value: test.id, label: test.name }))}
          onChange={(value) => setFilter('test_id', value)}
        />
        <Filter
          label="Agent"
          value={filters.agent_version}
          options={['v1', 'v2'].map((version) => ({ value: version, label: `Agent ${version}` }))}
          onChange={(value) => setFilter('agent_version', value)}
        />
        <Filter
          label="Outcome"
          value={filters.outcome}
          options={outcomes.map(([value, label]) => ({ value, label }))}
          onChange={(value) => setFilter('outcome', value)}
        />
      </div>
      {loadError && <p className="text-sm text-destructive">Couldn't load results: {loadError}</p>}
      {runs && runs.length === 0 && <p className="text-sm text-muted-foreground">No runs match these filters.</p>}
      {runs && runs.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Run</TableHead>
              <TableHead>When</TableHead>
              <TableHead>Test</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead>Outcome</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id} onClick={() => navigate(`/runs/${run.id}`)} className="cursor-pointer">
                <TableCell className="font-mono">
                  <Link to={`/runs/${run.id}`}>{run.id}</Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{startedAtFormat.format(new Date(run.started_at))}</TableCell>
                <TableCell>
                  {run.test_name} <span className="text-muted-foreground">v{run.test_version}</span>
                </TableCell>
                <TableCell>{run.agent_version}</TableCell>
                <TableCell>
                  <OutcomeBadge run={run} now={loadedAt} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  )
}
