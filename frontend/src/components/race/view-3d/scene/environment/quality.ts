/**
 * Chave de qualidade do cenário. "off" desenha a cena antiga (fundo liso,
 * só a faixa da pista): serve de referência de desempenho e de saída para
 * máquinas fracas.
 */
import { TREE_LOW_FRACTION } from "./layout.ts"

export type Quality = "high" | "low" | "off"

export const QUALITIES: Quality[] = ["high", "low", "off"]

export const QUALITY_LABEL: Record<Quality, string> = { high: "Alta", low: "Baixa", off: "Sem cenário" }

export type QualitySettings = {
  environment: boolean
  shadows: boolean
  shadowMapSize: number
  /** Fração das árvores desenhada (as primeiras da lista, já embaralhada). */
  treeFraction: number
}

export const QUALITY: Record<Quality, QualitySettings> = {
  high: { environment: true, shadows: true, shadowMapSize: 2048, treeFraction: 1 },
  low: { environment: true, shadows: false, shadowMapSize: 2048, treeFraction: TREE_LOW_FRACTION },
  off: { environment: false, shadows: false, shadowMapSize: 2048, treeFraction: 0 },
}

const KEY = "race3d.quality"

let software: boolean | null = null
let probeCanvas: HTMLCanvasElement | null = null
const SOFTWARE_RENDERER = /swiftshader|llvmpipe|softpipe|software|basic render/i

/**
 * WebGL só por software (SwiftShader, llvmpipe, sem GPU)? O navegador recusa
 * um contexto pedido com `failIfMajorPerformanceCaveat` nesses casos. Medido
 * no SwiftShader, 750x541: cenário alto ~225 ms por quadro, baixo ~77 ms, sem
 * cenário ~9 ms (numa GTX 1660: 1,5 ms no alto).
 */
export function softwareRendering(): boolean {
  if (software !== null) return software
  software = false
  try {
    // Uma vez por página (resultado guardado em `software`). O canvas fica
    // referenciado até o evento de perda chegar: `loseContext()` o despacha
    // depois, e um canvas solto pode ser coletado antes, sem o evento.
    const canvas = document.createElement("canvas")
    probeCanvas = canvas
    canvas.addEventListener("webglcontextlost", () => (probeCanvas = null), { once: true })
    const strict = canvas.getContext("webgl2", { failIfMajorPerformanceCaveat: true })
    if (!strict) {
      software = true
      probeCanvas = null
    } else {
      // Com o SwiftShader pedido explicitamente (ex.: Chrome headless) o
      // contexto acima não falha; o nome do renderizador entrega.
      const info = strict.getExtension("WEBGL_debug_renderer_info")
      const name = info ? String(strict.getParameter(info.UNMASKED_RENDERER_WEBGL)) : ""
      software = SOFTWARE_RENDERER.test(name)
      strict.getExtension("WEBGL_lose_context")?.loseContext()
    }
  } catch {
    // Sem como testar: assume GPU.
  }
  return software
}

/** O contexto descartável de `softwareRendering()` já foi liberado (evento de perda recebido)? */
export function softwareProbeReleased(): boolean {
  return probeCanvas === null
}

/** Escolha guardada; sem ela, alta com GPU e sem cenário com WebGL por software. */
export function loadQuality(): Quality {
  try {
    const v = window.localStorage.getItem(KEY)
    if (v === "high" || v === "low" || v === "off") return v
  } catch {
    // Armazenamento bloqueado: fica no padrão.
  }
  return softwareRendering() ? "off" : "high"
}

export function saveQuality(q: Quality): void {
  try {
    window.localStorage.setItem(KEY, q)
  } catch {
    // Sem armazenamento: a escolha vale só nesta sessão.
  }
}
