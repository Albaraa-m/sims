import { useState, type ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

type SpecFieldProps = {
  label: string
  value: ReactNode
  // Undefined or null when the model suggested nothing; the field then has no label.
  inferredValue: ReactNode | undefined
  // Needed when the values aren't plain text and can't be compared directly.
  isEdited?: boolean
}

export default function SpecField({ label, value, inferredValue, isEdited }: SpecFieldProps) {
  const [isShowingInferred, setIsShowingInferred] = useState(false)
  const wasInferred = inferredValue !== undefined && inferredValue !== null
  const edited = wasInferred && (isEdited ?? value !== inferredValue)

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium">{label}</h2>
        {wasInferred && <Badge variant={edited ? 'outline' : 'secondary'}>{edited ? 'Edited' : 'Inferred'}</Badge>}
        {edited && (
          <Button
            variant="link"
            size="sm"
            className="h-auto p-0 text-muted-foreground"
            onClick={() => setIsShowingInferred(!isShowingInferred)}
            aria-expanded={isShowingInferred}
          >
            {isShowingInferred ? 'Hide AI version' : 'Show AI version'}
          </Button>
        )}
      </div>
      <div className="text-sm">{value}</div>
      {edited && isShowingInferred && (
        <div className="border-l-2 pl-3 text-sm text-muted-foreground">{inferredValue}</div>
      )}
    </div>
  )
}
