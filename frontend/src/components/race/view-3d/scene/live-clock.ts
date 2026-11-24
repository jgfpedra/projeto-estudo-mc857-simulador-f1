/**
 * O que o 3D desenha a cada quadro: um par de frames e o `alpha` entre eles.
 *
 * Vem da reprodução com buffer (`playback.ts`): enquanto o 3D está montado,
 * uma assinatura da store empurra cada frame novo (por `simTs`) para o
 * relógio, e `readLive()` o avança até o quadro atual. O 2D, o painel de
 * tempos e o cartão do piloto continuam lendo a store direto, na borda ao
 * vivo; o 3D fica ~150 ms atrás deles.
 *
 * O tempo de parede é o do quadro de animação (`document.timeline.currentTime`,
 * o mesmo carimbo do `requestAnimationFrame`), não o `performance.now()` do
 * meio do quadro: assim o passo desenhado acompanha a tela, quadro a quadro.
 *
 * O gancho de desenvolvimento (`dev-probe.ts`) pode congelar a vista: os
 * carros param na pose do último quadro desenhado (a velocidade lida vira
 * zero, para a câmera de perseguição assentar atrás do carro) enquanto o
 * WebSocket, o relógio e o 2D seguem. Pode também trocar para o caminho
 * antigo (borda ao vivo, `prevFrame -> frame`), para medir o antes e o
 * depois na mesma página. Em produção ninguém chama `freezeLive` nem
 * `setPlaybackMode`.
 */
import { useLiveRaceStore } from "@/stores/live-race-store"
import type { Frame } from "@/types/race"
import { frameAlpha } from "./live-pose"
import { PlaybackClock } from "./playback"

export type PlaybackMode = "buffered" | "live"

export type LiveView = {
  prev: Frame | null
  /** Nulo enquanto a store não tem frame. */
  cur: Frame | null
  alpha: number
  /** Instante de simulação desenhado, s. */
  simTs: number | null
  /** Muda a cada ressincronização: a câmera corta em vez de amortecer. */
  resyncs: number
  /** Parado no frame mais novo, à espera do próximo. */
  held: boolean
  /** Atraso atrás do frame mais novo da store, ms. */
  lagMs: number
  mode: PlaybackMode
}

const clock = new PlaybackClock()
let users = 0
let unsubscribe: (() => void) | null = null
let mode: PlaybackMode = "buffered"
let last: { now: number; view: LiveView } | null = null
let frozen: { now: number; view: LiveView } | null = null
const edge = { frame: null as Frame | null, resyncs: 0 }

const EMPTY: Omit<LiveView, "mode"> = { prev: null, cur: null, alpha: 1, simTs: null, resyncs: 0, held: false, lagMs: 0 }

/**
 * Liga a reprodução enquanto houver um 3D montado (contagem de referências).
 * Devolve a função que a desliga.
 */
export function acquirePlayback(): () => void {
  if (users++ === 0) {
    clock.clear()
    const s = useLiveRaceStore.getState()
    if (s.prevFrame) clock.push(s.prevFrame, s.frameAt - s.tickIntervalMs, true)
    if (s.frame) clock.push(s.frame, s.frameAt, s.prevFrame === null)
    unsubscribe = useLiveRaceStore.subscribe((st, prev) => {
      if (st.frame === prev.frame) return
      if (!st.frame) clock.clear()
      // Snapshot (carga, reconexão): a store zera `prevFrame`.
      else clock.push(st.frame, st.frameAt, st.prevFrame === null)
    })
  }
  let released = false
  return () => {
    if (released) return
    released = true
    if (--users > 0) return
    unsubscribe?.()
    unsubscribe = null
    clock.clear()
    last = null
    frozen = null
    mode = "buffered"
  }
}

function frameTime(): number {
  const t = typeof document !== "undefined" ? document.timeline?.currentTime : null
  return typeof t === "number" ? t : performance.now()
}

/** Caminho antigo: borda ao vivo, como o 2D. Só para comparação no gancho de desenvolvimento. */
function liveEdge(): LiveView {
  const s = useLiveRaceStore.getState()
  if (!s.frame) return { ...EMPTY, mode: "live" }
  if (s.frame !== edge.frame && s.prevFrame === null && edge.frame !== null) edge.resyncs++
  edge.frame = s.frame
  const alpha = frameAlpha(performance.now(), s.frameAt, s.tickIntervalMs)
  const simTs = s.prevFrame ? s.prevFrame.simTs + (s.frame.simTs - s.prevFrame.simTs) * alpha : s.frame.simTs
  return { prev: s.prevFrame, cur: s.frame, alpha, simTs, resyncs: edge.resyncs, held: alpha >= 1, lagMs: (s.frame.simTs - simTs) * 1000, mode: "live" }
}

/** O par de frames e o `alpha` deste quadro. Chamar uma vez por quadro. */
export function readLive(): { now: number; view: LiveView; frozen: boolean } {
  if (frozen) return { now: frozen.now, view: frozen.view, frozen: true }
  const now = frameTime()
  let view: LiveView
  if (mode === "live") {
    view = liveEdge()
  } else {
    const p = clock.sample(now)
    view = p
      ? { prev: p.prev, cur: p.cur, alpha: p.alpha, simTs: p.simTs, resyncs: p.resyncs, held: p.held, lagMs: p.lagMs, mode }
      : { ...EMPTY, mode }
  }
  last = { now, view }
  return { now, view, frozen: false }
}

export function freezeLive(): void {
  if (frozen) return
  frozen = last ?? readLive()
}

export function unfreezeLive(): void {
  frozen = null
}

export function liveFrozen(): boolean {
  return frozen !== null
}

export function setPlaybackMode(m: PlaybackMode): void {
  mode = m
}

export function playbackMode(): PlaybackMode {
  return mode
}
