import { useEffect, useState } from "react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  MAX_RACE_LAPS,
  MIN_RACE_LAPS,
  clampRaceLaps,
  useRaceLapsStore,
} from "@/stores/race-laps-store"

export function RaceLapsField() {
  const totalLaps = useRaceLapsStore((state) => state.totalLaps)
  const setTotalLaps = useRaceLapsStore((state) => state.setTotalLaps)

  // Rascunho local: permite apagar e digitar sem o valor ser corrigido a cada tecla.
  const [draft, setDraft] = useState(String(totalLaps))

  useEffect(() => {
    setDraft(String(totalLaps))
  }, [totalLaps])

  const commit = () => {
    const parsed = Number(draft)

    if (draft.trim() === "" || Number.isNaN(parsed)) {
      setDraft(String(totalLaps))
      return
    }

    const clamped = clampRaceLaps(parsed)
    setTotalLaps(clamped)
    setDraft(String(clamped))
  }

  return (
    <div className="space-y-2">
      <Label htmlFor="race-laps">Voltas da corrida</Label>

      <Input
        id="race-laps"
        type="number"
        inputMode="numeric"
        min={MIN_RACE_LAPS}
        max={MAX_RACE_LAPS}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") commit()
        }}
        className="h-12 rounded-none border-border bg-background text-right font-mono"
      />

      <p className="text-xs text-muted-foreground">
        De {MIN_RACE_LAPS} a {MAX_RACE_LAPS} voltas.
      </p>
    </div>
  )
}