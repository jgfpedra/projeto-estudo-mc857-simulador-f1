"use client"

import { useMemo, useState } from "react"
import { ChevronDown, ChevronUp, X, AlertCircle, CheckCircle, Loader2, Zap, Target } from "lucide-react"
import type { AiSuggestion, AiCommand } from "@/types/race"

interface AiFloatingPanelProps {
  // Estado da IA
  engineerStatus: "idle" | "started" | "monitoring" | "stopped" | "error"
  engineerStats?: Record<string, unknown> | null
  engineerError?: string | null
  
  // Dados da corrida
  raceId: string
  raceName: string
  
  // Piloto acompanhado (alvo do engenheiro)
  followedDriverId: string | null
  followedDriverName: string
  
  // Dados de recomendação
  suggestions: AiSuggestion[]
  commands: Map<string, AiCommand>
  
  // Callbacks
  onClose?: () => void
  onToggleCollapse?: () => void
  
  // Config
  position?: "top-right" | "top-left" | "bottom-right" | "bottom-left"
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
    color: "text-green-400",
    bg: "bg-green-500/10",
    border: "border-green-500/30",
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
  followedDriverId,
  followedDriverName,
  suggestions,
  commands,
  onClose,
  onToggleCollapse,
  position = "top-right",
  initiallyCollapsed = false,
}: AiFloatingPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(initiallyCollapsed)
  const [showAllSuggestions, setShowAllSuggestions] = useState(false)

  // Status config
  const statusCfg = STATUS_CONFIG[engineerStatus]

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

  const handleToggleCollapse = () => {
    setIsCollapsed(!isCollapsed)
    onToggleCollapse?.()
  }

  const handleClose = () => {
    onClose?.()
  }

  // Posicionamento fixo fora do canvas
  const positionClass = POSITION_CLASSES[position]

  return (
    <div
      className={`
        fixed ${positionClass} z-50 pointer-events-auto
        transition-all duration-300 ease-out
        ${isCollapsed ? "w-72" : "w-80"}
      `}
      role="region"
      aria-label="Painel do Engenheiro de IA"
    >
      {/* Header - sempre visível */}
      <div className={`
        flex items-center gap-2 p-3 rounded-t-lg border-b border-border/50
        bg-background/95 backdrop-blur-sm
        ${statusCfg.border} ${statusCfg.bg}
      `}>
        {/* Status Badge */}
        <div className={`flex items-center gap-1.5 ${statusCfg.color} ${statusCfg.pulse ? "animate-pulse" : ""}`}>
          {renderStatusIcon(statusCfg.iconType)}
          <span className="text-xs font-bold uppercase tracking-wider">{statusCfg.label}</span>
        </div>

        {/* Race Info */}
        <div className="flex-1 min-w-0 ml-2">
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-muted-foreground truncate">{raceName}</span>
            <span className="px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20 text-primary text-[10px] font-mono">
              #{shortRaceId}
            </span>
          </div>
          {followedDriverId && (
            <div className="flex items-center gap-1.5 text-[11px] mt-0.5">
              <Target className="w-3 h-3 text-green-400" />
              <span className="text-muted-foreground">Engenheiro:</span>
              <span className="text-foreground font-medium">{followedDriverName}</span>
              <span className="px-1 py-0.5 rounded bg-green-500/10 border border-green-500/20 text-green-400 text-[9px]">
                ACOMPANHADO
              </span>
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleToggleCollapse}
            className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            aria-label={isCollapsed ? "Expandir" : "Colapsar"}
            aria-expanded={!isCollapsed}
          >
            {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
          {onClose && (
            <button
              onClick={handleClose}
              className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Fechar painel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Content - colapsável */}
      {!isCollapsed && (
        <div className="bg-background/95 backdrop-blur-sm border border-border/50 rounded-b-lg max-h-[500px] overflow-hidden flex flex-col">
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
      </div>
      <div className="text-foreground text-xs leading-relaxed">{suggestion.message}</div>
    </div>
  )
}

export default AiFloatingPanel