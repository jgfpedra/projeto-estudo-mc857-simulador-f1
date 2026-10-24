import { useEffect, useMemo, useState } from "react"
import { AlertTriangle, ArrowLeft, Pause, Play, RotateCcw } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { TrackMap } from "@/components/race/track-map"
import { useCurrentTick, usePlayerState } from "@/hooks/use-current-tick"
import { tickPlayer } from "@/services/tick-player"
import type { RaceData, RaceEvent } from "@/types/race"

const RACE_URL = "/races/interlagos-2025.json"
const BANNER_S = 6
const FEED_SIZE = 15
const SPEEDS = [1, 2, 4, 8]

const TRACK_LABEL: Record<string, string> = {
  yellow: "Bandeira amarela",
  safety_car: "Safety car",
  vsc: "VSC",
  red_flag: "Bandeira vermelha",
}

function formatTime(s: number): string {
  const total = Math.max(0, s)
  const m = Math.floor(total / 60)
  return `${String(m).padStart(2, "0")}:${(total % 60).toFixed(1).padStart(4, "0")}`
}

export function RaceSimulation() {
  const navigate = useNavigate()
  const [race, setRace] = useState<RaceData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const tick = useCurrentTick()
  const { playing, speed } = usePlayerState()

  useEffect(() => {
    let active = true

    fetch(RACE_URL)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Falha ao carregar a corrida (${res.status}).`)
        return (await res.json()) as RaceData
      })
      .then((data) => {
        if (!active) return
        tickPlayer.load(data.ticks, data.meta.tickHz)
        setRace(data)
      })
      .catch((e: unknown) => {
        if (active) setError(e instanceof Error ? e.message : "Erro desconhecido.")
      })

    return () => {
      active = false
      tickPlayer.pause()
    }
  }, [])

  const now = tick?.t ?? 0

  const recent = useMemo(
    () => (race ? race.events.filter((e) => e.t <= now) : []),
    [race, now],
  )

  const banner = useMemo(() => {
    let found: RaceEvent | null = null
    for (const e of recent) if (now - e.t < BANNER_S) found = e
    return found
  }, [recent, now])

  if (error) {
    return <Message text={error} onBack={() => navigate("/weather-tires-selection")} />
  }

  if (!race) {
    return <Message text="Carregando corrida..." />
  }

  const driverById = new Map(race.drivers.map((d) => [d.id, d]))
  const leaderLap = tick?.cars[0]?.lap ?? 0
  const feed = recent.slice(-FEED_SIZE).reverse()

  return (
    <main className="relative min-h-svh bg-background text-foreground lg:h-svh lg:overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_45%,rgba(220,38,38,0.12),transparent_40%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,rgba(0,0,0,0.25)_100%)]" />
      </div>
      <div className="absolute left-0 top-0 h-1 w-full bg-primary" />

      <div className="relative z-10 flex min-h-svh flex-col lg:h-svh">
        <header className="shrink-0 border-b border-border">
          <div className="container mx-auto flex items-center justify-between gap-6 px-6 py-6 lg:px-12 lg:py-7">
            <div className="flex items-center gap-5">
              <Button
                variant="outline"
                onClick={() => navigate("/weather-tires-selection")}
                aria-label="Voltar para clima e pneus"
                className="h-11 w-11 shrink-0 rounded-none border-border bg-transparent p-0 hover:bg-accent sm:w-auto sm:px-4"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <div className="mb-2 flex items-center gap-3">
                  <div className="h-1 w-10 bg-primary" />
                  <span className="text-xs font-bold uppercase tracking-[0.3em] text-primary">
                    F1 SIMULATOR
                  </span>
                </div>
                <h1 className="text-3xl font-black uppercase italic tracking-tighter sm:text-5xl">
                  Replay
                </h1>
              </div>
            </div>

            <div className="hidden text-right sm:block">
              <div className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
                Volta
              </div>
              <div className="text-4xl font-black italic tabular-nums">
                {leaderLap}
                <span className="text-xl text-muted-foreground">/{race.meta.totalLaps}</span>
              </div>
            </div>
          </div>
        </header>

        <div className="container mx-auto grid min-h-0 flex-1 grid-cols-1 gap-6 px-6 py-5 lg:grid-cols-[1fr_360px] lg:px-12 lg:py-7">
          <section className="flex min-h-[360px] flex-col border border-border bg-card/40 lg:min-h-0">
            <div className="relative min-h-0 flex-1 bg-background/50 p-6">
              <TrackMap race={race} />

              {banner && (
                <div className="absolute left-4 top-4 flex max-w-[70%] items-center gap-3 border-l-4 border-primary bg-background/90 px-4 py-3 backdrop-blur">
                  <AlertTriangle className="h-5 w-5 shrink-0 text-primary" />
                  <div className="min-w-0">
                    <div className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">
                      {banner.type.replace("_", " ")}
                    </div>
                    <div className="truncate text-sm font-bold">{banner.message}</div>
                  </div>
                </div>
              )}

              {tick && tick.trackStatus !== "green" && (
                <div
                  className={[
                    "absolute right-4 top-4 px-3 py-1.5 text-xs font-black uppercase tracking-wider",
                    tick.trackStatus === "red_flag" ? "bg-red-600 text-white" : "bg-yellow-400 text-black",
                  ].join(" ")}
                >
                  {TRACK_LABEL[tick.trackStatus] ?? tick.trackStatus}
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 border-t border-border p-4 lg:flex-row lg:items-center">
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => tickPlayer.toggle()}
                  aria-label={playing ? "Pausar" : "Reproduzir"}
                  className="h-10 w-10 rounded-none p-0"
                >
                  {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 fill-current" />}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    tickPlayer.seek(0)
                    tickPlayer.play()
                  }}
                  aria-label="Reiniciar"
                  className="h-10 w-10 rounded-none border-border bg-transparent p-0"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </div>

              <input
                type="range"
                min={0}
                max={tickPlayer.duration}
                step={1 / race.meta.tickHz}
                value={now}
                onChange={(e) => tickPlayer.seek(Number(e.target.value))}
                aria-label="Linha do tempo"
                className="w-full accent-red-600 lg:flex-1"
              />

              <div className="flex items-center justify-between gap-4 lg:justify-end">
                <span className="font-mono text-sm tabular-nums">
                  {formatTime(now)} / {formatTime(tickPlayer.duration)}
                </span>
                <div className="grid grid-cols-4 border border-border">
                  {SPEEDS.map((option) => (
                    <button
                      key={option}
                      type="button"
                      onClick={() => tickPlayer.setSpeed(option)}
                      className={[
                        "h-9 px-3 text-xs font-black uppercase transition-colors",
                        option === speed
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-foreground",
                      ].join(" ")}
                    >
                      {option}x
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <aside className="flex min-h-0 flex-col gap-6">
            <section className="flex min-h-[320px] flex-1 flex-col overflow-hidden border border-border bg-card/40">
              <h2 className="shrink-0 border-b border-border px-4 py-3 text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                Classificação ao vivo
              </h2>
              <ol className="min-h-0 flex-1 overflow-y-auto">
                {(tick?.cars ?? []).map((car) => {
                  const driver = driverById.get(car.id)
                  return (
                    <li
                      key={car.id}
                      className="grid grid-cols-[2rem_4px_1fr_auto] items-center gap-3 border-b border-border px-4 py-2.5"
                    >
                      <span className="text-sm font-black italic tabular-nums">
                        {String(car.position).padStart(2, "0")}
                      </span>
                      <span className="h-8 w-1" style={{ backgroundColor: driver?.teamColor }} />
                      <div className="min-w-0">
                        <div className="text-sm font-black uppercase">{driver?.code ?? car.id}</div>
                        <div className="truncate text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                          {car.tyre.toLowerCase()} {car.inPit && "· box"}
                        </div>
                      </div>
                      <span className="text-right text-xs font-bold tabular-nums">
                        {car.position === 1 ? (
                          <span className="text-primary">LÍDER</span>
                        ) : car.gapToLeaderS === null ? (
                          "—"
                        ) : (
                          `+${car.gapToLeaderS.toFixed(1)}`
                        )}
                      </span>
                    </li>
                  )
                })}
              </ol>
            </section>

            <section className="flex h-[260px] shrink-0 flex-col overflow-hidden border border-border bg-card/40">
              <h2 className="shrink-0 border-b border-border px-4 py-3 text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                Eventos
              </h2>
              {feed.length === 0 ? (
                <div className="flex flex-1 items-center justify-center text-xs uppercase tracking-wider text-muted-foreground">
                  Nenhum evento ainda
                </div>
              ) : (
                <ul className="min-h-0 flex-1 overflow-y-auto">
                  {feed.map((e, i) => (
                    <li key={`${e.t}-${i}`} className="border-b border-border px-4 py-2.5">
                      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground tabular-nums">
                        {formatTime(e.t)} · L{e.lap}
                      </div>
                      <div className="text-xs font-semibold">{e.message}</div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </aside>
        </div>
      </div>
    </main>
  )
}

function Message({ text, onBack }: { text: string; onBack?: () => void }) {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background p-6 text-center text-sm text-muted-foreground">
      <span>{text}</span>
      {onBack && (
        <Button variant="outline" onClick={onBack} className="rounded-none">
          Voltar
        </Button>
      )}
    </main>
  )
}