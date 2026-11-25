import { useEffect, useReducer } from 'react'
import type { LiveStore } from '../live/store'

interface Props {
  store: LiveStore
  /** Grid index of the followed car. */
  selected: number
}

const URGENCY_COLOUR: Record<string, string> = {
  alta: '#ff5252',
  media: '#ffb020',
  baixa: '#9a9aa8',
}

/**
 * The AI race engineer, over the circuit.
 *
 * Two outputs, both arriving from the backend over the same WebSocket:
 * `ai_suggestion` (what the engineer says) and `ai_command` (what the coach is
 * doing to the followed car). The commands are highlighted on the car panel's
 * telemetry, so the text and the visible change stay side by side.
 *
 * Polled/subscribed rather than frame-driven: messages arrive every few seconds,
 * not every frame.
 */
export function AiPanel({ store, selected }: Props) {
  const [, force] = useReducer((n: number) => n + 1, 0)
  useEffect(() => store.subscribe(force), [store])

  const messages = store.messages
  // The AI only commands the followed driver; the panel must describe that car
  // even if the user selects another one in the field.
  const followedId = store.meta.followed_driver_id
  const followedIndex =
    (followedId ? store.indexOfDriver(followedId) : undefined) ?? selected
  const command = store.activeCommand(followedIndex)
  const followed = store.meta.drivers[followedIndex]
  const position = store.positionOf(followedIndex)
  const lastLap = store.lapOf(followedIndex)

  return (
    <div
      style={{
        position: 'absolute',
        top: 12,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 420,
        maxHeight: 300,
        overflow: 'hidden',
        padding: '8px 12px',
        background: 'rgba(12,12,18,0.86)',
        border: '1px solid #2c2c38',
        borderRadius: 4,
        color: '#d8d8e0',
        font: '12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace',
      }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
        <span style={{ color: '#fff' }}>engenheiro</span>
        <span style={{ opacity: 0.6 }}>ao vivo</span>
        <span style={{ flex: 1 }} />
        <span
          style={{
            color:
              store.status === 'live'
                ? '#3ecf5a'
                : store.status === 'error'
                  ? '#ff5252'
                  : '#ffb020',
          }}
        >
          {store.status}
        </span>
      </div>

      <div style={{ marginTop: 4, opacity: 0.75 }}>
        seguindo{' '}
        <span style={{ color: '#fff' }}>
          {followed?.driver_id} {followed?.name ?? ''}
        </span>
        {position > 0 ? ` P${position}` : ''}
        {` · volta ${lastLap}`}
        {' · '}
        {command && command.command !== 'neutral' ? (
          <span style={{ color: '#ffd27a' }}>
            comando {command.command.toUpperCase()}
            {command.reason ? ` — ${command.reason}` : ''}
          </span>
        ) : (
          <span style={{ color: '#9a9aa8' }}>sem comando ativo</span>
        )}
      </div>

      {messages.length === 0 ? (
        <p style={{ margin: '8px 0 0', opacity: 0.55 }}>
          aguardando a primeira sugestão da IA…
        </p>
      ) : (
        <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 5 }}>
          {[...messages]
            .slice(-5)
            .reverse()
            .map((message, index) => {
              const mine = message.driver_id === (followedId ?? followed?.driver_id)
              const commandType = message.comando?.tipo
              return (
                <div
                  key={`${message.sim_ts}-${index}`}
                  style={{
                    padding: '3px 6px',
                    borderLeft: `2px solid ${URGENCY_COLOUR[message.urgencia] ?? '#9a9aa8'}`,
                    background: mine ? 'rgba(62,207,90,0.07)' : 'rgba(255,255,255,0.03)',
                    color: message.fallback ? '#9a9aa8' : '#e8e8ee',
                  }}
                >
                  <span style={{ opacity: 0.55 }}>
                    {(message.sim_ts ?? 0).toFixed(0)}s · {message.urgencia ?? '—'}
                    {commandType && commandType !== 'neutral' ? ` · ${commandType}` : ''}
                  </span>
                  <div>{message.aviso || '—'}</div>
                </div>
              )
            })}
        </div>
      )}
    </div>
  )
}
