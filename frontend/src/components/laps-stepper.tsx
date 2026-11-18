import { useEffect, useState } from "react"
import { Minus, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type LapsStepperProps = {
  id?: string
  value: number
  min: number
  max: number
  onChange: (value: number) => void
  ariaLabel: string
  className?: string
}

export function LapsStepper({
  id,
  value,
  min,
  max,
  onChange,
  ariaLabel,
  className,
}: LapsStepperProps) {
  // Rascunho local: permite apagar e digitar sem corrigir o valor a cada tecla.
  const [draft, setDraft] = useState(String(value))

  useEffect(() => {
    setDraft(String(value))
  }, [value])

  const clamp = (laps: number) =>
    Math.min(max, Math.max(min, Math.floor(laps)))

  const commit = (laps: number) => {
    const next = clamp(laps)
    onChange(next)
    setDraft(String(next))
  }

  const commitDraft = () => {
    if (draft === "") {
      setDraft(String(value))
      return
    }
    commit(Number(draft))
  }

  const canDecrease = value > min
  const canIncrease = value < max

  const stepButtonClass =
  "h-full w-8 shrink-0 rounded-none bg-transparent p-0 text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-30 sm:w-10"

  return (
    <div
      className={"flex h-9 items-stretch border border-border bg-background".concat(className ?? "")}
    >
      <Button
        type="button"
        variant="ghost"
        onClick={() => commit(value - 1)}
        disabled={!canDecrease}
        aria-label={`Diminuir ${ariaLabel}`}
        className={stepButtonClass.concat("border-r border-border")}
      >
        <Minus className="h-4 w-4" />
      </Button>

      <Input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        aria-label={ariaLabel}
        value={draft}
        onChange={(event) => setDraft(event.target.value.replace(/\D/g, ""))}
        onBlur={commitDraft}
        onKeyDown={(event) => {
          if (event.key === "Enter") commitDraft()
        }}
        className="h-full min-w-0 flex-1 rounded-none border-0 bg-transparent px-0 py-0 text-center font-mono text-base font-black shadow-none focus-visible:ring-0 sm:text-lg"
      />

      <Button
        type="button"
        variant="ghost"
        onClick={() => commit(value + 1)}
        disabled={!canIncrease}
        aria-label={`Aumentar ${ariaLabel}`}
        className={stepButtonClass.concat("border-l border-border")}
      >
        <Plus className="h-4 w-4" />
      </Button>
    </div>
  )
}