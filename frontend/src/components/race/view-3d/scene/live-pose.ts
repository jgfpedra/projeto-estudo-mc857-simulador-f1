/**
 * Poses dos carros no mesmo instante que o mapa 2D.
 *
 * Puro (sem React, sem three) para ser testado com `node --test`. As posições
 * vêm de `interpolateCars`, a mesma função que `track-2d.tsx` usa, e o `alpha`
 * é calculado com a mesma fórmula; assim as duas vistas mostram o mesmo
 * instante para o mesmo `performance.now()`.
 *
 * Eixos: o backend usa o plano (x, y) e o Three.js tem y para cima, então
 * `three.x = x` e `three.z = -y`. Sem o sinal de menos a pista sai espelhada.
 */
import type { Frame } from "@/types/race"
import { interpolateCars } from "../../../../helpers/race-live.ts"

/** Fração entre `prevFrame` e `frame`, idêntica à de `track-2d.tsx`. */
export function frameAlpha(now: number, frameAt: number, tickIntervalMs: number): number {
  return Math.min(1, Math.max(0, (now - frameAt) / tickIntervalMs))
}

/** Interpola dois ângulos (radianos) pelo arco mais curto. */
export function lerpAngle(a: number, b: number, f: number): number {
  const d = Math.atan2(Math.sin(b - a), Math.cos(b - a))
  return a + d * f
}

/** Ângulo em (-pi, pi]. */
export function wrapAngle(a: number): number {
  return Math.atan2(Math.sin(a), Math.cos(a))
}

export const toThreeX = (x: number): number => x
export const toThreeZ = (y: number): number => -y

/**
 * Direção da engine (anti-horária a partir de +x no plano) para o giro do
 * modelo em torno de +y. O modelo aponta para -Z local; a direção da engine
 * `(cos h, sin h)` vira `(cos h, 0, -sin h)` no Three.js, logo `yaw = h - pi/2`.
 * Copiado de `viz3d/src/engine/source.ts` (`engineYaw`).
 */
export function engineYaw(headingRad: number): number {
  return headingRad - Math.PI / 2
}

export type CarPose = {
  /** Plano do backend, metros. */
  x: number
  y: number
  /** Direção no plano do backend, radianos. */
  headingRad: number
  /** `progress_m` interpolado; nulo se o backend não envia. */
  progressM: number | null
  /** `s_m` do tick atual (já é relativo à linha, não se interpola através dela). */
  sM: number | null
  speedMps: number
}

/**
 * Pose de cada carro em `alpha`. `x`/`y` são exatamente os de `interpolateCars`.
 *
 * `lastHeading` guarda a última direção conhecida por piloto, usada quando o
 * backend não envia `heading_deg` e o carro está parado.
 */
export function interpolatePoses(
  prev: Frame | null,
  cur: Frame,
  alpha: number,
  lastHeading: Map<string, number> = new Map(),
): Map<string, CarPose> {
  const xy = interpolateCars(prev, cur, alpha)
  const prevById = new Map((prev?.cars ?? []).map((c) => [c.driverId, c]))
  const out = new Map<string, CarPose>()

  for (const c of cur.cars) {
    const p = prevById.get(c.driverId) ?? c
    const pos = xy.get(c.driverId) ?? { x: c.x, y: c.y }

    const a = p.headingDeg ?? c.headingDeg
    const b = c.headingDeg ?? a
    let heading: number
    if (a !== null && b !== null) {
      heading = wrapAngle(lerpAngle((a * Math.PI) / 180, (b * Math.PI) / 180, alpha))
    } else {
      const dx = c.x - p.x
      const dy = c.y - p.y
      heading = dx * dx + dy * dy > 1e-12 ? Math.atan2(dy, dx) : (lastHeading.get(c.driverId) ?? 0)
    }
    lastHeading.set(c.driverId, heading)

    const progressM =
      p.progressM !== null && c.progressM !== null
        ? p.progressM + (c.progressM - p.progressM) * alpha
        : c.progressM

    out.set(c.driverId, {
      x: pos.x,
      y: pos.y,
      headingRad: heading,
      progressM,
      sM: c.sM,
      speedMps: (p.speedKmh + (c.speedKmh - p.speedKmh) * alpha) / 3.6,
    })
  }

  return out
}

/**
 * Deslocamento no chão ao longo da direção média do carro, em metros.
 * Copiado de `viz3d/src/cars/odometry.ts`: o progresso da engine é uma projeção
 * na pista e não serve de hodômetro numa rodada ou ré.
 */
export function signedWheelTravel(
  x0: number,
  y0: number,
  heading0: number,
  x1: number,
  y1: number,
  heading1: number,
): number {
  const delta = Math.atan2(Math.sin(heading1 - heading0), Math.cos(heading1 - heading0))
  const heading = heading0 + delta / 2
  return (x1 - x0) * Math.cos(heading) + (y1 - y0) * Math.sin(heading)
}

/**
 * Hodômetro das rodas a partir dos frames da store, no lugar do `LiveBuffer`
 * do viz3d. Acumula o deslocamento entre `prevFrame` e `frame` a cada tick
 * novo e interpola com o mesmo `alpha` das posições. Depois de uma
 * ressincronização (`prevFrame` nulo) mantém a fase exibida, sem salto.
 */
export class WheelOdometer {
  private frame: Frame | null = null
  private atPrev = new Map<string, number>()
  private atCur = new Map<string, number>()
  private readonly shown = new Map<string, number>()

  update(prev: Frame | null, cur: Frame): void {
    if (cur === this.frame) return
    const base = prev !== null && prev === this.frame ? this.atCur : this.shown
    const prevById = new Map((prev?.cars ?? []).map((c) => [c.driverId, c]))
    this.atPrev = new Map(base)
    this.atCur = new Map()

    for (const c of cur.cars) {
      const start = this.atPrev.get(c.driverId) ?? this.shown.get(c.driverId) ?? 0
      this.atPrev.set(c.driverId, start)
      const p = prevById.get(c.driverId)
      if (!p) {
        this.atCur.set(c.driverId, start)
        continue
      }
      const along = Math.atan2(c.y - p.y, c.x - p.x)
      const h0 = p.headingDeg !== null ? (p.headingDeg * Math.PI) / 180 : along
      const h1 = c.headingDeg !== null ? (c.headingDeg * Math.PI) / 180 : along
      this.atCur.set(c.driverId, start + signedWheelTravel(p.x, p.y, h0, c.x, c.y, h1))
    }
    this.frame = cur
  }

  sample(driverId: string, alpha: number): number {
    const a = this.atPrev.get(driverId) ?? this.atCur.get(driverId) ?? 0
    const b = this.atCur.get(driverId) ?? a
    const v = a + (b - a) * alpha
    this.shown.set(driverId, v)
    return v
  }
}

/**
 * Desembrulha uma distância na volta (`s_m`, ou uma projeção) para crescer sem
 * limite, como `progress_m`. A câmera de perseguição amortece essa grandeza e
 * não pode ver um salto de uma volta na linha de chegada.
 */
export class LapUnwrapper {
  private value: number | null = null
  private lastWrapped = 0

  reset(): void {
    this.value = null
  }

  next(wrapped: number, lengthM: number): number {
    if (this.value === null || !(lengthM > 0)) {
      this.value = wrapped
    } else {
      let d = (wrapped - this.lastWrapped) % lengthM
      if (d > lengthM / 2) d -= lengthM
      if (d < -lengthM / 2) d += lengthM
      this.value += d
    }
    this.lastWrapped = wrapped
    return this.value
  }
}
