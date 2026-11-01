import { XIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export type FactRow = { key: string; value: string }

type FactsEditorProps = {
  rows: FactRow[]
  onChange: (rows: FactRow[]) => void
}

export default function FactsEditor({ rows, onChange }: FactsEditorProps) {
  function updateRow(index: number, change: Partial<FactRow>) {
    onChange(rows.map((row, i) => (i === index ? { ...row, ...change } : row)))
  }

  return (
    <div className="space-y-2">
      {rows.map((row, index) => (
        <div key={index} className="flex gap-2">
          <Input
            aria-label="Fact name"
            placeholder="party_size"
            value={row.key}
            onChange={(event) => updateRow(index, { key: event.target.value })}
            className="w-40"
          />
          <Input
            aria-label="Fact value"
            placeholder="4"
            value={row.value}
            onChange={(event) => updateRow(index, { value: event.target.value })}
          />
          <Button
            variant="ghost"
            size="icon"
            aria-label="Remove fact"
            onClick={() => onChange(rows.filter((_, i) => i !== index))}
          >
            <XIcon />
          </Button>
        </div>
      ))}
      <Button variant="outline" size="sm" onClick={() => onChange([...rows, { key: '', value: '' }])}>
        Add fact
      </Button>
    </div>
  )
}
