/**
 * Tremor de um ângulo ao longo dos quadros (gancho de desenvolvimento e
 * testes): usado na direção da câmera de perseguição e na posição do carro
 * seguido na tela.
 *
 * Para cada quadro, a taxa é a variação do ângulo pelo intervalo do quadro
 * (graus/s, pelo arco mais curto). Ela é comparada à média das taxas numa
 * janela centrada de ±`windowS` (tempo, não quadros, para não depender da
 * taxa de quadros), o que ignora a rotação real numa curva e isola o tremor.
 * `jitterDegS` é a raiz da média dos quadrados da diferença. Uma rotação lisa
 * (taxa constante ou variando devagar) dá ~0.
 *
 * Quadros cuja janela passa por uma quebra (`key` diferente: corte de câmera,
 * ressincronização, outra passagem pelo trecho) ficam de fora.
 */
export type AngleSample = {
  /** Tempo do quadro, ms. */
  wallMs: number
  /** Ângulo, rad. */
  rad: number
  /** Trecho contínuo; muda num corte. */
  key: number
}

export type AngleJitter = {
  /** Quadros avaliados. */
  frames: number
  /** RMS da taxa menos a média local, graus/s. */
  jitterDegS: number
  /** Maior |taxa - média local|, graus/s. */
  maxDegS: number
  /** RMS da própria taxa, graus/s (quanto o ângulo gira, para escala). */
  rateRmsDegS: number
}

export const ANGLE_JITTER = { windowS: 0.25 } as const

const DEG = 180 / Math.PI

export function angleJitter(samples: AngleSample[], windowS: number = ANGLE_JITTER.windowS): AngleJitter {
  // rate[i]: entre samples[i-1] e samples[i], no instante médio dos dois.
  const rates: { t: number; v: number; key: number }[] = []
  for (let i = 1; i < samples.length; i++) {
    const a = samples[i - 1]
    const b = samples[i]
    const dt = (b.wallMs - a.wallMs) / 1000
    if (!(dt > 0) || a.key !== b.key) continue
    const d = Math.atan2(Math.sin(b.rad - a.rad), Math.cos(b.rad - a.rad))
    rates.push({ t: (a.wallMs + b.wallMs) / 2000, v: (d / dt) * DEG, key: b.key })
  }

  let sq = 0
  let rateSq = 0
  let max = 0
  let n = 0
  // Janela deslizante [lo, hi] em tempo, com soma corrente.
  let lo = 0
  let hi = 0
  let sum = 0
  for (let i = 0; i < rates.length; i++) {
    const r = rates[i]
    while (hi < rates.length && rates[hi].t <= r.t + windowS) sum += rates[hi++].v
    while (rates[lo].t < r.t - windowS) sum -= rates[lo++].v
    // Janela inteira dentro do mesmo trecho e com dados nas duas pontas.
    const first = rates[lo]
    const last = rates[hi - 1]
    if (first.key !== r.key || last.key !== r.key) continue
    if (lo === 0 || hi === rates.length) continue
    if (rates[lo - 1].key !== r.key || rates[hi].key !== r.key) continue
    const mean = sum / (hi - lo)
    const e = r.v - mean
    sq += e * e
    rateSq += r.v * r.v
    max = Math.max(max, Math.abs(e))
    n++
  }
  return {
    frames: n,
    jitterDegS: n ? Math.sqrt(sq / n) : 0,
    maxDegS: max,
    rateRmsDegS: n ? Math.sqrt(rateSq / n) : 0,
  }
}

/** Direção horizontal de `from` para `to` no plano (x, z) do three, rad. */
export function bearing(fromX: number, fromZ: number, toX: number, toZ: number): number {
  return Math.atan2(toX - fromX, toZ - fromZ)
}
