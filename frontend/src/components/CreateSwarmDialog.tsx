import { useState } from 'react'
import { useNavigate } from 'react-router'

import { generateSwarm } from '@/api'
import { Button } from '@/components/ui/button'
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

const DEFAULT_TEST_COUNT = 12
const MAX_TEST_COUNT = 40

type CreateSwarmDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function CreateSwarmDialog({ open, onOpenChange }: CreateSwarmDialogProps) {
  const [agentVersion, setAgentVersion] = useState('v2')
  const [testCount, setTestCount] = useState(DEFAULT_TEST_COUNT)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)
  const navigate = useNavigate()

  const isTestCountValid = Number.isInteger(testCount) && testCount >= 1 && testCount <= MAX_TEST_COUNT

  async function generateProposal() {
    setIsGenerating(true)
    setGenerateError(null)
    try {
      const proposal = await generateSwarm(agentVersion, testCount)
      onOpenChange(false)
      navigate('/swarms/new', { state: proposal })
    } catch (error) {
      setGenerateError(`Couldn't generate the swarm: ${(error as Error).message}`)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={isGenerating ? undefined : onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create swarm</DialogTitle>
          <DialogDescription>
            Reads the agent's instructions, finds its policies and writes caller scenarios that test each one. You
            review them before anything is saved.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
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
          <div className="grid gap-2">
            <Label htmlFor="swarm-test-count">Number of tests</Label>
            <Input
              id="swarm-test-count"
              type="number"
              min={1}
              max={MAX_TEST_COUNT}
              value={testCount}
              onChange={(event) => setTestCount(event.target.valueAsNumber)}
            />
          </div>
        </div>
        {isGenerating && (
          <p className="text-sm text-muted-foreground">
            Reading {agentVersion}'s instructions and writing {testCount} scenarios… this takes about half a minute.
          </p>
        )}
        {generateError && <p className="text-sm text-destructive">{generateError}</p>}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isGenerating}>
            Cancel
          </Button>
          <Button onClick={generateProposal} disabled={!isTestCountValid || isGenerating}>
            {isGenerating ? 'Generating…' : 'Generate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
