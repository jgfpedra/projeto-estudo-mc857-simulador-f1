import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchDebrief } from './api'
import type { Debrief, DebriefImpact } from './types'
import './DebriefPanel.css'

type Props = {
  raceId: string
  onClose: () => void
}

const IMPACT_LABEL: Record<DebriefImpact, string> = {
  alto: 'ALTO',
  medio: 'MÉDIO',
  baixo: 'BAIXO',
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="debrief-section">
      <h3>{title}</h3>
      <div>{children}</div>
    </section>
  )
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.includes('404')) {
    return 'O debrief ainda está sendo gerado. Uma nova tentativa será feita automaticamente.'
  }
  return 'Não foi possível carregar o debrief. Verifique o backend e tente novamente.'
}

/** Pós-corrida: consulta até o worker da IA persistir o debrief desta corrida. */
export function DebriefPanel({ raceId, onClose }: Props) {
  const [debrief, setDebrief] = useState<Debrief | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let disposed = false
    let completed = false
    let inFlight = false
    let interval: number | undefined

    setDebrief(null)
    setError(null)
    setLoading(true)

    async function load() {
      if (disposed || completed || inFlight) return
      inFlight = true
      try {
        const data = await fetchDebrief(raceId)
        if (disposed) return
        completed = true
        if (interval !== undefined) window.clearInterval(interval)
        setDebrief(data)
        setError(null)
      } catch (cause) {
        if (!disposed) setError(errorMessage(cause))
      } finally {
        inFlight = false
        if (!disposed) setLoading(false)
      }
    }

    void load()
    interval = window.setInterval(() => void load(), 10_000)
    return () => {
      disposed = true
      if (interval !== undefined) window.clearInterval(interval)
    }
  }, [raceId, attempt])

  return (
    <div className="debrief-overlay" role="dialog" aria-modal="true" aria-label="Debrief pós-corrida">
      <article className="debrief-panel">
        <header className="debrief-header">
          <div>
            <h2>Debrief pós-corrida</h2>
            {debrief && (
              <time dateTime={new Date(debrief.gerado_em * 1000).toISOString()}>
                Gerado em {new Date(debrief.gerado_em * 1000).toLocaleString('pt-BR')}
              </time>
            )}
          </div>
          <button type="button" onClick={onClose} aria-label="Fechar debrief">Fechar</button>
        </header>

        {debrief?.fallback && (
          <p className="debrief-fallback">
            Resumo factual de contingência: {debrief.fallback_motivo || 'LLM indisponível'}
          </p>
        )}

        {loading && !debrief ? (
          <div className="debrief-status" aria-live="polite">Carregando debrief…</div>
        ) : error && !debrief ? (
          <div className="debrief-status" aria-live="polite">
            <p>{error}</p>
            <button type="button" onClick={() => { setLoading(true); setAttempt((value) => value + 1) }}>
              Tentar agora
            </button>
          </div>
        ) : debrief ? (
          <div className="debrief-content">
            <Section title="Resumo geral">{debrief.resumo_geral}</Section>
            <Section title="Largada">{debrief.largada}</Section>
            <Section title="Estratégia de pneus">{debrief.estrategia_pneus}</Section>
            <Section title="Combustível">{debrief.combustivel}</Section>
            <Section title="Momentos-chave">
              {debrief.momentos_chave.length === 0 ? (
                <p>Nenhum momento-chave registrado.</p>
              ) : (
                <ol className="debrief-moments">
                  {debrief.momentos_chave.map((moment, index) => (
                    <li key={`${moment.volta}-${index}`}>
                      <strong>{moment.volta}ª volta</strong>
                      <span>{moment.evento}</span>
                      <span className={`debrief-impact debrief-impact--${moment.impacto}`}>
                        {IMPACT_LABEL[moment.impacto]}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </Section>
            <Section title="Contatos e incidentes">{debrief.contatos_incidentes}</Section>
            <Section title="Performance dos pilotos">
              <dl className="debrief-performance">
                {debrief.performance_pilotos.vencedor && <><dt>Vencedor</dt><dd>{debrief.performance_pilotos.vencedor}</dd></>}
                {debrief.performance_pilotos.surpresa_positiva && <><dt>Surpresa positiva</dt><dd>{debrief.performance_pilotos.surpresa_positiva}</dd></>}
                {debrief.performance_pilotos.decepcao && <><dt>Decepção</dt><dd>{debrief.performance_pilotos.decepcao}</dd></>}
                {debrief.performance_pilotos.melhor_ultrapassagem && <><dt>Melhor ultrapassagem</dt><dd>{debrief.performance_pilotos.melhor_ultrapassagem}</dd></>}
                {Object.keys(debrief.performance_pilotos).length === 0 && <dd>Não há dados suficientes para destacar pilotos.</dd>}
              </dl>
            </Section>
            <Section title="Decisões do engenheiro">{debrief.decisoes_engenheiro}</Section>
            <Section title="Lições aprendidas">{debrief.licoes_aprendidas}</Section>
          </div>
        ) : (
          <div className="debrief-status">Nenhum debrief disponível.</div>
        )}
      </article>
    </div>
  )
}

export default DebriefPanel
