import { AlertTriangleIcon } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'

import { saveSwarm } from '@/api'
import TestFieldsEditor from '@/components/TestFieldsEditor'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { groupByPolicy } from '@/swarms'
import { areFieldsComplete, fieldsFromSpec, specFromFields, type TestFields } from '@/testFields'
import type { SwarmProposal } from '@/types'

type DraftScenario = {
  key: number
  fields: TestFields
  // What the model wrote, to mark the reviewer's edits.
  generated: TestFields
}

function defaultSwarmName(agentVersion: string): string {
  const today = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date())
  return `Agent ${agentVersion} · ${today}`
}

function ReviewSwarm({ proposal }: { proposal: SwarmProposal }) {
  const [name, setName] = useState(() => defaultSwarmName(proposal.agent_version))
  const [scenarios, setScenarios] = useState<DraftScenario[]>(() =>
    proposal.scenarios.map((scenario, key) => {
      const fields = fieldsFromSpec(scenario.name, scenario.spec)
      return { key, fields, generated: fields }
    }),
  )
  const [editingKey, setEditingKey] = useState<number | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const navigate = useNavigate()

  const incompleteCount = scenarios.filter((scenario) => !areFieldsComplete(scenario.fields)).length
  const canSave = name.trim() !== '' && scenarios.length > 0 && incompleteCount === 0 && !isSaving

  function updateScenario(key: number, fields: TestFields) {
    setScenarios(scenarios.map((scenario) => (scenario.key === key ? { ...scenario, fields } : scenario)))
  }

  async function saveReviewedSwarm() {
    setIsSaving(true)
    setSaveError(null)
    try {
      const swarm = await saveSwarm({
        name: name.trim(),
        agent_version: proposal.agent_version,
        // A policy whose tests were all removed isn't part of the swarm.
        policies: groups.filter(({ items }) => items.length > 0).map(({ policy }) => policy),
        scenarios: scenarios.map(({ fields }) => ({ name: fields.name.trim(), spec: specFromFields(fields) })),
      })
      navigate(`/swarms/${swarm.id}`, { replace: true })
    } catch (error) {
      setSaveError(`Couldn't save the swarm: ${(error as Error).message}`)
      setIsSaving(false)
    }
  }

  const groups = groupByPolicy(proposal.policies, scenarios, (scenario) => scenario.fields.policy_under_test)
  return (
    <section className="space-y-6">
      <div className="space-y-2">
        <Link to="/swarms" className="text-sm text-muted-foreground hover:text-foreground">
          Swarms
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">New swarm</h1>
          <span className="text-sm text-muted-foreground">
            Agent {proposal.agent_version} · {scenarios.length} tests · Not saved yet
          </span>
          <div className="ml-auto flex gap-2">
            <Button variant="outline" onClick={() => navigate('/swarms')} disabled={isSaving}>
              Discard
            </Button>
            <Button onClick={saveReviewedSwarm} disabled={!canSave}>
              {isSaving ? 'Saving…' : 'Save swarm'}
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Review the generated tests, edit or remove any, then save. Saving doesn't run anything.
        </p>
      </div>

      <div className="grid max-w-md gap-2">
        <Label htmlFor="swarm-name">Name</Label>
        <Input id="swarm-name" value={name} onChange={(event) => setName(event.target.value)} />
      </div>

      {proposal.warnings.map((warning) => (
        <Alert key={warning}>
          <AlertTriangleIcon />
          <AlertTitle>Generation</AlertTitle>
          <AlertDescription>{warning}</AlertDescription>
        </Alert>
      ))}
      {incompleteCount > 0 && (
        <p className="text-sm text-destructive">Fill in every field of {incompleteCount} test(s) before saving.</p>
      )}
      {saveError && <p className="text-sm text-destructive">{saveError}</p>}

      {groups.map(({ policy, items }) => (
        <div key={policy} className="space-y-2">
          <h2 className="text-base font-semibold">
            {policy}{' '}
            <span className="font-normal text-muted-foreground">
              · {items.length} {items.length === 1 ? 'test' : 'tests'}
            </span>
          </h2>
          {items.length === 0 && (
            <p className="text-sm text-muted-foreground">No tests left, so this policy won't be saved.</p>
          )}
          {items.map((scenario) => (
            <div key={scenario.key} className="space-y-3 rounded-lg border p-3 text-sm">
              <div className="flex items-start gap-3">
                <div className="flex-1 space-y-1">
                  <p className="font-medium">{scenario.fields.name || 'Untitled'}</p>
                  <p className="text-muted-foreground">{scenario.fields.behavior}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditingKey(editingKey === scenario.key ? null : scenario.key)}
                >
                  {editingKey === scenario.key ? 'Done' : 'Edit'}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setScenarios(scenarios.filter((other) => other.key !== scenario.key))}
                >
                  Remove
                </Button>
              </div>
              {editingKey === scenario.key && (
                <div className="grid gap-4 border-t pt-3">
                  <TestFieldsEditor
                    fields={scenario.fields}
                    onChange={(fields) => updateScenario(scenario.key, fields)}
                    aiFields={scenario.generated}
                    aiLabel="Generated"
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      ))}
    </section>
  )
}

export default function NewSwarmPage() {
  const proposal = useLocation().state as SwarmProposal | null
  if (!proposal) {
    return (
      <p className="text-sm text-muted-foreground">
        Nothing to review: generated swarms aren't kept until saved.{' '}
        <Link to="/swarms" className="underline">
          Create a swarm
        </Link>
        .
      </p>
    )
  }
  return <ReviewSwarm proposal={proposal} />
}
