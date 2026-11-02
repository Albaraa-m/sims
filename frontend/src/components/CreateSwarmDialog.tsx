import { useState } from 'react'
import { useNavigate } from 'react-router'

import { findPolicies, generateSwarm } from '@/api'
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
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { Policy } from '@/types'

type CreateSwarmDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function CreateSwarmDialog({ open, onOpenChange }: CreateSwarmDialogProps) {
  const [agentVersion, setAgentVersion] = useState('v2')
  // Null until the policies are found; then the dialog lists them.
  const [policies, setPolicies] = useState<Policy[] | null>(null)
  const [untickedNames, setUntickedNames] = useState<string[]>([])
  const [isFinding, setIsFinding] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [requestError, setRequestError] = useState<string | null>(null)
  const navigate = useNavigate()

  const tickedPolicies = (policies ?? []).filter((policy) => !untickedNames.includes(policy.name))

  function close() {
    onOpenChange(false)
    setPolicies(null)
    setUntickedNames([])
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
      const proposal = await generateSwarm(agentVersion, tickedPolicies)
      close()
      navigate('/swarms/new', { state: proposal })
    } catch (error) {
      setRequestError(`Couldn't generate the tests: ${(error as Error).message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  function togglePolicy(name: string, isTicked: boolean) {
    setUntickedNames(isTicked ? untickedNames.filter((other) => other !== name) : [...untickedNames, name])
  }

  return (
    <Dialog open={open} onOpenChange={isFinding || isGenerating ? undefined : (isOpen) => !isOpen && close()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create swarm</DialogTitle>
          <DialogDescription>
            {policies === null
              ? "Finds the policies in the agent's instructions; each policy you keep gets one test."
              : `Policies found in ${agentVersion}'s instructions. Each ticked policy gets one test.`}
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
          <ul className="divide-y rounded-lg border text-sm">
            {policies.map((policy) => {
              const isTicked = !untickedNames.includes(policy.name)
              return (
                <li key={policy.name}>
                  <Label className="flex items-start gap-3 px-3 py-2 font-normal">
                    <Checkbox
                      checked={isTicked}
                      onCheckedChange={(checked) => togglePolicy(policy.name, checked === true)}
                      className="mt-0.5"
                    />
                    <span className={`space-y-0.5 ${isTicked ? '' : 'opacity-50'}`}>
                      <span className="block font-medium">{policy.name}</span>
                      <span className="block text-muted-foreground">{policy.rule}</span>
                    </span>
                  </Label>
                </li>
              )
            })}
          </ul>
        )}

        {(isFinding || isGenerating) && (
          <p className="text-sm text-muted-foreground">
            {isFinding
              ? `Reading ${agentVersion}'s instructions…`
              : `Writing ${tickedPolicies.length} tests… this takes about half a minute.`}
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
              <Button onClick={generateTests} disabled={tickedPolicies.length === 0 || isGenerating}>
                {isGenerating ? 'Generating…' : `Generate ${tickedPolicies.length} tests`}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
