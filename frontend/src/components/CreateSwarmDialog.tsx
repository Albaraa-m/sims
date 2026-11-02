import { AlertTriangleIcon } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { findPolicies, generateSwarm } from '@/api'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { MAX_TESTS_PER_POLICY, MAX_TESTS_PER_SWARM, spreadTestsAcrossPolicies } from '@/swarms'

const DEFAULT_MAXIMUM_TESTS = 12

type CreateSwarmDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function CreateSwarmDialog({ open, onOpenChange }: CreateSwarmDialogProps) {
  const [agentVersion, setAgentVersion] = useState('v2')
  // Null until the policies are found; then the dialog shows them.
  const [policies, setPolicies] = useState<string[] | null>(null)
  const [untickedPolicies, setUntickedPolicies] = useState<string[]>([])
  const [typedCounts, setTypedCounts] = useState<Record<string, number>>({})
  const [maximumTests, setMaximumTests] = useState(DEFAULT_MAXIMUM_TESTS)
  const [isFinding, setIsFinding] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [requestError, setRequestError] = useState<string | null>(null)
  const navigate = useNavigate()

  const tickedPolicies = (policies ?? []).filter((policy) => !untickedPolicies.includes(policy))
  const tickedTypedCounts = Object.fromEntries(
    Object.entries(typedCounts).filter(([policy]) => tickedPolicies.includes(policy)),
  )
  const counts = spreadTestsAcrossPolicies(maximumTests, tickedPolicies, tickedTypedCounts)
  const totalTests = Object.values(counts).reduce((sum, count) => sum + count, 0)
  const minimumTests = tickedPolicies.reduce((sum, policy) => sum + (tickedTypedCounts[policy] ?? 1), 0)
  const isOverMaximum = totalTests > maximumTests
  const canGenerate =
    tickedPolicies.length > 0 && !isOverMaximum && maximumTests <= MAX_TESTS_PER_SWARM && !isGenerating

  function close() {
    onOpenChange(false)
    setPolicies(null)
    setUntickedPolicies([])
    setTypedCounts({})
    setRequestError(null)
  }

  async function findPoliciesOfAgent() {
    setIsFinding(true)
    setRequestError(null)
    try {
      setPolicies((await findPolicies(agentVersion)).policies)
    } catch (error) {
      setRequestError(`Couldn't find the policies: ${(error as Error).message}`)
    } finally {
      setIsFinding(false)
    }
  }

  async function generateTests() {
    setIsGenerating(true)
    setRequestError(null)
    try {
      const testCounts = tickedPolicies.map((policy) => ({ policy, count: counts[policy] }))
      const proposal = await generateSwarm(agentVersion, testCounts)
      close()
      navigate('/swarms/new', { state: proposal })
    } catch (error) {
      setRequestError(`Couldn't generate the tests: ${(error as Error).message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  function togglePolicy(policy: string, isTicked: boolean) {
    setUntickedPolicies(isTicked ? untickedPolicies.filter((p) => p !== policy) : [...untickedPolicies, policy])
  }

  return (
    <Dialog open={open} onOpenChange={isFinding || isGenerating ? undefined : (isOpen) => !isOpen && close()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create swarm</DialogTitle>
          <DialogDescription>
            {policies === null
              ? "Finds the policies in the agent's instructions; you then choose which to test and how many tests each gets."
              : `Policies found in ${agentVersion}'s instructions. Every ticked policy gets at least one test.`}
          </DialogDescription>
        </DialogHeader>

        {policies === null ? (
          <div className="grid max-w-xs gap-2">
            <Label htmlFor="swarm-agent-version">Agent version</Label>
            <Select value={agentVersion} onValueChange={setAgentVersion}>
              <SelectTrigger id="swarm-agent-version" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="v1">v1</SelectItem>
                <SelectItem value="v2">v2</SelectItem>
              </SelectContent>
            </Select>
          </div>
        ) : (
          <div className="grid gap-4">
            <div className="flex items-center gap-3">
              <Label htmlFor="swarm-maximum-tests">Maximum tests</Label>
              <Input
                id="swarm-maximum-tests"
                type="number"
                min={1}
                max={MAX_TESTS_PER_SWARM}
                value={maximumTests}
                onChange={(event) => setMaximumTests(event.target.valueAsNumber || 0)}
                className="w-20"
              />
              <span className="ml-auto text-sm text-muted-foreground">
                Tests: {totalTests} of {maximumTests}
              </span>
            </div>

            {isOverMaximum && (
              <Alert>
                <AlertTriangleIcon />
                <AlertDescription>
                  <p>
                    {tickedPolicies.length} ticked policies need at least {minimumTests} tests. Raise the maximum or
                    untick policies.
                  </p>
                  {minimumTests <= MAX_TESTS_PER_SWARM && (
                    <Button size="sm" variant="outline" className="mt-2" onClick={() => setMaximumTests(minimumTests)}>
                      Raise maximum to {minimumTests}
                    </Button>
                  )}
                </AlertDescription>
              </Alert>
            )}
            {maximumTests > MAX_TESTS_PER_SWARM && (
              <p className="text-sm text-destructive">A swarm can have at most {MAX_TESTS_PER_SWARM} tests.</p>
            )}

            <ul className="divide-y rounded-lg border text-sm">
              {policies.map((policy) => {
                const isTicked = tickedPolicies.includes(policy)
                return (
                  <li key={policy} className="flex items-center gap-3 px-3 py-2">
                    <Checkbox
                      checked={isTicked}
                      onCheckedChange={(checked) => togglePolicy(policy, checked === true)}
                      aria-label={`Test: ${policy}`}
                    />
                    <span className={`flex-1 ${isTicked ? '' : 'text-muted-foreground line-through'}`}>{policy}</span>
                    {isTicked && (
                      <Input
                        type="number"
                        min={1}
                        max={MAX_TESTS_PER_POLICY}
                        value={counts[policy]}
                        onChange={(event) => {
                          const count = Math.min(MAX_TESTS_PER_POLICY, Math.max(1, event.target.valueAsNumber || 1))
                          setTypedCounts({ ...typedCounts, [policy]: count })
                        }}
                        aria-label={`Tests for: ${policy}`}
                        className="w-16"
                      />
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {(isFinding || isGenerating) && (
          <p className="text-sm text-muted-foreground">
            {isFinding
              ? `Reading ${agentVersion}'s instructions…`
              : `Writing ${totalTests} tests for ${tickedPolicies.length} policies… this takes about half a minute.`}
          </p>
        )}
        {requestError && <p className="text-sm text-destructive">{requestError}</p>}

        <DialogFooter>
          {policies === null ? (
            <>
              <Button variant="outline" onClick={close} disabled={isFinding}>
                Cancel
              </Button>
              <Button onClick={findPoliciesOfAgent} disabled={isFinding}>
                {isFinding ? 'Finding policies…' : 'Find policies'}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setPolicies(null)} disabled={isGenerating}>
                Back
              </Button>
              <Button onClick={generateTests} disabled={!canGenerate}>
                {isGenerating ? 'Generating…' : `Generate ${totalTests} tests`}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
