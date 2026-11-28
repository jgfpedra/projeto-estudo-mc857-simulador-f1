import { useEffect, useState } from "react"
import { AlertTriangle, ArrowLeft, Radio, X } from "lucide-react"
import { useLocation, useNavigate, useParams } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { DriverFollowCard } from "@/components/race/driver-follow-card"
import { EventFeed } from "@/components/race/event-feed"
import { RaceBanner } from "@/components/race/race-banner"
import { RaceView3D } from "@/components/race/view-3d/race-view-3d"
import { View3DToolbarSlot } from "@/components/race/view-3d/toolbar-slot"
import { ViewToggle } from "@/components/race/view-toggle"
import { TimingPanel } from "@/components/race/timing-panel"
import { UserPitPanel } from "@/components/race/user-pit-panel"
import { Track2D } from "@/components/race/track-2d"
import { AiFloatingPanel } from "@/components/race/ai/ai-floating-panel"
import { TRACK_STATUS_LABEL, currentLap, formatClock, weatherLabel } from "@/helpers/race-live"
import type { RaceStartResponse } from "@/services/api"
import { speechSynthesis } from "@/services/speech-synthesis"
import { useLiveRaceStore, type LiveStatus } from "@/stores/live-race-store"

const STATUS_BADGE: Record<LiveStatus, { label: string; className: string }> = {
  idle: { label: "Aguardando", className: "bg-secondary text-muted-foreground" },
  loading: { label: "Carregando", className: "bg-secondary text-muted-foreground" },
  live: { label: "Ao vivo", className: "bg-primary text-primary-foreground" },
  reconnecting: { label: "Reconectando", className: "bg-amber-400 text-black" },
  syncing: { label: "Reconectando", className: "bg-amber-400 text-black" },
  finished: { label: "Finalizada", className: "bg-zinc-100 text-black" },
  error: { label: "Erro", className: "bg-destructive text-destructive-foreground" },
}

