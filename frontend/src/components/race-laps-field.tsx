import { LapsStepper } from "@/components/laps-stepper"
import {
  MAX_RACE_LAPS,
  MIN_RACE_LAPS,
  useRaceLapsStore,
} from "@/stores/race-laps-store"

export function RaceLapsField() {
  const totalLaps = useRaceLapsStore((state) => state.totalLaps)
  const setTotalLaps = useRaceLapsStore((state) => state.setTotalLaps)

  return (
    <div>
      <label
        htmlFor="race-laps"
        className="mb-2 block text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground"
      >
        Voltas
      </label>

      <LapsStepper
        id="race-laps"
        value={totalLaps}
        min={MIN_RACE_LAPS}
        max={MAX_RACE_LAPS}
        onChange={setTotalLaps}
        ariaLabel="voltas da corrida"
      />

      <p className="mt-2 text-xs text-muted-foreground">
        De {MIN_RACE_LAPS} a {MAX_RACE_LAPS} voltas.
      </p>
    </div>
  )
}