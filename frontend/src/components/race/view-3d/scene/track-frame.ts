/**
 * Referencial da pista: `(s, d)` para o mundo.
 *
 * Portado de `viz3d/src/track/frame.ts` sem mudar a matemática. Só o tipo de
 * entrada encolheu: aqui basta a lista de pontos já no espaço do Three.js.
 *
 * Convenção de lateralidade, fixada aqui e em nenhum outro lugar (y para cima):
 *
 *     right = tangent x up        up = right x tangent
 *
 * É um referencial de *estrada*, não o de Frenet: `up` vem do "para cima" do
 * mundo, então não troca de sinal no meio de cada chicane.
 */
import { Vector3 } from "three"

const UP = new Vector3(0, 1, 0)

export interface TrackFrame {
  /** Comprimento de arco acumulado em cada ponto, metros, s[0] = 0. */
  s: Float64Array
  /** Soma dos segmentos, incluindo o que fecha a volta. */
  lengthM: number
  points: Vector3[]
  /** Tangente unitária, no sentido da corrida. */
  tangent: Vector3[]
  /** Unitário à DIREITA do sentido da corrida. */
  right: Vector3[]
  up: Vector3[]
  /** Curvatura assinada, 1/m. Positiva = curva à direita. */
  curvature: Float64Array
}

export interface Sample {
  position: Vector3
  tangent: Vector3
  right: Vector3
  up: Vector3
}

const wrapIndex = (i: number, n: number) => (i + n) % n

/** Monta o referencial. `points` é um laço aberto (último != primeiro), s = 0 no primeiro. */
export function buildFrame(points: Vector3[]): TrackFrame {
  const n = points.length

  const s = new Float64Array(n)
  let total = 0
  for (let i = 0; i < n; i++) {
    s[i] = total
    total += points[i].distanceTo(points[wrapIndex(i + 1, n)])
  }

  const tangent: Vector3[] = []
  const right: Vector3[] = []
  const up: Vector3[] = []
  for (let i = 0; i < n; i++) {
    // Diferença central: menos sensível ao ruído de amostragem.
    const t = new Vector3().subVectors(points[wrapIndex(i + 1, n)], points[wrapIndex(i - 1, n)]).normalize()
    const r = new Vector3().crossVectors(t, UP).normalize()
    tangent.push(t)
    right.push(r)
    up.push(new Vector3().crossVectors(r, t).normalize())
  }

  const curvature = new Float64Array(n)
  for (let i = 0; i < n; i++) {
    const prev = wrapIndex(i - 1, n)
    const next = wrapIndex(i + 1, n)
    const ds = (s[next] - s[prev] + total) % total
    const dt = new Vector3().subVectors(tangent[next], tangent[prev])
    curvature[i] = ds > 0 ? dt.dot(right[i]) / ds : 0
  }

  return { s, lengthM: total, points, tangent, right, up, curvature }
}

/** Embrulha um comprimento de arco em [0, lengthM). */
export function wrapS(frame: TrackFrame, s: number): number {
  const L = frame.lengthM
  return ((s % L) + L) % L
}

/** Índice do ponto em ou antes de `s` (já embrulhado). Busca binária: o espaçamento não é uniforme. */
function segmentIndex(frame: TrackFrame, s: number): number {
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

/** Avalia a linha da pista em `s`, interpolando linearmente entre os pontos servidos. */
export function sampleAt(frame: TrackFrame, s: number, out?: Sample): Sample {
  const n = frame.points.length
  const sw = wrapS(frame, s)
  const i = segmentIndex(frame, sw)
  const j = wrapIndex(i + 1, n)
  const segLen = (frame.s[j] - frame.s[i] + frame.lengthM) % frame.lengthM
  const t = segLen > 0 ? (sw - frame.s[i]) / segLen : 0

  const target: Sample = out ?? {
    position: new Vector3(),
    tangent: new Vector3(),
    right: new Vector3(),
    up: new Vector3(),
  }
  target.position.lerpVectors(frame.points[i], frame.points[j], t)
  target.tangent.lerpVectors(frame.tangent[i], frame.tangent[j], t).normalize()
  target.right.crossVectors(target.tangent, UP).normalize()
  target.up.crossVectors(target.right, target.tangent).normalize()
  return target
}

const scratch: Sample = {
  position: new Vector3(),
  tangent: new Vector3(),
  right: new Vector3(),
  up: new Vector3(),
}

/** `(s, d)` para o mundo. `d` positivo à direita; `h` levanta o ponto da superfície. */
export function toWorld(frame: TrackFrame, s: number, d = 0, h = 0, out = new Vector3()): Vector3 {
  const sample = sampleAt(frame, s, scratch)
  return out.copy(sample.position).addScaledVector(sample.right, d).addScaledVector(sample.up, h)
}

/** Curvatura assinada em `s`. */
export function curvatureAt(frame: TrackFrame, s: number): number {
  const sw = wrapS(frame, s)
  const i = segmentIndex(frame, sw)
  const j = wrapIndex(i + 1, frame.points.length)
  const segLen = (frame.s[j] - frame.s[i] + frame.lengthM) % frame.lengthM
  const t = segLen > 0 ? (sw - frame.s[i]) / segLen : 0
  return frame.curvature[i] * (1 - t) + frame.curvature[j] * t
}

/**
 * `s` do ponto da linha mais próximo de `(x, z)`. Só para a câmera quando o
 * backend não envia `progress_m` nem `s_m`; carros são posicionados pela pose.
 */
export function nearestS(frame: TrackFrame, x: number, z: number): number {
  const n = frame.points.length
  let best = Infinity
  let bestS = 0
  for (let i = 0; i < n; i++) {
    const a = frame.points[i]
    const b = frame.points[wrapIndex(i + 1, n)]
    const abx = b.x - a.x
    const abz = b.z - a.z
    const len2 = abx * abx + abz * abz
    const t = len2 > 0 ? Math.min(1, Math.max(0, ((x - a.x) * abx + (z - a.z) * abz) / len2)) : 0
    const px = a.x + abx * t - x
    const pz = a.z + abz * t - z
    const dist = px * px + pz * pz
    if (dist < best) {
      best = dist
      bestS = frame.s[i] + Math.sqrt(len2) * t
    }
  }
  return wrapS(frame, bestS)
}
