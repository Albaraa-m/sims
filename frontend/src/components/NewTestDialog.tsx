import { AlertTriangleIcon } from 'lucide-react'
import { useState } from 'react'

import { createTest, inferTest } from '@/api'
import TestFieldsEditor from '@/components/TestFieldsEditor'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
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
import { Textarea } from '@/components/ui/textarea'
import {
  areFieldsComplete,
  EMPTY_FIELDS,
  fieldsFromSpec,
  specFromFields,
  type TestFields,
} from '@/testFields'
import type { TestSpec } from '@/types'

const UNKNOWN_AGENT_VERSION = 'unknown'

type NewTestDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}

export default function NewTestDialog({ open, onOpenChange, onCreated }: NewTestDialogProps) {
  const [transcript, setTranscript] = useState('')
  const [reportedIssue, setReportedIssue] = useState('')
  const [agentVersion, setAgentVersion] = useState(UNKNOWN_AGENT_VERSION)
  const [fields, setFields] = useState<TestFields>(EMPTY_FIELDS)
  const [fieldsFromLastInfer, setFieldsFromLastInfer] = useState<TestFields>(EMPTY_FIELDS)
  const [inferredSpec, setInferredSpec] = useState<TestSpec | null>(null)
  const [noRegressionReason, setNoRegressionReason] = useState<string | null>(null)
  const [isInferring, setIsInferring] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isConfirmingOverwrite, setIsConfirmingOverwrite] = useState(false)
  const [requestError, setRequestError] = useState<string | null>(null)

  const hasUnsavedEdits = JSON.stringify(fields) !== JSON.stringify(fieldsFromLastInfer)
  const canCreate = transcript.trim() !== '' && areFieldsComplete(fields) && !isCreating

  function resetForm() {
    setTranscript('')
    setReportedIssue('')
    setAgentVersion(UNKNOWN_AGENT_VERSION)
    setFields(EMPTY_FIELDS)
    setFieldsFromLastInfer(EMPTY_FIELDS)
    setInferredSpec(null)
    setNoRegressionReason(null)
    setRequestError(null)
  }

  async function inferFields() {
    setIsConfirmingOverwrite(false)
    setIsInferring(true)
    setRequestError(null)
    try {
      const inferred = await inferTest(transcript, reportedIssue.trim() || null)
      const inferredFields = fieldsFromSpec(inferred.name, inferred.spec)
      setFields(inferredFields)
      setFieldsFromLastInfer(inferredFields)
      setInferredSpec(inferred.spec)
      setNoRegressionReason(inferred.spec ? null : inferred.reason)
    } catch (error) {
      setRequestError(`Couldn't infer the fields: ${(error as Error).message}`)
    } finally {
      setIsInferring(false)
    }
  }

  function requestInfer() {
    if (hasUnsavedEdits) setIsConfirmingOverwrite(true)
    else void inferFields()
  }

  async function createTestFromFields() {
    setIsCreating(true)
    setRequestError(null)
    try {
      await createTest({
        transcript,
        reported_issue: reportedIssue.trim() || null,
        agent_version: agentVersion === UNKNOWN_AGENT_VERSION ? null : agentVersion,
        name: fields.name.trim(),
        spec: specFromFields(fields),
        inferred_spec: inferredSpec,
      })
      resetForm()
      onOpenChange(false)
      onCreated()
    } catch (error) {
      setRequestError(`Couldn't create the test: ${(error as Error).message}`)
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>New test</DialogTitle>
          <DialogDescription>
            Paste a call transcript, then infer the test fields or write them yourself.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="transcript">Transcript</Label>
            <Textarea
              id="transcript"
              rows={8}
              placeholder={'Agent: Hello, how can I help?\nCaller: …'}
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <div className="grid grid-cols-[1fr_10rem] gap-4">
            <div className="grid gap-2">
              <Label htmlFor="reported-issue">Reported issue (optional)</Label>
              <Input
                id="reported-issue"
                placeholder="What went wrong on the call"
                value={reportedIssue}
                onChange={(event) => setReportedIssue(event.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="agent-version">Agent version</Label>
              <Select value={agentVersion} onValueChange={setAgentVersion}>
                <SelectTrigger id="agent-version" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={UNKNOWN_AGENT_VERSION}>Unknown</SelectItem>
                  <SelectItem value="v1">v1</SelectItem>
                  <SelectItem value="v2">v2</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="secondary" onClick={requestInfer} disabled={!transcript.trim() || isInferring}>
              {isInferring ? 'Inferring…' : 'Infer fields'}
            </Button>
          </div>

          {noRegressionReason && (
            <Alert>
              <AlertTriangleIcon />
              <AlertTitle>No regression found</AlertTitle>
              <AlertDescription>
                {noRegressionReason} You can still write the test yourself.
              </AlertDescription>
            </Alert>
          )}

          <TestFieldsEditor
            fields={fields}
            onChange={setFields}
            aiFields={inferredSpec ? fieldsFromLastInfer : null}
          />

          {requestError && <p className="text-sm text-destructive">{requestError}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={createTestFromFields} disabled={!canCreate}>
            {isCreating ? 'Creating…' : 'Create test'}
          </Button>
        </DialogFooter>
      </DialogContent>

      <AlertDialog open={isConfirmingOverwrite} onOpenChange={setIsConfirmingOverwrite}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Replace your edits?</AlertDialogTitle>
            <AlertDialogDescription>
              Inferring again overwrites the fields you've changed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep my edits</AlertDialogCancel>
            <AlertDialogAction onClick={inferFields}>Infer again</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Dialog>
  )
}
