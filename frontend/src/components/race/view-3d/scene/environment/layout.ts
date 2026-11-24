/**
 * Onde fica cada coisa do cenário, derivado só dos waypoints servidos.
 *
 * Função pura (sem WebGL, sem DOM), testada em `tests/view-3d.test.mjs`.
 * Mesma pista + mesma largura + mesma via dos boxes = mesmo cenário: a
 * aleatoriedade vem de um gerador com semente tirada dos próprios pontos.
 *
 * Regras (limiares do protótipo de cenário, em metros):
 * - zebras e caixas de brita onde |curvatura| > 1/140 1/m, alargadas 40 m;
 *   a brita fica só do lado de fora da curva;
 * - pórtico em s = 0 atravessando a pista (e a via dos boxes, se ela estiver
 *   colada à pista ali);
 * - boxes ao longo da via dos boxes, do lado oposto à pista, de frente para ela;
 * - arquibancadas do outro lado da reta principal e por fora dos ápices
 *   (|curvatura| > 1/70 1/m);
 * - árvores a pelo menos 55 m da linha central, mais raras depois de 140 m.
 *
 * Toda colocação passa por uma checagem de folga contra a faixa de asfalto,
 * a via dos boxes e o que já foi colocado; o que não cabe é descartado.
 */
import { Matrix4 } from "three"

import { sampleAt } from "../track-frame.ts"
import type { TrackFrame } from "../track-frame.ts"
import { cornerPeaks, kappaAt, rangesWhere, robustCurvature } from "./curvature.ts"
import type { SRange } from "./curvature.ts"

export const KERB_KAPPA = 1 / 140
export const KERB_PAD_M = 40
export const PEAK_KAPPA = 1 / 70
export const PEAK_SEPARATION_M = 80
/** |curvatura| abaixo disto conta como reta (arquibancadas da reta principal). */
export const STRAIGHT_KAPPA = 1 / 250
export const TREE_MIN_M = 55
export const TREE_THIN_M = 140
export const TREE_MAX = 2600
/** Fração das árvores desenhada na qualidade baixa. */
export const TREE_LOW_FRACTION = 0.35

export type PropKind =
  | "treeLarge"
  | "treeSmall"
  | "grandStandCovered"
  | "grandStandCoveredRound"
  | "pitsGarage"
  | "pitsOffice"
  | "overheadLights"
  | "billboard"
  | "lightPostLarge"
  | "tentLong"
  | "bannerTowerRed"
  | "flagCheckers"

export const PROP_KINDS: PropKind[] = [
  "treeLarge",
  "treeSmall",
  "grandStandCovered",
  "grandStandCoveredRound",
  "pitsGarage",
  "pitsOffice",
  "overheadLights",
  "billboard",
  "lightPostLarge",
  "tentLong",
  "bannerTowerRed",
  "flagCheckers",
]

export type ModelInfo = {
  /** Caixa do modelo no próprio espaço (Kenney Racing Kit 2.0), x/y/z. */
  min: [number, number, number]
  max: [number, number, number]
  /** Para onde o modelo "olha" (x, z locais): esse lado vira para a pista. */
  front: [number, number]
  /** Pés do pórtico, intervalos em x local: só eles tocam o chão. */
  legs?: [number, number][]
}

/**
 * Caixas medidas nos GLBs (o teste confere contra os arquivos). Os modelos do
 * kit não são centrados na origem; `propMatrix` recentra a pegada.
 */
