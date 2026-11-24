/**
 * Medida de suavidade do carro seguido, quadro a quadro (gancho de
 * desenvolvimento e testes).
 *
 * Para cada quadro desenhado, a velocidade aparente é o passo no chão dividido
 * pelo intervalo do quadro. Ela é comparada à mediana da vizinhança (±15
 * quadros, ~0,25 s a 60 Hz), o que ignora as mudanças reais de velocidade
 * (frenagem, retomada) e isola o tremor: `r = v / mediana`. Um movimento liso
 * dá `r` = 1 em todo quadro.
 *
 * - `spread`: desvio-padrão de `r`.
 * - `stalls`: quadros com `r` < 0,5 (o carro quase parou entre dois quadros).
 * - `jumps`: quadros com `r` > 1,5.
 * - `backwards`: quadros em que o passo vai contra a direção do carro (> 1 cm).
 *
 * Quadros com a mediana abaixo de 5 m/s (box, carro parado) ficam de fora, e
 * também os quadros logo após uma ressincronização (a câmera corta ali).
 */
export type TraceSample = {
  /** Tempo do quadro, ms. */
  wallMs: number
  /** Posição desenhada no plano do backend, m. */
  x: number
  y: number
  /** Direção desenhada, rad. */
  headingRad: number
  /** Contador de ressincronizações do relógio neste quadro. */
  resyncs: number
}

export type Smoothness = {
  /** Quadros avaliados. */
  frames: number
  spread: number
  stalls: number
  jumps: number
  backwards: number
  /** Velocidade mediana aparente, m/s. */
  medianSpeedMps: number
}

export const SMOOTHNESS = { window: 15, stall: 0.5, jump: 1.5, minSpeedMps: 5, backwardsM: 0.01 } as const

function median(values: number[]): number {
  const v = [...values].sort((a, b) => a - b)
  const n = v.length
  if (n === 0) return 0
  return n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2
}

export function smoothness(trace: TraceSample[]): Smoothness {
  // Passos: speed[i] entre trace[i-1] e trace[i], só dentro do mesmo trecho sem ressincronização.
  const speed: (number | null)[] = [null]
  let backwards = 0
  for (let i = 1; i < trace.length; i++) {
    const a = trace[i - 1]
    const b = trace[i]
    const dt = (b.wallMs - a.wallMs) / 1000
    if (!(dt > 0) || a.resyncs !== b.resyncs) {
      speed.push(null)
      continue
    }
    const dx = b.x - a.x
    const dy = b.y - a.y
    const h = a.headingRad + Math.atan2(Math.sin(b.headingRad - a.headingRad), Math.cos(b.headingRad - a.headingRad)) / 2
    if (dx * Math.cos(h) + dy * Math.sin(h) < -SMOOTHNESS.backwardsM) backwards++
    speed.push(Math.hypot(dx, dy) / dt)
  }

  const ratios: number[] = []
  const speeds: number[] = []
  for (let i = 1; i < speed.length; i++) {
    const v = speed[i]
    if (v === null) continue
    const near: number[] = []
    let complete = true
    for (let k = i - SMOOTHNESS.window; k <= i + SMOOTHNESS.window; k++) {
      const w = speed[k]
      if (w === undefined || w === null) {
        complete = false
        break
      }
      near.push(w)
    }
    if (!complete) continue
    const m = median(near)
    if (m < SMOOTHNESS.minSpeedMps) continue
    ratios.push(v / m)
    speeds.push(v)
  }

  const n = ratios.length
  const mean = n ? ratios.reduce((s, r) => s + r, 0) / n : 1
  const variance = n ? ratios.reduce((s, r) => s + (r - mean) ** 2, 0) / n : 0
  return {
    frames: n,
    spread: Math.sqrt(variance),
    stalls: ratios.filter((r) => r < SMOOTHNESS.stall).length,
    jumps: ratios.filter((r) => r > SMOOTHNESS.jump).length,
    backwards,
    medianSpeedMps: median(speeds),
  }
}
