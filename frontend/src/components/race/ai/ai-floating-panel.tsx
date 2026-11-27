"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { ChevronDown, ChevronUp, X, AlertCircle, CheckCircle, Loader2, Zap, Target, ThumbsDown, ThumbsUp, MessageSquare } from "lucide-react"
import { useLiveRaceStore } from "@/stores/live-race-store"
import type { AiSuggestion, AiCommand, DriverRadio } from "@/types/race"
import { speechSynthesis } from "@/services/speech-synthesis"
import { SpeechControls } from "./speech-controls"

interface AiFloatingPanelProps {
  // Estado da IA
  engineerStatus: "idle" | "started" | "monitoring" | "stopped" | "error"
  engineerStats?: Record<string, unknown> | null
  engineerError?: string | null
  
  // Dados da corrida
  raceId: string
  raceName: string
  
  // Dados de recomendação
  suggestions: AiSuggestion[]
  commands: Map<string, AiCommand>
  
  // Callbacks
  onClose?: () => void
  onToggleCollapse?: () => void
  
  // Config
  position?: "top-right" | "top-left" | "bottom-right" | "bottom-left" | "inline" | "viewer-right"
  initiallyCollapsed?: boolean
}

interface StatusConfig {
  label: string
  iconType: "dot" | "loader" | "zap" | "check" | "alert"
  color: string
  bg: string
  border: string
  pulse: boolean
}

const STATUS_CONFIG: Record<"idle" | "started" | "monitoring" | "stopped" | "error", StatusConfig> = {
  idle: {
    label: "PARADO",
    iconType: "dot",
    color: "text-zinc-500",
    bg: "bg-zinc-500/10",
    border: "border-zinc-500/30",
    pulse: false,
  },
  started: {
    label: "INICIANDO",
    iconType: "loader",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    pulse: true,
  },
  monitoring: {
    label: "MONITORANDO",
    iconType: "zap",
    color: "text-green-50",
    bg: "bg-green-700",
    border: "border-green-400",
    pulse: true,
  },
  stopped: {
    label: "ENCERRADO",
    iconType: "check",
    color: "text-zinc-500",
    bg: "bg-zinc-500/10",
    border: "border-zinc-500/30",
    pulse: false,
  },
  error: {
    label: "ERRO",
    iconType: "alert",
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    pulse: true,
  },
}

function renderStatusIcon(type: StatusConfig["iconType"]): React.ReactNode {
  switch (type) {
    case "dot":
      return <span className="w-2 h-2 rounded-full bg-current" />
    case "loader":
      return <Loader2 className="w-3 h-3 animate-spin" />
    case "zap":
      return <Zap className="w-3 h-3 animate-pulse" />
    case "check":
      return <CheckCircle className="w-3 h-3" />
    case "alert":
      return <AlertCircle className="w-3 h-3 animate-pulse" />
  }
}

const URGENCY_STYLE: Record<"baixa" | "media" | "alta", { bg: string; border: string; text: string; icon: string }> = {
  alta: { bg: "bg-red-500/15", border: "border-red-500/40", text: "text-red-300", icon: "🔴" },
  media: { bg: "bg-amber-500/15", border: "border-amber-500/40", text: "text-amber-300", icon: "🟡" },
  baixa: { bg: "bg-zinc-500/15", border: "border-zinc-500/40", text: "text-zinc-300", icon: "🟢" },
}

const POSITION_CLASSES: Record<string, string> = {
  "top-right": "top-4 right-4",
  "top-left": "top-4 left-4",
  "bottom-right": "bottom-4 right-4",
  "bottom-left": "bottom-4 left-4",
}

