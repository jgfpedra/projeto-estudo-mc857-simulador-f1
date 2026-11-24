/**
 * Relógio e estado ao vivo como o 3D os lê a cada quadro.
 *
 * Normalmente é só `performance.now()` e `useLiveRaceStore.getState()`, os
 * mesmos do 2D. O gancho de desenvolvimento (`dev-probe.ts`) pode congelar os
 * dois: os carros param na pose do instante congelado (a velocidade lida vira
 * zero, para a câmera de perseguição assentar atrás do carro) enquanto o
 * WebSocket e o 2D seguem normalmente. Serve para a verificação ao vivo tirar
 * a captura e ler as posições no mesmo instante, em qualquer velocidade de
 * renderização. Em produção ninguém chama `freezeLive`.
 */
import { useLiveRaceStore } from "@/stores/live-race-store"
import type { Frame } from "@/types/race"

export type LiveSnapshot = {
  frame: Frame | null
  prevFrame: Frame | null
  frameAt: number
  tickIntervalMs: number
}

let frozen: { now: number; s: LiveSnapshot } | null = null

export function readLive(): { now: number; s: LiveSnapshot; frozen: boolean } {
  if (frozen) return { now: frozen.now, s: frozen.s, frozen: true }
  return { now: performance.now(), s: useLiveRaceStore.getState(), frozen: false }
}

export function freezeLive(): void {
  if (frozen) return
  const s = useLiveRaceStore.getState()
  frozen = {
    now: performance.now(),
    s: { frame: s.frame, prevFrame: s.prevFrame, frameAt: s.frameAt, tickIntervalMs: s.tickIntervalMs },
  }
}

export function unfreezeLive(): void {
  frozen = null
}

export function liveFrozen(): boolean {
  return frozen !== null
}