export const MODELS: Record<PropKind, ModelInfo> = {
  treeLarge: { min: [-0.53, -0.01, -0.86], max: [-0.17, 1.5, -0.44], front: [0, 1] },
  treeSmall: { min: [-0.48, -0.01, -0.8], max: [-0.22, 1.06, -0.5], front: [0, 1] },
  // Assentos sobem para -z; o lado aberto (e a cobertura) fica em +z.
  grandStandCovered: { min: [-0.35, -0.01, -1.65], max: [0.65, 1.18, -0.63], front: [0, 1] },
  // Quarto de círculo; o lado côncavo olha para o canto (-x, +z).
  grandStandCoveredRound: { min: [-0.35, -0.01, -1.65], max: [1.29, 1.18, -0.01], front: [-Math.SQRT1_2, Math.SQRT1_2] },
  pitsGarage: { min: [-0.35, -0.01, -1.65], max: [0.65, 0.69, -0.56], front: [0, 1] },
  pitsOffice: { min: [-0.35, -0.01, -1.65], max: [0.65, 0.5, -0.61], front: [0, 1] },
  overheadLights: {
    min: [-0.48, -0.01, -0.65],
    max: [0.78, 0.68, -0.46],
    front: [0, 1],
    legs: [
      [-0.48, -0.35],
      [0.65, 0.78],
    ],
  },
  billboard: { min: [-0.41, -0.01, -1.09], max: [0.59, 0.99, -0.61], front: [0, 1] },
  lightPostLarge: { min: [-0.54, -0.01, -0.67], max: [-0.16, 0.79, -0.57], front: [0, 1] },
  tentLong: { min: [-0.35, -0.01, -1.65], max: [1.65, 0.69, -0.65], front: [0, 1] },
  bannerTowerRed: { min: [-0.35, -0.01, -1.04], max: [0.04, 1.24, -0.65], front: [0, 1] },
  flagCheckers: { min: [-0.35, -0.01, -0.69], max: [-0.15, 1.24, -0.65], front: [0, 1] },
}

/** Escala por categoria (protótipo): metros por unidade do modelo. */
export const PROP_SCALE = {
  treeMin: 6,
  treeMax: 11,
  grandStand: 14,
  garage: 9,
  tent: 8,
  bannerTower: 6,
  billboard: 7,
  lightPost: 9,
  flag: 5,
} as const

export type Placement = {
  x: number
  z: number
  /** Rotação em torno de +y (radianos, convenção do Three.js). */
  yaw: number
  scale: number
  /** Esticamento extra em x local (só o pórtico, para vencer a largura). */
  stretchX?: number
}

export type Layout = {
  kappa: Float64Array
  kerbs: SRange[]
  /** Brita do lado esquerdo (d < 0): por fora das curvas à direita. */
  sandLeft: SRange[]
  sandRight: SRange[]
  peaks: number[]
  /** Lado da via dos boxes em s = 0: +1 à direita da pista, -1 à esquerda. */
  pitSide: 1 | -1
  mainStraight: SRange
  props: Record<PropKind, Placement[]>
  seed: number
}

export type PitInput = { points: { x: number; z: number }[]; widthM: number }

// ---------------------------------------------------------------------------
// Aleatoriedade com semente

/** mulberry32: pequeno, rápido e igual em qualquer navegador. */
export function rng(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** FNV-1a dos pontos arredondados ao decímetro e da largura. */
export function seedFor(points: { x: number; z: number }[], widthM: number): number {
  let h = 0x811c9dc5
  const mix = (v: number) => {
    h ^= v & 0xffff
    h = Math.imul(h, 0x01000193)
    h ^= (v >>> 16) & 0xffff
    h = Math.imul(h, 0x01000193)
  }
  mix(points.length)
  mix(Math.round(widthM * 10))
  for (const p of points) {
    mix(Math.round(p.x * 10))
    mix(Math.round(p.z * 10))
  }
  return h >>> 0
}

// ---------------------------------------------------------------------------
// Geometria 2D (x, z)

type Pt = [number, number]
type Quad = Pt[]

function distPointSeg(px: number, pz: number, ax: number, az: number, bx: number, bz: number): number {
  const abx = bx - ax
  const abz = bz - az
  const len2 = abx * abx + abz * abz
  const t = len2 > 0 ? Math.min(1, Math.max(0, ((px - ax) * abx + (pz - az) * abz) / len2)) : 0
  return Math.hypot(ax + abx * t - px, az + abz * t - pz)
}

function cross(ox: number, oz: number, ax: number, az: number, bx: number, bz: number): number {
  return (ax - ox) * (bz - oz) - (az - oz) * (bx - ox)
}

function segsCross(a: Pt, b: Pt, c: Pt, d: Pt): boolean {
  const d1 = cross(c[0], c[1], d[0], d[1], a[0], a[1])
  const d2 = cross(c[0], c[1], d[0], d[1], b[0], b[1])
  const d3 = cross(a[0], a[1], b[0], b[1], c[0], c[1])
  const d4 = cross(a[0], a[1], b[0], b[1], d[0], d[1])
  return d1 * d2 < 0 && d3 * d4 < 0
}

function distSegSeg(a: Pt, b: Pt, c: Pt, d: Pt): number {
  if (segsCross(a, b, c, d)) return 0
  return Math.min(
    distPointSeg(a[0], a[1], c[0], c[1], d[0], d[1]),
    distPointSeg(b[0], b[1], c[0], c[1], d[0], d[1]),
    distPointSeg(c[0], c[1], a[0], a[1], b[0], b[1]),
    distPointSeg(d[0], d[1], a[0], a[1], b[0], b[1]),
  )
}

function insideConvex(poly: Quad, x: number, z: number): boolean {
  let sign = 0
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i]
    const b = poly[(i + 1) % poly.length]
    const c = cross(a[0], a[1], b[0], b[1], x, z)
    if (c === 0) continue
    const s = c > 0 ? 1 : -1
    if (sign === 0) sign = s
    else if (s !== sign) return false
  }
  return true
}

