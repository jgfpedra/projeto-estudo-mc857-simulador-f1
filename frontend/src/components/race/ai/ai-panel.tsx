"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import type { AiSuggestion, AiCommand } from "@/types/race"

interface Props {
  suggestions: AiSuggestion[]
  commands: Map<string, AiCommand>
  followedDriverId: string | null
  /** Status do ciclo de vida do engenheiro: "idle" | "started" | "monitoring" | "stopped" | "error" */
  engineerStatus?: "idle" | "started" | "monitoring" | "stopped" | "error"
  /** Estatísticas do engenheiro */
  engineerStats?: Record<string, unknown> | null
  /** Erro do engenheiro, se houver */
  engineerError?: string | null
}

const URGENCY_STYLE: Record<"baixa" | "media" | "alta", { bg: string; border: string; text: string }> = {
  alta: { bg: "bg-red-500/20", border: "border-red-500", text: "text-red-400" },
  media: { bg: "bg-amber-500/20", border: "border-amber-500", text: "text-amber-400" },
  baixa: { bg: "bg-zinc-500/20", border: "border-zinc-500", text: "text-zinc-400" },
}

const STATUS_STYLE: Record<"idle" | "started" | "monitoring" | "stopped" | "error", { dot: string; label: string; color: string }> = {
  idle: { dot: "bg-zinc-500", label: "parado", color: "text-zinc-500" },
  started: { dot: "bg-blue-500 animate-pulse", label: "iniciando", color: "text-blue-400" },
  monitoring: { dot: "bg-green-500 animate-pulse", label: "analisando", color: "text-green-400" },
  stopped: { dot: "bg-zinc-500", label: "finalizado", color: "text-zinc-500" },
  error: { dot: "bg-red-500 animate-pulse", label: "erro", color: "text-red-400" },
}

function statValue(stats: Record<string, unknown> | null, key: string): string {
  if (!stats) return ""
  const v = stats[key]
  return v === undefined || v === null ? "" : String(v)
}

