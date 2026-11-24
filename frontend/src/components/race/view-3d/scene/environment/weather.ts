/**
 * Clima da simulação -> parâmetros da cena (funções puras, testadas em
 * `tests/view-3d.test.mjs`).
 *
 * O clima do frame (`Frame.weather`: `kind` DRY/CLOUDY/DAMP/WET em qualquer
 * caixa, `rainfall` em mm/h, `trackTemp` em °C) vira três números entre 0 e 1:
 *
 * - `cloud`: céu encoberto (CLOUDY, DAMP e WET);
 * - `wet`: asfalto molhado (DAMP pela temperatura da pista, WET inteiro);
 * - `rain`: intensidade da chuva, pelo `rainfall` (0,5 mm/h = chuva fraca do
 *   backend, 2,5 = chuva, 8 = chuva forte).
 *
 * Esses três números são misturados ao longo de `WEATHER.blendS` (~5 s,
 * `WeatherBlend`) e só então viram cores, intensidades e a neblina
 * (`weatherParams`, `fogRange`): como tudo é contínuo neles, a cena nunca salta.
 * Seco (ou sem clima, ou um `kind` desconhecido) dá exatamente a cena de antes.
 */
import type { Weather } from "@/types/race"
import type { Quality } from "./quality"

export type WeatherLook = { cloud: number; wet: number; rain: number }

export const DRY_LOOK: WeatherLook = { cloud: 0, wet: 0, rain: 0 }

export const WEATHER = {
  /** Duração da mistura entre dois climas, s. */
  blendS: 5,
  /** `rain = 1 - exp(-rainfall / rainScaleMmH)`: 0,5 mm/h -> 0,15; 2,5 -> 0,57; 8 -> 0,93. */
  rainScaleMmH: 3,
  /** WET sem `rainfall` (o parser põe 0 quando falta): a chuva padrão do backend. */
  wetDefaultMmH: 2.5,
  /** Riscos de chuva com `rain` = 1, por qualidade. Sem cenário não há clima. */
  streaks: { high: 9000, low: 1500, off: 0 } as Record<Quality, number>,
} as const

const clamp01 = (v: number) => Math.min(1, Math.max(0, v))
const lerp = (a: number, b: number, k: number) => a + (b - a) * k

/** Intensidade da chuva (0..1) pelo `rainfall` em mm/h. */
export function rainLevel(mmH: number): number {
  return mmH > 0 && Number.isFinite(mmH) ? 1 - Math.exp(-mmH / WEATHER.rainScaleMmH) : 0
}

/** Pista úmida (DAMP) seca mais rápido quente: 0,7 até 24 °C, 0,4 a partir de 40 °C. */
export function dampWetness(trackTempC: number): number {
  return lerp(0.7, 0.4, clamp01((trackTempC - 24) / 16))
}

/** O alvo da cena para o clima do frame. */
export function weatherLook(w: Weather | null | undefined): WeatherLook {
  const kind = typeof w?.kind === "string" ? w.kind.trim().toUpperCase() : ""
  const mm = w && Number.isFinite(w.rainfall) ? w.rainfall : 0
  switch (kind) {
    case "CLOUDY":
      return { cloud: 1, wet: 0, rain: 0 }
    case "DAMP":
      return { cloud: 1, wet: dampWetness(w?.trackTemp ?? 24), rain: rainLevel(mm) }
    case "WET":
      return { cloud: 1, wet: 1, rain: rainLevel(mm > 0 ? mm : WEATHER.wetDefaultMmH) }
    default:
      return { ...DRY_LOOK }
  }
}

export function lerpLook(a: WeatherLook, b: WeatherLook, k: number): WeatherLook {
  return { cloud: lerp(a.cloud, b.cloud, k), wet: lerp(a.wet, b.wet, k), rain: lerp(a.rain, b.rain, k) }
}

const sameLook = (a: WeatherLook, b: WeatherLook) =>
  Math.abs(a.cloud - b.cloud) < 1e-9 && Math.abs(a.wet - b.wet) < 1e-9 && Math.abs(a.rain - b.rain) < 1e-9

const smoothstep = (k: number) => k * k * (3 - 2 * k)

/**
 * Mistura no tempo. O primeiro alvo é aplicado na hora (a cena abre no clima
 * atual); cada mudança depois parte do valor do instante e chega ao alvo em
 * `blendS` segundos, por uma `smoothstep` (sem salto no valor nem na taxa).
 * Um alvo novo no meio de uma mistura recomeça dali, sem salto.
 */
export class WeatherBlend {
  private from: WeatherLook = { ...DRY_LOOK }
  private to: WeatherLook = { ...DRY_LOOK }
  private t0 = 0
  private started = false
  current: WeatherLook = { ...DRY_LOOK }
  private readonly blendMs: number

  constructor(blendMs: number = WEATHER.blendS * 1000) {
    this.blendMs = blendMs
  }

  update(target: WeatherLook, nowMs: number): WeatherLook {
    if (!this.started) {
      this.started = true
      this.from = { ...target }
      this.to = { ...target }
      this.current = { ...target }
      // Nada a misturar: a mistura "terminou".
      this.t0 = nowMs - this.blendMs
      return this.current
    }
    if (!sameLook(target, this.to)) {
      this.from = { ...this.current }
      this.to = { ...target }
      this.t0 = nowMs
    }
    this.current = lerpLook(this.from, this.to, smoothstep(this.progress(nowMs)))
    return this.current
  }

