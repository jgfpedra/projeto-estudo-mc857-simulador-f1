import { useEffect, useMemo } from "react"
import {
  AlertTriangle,
  ArrowLeft,
  Cloud,
  CloudDrizzle,
  CloudLightning,
  CloudRain,
  Flag,
  Plus,
  Sun,
  Trash2,
} from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { SummaryRow } from "@/components/summary-row"
import { ToggleButton } from "@/components/toggle-button"
import { Section } from "@/components/section"

import { useCircuitStore } from "@/stores/circuit-store"
import { useDriverStore } from "@/stores/driver-store"
import { isWeatherConfigValid, useWeatherStore } from "@/stores/weather-store"
import { useRaceLaunchStore } from "@/stores/race-launch-store"
import { useRaceLapsStore } from "@/stores/race-laps-store"
import { MAX_STINTS, getRemainingStintLaps, isTireConfigValid, useTiresStore } from "@/stores/tires-store"

import type { Driver } from "@/types/driver"
import { WEATHER_CONDITIONS, WEATHER_LABELS, type WeatherCondition } from "@/types/weather"
import { TIRE_COMPOUNDS, TIRE_LABELS, type TireCompound } from "@/types/tires"

const GRID_SIZE = 20

const WEATHER_ICONS: Record<WeatherCondition, typeof Sun> = {
  dry: Sun,
  cloudy: Cloud,
  light_rain: CloudDrizzle,
  rain: CloudRain,
  heavy_rain: CloudLightning,
}

const TIRE_DOT: Record<TireCompound, string> = {
  SOFT: "bg-red-600",
  MEDIUM: "bg-yellow-400",
  HARD: "bg-zinc-100",
  INTERMEDIATE: "bg-green-600",
  WET: "bg-blue-600",
}

const WET_WEATHER: WeatherCondition[] = ["light_rain", "rain", "heavy_rain"]
const WET_COMPOUNDS: TireCompound[] = ["INTERMEDIATE", "WET"]

function getCompoundWarning(
  weather: WeatherCondition,
  compound: TireCompound,
): string | null {
  const isWetTrack = WET_WEATHER.includes(weather)
  const isWetTire = WET_COMPOUNDS.includes(compound)

  if (isWetTrack && !isWetTire) {
    return "Pneus slick em pista molhada podem ser perigosos. Considere intermediário ou chuva."
  }

  if (!isWetTrack && compound === "WET") {
    return "Pneus de chuva em pista seca desgastam muito rápido."
  }

  return null
}