export function RaceSimulation() {
  const { raceId } = useParams<{ raceId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  // Avisos do POST. Só existem quando a página foi aberta logo após a criação da corrida.
  const warnings = (location.state as RaceStartResponse | null)?.warnings ?? []

  const status = useLiveRaceStore((s) => s.status)
  const justResumed = useLiveRaceStore((s) => s.justResumed)
  const error = useLiveRaceStore((s) => s.error)
  const race = useLiveRaceStore((s) => s.race)
  const frame = useLiveRaceStore((s) => s.frame)
  const prevFrame = useLiveRaceStore((s) => s.prevFrame)
  const trackStatus = useLiveRaceStore((s) => s.trackStatus)
  const feed = useLiveRaceStore((s) => s.feed)
  const classification = useLiveRaceStore((s) => s.classification)
  const selectedDriverId = useLiveRaceStore((s) => s.selectedDriverId)
  const followedDriverId = useLiveRaceStore((s) => s.followedDriverId)
  const viewMode = useLiveRaceStore((s) => s.viewMode)
  const aiSuggestions = useLiveRaceStore((s) => s.aiSuggestions)
  const aiCommands = useLiveRaceStore((s) => s.aiCommands)
  const aiEngineerStatus = useLiveRaceStore((s) => s.aiEngineerStatus)
  const aiEngineerStats = useLiveRaceStore((s) => s.aiEngineerStats)
  const aiEngineerError = useLiveRaceStore((s) => s.aiEngineerError)
  const followDriver = useLiveRaceStore((s) => s.followDriver)
  const unfollowDriver = useLiveRaceStore((s) => s.unfollowDriver)
  const load = useLiveRaceStore((s) => s.load)
  const disconnect = useLiveRaceStore((s) => s.disconnect)
  const selectDriver = useLiveRaceStore((s) => s.selectDriver)
  const setViewMode = useLiveRaceStore((s) => s.setViewMode)
  const pitBusy = useLiveRaceStore((s) => s.pitBusy)
  const pitError = useLiveRaceStore((s) => s.pitError)
  const requestPit = useLiveRaceStore((s) => s.requestPit)
  const cancelPit = useLiveRaceStore((s) => s.cancelPit)
  // Onde o 3D põe o seletor de cenário, ao lado da chave 2D/3D.
  const [toolbarSlot, setToolbarSlot] = useState<HTMLDivElement | null>(null)

  const handleFollowDriver = (driverId: string) => {
    // O clique no olho também libera o áudio no Zen/Firefox e fala a mensagem já exibida.
    speechSynthesis.unlock()
    followDriver(driverId)
    const latest = [...aiSuggestions].reverse().find((suggestion) => suggestion.driverId === driverId)
    if (latest) speechSynthesis.speak(latest.message, latest.urgency)
  }

  useEffect(() => {
    if (raceId) void load(raceId)
    return () => disconnect()
  }, [raceId, load, disconnect])

  if (status === "error") {
    return (
      <main className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background p-6 text-center text-sm text-muted-foreground">
        <span>{error}</span>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => {
              if (raceId) void load(raceId)
            }}
            className="rounded-none"
          >
            Tentar novamente
          </Button>
          <Button variant="outline" onClick={() => navigate("/")} className="rounded-none">
            Menu principal
          </Button>
        </div>
      </main>
    )
  }

  if (!race) {
    return (
      <main className="flex min-h-svh items-center justify-center bg-background p-6 text-sm text-muted-foreground">
        Carregando corrida...
      </main>
    )
  }

  const badge = justResumed
    ? { label: "Corrida retomada", className: "bg-emerald-500 text-black" }
    : STATUS_BADGE[status]
  const mapReady = race.track.waypoints.length >= 2
  const aiPanel = (
    <AiFloatingPanel
      engineerStatus={aiEngineerStatus}
      engineerStats={aiEngineerStats}
      engineerError={aiEngineerError}
      raceId={race.raceId}
      raceName={race.track.name}
      suggestions={aiSuggestions}
      commands={aiCommands}
      position="viewer-right"
      initiallyCollapsed={false}
    />
  )

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
                onClick={() => navigate("/")}
                aria-label="Voltar ao menu principal"
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
                  <span
                    className={`flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider ${badge.className}`}
                  >
                    {status === "live" && <Radio className="h-3 w-3 animate-pulse" />}
                    {badge.label}
                  </span>
                </div>
                <h1 className="text-3xl font-black uppercase italic tracking-tighter sm:text-5xl">
                  Corrida
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">{race.track.name}</p>
              </div>
            </div>

            <div className="hidden text-right sm:block">
              <div className="text-[10px] font-bold uppercase tracking-[0.25em] text-muted-foreground">
                Volta
              </div>
              <div className="text-4xl font-black italic tabular-nums">
                {currentLap(frame?.lap ?? 0, race.numLaps)}
                <span className="text-xl text-muted-foreground">/{race.numLaps}</span>
              </div>
            </div>
          </div>
        </header>

        {warnings.length > 0 && (
          <div className="shrink-0 border-b border-border bg-primary/10 px-6 py-3 text-xs lg:px-12">
            {warnings.map((w) => (
              <p key={w} className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                <span>{w}</span>
              </p>
            ))}
          </div>
        )}

        <div className="container mx-auto grid min-h-0 flex-1 grid-cols-1 gap-6 px-6 py-5 lg:grid-cols-[1fr_360px] lg:px-12 lg:py-7">
          <section className="flex min-h-[420px] flex-col border border-border bg-card/40 lg:min-h-0">
            <div className="relative min-h-0 flex-1 bg-background/50">
              {/* Uma linha: chave 2D/3D, controles do 3D e a faixa de eventos no espaço que sobra. */}
              <div className="pointer-events-none absolute left-4 right-4 top-4 z-20 flex min-w-0 items-start gap-3">
                <div className="pointer-events-auto flex shrink-0 items-start gap-2">
                  <ViewToggle value={viewMode} onChange={setViewMode} />
                  <div ref={setToolbarSlot} className="flex empty:hidden" />
                </div>
                <RaceBanner items={feed} simTs={frame?.simTs ?? 0} />
              </div>

              <div className="absolute inset-0 p-6 pt-16">
                {viewMode === "2d" ? (
                  mapReady ? (
                    <Track2D race={race} />
                  ) : (
                    <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                      Traçado indisponível: o backend não enviou os waypoints da pista.
                    </div>
                  )
                ) : (
                  <View3DToolbarSlot.Provider value={toolbarSlot}>
                    <RaceView3D
                      race={race}
                      frame={frame}
                      selectedDriverId={selectedDriverId}
                      onSelectDriver={selectDriver}
                      aiSuggestions={aiSuggestions}
                      aiCommands={aiCommands}
                    />
                  </View3DToolbarSlot.Provider>
                )}
              </div>

              {/* Estatísticas à esquerda e engenheiro ao centro-direita, dentro do visualizador. */}
              {followedDriverId && (
                <>
                  <DriverFollowCard
                    race={race}
                    frame={frame}
                    prevFrame={prevFrame}
                    feed={feed}
                    classification={classification}
                    driverId={followedDriverId}
                  />
                  {aiPanel}
                </>
              )}

              {/* Botão "Visão geral" apenas quando há piloto selecionado visualmente mas não acompanhado */}
              {selectedDriverId && !followedDriverId && (
                <div className="absolute bottom-4 left-4 z-20">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => selectDriver(null)}
                    className="rounded-none border-border bg-background/90 uppercase"
                  >
                    <X className="mr-2 h-4 w-4" />
                    Visão geral
                  </Button>
                </div>
              )}

              {!frame && status !== "finished" && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
                  Aguardando o simulador...
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 border-t border-border p-4">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {status === "finished"
                  ? "Corrida concluída"
                  : status === "reconnecting" || status === "syncing"
                    ? "Reconectando ao simulador..."
                    : justResumed
                      ? "Corrida retomada"
                      : trackStatus !== "GREEN"
                        ? TRACK_STATUS_LABEL[trackStatus]
                        : "Simulação em andamento"}
              </span>
              <div className="flex items-center gap-4">
                {frame?.weather && (
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    {weatherLabel(frame.weather.kind)} · pista {frame.weather.trackTemp.toFixed(0)}°C
                  </span>
                )}
                <span className="font-mono text-sm tabular-nums">T+ {formatClock(frame?.simTs ?? 0)}</span>
              </div>
            </div>
          </section>

          <aside className="flex min-h-0 flex-col gap-4">
            <section className="flex min-h-0 flex-1 flex-col overflow-hidden border border-border bg-card/40">
              <h2 className="shrink-0 border-b border-border px-4 py-3 text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                {classification ? "Resultado final" : "Classificação ao vivo"}
              </h2>
              <TimingPanel
                race={race}
                frame={frame}
                prevFrame={prevFrame}
                classification={classification}
                selectedDriverId={selectedDriverId}
                followedDriverId={followedDriverId}
                onSelect={selectDriver}
                onFollow={handleFollowDriver}
                onUnfollow={unfollowDriver}
                controlledDriverId={race.userDriverId}
              />
            </section>

            {race.userDriverId && (
              <UserPitPanel
                race={race}
                frame={frame}
                active={status === "live"}
                busy={pitBusy}
                error={pitError}
                onRequest={(tyre) => void requestPit(race.userDriverId ?? "", tyre)}
                onCancel={() => void cancelPit(race.userDriverId ?? "")}
              />
            )}

            <section className="flex h-44 shrink-0 flex-col overflow-hidden border border-border bg-card/40">
              <h2 className="shrink-0 border-b border-border px-4 py-3 text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                Eventos
              </h2>
              <EventFeed items={feed} />
            </section>
          </aside>
        </div>
      </div>
    </main>
  )
}