  /** 0 no início da mistura em curso, 1 quando ela terminou (ou se não houve mudança). */
  progress(nowMs: number): number {
    return this.blendMs > 0 ? clamp01((nowMs - this.t0) / this.blendMs) : 1
  }

  get target(): WeatherLook {
    return this.to
  }
}

// --- parâmetros da cena -------------------------------------------------------

export type RGB = [number, number, number]

function hex(h: string): RGB {
  const n = parseInt(h.slice(1), 16)
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]
}
const mix = (a: RGB, b: RGB, k: number): RGB => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)]

/** Valores de hoje (seco) e dos extremos. Cores em sRGB 0..1, exceto o `overcast` (linear, do shader do céu). */
export const LOOK = {
  dry: {
    turbidity: 3,
    rayleigh: 1.2,
    mie: 0.004,
    sun: 2.4,
    sunColor: hex("#fff3e0"),
    hemi: 0.9,
    hemiSky: hex("#cfe3ff"),
    hemiGround: hex("#4d6b3d"),
    fog: hex("#b9cfe0"),
    asphaltRoughness: 0.92,
  },
  cloudy: {
    turbidity: 10,
    rayleigh: 0.4,
    mie: 0.02,
    sun: 0.9,
    sunColor: hex("#eef1f4"),
    hemi: 1.05,
    hemiSky: hex("#b3bdc8"),
    hemiGround: hex("#3d4a44"),
    fog: hex("#a3acb5"),
    /** Quanto do céu é trocado pelo cinza (o resto é o `Sky` com turbidez alta). */
    overcast: 0.85,
    overcastColor: [0.5, 0.53, 0.57] as RGB,
  },
  rain: {
    /** Multiplicadores com `rain` = 1. */
    sun: 0.6,
    hemi: 0.75,
    fog: hex("#7c858e"),
    overcast: 0.95,
    overcastColor: [0.24, 0.26, 0.29] as RGB,
  },
  wet: {
    /** Asfalto e via dos boxes multiplicados por isto com `wet` = 1; rugosidade do asfalto molhado. */
    shade: 0.58,
    asphaltRoughness: 0.55,
  },
} as const

export type WeatherParams = {
  turbidity: number
  rayleigh: number
  mie: number
  /** Fração do céu trocada pelo cinza encoberto. */
  overcast: number
  overcastColor: RGB
  sunIntensity: number
  sunColor: RGB
  hemiIntensity: number
  hemiSky: RGB
  hemiGround: RGB
  fogColor: RGB
  /** Multiplica a cor do asfalto e da via dos boxes (1 = seco). */
  asphaltShade: number
  asphaltRoughness: number
  rain: number
}

export function weatherParams(look: WeatherLook): WeatherParams {
  const { cloud, wet, rain } = look
  const d = LOOK.dry
  const c = LOOK.cloudy
  const r = LOOK.rain
  return {
    turbidity: lerp(d.turbidity, c.turbidity, cloud),
    rayleigh: lerp(d.rayleigh, c.rayleigh, cloud),
    mie: lerp(d.mie, c.mie, cloud),
    overcast: lerp(0, lerp(c.overcast, r.overcast, rain), cloud),
    overcastColor: mix(c.overcastColor, r.overcastColor, rain),
    sunIntensity: lerp(d.sun, c.sun, cloud) * lerp(1, r.sun, rain),
    sunColor: mix(d.sunColor, c.sunColor, cloud),
    hemiIntensity: lerp(d.hemi, c.hemi, cloud) * lerp(1, r.hemi, rain),
    hemiSky: mix(d.hemiSky, c.hemiSky, cloud),
    hemiGround: mix(d.hemiGround, c.hemiGround, cloud),
    fogColor: mix(mix(d.fog, c.fog, cloud), r.fog, rain),
    asphaltShade: lerp(1, LOOK.wet.shade, wet),
    asphaltRoughness: lerp(d.asphaltRoughness, LOOK.wet.asphaltRoughness, wet),
    rain,
  }
}

/**
 * Neblina linear. Seco: `overviewDistance` a 3x (a de antes, em qualquer
 * câmera). Com chuva ela se aproxima de uma escala que acompanha a câmera
 * (25x a distância até o alvo, entre 250 m e a da visão geral): na
 * perseguição a chuva forte fecha a vista em algumas centenas de metros, na
 * visão geral a pista continua legível. Céu encoberto aproxima um pouco.
 */
export function fogRange(look: WeatherLook, overviewDistance: number, cameraDistance: number): { near: number; far: number } {
  const od = overviewDistance
  const view = Math.min(od, Math.max(250, cameraDistance * 25))
  const near = lerp(od, 0.3 * view, look.rain) * (1 - 0.25 * look.cloud)
  const far = lerp(3 * od, 1.9 * view, look.rain) * (1 - 0.15 * look.cloud)
  return { near, far: Math.max(far, near + 1) }
}

/** Riscos de chuva desenhados com esta qualidade e intensidade. */
export function rainStreakCount(quality: Quality, rain: number): number {
  return Math.round(WEATHER.streaks[quality] * clamp01(rain))
}

// --- gancho de desenvolvimento -------------------------------------------------

let debugSource: (() => object) | null = null

/** O cenário montado registra como ler o clima desenhado; devolve a função que desfaz o registro. */
export function setWeatherDebug(read: () => object): () => void {
  debugSource = read
  return () => {
    if (debugSource === read) debugSource = null
  }
}

/** Clima desenhado no último quadro (`__race3d.weather()`); null sem cenário. */
export function weatherSnapshot(): object | null {
  return debugSource ? debugSource() : null
}
