/**
 * Texturas procedurais pequenas (canvas), com semente: a mesma pista tem
 * sempre o mesmo grão. Cores da paleta do Kenney Racing Kit.
 */
import { CanvasTexture, RepeatWrapping, SRGBColorSpace } from "three"

import { rng } from "./layout"

export const PALETTE = {
  grass: "#4d8f6d",
  verge: "#5a9a76",
  road: "#444444",
  sand: "#c7b795",
  red: "#e85452",
  white: "#f4f4f4",
} as const

function texture(size: number, draw: (ctx: CanvasRenderingContext2D, size: number) => void): CanvasTexture {
  const c = document.createElement("canvas")
  c.width = size
  c.height = size
  const ctx = c.getContext("2d")
  if (ctx) draw(ctx, size)
  const tex = new CanvasTexture(c)
  tex.wrapS = RepeatWrapping
  tex.wrapT = RepeatWrapping
  tex.colorSpace = SRGBColorSpace
  tex.anisotropy = 8
  return tex
}

/** Cor de base com pontos claros e escuros espalhados (grão). */
export function noiseTexture(base: string, spread: number, dots: number, seed: number, size = 256): CanvasTexture {
  const rand = rng(seed)
  return texture(size, (ctx, s) => {
    ctx.fillStyle = base
    ctx.fillRect(0, 0, s, s)
    for (let i = 0; i < dots; i++) {
      const v = (rand() - 0.5) * spread
      const c = v > 0 ? 255 : 0
      ctx.fillStyle = `rgba(${c},${c},${c},${Math.abs(v).toFixed(3)})`
      const w = 1 + Math.floor(rand() * 2)
      ctx.fillRect(Math.floor(rand() * s), Math.floor(rand() * s), w, w)
    }
  })
}

/** Zebra: listras vermelhas e brancas ao longo de v (a direção da pista nas faixas). */
export function kerbTexture(): CanvasTexture {
  return texture(64, (ctx, s) => {
    for (let k = 0; k < 2; k++) {
      ctx.fillStyle = k % 2 ? PALETTE.white : PALETTE.red
      ctx.fillRect(0, (k * s) / 2, s, s / 2)
    }
  })
}
