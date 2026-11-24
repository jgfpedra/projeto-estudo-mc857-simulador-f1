/**
 * Faixas do chão geradas a partir da linha servida: asfalto, linhas brancas,
 * zebras, brita, gramado aparado e a via dos boxes.
 *
 * Uma faixa é `[d0, d1]` de deslocamento lateral (positivo à direita) ao longo
 * de trechos `[s0, s1]` de arco. Entre dois pontos servidos a posição e o vetor
 * lateral são interpolados linearmente (o vetor *sem* normalizar): assim a
 * borda de uma faixa em `d = W/2` coincide exatamente com a borda da pista de
 * `buildRibbonGeometry`, também numa pista grossa do OpenF1.
 *
 * Alturas (y) e `polygonOffset`: ver `LAYERS`. Nada fica coplanar.
 */
import { BufferAttribute, BufferGeometry } from "three"

import type { TrackFrame } from "../track-frame.ts"
import type { SRange } from "./curvature.ts"

/**
 * Camadas, de baixo para cima. `y` em metros; `offset` vai para
 * `polygonOffsetFactor/Units` (negativo = puxado para a câmera), o que segura
 * a ordem também na visão geral, quando 1 cm de altura vira menos de um
 * degrau do depth buffer.
 */
export const LAYERS = {
  ground: { y: -0.12, offset: 4 },
  verge: { y: -0.08, offset: 3 },
  sand: { y: -0.05, offset: 2 },
  asphalt: { y: 0, offset: 0 },
  lines: { y: 0.012, offset: -2 },
  kerb: { y: 0.02, offset: -2 },
  pit: { y: 0.03, offset: -1 },
  pitLines: { y: 0.04, offset: -3 },
} as const

const wrapI = (i: number, n: number) => ((i % n) + n) % n

/** Posição e vetor lateral (não normalizado) em `s`, interpolados entre os pontos. */
function lateralAt(frame: TrackFrame, s: number, out: number[]): void {
  const n = frame.points.length
  const L = frame.lengthM
  const sw = ((s % L) + L) % L
  let lo = 0
  let hi = n - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (frame.s[mid] <= sw) lo = mid
    else hi = mid - 1
  }
  const j = (lo + 1) % n
  const seg = (frame.s[j] - frame.s[lo] + L) % L
  const t = seg > 0 ? (sw - frame.s[lo]) / seg : 0
  const a = frame.points[lo]
  const b = frame.points[j]
  const ra = frame.right[lo]
  const rb = frame.right[j]
  out[0] = a.x + (b.x - a.x) * t
  out[1] = a.z + (b.z - a.z) * t
  out[2] = ra.x + (rb.x - ra.x) * t
  out[3] = ra.z + (rb.z - ra.z) * t
}

/** Valores de `s` de um trecho: as pontas mais todo ponto servido no meio. */
function stations(frame: TrackFrame, [s0, s1]: SRange): number[] {
  const n = frame.points.length
  const L = frame.lengthM
  const out = [s0]
  const lap0 = Math.floor(s0 / L)
  for (let lap = lap0; lap * L < s1; lap++) {
    for (let i = 0; i < n; i++) {
      const s = frame.s[i] + lap * L
      if (s > s0 + 1e-6 && s < s1 - 1e-6) out.push(s)
    }
  }
  out.push(s1)
  return out
}

export type BandOptions = {
  y: number
  /** Metros por repetição da textura ao longo da pista e na lateral. */
  alongM?: number
  acrossM?: number
}

/**
 * Faixa `[d0, d1]` (d0 < d1) sobre os trechos `ranges`. Use `[[0, L]]` para a
 * volta inteira: o último anel coincide com o primeiro.
 */
