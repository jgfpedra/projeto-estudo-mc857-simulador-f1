import * as d3 from "d3"

import type { Bounds } from "@/types/race"

/** Projeção uniforme (mesma escala em X e Y) dos dados da FastF1 para o viewBox. */
export function createTrackProjection(
  bounds: Bounds,
  width: number,
  height: number,
  padding = 32,
) {
  const dataW = bounds.maxX - bounds.minX
  const dataH = bounds.maxY - bounds.minY
  const k = Math.min((width - 2 * padding) / dataW, (height - 2 * padding) / dataH)
  const offX = (width - dataW * k) / 2
  const offY = (height - dataH * k) / 2

  const x = d3.scaleLinear().domain([bounds.minX, bounds.maxX]).range([offX, offX + dataW * k])
  // Y invertido: no sistema da FastF1, Y cresce "para cima"; no SVG, cresce "para baixo".
  // Se a pista sair espelhada, troque o range por [offY, offY + dataH * k].
  const y = d3.scaleLinear().domain([bounds.minY, bounds.maxY]).range([offY + dataH * k, offY])

  return { x, y, scale: k }
}