/** Distância entre um quadrilátero convexo e um segmento (0 se se tocam). */
function distQuadSeg(q: Quad, a: Pt, b: Pt): number {
  if (insideConvex(q, a[0], a[1]) || insideConvex(q, b[0], b[1])) return 0
  let best = Infinity
  for (let i = 0; i < q.length; i++) best = Math.min(best, distSegSeg(q[i], q[(i + 1) % q.length], a, b))
  return best
}

function distQuadQuad(p: Quad, q: Quad): number {
  for (const v of p) if (insideConvex(q, v[0], v[1])) return 0
  for (const v of q) if (insideConvex(p, v[0], v[1])) return 0
  let best = Infinity
  for (let i = 0; i < p.length; i++)
    for (let j = 0; j < q.length; j++) best = Math.min(best, distSegSeg(p[i], p[(i + 1) % p.length], q[j], q[(j + 1) % q.length]))
  return best
}

type Box = { minX: number; maxX: number; minZ: number; maxZ: number }
const quadBox = (q: Quad): Box => ({
  minX: Math.min(...q.map((p) => p[0])),
  maxX: Math.max(...q.map((p) => p[0])),
  minZ: Math.min(...q.map((p) => p[1])),
  maxZ: Math.max(...q.map((p) => p[1])),
})

/** Grade espacial genérica: itens indexados pela caixa envolvente. */
class Grid<T> {
  private cells = new Map<number, T[]>()
  private readonly cell: number
  constructor(cell: number) {
    this.cell = cell
  }
  private key(i: number, j: number) {
    return (i + 32768) * 65536 + (j + 32768)
  }
  add(box: Box, item: T): void {
    const c = this.cell
    for (let i = Math.floor(box.minX / c); i <= Math.floor(box.maxX / c); i++)
      for (let j = Math.floor(box.minZ / c); j <= Math.floor(box.maxZ / c); j++) {
        const k = this.key(i, j)
        const list = this.cells.get(k)
        if (list) list.push(item)
        else this.cells.set(k, [item])
      }
  }
  query(box: Box, visit: (item: T) => boolean | void): void {
    const c = this.cell
    const seen = new Set<T>()
    for (let i = Math.floor(box.minX / c); i <= Math.floor(box.maxX / c); i++)
      for (let j = Math.floor(box.minZ / c); j <= Math.floor(box.maxZ / c); j++) {
        const list = this.cells.get(this.key(i, j))
        if (!list) continue
        for (const it of list) {
          if (seen.has(it)) continue
          seen.add(it)
          if (visit(it) === false) return
        }
      }
  }
}

type Seg = { a: Pt; b: Pt; s0: number }

