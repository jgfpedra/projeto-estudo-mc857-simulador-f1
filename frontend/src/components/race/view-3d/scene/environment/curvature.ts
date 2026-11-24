/**
 * Curvatura da linha servida, medida em metros e não em pontos.
 *
 * O `frame.curvature` de `track-frame.ts` usa os vizinhos imediatos: nos
 * arquivos de 4 m isso é ruído; nas pistas do OpenF1 (pontos a 14–42 m) a
 * janela muda de tamanho a cada ponto. Aqui a curvatura de Menger (círculo por
 * três pontos) usa vizinhos a pelo menos `baselineM` de arco de cada lado e é
 * suavizada por uma janela triangular também em metros. Pontos sobre um
 * círculo dão 1/R exato com qualquer espaçamento, então os mesmos limiares
 * servem para as duas resoluções.
 *
 * Sinal igual ao de `track-frame.ts`: positivo = curva à direita.
 */
import type { TrackFrame } from "../track-frame.ts"

/** Arco mínimo até cada vizinho da curvatura de Menger. */
export const CURVATURE_BASELINE_M = 12
/** Meia largura da janela triangular de suavização. */
export const CURVATURE_SMOOTH_M = 16

/** Intervalo de arco `[s0, s1]`, com `s0` em `[0, L)` e `s1 > s0` (pode passar de L: dá a volta). */
export type SRange = [number, number]

const wrapI = (i: number, n: number) => ((i % n) + n) % n

/** Curvatura assinada (1/m) em cada ponto da linha. */
export function robustCurvature(
  frame: TrackFrame,
  baselineM = CURVATURE_BASELINE_M,
  smoothM = CURVATURE_SMOOTH_M,
): Float64Array {
  const P = frame.points
  const n = P.length
  const L = frame.lengthM
  const s = frame.s
  const ahead = (from: number, to: number) => (s[to] - s[from] + L) % L
  const raw = new Float64Array(n)
  const maxSteps = Math.max(1, Math.floor(n / 3))

  for (let i = 0; i < n; i++) {
    let a = i
    for (let k = 0; k < maxSteps; k++) {
      a = wrapI(a - 1, n)
      if (ahead(a, i) >= baselineM) break
    }
    let c = i
    for (let k = 0; k < maxSteps; k++) {
      c = wrapI(c + 1, n)
      if (ahead(i, c) >= baselineM) break
    }
    const ux = P[i].x - P[a].x
    const uz = P[i].z - P[a].z
    const vx = P[c].x - P[i].x
    const vz = P[c].z - P[i].z
    const wx = P[c].x - P[a].x
    const wz = P[c].z - P[a].z
    const denom = Math.hypot(ux, uz) * Math.hypot(vx, vz) * Math.hypot(wx, wz)
    // u x v > 0: o segmento seguinte gira para a direita (direita = tangente x cima).
    raw[i] = denom > 1e-9 ? (2 * (ux * vz - uz * vx)) / denom : 0
  }

  if (smoothM <= 0) return raw
  const out = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    let sum = 0
    let wsum = 0
    for (const dir of [-1, 1]) {
      for (let k = dir < 0 ? 0 : 1; k < n; k++) {
        const j = wrapI(i + dir * k, n)
        const dist = dir < 0 ? ahead(j, i) : ahead(i, j)
        if (k > 0 && dist >= smoothM) break
        // Peso pelo arco que o ponto representa (espaçamento não uniforme).
        const span = (ahead(wrapI(j - 1, n), j) + ahead(j, wrapI(j + 1, n))) / 2
        const w = (1 - dist / smoothM) * Math.max(span, 1e-6)
        sum += raw[j] * w
        wsum += w
      }
    }
    out[i] = wsum > 0 ? sum / wsum : raw[i]
  }
  return out
}

/** Índice do ponto em ou antes de `s` (já embrulhado). */
export function segmentAt(frame: TrackFrame, s: number): number {
  const arr = frame.s
  let lo = 0
  let hi = arr.length - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (arr[mid] <= s) lo = mid
    else hi = mid - 1
  }
  return lo
}

