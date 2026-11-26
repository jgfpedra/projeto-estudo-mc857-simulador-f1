import type { RaceMeta } from './types'

/**
 * Live backend (`backend/api`) — **consumer only**.
 *
 * Starting a race (`POST /races`) is someone else's interface; this module only
 * joins a race that already exists (`GET /races/{id}` + `WS /ws/races/{id}`),
 * so the viewer never grows a second way to create one.
 */
const API_BASE = (
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'
).replace(/\/$/, '')

async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown }
    if (typeof data.detail === 'string' && data.detail) return data.detail
  } catch {
    // Not JSON; fall through to the status line.
  }
  return `API error (${response.status})`
}

export async function fetchRaceMeta(raceId: string): Promise<RaceMeta> {
  const response = await fetch(`${API_BASE}/races/${encodeURIComponent(raceId)}`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as RaceMeta
}

/**
 * Join an existing race's WebSocket and feed every event into `onEvent`.
 *
 * This is the only connection the viewer opens: the race itself is created by
 * the backend's own interface, not here.
 */
export function openRaceSocket(raceId: string, onEvent: (event: unknown) => void): WebSocket {
  const url = `${API_BASE.replace(/^http/, 'ws')}/ws/races/${encodeURIComponent(raceId)}`
  const socket = new WebSocket(url)
  socket.addEventListener('message', (message) => {
    try {
      onEvent(JSON.parse(message.data as string))
    } catch {
      // A single malformed frame must not take the viewer down.
    }
  })
  return socket
}