/** Polilinha (pista fechada ou via aberta) com consultas de distância. */
export class Band {
  readonly halfWidth: number
  private grid = new Grid<Seg>(40)
  readonly segs: Seg[] = []
  constructor(points: { x: number; z: number }[], halfWidth: number, closed: boolean) {
    this.halfWidth = halfWidth
    const n = points.length
    let s = 0
    for (let i = 0; i < (closed ? n : n - 1); i++) {
      const p = points[i]
      const q = points[(i + 1) % n]
      const seg: Seg = { a: [p.x, p.z], b: [q.x, q.z], s0: s }
      s += Math.hypot(q.x - p.x, q.z - p.z)
      this.segs.push(seg)
      this.grid.add(
        { minX: Math.min(p.x, q.x), maxX: Math.max(p.x, q.x), minZ: Math.min(p.z, q.z), maxZ: Math.max(p.z, q.z) },
        seg,
      )
    }
  }
  /** Distância da linha central até (x, z), ou Infinity se passar de `maxR`. */
  distance(x: number, z: number, maxR: number): number {
    let best = Infinity
    this.grid.query({ minX: x - maxR, maxX: x + maxR, minZ: z - maxR, maxZ: z + maxR }, (seg) => {
      best = Math.min(best, distPointSeg(x, z, seg.a[0], seg.a[1], seg.b[0], seg.b[1]))
    })
    return best <= maxR ? best : Infinity
  }
  /** Distância de lado (+ à direita do sentido da polilinha) até o segmento mais próximo. */
  signedOffset(x: number, z: number, maxR = 400): number {
    let best = Infinity
    let side = 0
    this.grid.query({ minX: x - maxR, maxX: x + maxR, minZ: z - maxR, maxZ: z + maxR }, (seg) => {
      const d = distPointSeg(x, z, seg.a[0], seg.a[1], seg.b[0], seg.b[1])
      if (d < best) {
        best = d
        const tx = seg.b[0] - seg.a[0]
        const tz = seg.b[1] - seg.a[1]
        // direita = tangente x cima = (-tz, tx)
        side = (x - seg.a[0]) * -tz + (z - seg.a[1]) * tx
      }
    })
    return best === Infinity ? Infinity : Math.sign(side) * best
  }
  /** A pegada fica a pelo menos `halfWidth + margin` da linha central? */
  clear(q: Quad, margin: number): boolean {
    const r = this.halfWidth + margin
    const b = quadBox(q)
    let ok = true
    this.grid.query({ minX: b.minX - r, maxX: b.maxX + r, minZ: b.minZ - r, maxZ: b.maxZ + r }, (seg) => {
      if (distQuadSeg(q, seg.a, seg.b) < r) {
        ok = false
        return false
      }
    })
    return ok
  }
}

// ---------------------------------------------------------------------------
// Transformações dos modelos

const centreOf = (m: ModelInfo): Pt => [(m.min[0] + m.max[0]) / 2, (m.min[2] + m.max[2]) / 2]

/** Yaw que gira o lado `front` do modelo para a direção mundial (wx, wz). */
export function yawFacing(kind: PropKind, wx: number, wz: number): number {
  const f = MODELS[kind].front
  return Math.atan2(wx, wz) - Math.atan2(f[0], f[1])
}

/** Ponto local (x, z) do modelo para o mundo, igual a `propMatrix` no plano. */
function localToWorld(kind: PropKind, p: Placement, lx: number, lz: number): Pt {
  const c = centreOf(MODELS[kind])
  const x = (lx - c[0]) * p.scale * (p.stretchX ?? 1)
  const z = (lz - c[1]) * p.scale
  const cos = Math.cos(p.yaw)
  const sin = Math.sin(p.yaw)
  return [p.x + x * cos + z * sin, p.z - x * sin + z * cos]
}

/** Partes da pegada no chão (o pórtico só toca o chão nos pés). */
export function footprints(kind: PropKind, p: Placement): Quad[] {
  const m = MODELS[kind]
  const spans: [number, number][] = m.legs ?? [[m.min[0], m.max[0]]]
  return spans.map(([x0, x1]) => [
    localToWorld(kind, p, x0, m.min[2]),
    localToWorld(kind, p, x1, m.min[2]),
    localToWorld(kind, p, x1, m.max[2]),
    localToWorld(kind, p, x0, m.max[2]),
  ])
}

/**
 * Matriz de instância do modelo inteiro: recentra a pegada na origem, põe a
 * base em y = 0, escala, gira e posiciona. É a mesma para o desenho e o teste.
 */
