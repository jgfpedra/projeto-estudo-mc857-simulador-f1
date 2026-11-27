"use client"

import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { api } from "@/services/api"

const IMPACT_COLORS = {
  alta: { bg: "bg-red-500/20", text: "text-red-400", icon: "🔴" },
  media: { bg: "bg-amber-500/20", text: "text-amber-400", icon: "🟡" },
  baixa: { bg: "bg-zinc-500/20", text: "text-zinc-400", icon: "🟢" },
} as const

interface Debrief {
  resumo_geral: string
  largada: string
  estrategia_pneus: string
  combustivel: string
  momentos_chave: Array<{ volta: number; evento: string; impacto: "alta" | "media" | "baixa" }>
  contatos_incidentes: string
  performance_pilotos: {
    vencedor?: string
    surpresa_positiva?: string
    decepcao?: string
    melhor_ultrapassagem?: string
  }
  decisoes_engenheiro: string
  licoes_aprendidas: string
  fallback?: boolean
  fallback_motivo?: string
  race_id: string
  gerado_em: number
}

export function DebriefPanel() {
  const { raceId } = useParams<{ raceId: string }>()
  const [debrief, setDebrief] = useState<Debrief | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!raceId) return

    const fetchDebrief = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await api.getDebrief(raceId!)
        setDebrief(data)
      } catch (err: any) {
        if (err.response?.status === 404) {
          setError("Debrief ainda não gerado. Aguarde a corrida terminar.")
        } else {
          setError("Erro ao carregar debrief. Tente novamente.")
        }
      } finally {
        setLoading(false)
      }
    }

    fetchDebrief()

    const interval = setInterval(() => {
      if (raceId) fetchDebrief()
    }, 10000)

    return () => clearInterval(interval)
  }, [raceId])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="w-10 h-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-muted-foreground text-sm">Carregando debrief...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="text-center text-muted-foreground">
          <span className="text-4xl">⚠️</span>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  if (!debrief) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="text-center text-muted-foreground">
          <span className="text-4xl">📋</span>
          <p className="text-sm">Nenhum debrief disponível</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col overflow-y-auto p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/50 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">📋</span>
          <div>
            <h2 className="text-lg font-bold">Debrief Pós-Corrida</h2>
            <p className="text-xs text-muted-foreground">
              Gerado em {new Date(debrief.gerado_em * 1000).toLocaleString("pt-BR")}
            </p>
          </div>
        </div>
        {debrief.fallback && (
          <span className="px-2 py-1 text-[10px] font-bold rounded bg-amber-500/20 border border-amber-500/30 text-amber-400">
            ⚠️ Fallback: {debrief.fallback_motivo || "LLM indisponível"}
          </span>
        )}
      </div>

      {/* Sections */}
      <div className="space-y-3">
        <Section title="Resumo Geral" icon="📋">
          {debrief.resumo_geral}
        </Section>
        <Section title="Largada" icon="🏁">
          {debrief.largada}
        </Section>
        <Section title="Estratégia de Pneus" icon="🔧">
          {debrief.estrategia_pneus}
        </Section>
        <Section title="Combustível" icon="⛽">
          {debrief.combustivel}
        </Section>
        <Section title="Momentos-Chave" icon="⏱️">
          {debrief.momentos_chave.length > 0
            ? debrief.momentos_chave.map((m: { volta: number; evento: string; impacto: "alta" | "media" | "baixa" }, i: number) => (
                <div key={i} className="flex items-start gap-2 p-2 rounded bg-muted/30 border border-border/30">
                  <span className="font-mono text-xs text-primary">{m.volta}ª volta</span>
                  <span className="flex-1 text-xs leading-relaxed">{m.evento}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${IMPACT_COLORS[m.impacto].bg} ${IMPACT_COLORS[m.impacto].text}`}>
                    {IMPACT_COLORS[m.impacto].icon} {m.impacto.toUpperCase()}
                  </span>
                </div>
              ))
            : <span>Nenhum momento-chave registrado</span>
          }
        </Section>
        <Section title="Contatos & Incidentes" icon="⚠️">
          {debrief.contatos_incidentes}
        </Section>
        <Section title="Performance dos Pilotos" icon="🏆">
          {debrief.performance_pilotos?.vencedor && (
            <div className="p-2 rounded bg-green-500/10 border border-green-500/20">
              <strong className="text-green-400">🏆 Vencedor:</strong> {debrief.performance_pilotos.vencedor}
            </div>
          )}
          {debrief.performance_pilotos?.surpresa_positiva && (
            <div className="p-2 rounded bg-blue-500/10 border border-blue-500/20">
              <strong className="text-blue-400">⬆️ Surpresa Positiva:</strong> {debrief.performance_pilotos.surpresa_positiva}
            </div>
          )}
          {debrief.performance_pilotos?.decepcao && (
            <div className="p-2 rounded bg-red-500/10 border border-red-500/20">
              <strong className="text-red-400">📉 Decepção:</strong> {debrief.performance_pilotos.decepcao}
            </div>
          )}
          {debrief.performance_pilotos?.melhor_ultrapassagem && (
            <div className="p-2 rounded bg-purple-500/10 border border-purple-500/20">
              <strong className="text-purple-400">🏁 Melhor Ultrapassagem:</strong> {debrief.performance_pilotos.melhor_ultrapassagem}
            </div>
          )}
        </Section>
        <Section title="Decisões do Engenheiro" icon="🎯">
          {debrief.decisoes_engenheiro}
        </Section>
        <Section title="Lições Aprendidas" icon="💡">
          {debrief.licoes_aprendidas}
        </Section>
      </div>
    </div>
  )
}

const IMPACT_COLORS = {
  alta: { bg: "bg-red-500/20", text: "text-red-400", icon: "🔴" },
  media: { bg: "bg-amber-500/20", text: "text-amber-400", icon: "🟡" },
  baixa: { bg: "bg-zinc-500/20", text: "text-zinc-400", icon: "🟢" },
} as const

function Section({ title, icon, children }: { title: string; icon?: string; children: React.ReactNode }) {
  return (
    <div className="border border-border/50 rounded-lg bg-background/50 overflow-hidden">
      <div className="flex items-center gap-2 p-3 hover:bg-accent/50 transition-colors cursor-default">
        <span className="text-2xl">{icon || (title === "Momentos-Chave" ? "⏱️" : title === "Contatos & Incidentes" ? "⚠️" : title === "Performance dos Pilotos" ? "🏆" : title === "Decisões do Engenheiro" ? "🎯" : title === "Lições Aprendidas" ? "💡" : title === "Resumo Geral" ? "📋" : title === "Largada" ? "🏁" : title === "Estratégia de Pneus" ? "🔧" : title === "Combustível" ? "⛽" : "📋")}</span>
        <span className="text-sm font-bold uppercase tracking-wider text-foreground">{title}</span>
      </div>
      <div className="px-3 pb-3 border-t border-border/30 animate-in fade-in-20 duration-200">
        <div className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
          {children}
        </div>
      </div>
    </div>
  )
}

export default DebriefPanel