export function WeatherTiresSelection() {
  const navigate = useNavigate()

  const weatherConfig = useWeatherStore((state) => state.config)
  const setWeather = useWeatherStore((state) => state.setWeather)
  const setTransitionEnabled = useWeatherStore((state) => state.setTransitionEnabled)
  const setTransitionProbability = useWeatherStore((state) => state.setTransitionProbability)
  const toggleTransitionCondition = useWeatherStore((state) => state.toggleTransitionCondition)
  const resetWeather = useWeatherStore((state) => state.resetWeather)

  const tiresConfig = useTiresStore((state) => state.config)
  const setInitialCompound = useTiresStore((state) => state.setInitialCompound)
  const setStrategyEnabled = useTiresStore((state) => state.setStrategyEnabled)
  const addStint = useTiresStore((state) => state.addStint)
  const removeStint = useTiresStore((state) => state.removeStint)
  const updateStintCompound = useTiresStore((state) => state.updateStintCompound)
  const updateStintLaps = useTiresStore((state) => state.updateStintLaps)
  const resetTires = useTiresStore((state) => state.resetTires)

  const isSubmitting = useRaceLaunchStore((state) => state.isSubmitting)
  const submitError = useRaceLaunchStore((state) => state.submitError)
  const startRace = useRaceLaunchStore((state) => state.startRace)
  const clearSubmitError = useRaceLaunchStore((state) => state.clearSubmitError)

  const circuits = useCircuitStore((state) => state.circuits)
  const selectedCircuitId = useCircuitStore((state) => state.selectedCircuitId)
  const selectedLayoutId = useCircuitStore((state) => state.selectedLayoutId)
  const fetchCircuits = useCircuitStore((state) => state.fetchCircuits)

  const season = useDriverStore((state) => state.season)
  const drivers = useDriverStore((state) => state.drivers)

  const totalLaps = useRaceLapsStore((state) => state.totalLaps)
  const syncWithRaceLaps = useTiresStore((state) => state.syncWithRaceLaps)

  useEffect(() => {
    void fetchCircuits()
  }, [fetchCircuits])
  useEffect(() => {
    syncWithRaceLaps()
  }, [totalLaps, syncWithRaceLaps])

  const selectedCircuit = circuits.find((circuit) => circuit.id === selectedCircuitId)
  const selectedLayout = selectedCircuit?.layouts.find((layout) => layout.id === selectedLayoutId)

  const gridDrivers = useMemo(
    () => drivers.filter((driver): driver is Driver => driver !== null),
    [drivers],
  )
  const isGridComplete = gridDrivers.length === GRID_SIZE

  // Sem circuito ou grid completo não há corrida para configurar.
  useEffect(() => {
    if (!selectedCircuitId) {
      navigate("/circuit-selection", { replace: true })
      return
    }
    if (!isGridComplete) {
      navigate("/driver-team-selection", { replace: true })
    }
  }, [selectedCircuitId, isGridComplete, navigate])

  const isConfigValid =
    isWeatherConfigValid(weatherConfig) && isTireConfigValid(tiresConfig, totalLaps)
  const canStart =
    Boolean(selectedCircuitId) && isGridComplete && isConfigValid && !isSubmitting
  const compoundWarning = getCompoundWarning(weatherConfig.weather, tiresConfig.initialCompound)

  const possibleTransitionConditions = WEATHER_CONDITIONS.filter(
    (condition) => condition !== weatherConfig.weather,
  )

  const handleStart = async () => {
    if (!canStart || !selectedCircuitId) return

    const ok = await startRace({
      season,
      circuitId: selectedCircuitId,
      layoutId: selectedLayoutId ?? selectedCircuit?.layouts[0]?.id ?? "",
      grid: gridDrivers.map((driver) => driver.id),
      weather: weatherConfig,
      tires: tiresConfig, totalLaps
    })

    // TODO: definir a rota da corrida e navegar para ela.
    if (ok) navigate("/")
  }

  const handleReset = () => {
    resetWeather()
    resetTires()
    clearSubmitError()
  }

  return (
    <main className="relative min-h-svh bg-background text-foreground lg:h-svh lg:overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_40%,rgba(220,38,38,0.12),transparent_40%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,rgba(0,0,0,0.28)_100%)]" />
      </div>

      <div className="absolute left-0 top-0 h-1 w-full bg-primary" />

      <div className="relative z-10 flex min-h-svh flex-col lg:h-svh">
        {/* Header */}
        <header className="shrink-0 border-b border-border">
          <div className="container mx-auto px-6 py-6 lg:px-12 lg:py-7">
            <div className="flex items-center gap-5">
              <Button
                variant="outline"
                onClick={() => navigate("/driver-team-selection")}
                aria-label="Voltar para pilotos e equipes"
                className="h-11 w-11 shrink-0 rounded-none border-border bg-transparent p-0 hover:bg-accent sm:w-auto sm:px-4"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>

              <div className="min-w-0">
                <div className="mb-2 flex items-center gap-3">
                  <div className="h-1 w-10 bg-primary" />
                  <span className="text-xs font-bold uppercase tracking-[0.3em] text-primary">
                    F1 SIMULATOR
                  </span>
                </div>
                <h1 className="text-3xl font-black uppercase italic tracking-tighter sm:text-5xl">
                  Clima & Pneus
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Defina as condições iniciais e a estratégia de pneus da corrida.
                </p>
              </div>
            </div>
          </div>
        </header>

        <div className="container mx-auto grid min-h-0 flex-1 gap-6 px-6 py-5 lg:grid-cols-[1fr_380px] lg:px-12 lg:py-7">
          {/* Configuração */}
          <div className="min-h-0 space-y-6 overflow-y-auto pr-1">
            {/* Clima */}
            <Section step="01" title="Clima inicial" description="Condição da pista na largada.">
              <div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-5">
                {WEATHER_CONDITIONS.map((condition) => {
                  const Icon = WEATHER_ICONS[condition]
                  const isActive = weatherConfig.weather === condition

                  return (
                    <button
                      key={condition}
                      type="button"
                      onClick={() => setWeather(condition)}
                      aria-pressed={isActive}
                      className={[
                        "flex flex-col items-center gap-2 px-3 py-5 transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "bg-card text-muted-foreground hover:bg-accent hover:text-foreground",
                      ].join(" ")}
                    >
                      <Icon className="h-6 w-6" />
                      <span className="text-[11px] font-black uppercase tracking-wider">
                        {WEATHER_LABELS[condition]}
                      </span>
                    </button>
                  )
                })}
              </div>

              {/* Transição de clima */}
              <div className="mt-6 space-y-4 border-t border-border pt-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-black uppercase tracking-wider">
                      Mudança de clima durante a corrida
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">Opcional</div>
                  </div>
                  <ToggleButton
                    active={weatherConfig.transition.enabled}
                    onClick={() => setTransitionEnabled(!weatherConfig.transition.enabled)}
                    labelOn="Ativado"
                    labelOff="Desativado"
                  />
                </div>

                {weatherConfig.transition.enabled && (
                  <div className="space-y-5">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Label>Probabilidade de mudança</Label>
                        <span className="font-mono text-sm text-muted-foreground">
                          {weatherConfig.transition.probability}%
                        </span>
                      </div>
                      <Slider
                        value={[weatherConfig.transition.probability]}
                        min={0}
                        max={100}
                        step={5}
                        onValueChange={([value]) => setTransitionProbability(value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Condições possíveis</Label>
                      <div className="flex flex-wrap gap-2">
                        {possibleTransitionConditions.map((condition) => {
                          const isSelected = weatherConfig.transition.possibleConditions.includes(condition)

                          return (
                            <button
                              key={condition}
                              type="button"
                              onClick={() => toggleTransitionCondition(condition)}
                              aria-pressed={isSelected}
                              className={[
                                "border px-3 py-2 text-[11px] font-black uppercase tracking-wider transition-colors",
                                isSelected
                                  ? "border-primary bg-primary text-primary-foreground"
                                  : "border-border bg-background text-muted-foreground hover:bg-accent hover:text-foreground",
                              ].join(" ")}
                            >
                              {WEATHER_LABELS[condition]}
                            </button>
                          )
                        })}
                      </div>
                      {weatherConfig.transition.possibleConditions.length === 0 && (
                        <p className="text-xs text-primary">Selecione ao menos uma condição.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </Section>

            {/* Pneu inicial */}
            <Section step="02" title="Pneu inicial" description="Composto usado na largada.">
              <div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-5">
                {TIRE_COMPOUNDS.map((compound) => {
                  const isActive = tiresConfig.initialCompound === compound

                  return (
                    <button
                      key={compound}
                      type="button"
                      onClick={() => setInitialCompound(compound)}
                      aria-pressed={isActive}
                      className={[
                        "flex flex-col items-start gap-3 px-4 py-4 text-left transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "bg-card text-muted-foreground hover:bg-accent hover:text-foreground",
                      ].join(" ")}
                    >
                      <span className={`h-4 w-4 rounded-full ${TIRE_DOT[compound]}`} />
                      <div>
                        <div className="text-xs font-black uppercase tracking-wider">{compound}</div>
                        <div className="mt-0.5 text-[10px] uppercase tracking-wider opacity-80">
                          {TIRE_LABELS[compound]}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>

              {compoundWarning && (
                <div className="mt-4 flex items-start gap-3 border border-primary/50 bg-primary/10 p-3 text-xs text-foreground">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <span>{compoundWarning}</span>
                </div>
              )}
            </Section>

            {/* Estratégia */}
            <Section
              step="03"
              title="Estratégia de stints"
              description="Planeje as trocas de pneu antes da corrida. Opcional."
              action={
                <ToggleButton
                  active={tiresConfig.strategy.enabled}
                  onClick={() => setStrategyEnabled(!tiresConfig.strategy.enabled)}
                  labelOn="Definida"
                  labelOff="Não definida"
                />
              }
            >
              {tiresConfig.strategy.enabled ? (
                <div className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Voltas planejadas:{" "}
                    <span className="font-mono text-foreground">
                      {totalLaps - getRemainingStintLaps(tiresConfig.strategy.stints, totalLaps)}
                    </span>{" "}
                    / {totalLaps}
                  </p>
                  {tiresConfig.strategy.stints.map((stint, index) => {
                    const isFirst = index === 0

                    return (
                      <div
                        key={stint.id}
                        className="grid grid-cols-[auto_1fr_96px_auto] items-center gap-3 border border-border bg-background p-3"
                      >
                        <span className="flex h-10 w-10 items-center justify-center bg-card text-xs font-black italic">
                          {index + 1}
                        </span>

                        {isFirst ? (
                          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider">
                            <span className={`h-3 w-3 rounded-full ${TIRE_DOT[stint.compound]}`} />
                            {stint.compound}
                            <span className="font-normal text-muted-foreground">· pneu inicial</span>
                          </div>
                        ) : (
                          <Select
                            value={stint.compound}
                            onValueChange={(value) =>
                              updateStintCompound(stint.id, value as TireCompound)
                            }
                          >
                            <SelectTrigger className="h-10 w-full rounded-none border-border bg-card uppercase">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {TIRE_COMPOUNDS.map((compound) => (
                                <SelectItem key={compound} value={compound}>
                                  <span className="flex items-center gap-2">
                                    <span className={`h-3 w-3 rounded-full ${TIRE_DOT[compound]}`} />
                                    {compound}
                                  </span>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}

                        <div className="relative">
                          <Input
                            type="number"
                            min={1}
                            max={getRemainingStintLaps(tiresConfig.strategy.stints, totalLaps, stint.id)}
                            value={stint.laps}
                            onChange={(event) => updateStintLaps(stint.id, Number(event.target.value))}
                            aria-label={`Voltas do stint ${index + 1}`}
                            className="h-10 rounded-none border-border bg-card pr-10 text-right"
                          />
                          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[10px] uppercase text-muted-foreground">
                            voltas
                          </span>
                        </div>

                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => removeStint(stint.id)}
                          disabled={tiresConfig.strategy.stints.length <= 1}
                          aria-label={`Remover stint ${index + 1}`}
                          className="h-10 w-10 rounded-none border-border bg-transparent hover:border-destructive hover:bg-destructive hover:text-destructive-foreground"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    )
                  })}

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addStint}
                    disabled={
                      tiresConfig.strategy.stints.length >= MAX_STINTS ||
                      getRemainingStintLaps(tiresConfig.strategy.stints, totalLaps) < 1
                    }
                    className="rounded-none border-border bg-transparent uppercase"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Adicionar stint
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Ative para planejar as trocas de pneu. Sem estratégia definida, a decisão fica para o decorrer da corrida.
                </p>
              )}
            </Section>
          </div>

          {/* Resumo */}
          <aside className="flex min-h-0 flex-col border border-border bg-card/40">
            <div className="border-b border-border p-5">
              <div className="text-xs font-bold uppercase tracking-[0.25em] text-primary">Resumo</div>
            </div>

            <div className="min-h-0 flex-1 divide-y divide-border overflow-y-auto">
              <SummaryRow
                label="Circuito"
                value={
                  selectedCircuit
                    ? `${selectedCircuit.name}${selectedLayout ? ` · ${selectedLayout.name}` : ""}`
                    : "Carregando..."
                }
              />
              <SummaryRow
                label="Grid"
                value={`${gridDrivers.length}/${GRID_SIZE} pilotos · Temporada ${season}`}
              />
              <SummaryRow label="Clima inicial" value={WEATHER_LABELS[weatherConfig.weather]} />
              <SummaryRow
                label="Mudança de clima"
                value={
                  weatherConfig.transition.enabled
                    ? `${weatherConfig.transition.probability}% · ${
                        weatherConfig.transition.possibleConditions.length > 0
                          ? weatherConfig.transition.possibleConditions.map((c) => WEATHER_LABELS[c]).join(", ")
                          : "sem condições"
                      }`
                    : "Desativada"
                }
              />
              <SummaryRow
                label="Pneu inicial"
                value={`${tiresConfig.initialCompound} · ${TIRE_LABELS[tiresConfig.initialCompound]}`}
              />
              <SummaryRow
                label="Estratégia"
                value={
                  tiresConfig.strategy.enabled
                    ? tiresConfig.strategy.stints
                        .map((stint) => `${stint.compound} ${stint.laps}v`)
                        .join(" → ")
                    : "Não definida"
                }
              />
            </div>

            <div className="space-y-3 border-t border-border p-5">
              {!isConfigValid && (
                <p className="text-xs text-primary">
                  Revise a configuração: há campos incompletos.
                </p>
              )}
              {submitError && <p className="text-xs text-primary">{submitError}</p>}

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handleReset}
                  disabled={isSubmitting}
                  className="h-12 rounded-none border-border bg-transparent uppercase"
                >
                  Redefinir
                </Button>

                <Button
                  onClick={handleStart}
                  disabled={!canStart}
                  size="lg"
                  className="h-12 flex-1 rounded-none font-black uppercase tracking-wider"
                >
                  <Flag className="mr-2 h-4 w-4" />
                  {isSubmitting ? "Iniciando..." : "Iniciar Corrida"}
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  )
}