/** Curvatura interpolada linearmente em `s` (qualquer valor; é embrulhado). */
export function kappaAt(frame: TrackFrame, kappa: Float64Array, s: number): number {
  const L = frame.lengthM
  const sw = ((s % L) + L) % L
  const i = segmentAt(frame, sw)
  const j = (i + 1) % frame.points.length
  const seg = (frame.s[j] - frame.s[i] + L) % L
  const t = seg > 0 ? (sw - frame.s[i]) / seg : 0
  return kappa[i] * (1 - t) + kappa[j] * t
}

/** Une intervalos circulares; descarta os menores que `minLenM`. Resultado ordenado, `s0` em [0, L). */
export function mergeRanges(ranges: SRange[], L: number, minLenM = 0): SRange[] {
  if (!ranges.length) return []
  const norm: SRange[] = ranges.map(([a, b]) => {
    const len = Math.min(b - a, L)
    const a0 = ((a % L) + L) % L
    return [a0, a0 + len]
  })
  norm.sort((p, q) => p[0] - q[0])
  const out: SRange[] = []
  for (const r of norm) {
    const last = out[out.length - 1]
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1])
    else out.push([r[0], r[1]])
  }
  // O último pode dar a volta e alcançar o primeiro.
  while (out.length > 1 && out[out.length - 1][1] >= out[0][0] + L) {
    const last = out.pop() as SRange
    out[0] = [last[0], Math.max(last[1], out[0][1] + L)]
    out.sort((p, q) => p[0] - q[0])
  }
  for (const r of out) if (r[1] - r[0] >= L) r[1] = r[0] + L
  return out.filter(([a, b]) => b - a >= minLenM)
}

/**
 * Trechos onde `pred(kappa)` vale, com a curvatura interpolada entre os
 * pontos (numa pista grossa uma curva pode ter um ponto só), alargados
 * `padM` de cada lado.
 */
export function rangesWhere(
  frame: TrackFrame,
  kappa: Float64Array,
  pred: (k: number) => boolean,
  padM: number,
  minLenM = 6,
): SRange[] {
  const n = frame.points.length
  const L = frame.lengthM
  const raw: SRange[] = []
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    const s0 = frame.s[i]
    const seg = (frame.s[j] - s0 + L) % L
    // Sub-amostra o segmento a cada ~2 m para achar onde o limiar é cruzado.
    const steps = Math.max(1, Math.ceil(seg / 2))
    let start: number | null = null
    for (let k = 0; k <= steps; k++) {
      const t = k / steps
      const on = pred(kappa[i] * (1 - t) + kappa[j] * t)
      const at = s0 + seg * t
      if (on && start === null) start = at
      if ((!on || k === steps) && start !== null) {
        raw.push([start, at])
        start = null
      }
    }
  }
  return mergeRanges(
    raw.map(([a, b]) => [a - padM, b + padM]),
    L,
    minLenM,
  )
}

/**
 * Ápices: máximos locais de |curvatura| acima de `threshold`, com supressão
 * dos vizinhos a menos de `separationM`. Devolve `s` de cada ápice.
 */
export function cornerPeaks(frame: TrackFrame, kappa: Float64Array, threshold: number, separationM: number): number[] {
  const L = frame.lengthM
  const step = 2
  const m = Math.max(3, Math.ceil(L / step))
  const k = new Float64Array(m)
  for (let i = 0; i < m; i++) k[i] = Math.abs(kappaAt(frame, kappa, (i * L) / m))
  const candidates: number[] = []
  for (let i = 0; i < m; i++) {
    const a = k[(i - 1 + m) % m]
    const b = k[(i + 1) % m]
    if (k[i] > threshold && k[i] >= a && k[i] > b) candidates.push(i)
  }
  candidates.sort((p, q) => k[q] - k[p])
  const kept: number[] = []
  const gap = (p: number, q: number) => {
    const d = Math.abs(p - q) * (L / m)
    return Math.min(d, L - d)
  }
  for (const c of candidates) if (kept.every((o) => gap(o, c) >= separationM)) kept.push(c)
  return kept.map((i) => (i * L) / m).sort((p, q) => p - q)
}