export function AiFloatingPanel({
  engineerStatus,
  engineerStats,
  engineerError,
  raceId,
  raceName,
  suggestions,
  commands,
  onClose,
  onToggleCollapse,
  position = "top-right",
  initiallyCollapsed = false,
}: AiFloatingPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(initiallyCollapsed)
  const [showAllSuggestions, setShowAllSuggestions] = useState(false)
  const [ollamaEnabled, setOllamaEnabled] = useState(false)
  const [ollamaLoading, setOllamaLoading] = useState(false)
  const lastSpokenIndex = useRef(suggestions.length - 1)

  // Get followed driver from store
  const followedDriverId = useLiveRaceStore((s) => s.followedDriverId)
  const race = useLiveRaceStore((s) => s.race)
  const driverRadios = useLiveRaceStore((s) => s.driverRadios)

  // Status config
  const statusCfg = STATUS_CONFIG[engineerStatus]

  // Carrega estado inicial do Ollama
  useEffect(() => {
    fetch('/api/settings/ollama')
      .then(r => r.json())
      .then(data => setOllamaEnabled(data.enabled))
      .catch(() => {})
  }, [])

  // Toggle Ollama via API
  const toggleOllama = async () => {
    setOllamaLoading(true)
    try {
      const newVal = !ollamaEnabled
      const res = await fetch('/api/settings/ollama', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: newVal })
      })
      const data = await res.json()
      setOllamaEnabled(data.enabled)
    } catch (e) {
      console.error('Falha ao toggle Ollama:', e)
    } finally {
      setOllamaLoading(false)
    }
  }

  // Resolve followed driver name from race data
  const followedDriverName = useMemo(() => {
    if (!followedDriverId || !race) return "—"
    return race.drivers.find(d => d.driverId === followedDriverId)?.name ?? followedDriverId
  }, [followedDriverId, race])

  // Comando ativo para o piloto acompanhado
  const activeCommand = useMemo(() => {
    if (!followedDriverId) return null
    return commands.get(followedDriverId) ?? null
  }, [commands, followedDriverId])

  // Sugestões do piloto acompanhado (destaque)
  const followedSuggestions = useMemo(() => 
    suggestions.filter(s => s.driverId === followedDriverId).slice(-10).reverse(),
    [suggestions, followedDriverId]
  )

  // Outras sugestões (colapsadas)
  const otherSuggestions = useMemo(() =>
    suggestions.filter(s => s.driverId !== followedDriverId).slice(-5).reverse(),
    [suggestions, followedDriverId]
  )

  // Rádios do piloto acompanhado (respostas à IA)
  const followedRadios = useMemo(() =>
    driverRadios.filter(r => r.driverId === followedDriverId).slice(-5).reverse(),
    [driverRadios, followedDriverId]
  )

  // Stats formatadas
  const statsDisplay = useMemo(() => {
    if (!engineerStats) return []
    const entries = Object.entries(engineerStats)
    return entries
      .filter(([k]) => !["last_cycle_sim_ts"].includes(k))
      .map(([k, v]) => ({
        key: k.replace(/_/g, " "),
        value: typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(1)) : String(v),
      }))
  }, [engineerStats])

  // Short race ID para display
  const shortRaceId = useMemo(() => raceId.replace("race_", "").slice(0, 8), [raceId])

  // A fila global evita sobreposição e descarta duplicatas entre os painéis.
  useEffect(() => {
    const lastIndex = suggestions.length - 1
    const prevIndex = lastSpokenIndex.current

    if (lastIndex > prevIndex) {
      for (let i = prevIndex + 1; i <= lastIndex; i++) {
        const msg = suggestions[i]
        if (msg?.message) speechSynthesis.speak(msg.message, msg.urgency as "baixa" | "media" | "alta")
      }
      lastSpokenIndex.current = lastIndex
    }
  }, [suggestions])

  const handleToggleCollapse = () => {
    setIsCollapsed(!isCollapsed)
    onToggleCollapse?.()
  }

  const handleClose = () => {
    onClose?.()
  }

  // No acompanhamento, o painel fica ao centro-direita sem exceder o visualizador.
  const isInline = position === "inline"
  const isViewerRight = position === "viewer-right"
  const positionClass = isInline || isViewerRight ? "" : POSITION_CLASSES[position]

  return (
    <div
      className={`
        pointer-events-auto transition-all duration-300 ease-out
        ${isViewerRight
          ? "absolute right-6 top-1/2 z-10 flex max-h-[min(30rem,calc(100%_-_8rem))] w-80 max-w-[calc(100%_-_3rem)] -translate-y-1/2 flex-col overflow-hidden"
          : isInline
            ? "relative mt-3 w-full min-w-0 shrink-0"
            : `fixed ${positionClass} z-50 ${isCollapsed ? "w-72" : "w-80"}`}
      `}
      role="region"
      aria-label="Painel do Engenheiro de IA"
    >
      {/* Header em duas linhas: status/controles e, abaixo, os dados da corrida. */}
      <div className={`
        shrink-0 rounded-t-lg border-b p-3
        ${statusCfg.border} ${statusCfg.bg}
      `}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className={`flex shrink-0 items-center gap-1.5 ${statusCfg.color} ${statusCfg.pulse ? "animate-pulse" : ""}`}>
            {renderStatusIcon(statusCfg.iconType)}
            <span className="text-xs font-bold uppercase tracking-wider">{statusCfg.label}</span>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={toggleOllama}
              disabled={ollamaLoading}
              className={`rounded px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider transition-all ${
                ollamaEnabled
                  ? 'bg-green-500/20 text-green-400 border border-green-500/40 hover:bg-green-500/30'
                  : 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/30 hover:bg-zinc-500/20'
              } ${ollamaLoading ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
              title={ollamaEnabled ? 'Ollama LLM ativo (clique para desativar)' : 'Usando fallback tático (clique para ativar Ollama)'}
            >
              {ollamaLoading ? '...' : ollamaEnabled ? 'LLM ON' : 'LLM OFF'}
            </button>
            <SpeechControls />
            <button
              onClick={handleToggleCollapse}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label={isCollapsed ? "Expandir" : "Colapsar"}
              aria-expanded={!isCollapsed}
            >
              {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
            </button>
            {onClose && (
              <button
                onClick={handleClose}
                className="rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                aria-label="Fechar painel"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-2 min-w-0 border-t border-white/10 pt-2">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5 text-xs">
            <span className="min-w-0 break-words text-muted-foreground">{raceName}</span>
            <span className="shrink-0 rounded border border-primary/20 bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] text-primary">
              #{shortRaceId}
            </span>
          </div>
          {followedDriverId && (
            <div className="mt-1 flex min-w-0 items-center gap-1.5 text-[11px]">
              <Target className="h-3 w-3 shrink-0 text-green-300" />
              <span className="shrink-0 text-muted-foreground">Engenheiro:</span>
              <span className="min-w-0 truncate font-medium text-foreground">{followedDriverName}</span>
            </div>
          )}
        </div>
      </div>

      {/* Content - colapsável */}
      {!isCollapsed && (
        <div className={`flex min-h-0 flex-col overflow-hidden rounded-b-lg border border-border/50 bg-background/95 backdrop-blur-sm ${isViewerRight ? "flex-1" : "max-h-[500px]"}`}>
          {/* Error Banner */}
          {engineerError && (
            <div className="p-3 border-b border-red-500/20 bg-red-500/5">
              <div className="flex items-center gap-2 text-red-300 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{engineerError}</span>
              </div>
            </div>
          )}

          {/* Stats Row */}
          {statsDisplay.length > 0 && (
            <div className="px-3 py-2 border-b border-border/30 bg-muted/30">
              <div className="flex flex-wrap gap-3 text-[10px]">
                {statsDisplay.map(({ key, value }) => (
                  <span key={key} className="flex items-center gap-1 text-muted-foreground">
                    <span className="text-foreground">{key}:</span>
                    <span className="font-mono">{value}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Active Command */}
          {activeCommand && activeCommand.command !== "neutral" && (
            <div className="px-3 py-2 border-b border-border/30 bg-amber-500/5">
              <div className="flex items-center gap-2 text-xs">
                <span className="px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 font-bold text-[9px]">
                  COMANDO ATIVO
                </span>
                <span className="text-foreground font-mono">{activeCommand.command.toUpperCase()}</span>
                {activeCommand.value !== 0 && (
                  <span className="text-muted-foreground">×{activeCommand.value.toFixed(2)}</span>
                )}
                <span className="text-muted-foreground">—</span>
                <span className="text-foreground truncate">{activeCommand.reason}</span>
              </div>
            </div>
          )}

          {/* Suggestions List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {/* Followed Driver Suggestions (Priority) */}
            {followedSuggestions.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  <Target className="w-3 h-3 text-green-400" />
                  {followedDriverName} (prioritário)
                </div>
                <div className="space-y-1.5">
                  {followedSuggestions.map((suggestion, index) => (
                    <SuggestionCard key={`${suggestion.simTs}-${index}`} suggestion={suggestion} isOwn={true} />
                  ))}
                </div>
              </div>
            )}

            {/* Driver Radio Responses (when AI talks nonsense) */}
            {followedRadios.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-orange-400">
                  <MessageSquare className="w-3 h-3 text-orange-400" />
                  {followedDriverName} (rádio)
                </div>
                <div className="space-y-1.5">
                  {followedRadios.map((radio, index) => (
                    <DriverRadioCard key={`${radio.simTs}-${index}`} radio={radio} />
                  ))}
                </div>
              </div>
            )}

            {/* Other Drivers Suggestions (Collapsible) */}
            {otherSuggestions.length > 0 && (
              <div>
                <button
                  onClick={() => setShowAllSuggestions(!showAllSuggestions)}
                  className="w-full flex items-center justify-between px-1 py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground"
                >
                  <span>Outros pilotos ({otherSuggestions.length})</span>
                  <span className="text-xs">{showAllSuggestions ? "▲" : "▼"}</span>
                </button>
                {showAllSuggestions && (
                  <div className="space-y-1.5 mt-1 ml-2 border-l border-border/30 pl-2">
                    {otherSuggestions.map((suggestion, index) => (
                      <SuggestionCard key={`${suggestion.simTs}-${index}`} suggestion={suggestion} isOwn={false} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Empty State */}
            {suggestions.length === 0 && !engineerError && (
              <div className="flex flex-col items-center justify-center py-8 text-center text-xs text-muted-foreground">
                {engineerStatus === "monitoring" && (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin text-primary mb-2" />
                    <span>IA analisando a corrida...</span>
                  </>
                )}
                {engineerStatus === "started" && (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin text-blue-400 mb-2" />
                    <span>Inicializando engenheiro...</span>
                  </>
                )}
                {engineerStatus === "idle" && <span>Aguardando início da corrida</span>}
                {engineerStatus === "stopped" && <span>Corrida finalizada</span>}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Sub-componente para cada sugestão
function SuggestionCard({ suggestion, isOwn }: { suggestion: AiSuggestion; isOwn: boolean }) {
  const style = URGENCY_STYLE[suggestion.urgency]
  const hasCommand = suggestion.command && suggestion.command.type !== "neutral"
  const [feedback, setFeedback] = useState<"good" | "bad" | null>(null)

  const sendFeedback = async (rating: "good" | "bad") => {
    setFeedback(rating)
    try {
      await fetch(`/api/races/${suggestion.raceId}/ai-feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          suggestionId: suggestion.id ?? `${suggestion.driverId}-${suggestion.simTs}`,
          driverId: suggestion.driverId,
          simTs: suggestion.simTs,
          message: suggestion.message,
          urgency: suggestion.urgency,
          command: suggestion.command,
          rating,
          timestamp: Date.now(),
        }),
      })
    } catch (e) {
      console.warn("Falha ao enviar feedback:", e)
      setFeedback(null) // Permite tentar novamente
    }
  }

  return (
    <div
      className={`
        flex flex-col gap-1 p-2 rounded border-l-2
        ${style.bg} ${style.border}
        ${isOwn ? "ring-1 ring-inset ring-green-500/30 bg-green-500/5" : ""}
      `}
    >
      <div className="flex items-center gap-2 text-[10px]">
        <span className="font-mono text-muted-foreground">{suggestion.simTs.toFixed(0)}s</span>
        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${style.bg} ${style.text}`}>
          {style.icon} {suggestion.urgency.toUpperCase()}
        </span>
        {hasCommand && (
          <span className="px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20 text-primary text-[9px] font-mono">
            {suggestion.command!.type.toUpperCase()}
          </span>
        )}
        {suggestion.command?.confianca !== undefined && (
          <span className="px-1.5 py-0.5 rounded bg-zinc-500/10 border border-zinc-500/20 text-zinc-400 text-[9px]">
            Conf: {(suggestion.command.confianca * 100).toFixed(0)}%
          </span>
        )}
        {/* Feedback buttons */}
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => sendFeedback("good")}
            disabled={feedback !== null}
            className={`p-1 rounded transition-colors ${
              feedback === "good"
                ? "bg-green-500/20 text-green-400"
                : "text-zinc-500 hover:text-green-400 hover:bg-green-500/10"
            }`}
            title="Essa mensagem fez sentido"
            aria-label="Feedback positivo"
          >
            <ThumbsUp className="w-3 h-3" />
          </button>
          <button
            onClick={() => sendFeedback("bad")}
            disabled={feedback !== null}
            className={`p-1 rounded transition-colors ${
              feedback === "bad"
                ? "bg-red-500/20 text-red-400"
                : "text-zinc-500 hover:text-red-400 hover:bg-red-500/10"
            }`}
            title="Essa mensagem não fez sentido / sem nexo"
            aria-label="Feedback negativo"
          >
            <ThumbsDown className="w-3 h-3" />
          </button>
          {feedback && (
            <span className="text-[9px] text-green-400 font-medium">Obrigado!</span>
          )}
        </div>
      </div>
      <div className="text-foreground text-xs leading-relaxed">{suggestion.message}</div>
    </div>
  )
}

// Sub-componente para resposta do piloto (rádio)
function DriverRadioCard({ radio }: { radio: DriverRadio }) {
  const triggerLabels: Record<string, string> = {
    "repetitive_context": "Repetitivo",
    "defend_without_threat": "Defesa sem ameaça",
    "overtake_too_far": "Ultrapassagem longe",
    "push_on_critical_resources": "Push crítico",
    "conserve_unnecessary": "Economia desnecessária",
    "stale_message_context_changed": "Contexto velho",
    "generic_low_confidence": "Genérico",
    "low_confidence": "Baixa confiança",
  }

  return (
    <div className="flex flex-col gap-1 p-2 rounded border-l-2 bg-orange-500/10 border-orange-500/40 bg-orange-500/5">
      <div className="flex items-center gap-2 text-[10px]">
        <span className="font-mono text-muted-foreground">{radio.simTs.toFixed(0)}s</span>
        <span className="px-1.5 py-0.5 rounded bg-orange-500/20 border border-orange-500/30 text-orange-300 text-[9px] font-bold">
          📻 RÁDIO
        </span>
        <span className="px-1.5 py-0.5 rounded bg-orange-500/10 border border-orange-500/20 text-orange-400 text-[9px]">
          {triggerLabels[radio.trigger] ?? radio.trigger}
        </span>
        <span className="px-1.5 py-0.5 rounded bg-zinc-500/10 border border-zinc-500/20 text-zinc-400 text-[9px]">
          IA: {(radio.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <div className="text-orange-300 text-xs leading-relaxed font-mono">"{radio.message}"</div>
    </div>
  )
}

export default AiFloatingPanel