export function AiPanel({ suggestions, commands, followedDriverId, engineerStatus = "idle", engineerStats, engineerError }: Props) {
  const activeCommand = useMemo(() => {
    if (!followedDriverId) return null
    return commands.get(followedDriverId) ?? null
  }, [commands, followedDriverId])

  const recentSuggestions = useMemo(() => suggestions.slice(-5).reverse(), [suggestions])
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const lastSpokenIndex = useRef(suggestions.length - 1)

  // TTS: speak new suggestions
  useEffect(() => {
    if (!ttsEnabled) return
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return

    const lastIndex = suggestions.length - 1
    const prevIndex = lastSpokenIndex.current

    if (lastIndex > prevIndex) {
      for (let i = prevIndex + 1; i <= lastIndex; i++) {
        const msg = suggestions[i]
        if (msg?.message) {
          const urgency = msg.urgency as "baixa" | "media" | "alta" || "media"
          setTimeout(() => {
            if (typeof window !== "undefined" && "speechSynthesis" in window) {
              const utterance = new SpeechSynthesisUtterance(msg.message)
              utterance.lang = "pt-BR"
              utterance.rate = urgency === "alta" ? 1.1 : urgency === "media" ? 1.0 : 0.9
              utterance.pitch = urgency === "alta" ? 1.05 : urgency === "media" ? 1.0 : 0.98
              utterance.volume = urgency === "alta" ? 1.0 : urgency === "media" ? 0.95 : 0.9
              const voices = window.speechSynthesis.getVoices()
              const ptVoice = voices.find(v => v.lang === "pt-BR") || voices.find(v => v.lang.startsWith("pt"))
              if (ptVoice) utterance.voice = ptVoice
              window.speechSynthesis.speak(utterance)
            }
          }, (i - lastSpokenIndex.current) * 500)
        }
      }
      lastSpokenIndex.current = lastIndex
    }
  }, [suggestions])

  const statusStyle = STATUS_STYLE[engineerStatus]
  const hasContent = suggestions.length > 0 || activeCommand || engineerStatus !== "idle"

  if (!hasContent) {
    return (
      <div className="pointer-events-none absolute top-4 left-1/2 -translate-x-1/2 z-30 w-[380px] max-h-[280px] overflow-hidden rounded-lg border border-border/50 bg-background/90 backdrop-blur-sm p-3 text-xs font-mono text-muted-foreground">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-foreground">🤖 engenheiro</span>
          <span className="text-muted-foreground">ao vivo</span>
          <span className="flex-1" />
          <span className={`flex items-center gap-1 ${statusStyle.color}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusStyle.dot}`} />
            {statusStyle.label}
          </span>
        </div>
        <p className="text-center text-muted-foreground">aguardando primeira sugestão da IA…</p>
      </div>
    )
  }

  return (
    <div className="pointer-events-none absolute top-4 left-1/2 -translate-x-1/2 z-30 w-[380px] max-h-[280px] overflow-hidden rounded-lg border border-border/50 bg-background/90 backdrop-blur-sm p-3 text-xs font-mono">
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-foreground">🤖 engenheiro</span>
        <span className="text-muted-foreground">ao vivo</span>
        <span className="flex-1" />
        <span className={`flex items-center gap-1 ${activeCommand?.command && activeCommand.command !== "neutral" ? "text-amber-400" : statusStyle.color}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${statusStyle.dot}`} />
          {activeCommand?.command && activeCommand.command !== "neutral" ? "COMANDO ATIVO" : statusStyle.label}
        </span>
        {/* TTS Toggle */}
        <button
          onClick={() => setTtsEnabled(!ttsEnabled)}
          className={`p-1 rounded transition-colors ${ttsEnabled ? "text-green-400 hover:text-green-300" : "text-muted-foreground hover:text-red-400"}`}
          aria-label={ttsEnabled ? "Desativar síntese de voz" : "Ativar síntese de voz"}
          title={ttsEnabled ? "TTS Ativo (clique para desativar)" : "TTS Desativado (clique para ativar)"}
        >
          {ttsEnabled ? <span className="text-[10px] font-bold">🔊</span> : <span className="text-[10px] font-bold">🔇</span>}
        </button>
      </div>

      {engineerError && (
        <div className="mb-2 p-2 rounded bg-red-500/10 border border-red-500/30 text-red-300 text-[10px]">
          ⚠️ {engineerError}
        </div>
      )}

      {engineerStats && (
        <div className="mb-2 text-[10px] text-muted-foreground">
          <span>intervalo: {statValue(engineerStats, "decisionIntervalS")}s</span>
          {statValue(engineerStats, "numDrivers") && <span className="ml-2">· pilotos: {statValue(engineerStats, "numDrivers")}</span>}
          {statValue(engineerStats, "cycles") && <span className="ml-2">· ciclos: {statValue(engineerStats, "cycles")}</span>}
          {statValue(engineerStats, "recommendations_generated") && <span className="ml-2">· recomendações: {statValue(engineerStats, "recommendations_generated")}</span>}
          {statValue(engineerStats, "commands_executed") && <span className="ml-2">· executados: {statValue(engineerStats, "commands_executed")}</span>}
          {statValue(engineerStats, "user_driver_analyzed") && <span className="ml-2">· usuário analisado: {statValue(engineerStats, "user_driver_analyzed")}</span>}
        </div>
      )}

      {followedDriverId && (
        <div className="mb-2 text-muted-foreground">
          seguindo <span className="text-foreground">{followedDriverId}</span>
          {activeCommand && activeCommand.command !== "neutral" && (
            <span className="ml-2 text-amber-400">
              · comando {activeCommand.command.toUpperCase()}
              {activeCommand.reason && ` — ${activeCommand.reason}`}
            </span>
          )}
        </div>
      )}

      <div className="flex flex-col gap-1.5 max-h-[200px] overflow-y-auto">
        {recentSuggestions.map((suggestion, index) => {
          const style = URGENCY_STYLE[suggestion.urgency]
          const isOwn = suggestion.driverId === followedDriverId
          return (
            <div
              key={`${suggestion.simTs}-${index}`}
              className={`flex flex-col gap-1 p-2 rounded border-l-2 ${
                style.bg + " " + style.border + " " + (isOwn ? "ring-1 ring-inset ring-green-500/30" : "")
              }`}
            >
              <div className="flex items-center gap-2 text-[10px]">
                <span className={style.text}>{suggestion.simTs.toFixed(0)}s</span>
                <span className={`text-[9px] px-1 rounded ${style.bg} ${style.text}`}>{suggestion.urgency.toUpperCase()}</span>
                {suggestion.command && suggestion.command.type !== "neutral" && (
                  <span className="text-[9px] px-1 rounded bg-primary/20 border border-primary text-primary">
                    {suggestion.command.type}
                  </span>
                )}
              </div>
              <div className="text-foreground">{suggestion.message}</div>
            </div>
          )
        })}
      </div>

      {suggestions.length === 0 && activeCommand === null && engineerStatus === "monitoring" && (
        <p className="text-center text-muted-foreground py-4">IA analisando… sem recomendações no momento</p>
      )}
    </div>
  )
}