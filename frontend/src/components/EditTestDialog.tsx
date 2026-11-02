import { useState } from 'react'

import { editTest } from '@/api'
import TestFieldsEditor from '@/components/TestFieldsEditor'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { areFieldsComplete, fieldsFromSpec, specFromFields, type TestFields } from '@/testFields'
import type { TestDetail } from '@/types'

type EditTestDialogProps = {
  test: TestDetail
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: (newVersion: TestDetail) => void
}

export default function EditTestDialog({ test, open, onOpenChange, onSaved }: EditTestDialogProps) {
  const [fields, setFields] = useState<TestFields>(() => fieldsFromSpec(test.name, test.spec))
  const [isSaving, setIsSaving] = useState(false)
  const [requestError, setRequestError] = useState<string | null>(null)

  const aiFields = test.inferred ? fieldsFromSpec(null, test.inferred) : null
  const hasChanges = JSON.stringify(fields) !== JSON.stringify(fieldsFromSpec(test.name, test.spec))

  async function saveAsNewVersion() {
    setIsSaving(true)
    setRequestError(null)
    try {
      onSaved(await editTest(test.id, fields.name.trim(), specFromFields(fields)))
    } catch (error) {
      setRequestError(`Couldn't save the test: ${(error as Error).message}`)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit test</DialogTitle>
          <DialogDescription>
            Saving creates v{test.version + 1} as a draft. Earlier versions and their simulations stay as they are.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4">
          <TestFieldsEditor
            fields={fields}
            onChange={setFields}
            aiFields={aiFields}
            aiLabel={test.swarm_id ? 'Generated' : 'Inferred'}
          />
          {requestError && <p className="text-sm text-destructive">{requestError}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={saveAsNewVersion} disabled={!hasChanges || !areFieldsComplete(fields) || isSaving}>
            {isSaving ? 'Saving…' : 'Save as new version'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