export function propMatrix(kind: PropKind, p: Placement, out = new Matrix4()): Matrix4 {
  const m = MODELS[kind]
  const c = centreOf(m)
  const k = p.scale
  const cos = Math.cos(p.yaw)
  const sin = Math.sin(p.yaw)
  const sx = k * (p.stretchX ?? 1)
  // T(x, 0, z) * Ry(yaw) * S(sx, k, k) * T(-cx, -minY, -cz)
  return out.set(
    cos * sx, 0, sin * k, p.x + (-c[0] * cos * sx - c[1] * sin * k),
    0, k, 0, -m.min[1] * k,
    -sin * sx, 0, cos * k, p.z + (c[0] * sin * sx - c[1] * cos * k),
    0, 0, 0, 1,
  )
}

// ---------------------------------------------------------------------------
// Layout

type Placed = { quads: Quad[]; box: Box }

export function buildLayout(frame: TrackFrame, widthM: number, pit: PitInput | null): Layout {
  const L = frame.lengthM
  const half = widthM / 2
  const kappa = robustCurvature(frame)
  const kerbs = rangesWhere(frame, kappa, (k) => Math.abs(k) > KERB_KAPPA, KERB_PAD_M)
  const sandLeft = rangesWhere(frame, kappa, (k) => k > KERB_KAPPA, KERB_PAD_M)
  const sandRight = rangesWhere(frame, kappa, (k) => k < -KERB_KAPPA, KERB_PAD_M)
  const peaks = cornerPeaks(frame, kappa, PEAK_KAPPA, PEAK_SEPARATION_M)

  const track = new Band(frame.points, half, true)
  const pitBand = pit && pit.points.length >= 2 ? new Band(pit.points, pit.widthM / 2, false) : null
  const seed = seedFor(frame.points, widthM)
  const rand = rng(seed)

  const props = Object.fromEntries(PROP_KINDS.map((k) => [k, [] as Placement[]])) as Record<PropKind, Placement[]>
  const placed = new Grid<Placed>(60)

  /** Coloca se couber: folga da pista, da via dos boxes e do que já está no chão. */
  const tryPlace = (
    kind: PropKind,
    p: Placement,
    o: { track?: number; pit?: number; gap?: number; record?: boolean } = {},
  ): boolean => {
    const quads = footprints(kind, p)
    const tm = o.track ?? 2
    const pm = o.pit ?? 1.5
    const gap = o.gap ?? 1
    for (const q of quads) {
      if (!track.clear(q, tm)) return false
      if (pitBand && !pitBand.clear(q, pm)) return false
    }
    const boxes = quads.map(quadBox)
    const box: Box = {
      minX: Math.min(...boxes.map((b) => b.minX)),
      maxX: Math.max(...boxes.map((b) => b.maxX)),
      minZ: Math.min(...boxes.map((b) => b.minZ)),
      maxZ: Math.max(...boxes.map((b) => b.maxZ)),
    }
    let hit = false
    placed.query({ minX: box.minX - gap, maxX: box.maxX + gap, minZ: box.minZ - gap, maxZ: box.maxZ + gap }, (other) => {
      for (const a of quads)
        for (const b of other.quads)
          if (distQuadQuad(a, b) < gap) {
            hit = true
            return false
          }
    })
    if (hit) return false
    if (o.record !== false) placed.add(box, { quads, box })
    props[kind].push(p)
    return true
  }

  const at = (s: number, d: number) => {
    const smp = sampleAt(frame, s)
    return {
      x: smp.position.x + smp.right.x * d,
      z: smp.position.z + smp.right.z * d,
      tx: smp.tangent.x,
      tz: smp.tangent.z,
      rx: smp.right.x,
      rz: smp.right.z,
    }
  }
  /** Prop em (s, d) com a frente virada para a linha central. */
  const facingTrack = (kind: PropKind, s: number, d: number, scale: number): Placement => {
    const a = at(s, d)
    const side = Math.sign(d) || 1
    return { x: a.x, z: a.z, yaw: yawFacing(kind, -a.rx * side, -a.rz * side), scale }
  }

  // --- lado dos boxes -------------------------------------------------------
  let pitSide: 1 | -1 = 1
  if (pit && pitBand) {
    let far = 0
    for (const p of pit.points) {
      const d = track.signedOffset(p.x, p.z)
      if (Number.isFinite(d) && Math.abs(d) > Math.abs(far)) far = d
    }
    pitSide = far < 0 ? -1 : 1
  }
  const standSide = -pitSide as 1 | -1

  // --- pórtico na linha de chegada -----------------------------------------
  {
    const legs = MODELS.overheadLights.legs as [number, number][]
    const opening = legs[1][0] - legs[0][1]
    const legW = legs[0][1] - legs[0][0]
    // Vão livre: 1 m além da borda do asfalto de cada lado (escala (W + 2) / vão).
    const scale = (widthM + 2) / opening
    const near = half + 1
    let farSide = half + 1
    // Via dos boxes colada à pista em s = 0 (sem lugar para um pé entre as
    // duas): o pórtico passa por cima dela também, esticado só na largura.
    if (pit) {
      const p0 = at(0, 0)
      for (const p of pit.points) {
        const dx = p.x - p0.x
        const dz = p.z - p0.z
        if (Math.abs(dx * p0.tx + dz * p0.tz) > 30) continue
        const d = (dx * p0.rx + dz * p0.rz) * pitSide
        const inner = d - pit.widthM / 2
        if (inner < near + legW * scale + 1.5) farSide = Math.max(farSide, d + pit.widthM / 2 + 1)
      }
    }
    const span = near + farSide
    const a = at(0, ((farSide - near) / 2) * pitSide)
    tryPlace(
      "overheadLights",
      { x: a.x, z: a.z, yaw: Math.atan2(a.rx, a.rz) - Math.PI / 2, scale, stretchX: span / (opening * scale) },
      { track: 0.5, pit: 0.5, gap: 0 },
    )
  }

  // --- bandeira quadriculada junto à linha, do lado oposto aos boxes ---------
  tryPlace("flagCheckers", facingTrack("flagCheckers", 6, standSide * (half + 3), PROP_SCALE.flag), { track: 1, gap: 0.5 })

  // --- boxes ----------------------------------------------------------------
  if (pit && pitBand) {
    const pts = pit.points
    const cum = [0]
    for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].z - pts[i - 1].z))
    const total = cum[cum.length - 1]
    const pitAt = (u: number) => {
      let i = 0
      while (i < pts.length - 2 && cum[i + 1] < u) i++
      const seg = cum[i + 1] - cum[i]
      const t = seg > 0 ? Math.min(1, Math.max(0, (u - cum[i]) / seg)) : 0
      const tx = (pts[i + 1].x - pts[i].x) / (seg || 1)
      const tz = (pts[i + 1].z - pts[i].z) / (seg || 1)
      return { x: pts[i].x + (pts[i + 1].x - pts[i].x) * t, z: pts[i].z + (pts[i + 1].z - pts[i].z) * t, rx: -tz, rz: tx }
    }
    const width = (MODELS.pitsGarage.max[0] - MODELS.pitsGarage.min[0]) * PROP_SCALE.garage
    const depth = (MODELS.pitsGarage.max[2] - MODELS.pitsGarage.min[2]) * PROP_SCALE.garage
    const offset = pitBand.halfWidth + 1.5 + depth / 2
    let slot = 0
    for (let u = width; u <= total - width && props.pitsGarage.length + props.pitsOffice.length < 40; u += width + 0.3) {
      const p = pitAt(u)
      // Só onde a via já saiu do asfalto.
      if (track.distance(p.x, p.z, half + pitBand.halfWidth + 1) < half + pitBand.halfWidth + 0.5) continue
      const cands = [1, -1].map((side) => ({ side, x: p.x + p.rx * offset * side, z: p.z + p.rz * offset * side }))
      const best = cands.sort((a, b) => track.distance(b.x, b.z, 400) - track.distance(a.x, a.z, 400))[0]
      const kind: PropKind = slot % 6 === 3 ? "pitsOffice" : "pitsGarage"
      const ok = tryPlace(
        kind,
        { x: best.x, z: best.z, yaw: yawFacing(kind, -p.rx * best.side, -p.rz * best.side), scale: PROP_SCALE.garage },
        { track: 3, pit: 1, gap: 0.1 },
      )
      if (ok) slot++
    }
  }

  // --- reta principal -------------------------------------------------------
  let back = 0
  while (back < 320 && Math.abs(kappaAt(frame, kappa, -back - 5)) < STRAIGHT_KAPPA) back += 5
  let fwd = 0
  while (fwd < 260 && Math.abs(kappaAt(frame, kappa, fwd + 5)) < STRAIGHT_KAPPA) fwd += 5
  const straightStart = (((-back + 20) % L) + L) % L
  const mainStraight: SRange = [straightStart, straightStart + Math.max(0, back + fwd - 40)]
  {
    const standW = (MODELS.grandStandCovered.max[0] - MODELS.grandStandCovered.min[0]) * PROP_SCALE.grandStand
    for (let s = -back + 20 + standW / 2; s <= fwd - 20 - standW / 2; s += standW + 0.5) {
      tryPlace("grandStandCovered", facingTrack("grandStandCovered", s, standSide * (half + 16), PROP_SCALE.grandStand), {
        track: 6,
        gap: 0.2,
      })
    }
  }

  // --- ápices: arquibancada curva, tenda e torre de faixa por fora -----------
  peaks.forEach((s, n) => {
    const out = kappaAt(frame, kappa, s) > 0 ? -1 : 1
    for (const extra of [40, 55, 70]) {
      if (tryPlace("grandStandCoveredRound", facingTrack("grandStandCoveredRound", s, out * (half + extra), PROP_SCALE.grandStand), { track: 20 }))
        break
    }
    if (n % 2 === 1) {
      for (const extra of [34, 46]) {
        if (tryPlace("tentLong", facingTrack("tentLong", s - 45, out * (half + extra), PROP_SCALE.tent), { track: 20 })) break
      }
    }
    tryPlace("bannerTowerRed", facingTrack("bannerTowerRed", s + 35, out * (half + 26), PROP_SCALE.bannerTower), { track: 20 })
  })

  // --- placas e postes nas retas ---------------------------------------------
  {
    let k = 0
    for (let s = 44; s < L - 44; s += 88) {
      if (Math.abs(kappaAt(frame, kappa, s)) > KERB_KAPPA) continue
      const side = k % 2 === 0 ? -1 : 1
      const board = k % 4 < 2
      const kind: PropKind = board ? "billboard" : "lightPostLarge"
      const p = facingTrack(kind, s, side * (half + 9), board ? PROP_SCALE.billboard : PROP_SCALE.lightPost)
      tryPlace(kind, p, { track: 2, pit: 2, gap: 2 })
      k++
    }
  }

  // --- árvores ---------------------------------------------------------------
  {
    let minX = Infinity
    let maxX = -Infinity
    let minZ = Infinity
    let maxZ = -Infinity
    for (const p of frame.points) {
      minX = Math.min(minX, p.x)
      maxX = Math.max(maxX, p.x)
      minZ = Math.min(minZ, p.z)
      maxZ = Math.max(maxZ, p.z)
    }
    let count = 0
    for (let attempt = 0; attempt < TREE_MAX * 6 && count < TREE_MAX; attempt++) {
      let x: number
      let z: number
      if (rand() < 0.6) {
        const a = at(rand() * L, (rand() < 0.5 ? -1 : 1) * (TREE_MIN_M + 230 * rand() ** 2))
        x = a.x
        z = a.z
      } else {
        x = minX - 500 + rand() * (maxX - minX + 1000)
        z = minZ - 500 + rand() * (maxZ - minZ + 1000)
      }
      const large = rand() < 0.6
      const scale = PROP_SCALE.treeMin + (PROP_SCALE.treeMax - PROP_SCALE.treeMin) * rand()
      const yaw = rand() * Math.PI * 2
      const thin = rand()
      const d = track.distance(x, z, TREE_THIN_M)
      if (d < TREE_MIN_M) continue
      if (d === Infinity && thin < 0.55) continue
      const kind: PropKind = large ? "treeLarge" : "treeSmall"
      // Árvores não entram na ocupação: podem se tocar, como num bosque.
      if (tryPlace(kind, { x, z, yaw, scale }, { track: 2, pit: 4, gap: 1, record: false })) count++
    }
  }

  return { kappa, kerbs, sandLeft, sandRight, peaks, pitSide, mainStraight, props, seed }
}