export function bandGeometry(frame: TrackFrame, d0: number, d1: number, ranges: SRange[], o: BandOptions): BufferGeometry {
  const pos: number[] = []
  const uv: number[] = []
  const idx: number[] = []
  const along = o.alongM ?? 10
  const across = o.acrossM ?? d1 - d0
  const tmp = [0, 0, 0, 0]
  for (const r of ranges) {
    const base = pos.length / 3
    const st = stations(frame, r)
    st.forEach((s, k) => {
      lateralAt(frame, s, tmp)
      for (const d of [d0, d1]) {
        pos.push(tmp[0] + tmp[2] * d, o.y, tmp[1] + tmp[3] * d)
        uv.push((d - d0) / across, (s - r[0]) / along)
      }
      if (k > 0) {
        const a = base + 2 * (k - 1)
        // Anti-horário visto de cima (mesma ordem de buildRibbonGeometry).
        idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2)
      }
    })
  }
  return finish(pos, uv, idx)
}

function finish(pos: number[], uv: number[], idx: number[]): BufferGeometry {
  const g = new BufferGeometry()
  const normals = new Float32Array(pos.length)
  for (let i = 1; i < normals.length; i += 3) normals[i] = 1
  g.setAttribute("position", new BufferAttribute(new Float32Array(pos), 3))
  g.setAttribute("normal", new BufferAttribute(normals, 3))
  g.setAttribute("uv", new BufferAttribute(new Float32Array(uv), 2))
  g.setIndex(new BufferAttribute(new Uint32Array(idx), 1))
  g.computeBoundingSphere()
  return g
}

/** Vetores laterais de uma via aberta (diferença central, como `buildPitRibbon`). */
export function openLaterals(points: { x: number; z: number }[]): { x: number; z: number; rx: number; rz: number; u: number }[] {
  const n = points.length
  const out: { x: number; z: number; rx: number; rz: number; u: number }[] = []
  let u = 0
  for (let i = 0; i < n; i++) {
    if (i > 0) u += Math.hypot(points[i].x - points[i - 1].x, points[i].z - points[i - 1].z)
    const a = points[Math.max(0, i - 1)]
    const b = points[Math.min(n - 1, i + 1)]
    let tx = b.x - a.x
    let tz = b.z - a.z
    if (tx * tx + tz * tz < 1e-12) {
      const c = points[wrapI(Math.min(n - 1, i + 1), n)]
      tx = c.x - points[i].x
      tz = c.z - points[i].z
    }
    const len = Math.hypot(tx, tz) || 1
    // direita = tangente x cima = (-tz, tx)
    out.push({ x: points[i].x, z: points[i].z, rx: -tz / len, rz: tx / len, u })
  }
  return out
}

/**
 * Faixa `[d0, d1]` sobre uma via aberta; `visible(i)` escolhe os pontos
 * desenhados (trechos contíguos viram tiras separadas).
 */
export function openBandGeometry(
  points: { x: number; z: number }[],
  d0: number,
  d1: number,
  o: BandOptions,
  visible: (i: number) => boolean = () => true,
): BufferGeometry {
  const lat = openLaterals(points)
  const pos: number[] = []
  const uv: number[] = []
  const idx: number[] = []
  const along = o.alongM ?? 10
  const across = o.acrossM ?? d1 - d0
  let prev = -1
  for (let i = 0; i < lat.length; i++) {
    if (!visible(i)) {
      prev = -1
      continue
    }
    const p = lat[i]
    const v = pos.length / 3
    for (const d of [d0, d1]) {
      pos.push(p.x + p.rx * d, o.y, p.z + p.rz * d)
      uv.push((d - d0) / across, p.u / along)
    }
    if (prev >= 0) idx.push(prev, prev + 1, v, prev + 1, v + 1, v)
    prev = v
  }
  return finish(pos, uv, idx)
}

/** Plano do gramado centrado em (cx, cz), `half` metros para cada lado. */
export function groundGeometry(cx: number, cz: number, half: number, tileM: number): BufferGeometry {
  const pos = [cx - half, LAYERS.ground.y, cz - half, cx + half, LAYERS.ground.y, cz - half, cx + half, LAYERS.ground.y, cz + half, cx - half, LAYERS.ground.y, cz + half]
  const k = (2 * half) / tileM
  const uv = [0, 0, k, 0, k, k, 0, k]
  // Anti-horário visto de cima (+y): (-,-) -> (-,+) -> (+,+).
  return finish(pos, uv, [0, 3, 2, 0, 2, 1])
}
