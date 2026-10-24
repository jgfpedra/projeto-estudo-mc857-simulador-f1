import { useEffect, useRef } from "react"
import * as d3 from "d3"

import { createTrackProjection } from "@/services/track-projection"
import { tickPlayer } from "@/services/tick-player"
import type { RaceData, TickCar } from "@/types/race"

const VIEW_W = 1000
const VIEW_H = 700
/** Largura aproximada da pista em décimos de metro (~11 m). */
const TRACK_WIDTH_UNITS = 110
/** Raio aproximado do carro em décimos de metro. */
const CAR_RADIUS_UNITS = 45

type RenderCar = TickCar & { color: string; code: string }

export function TrackMap({ race }: { race: RaceData }) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    const proj = createTrackProjection(race.track.bounds, VIEW_W, VIEW_H)
    const k = proj.scale
    const drivers = new Map(race.drivers.map((d) => [d.id, d]))

    const line = d3
      .line<[number, number]>()
      .x(([px]) => proj.x(px))
      .y(([, py]) => proj.y(py))

    svg
      .select<SVGPathElement>("path.track")
      .attr("d", line(race.track.points))
      .attr("stroke-width", TRACK_WIDTH_UNITS * k)

    const layer = svg.select<SVGGElement>("g.cars")
    const r = Math.max(5, CAR_RADIUS_UNITS * k)
    const fontSize = r * 1.1

    const render = () => {
      const ticks = tickPlayer.ticks
      if (ticks.length === 0) return

      const f = Math.min(ticks.length - 1, tickPlayer.time * tickPlayer.hz)
      const i = Math.floor(f)
      const a = ticks[i]
      const b = ticks[i + 1] ?? a
      const alpha = f - i
      const nextById = new Map(b.cars.map((c) => [c.id, c]))

      // Interpola X/Y entre dois ticks; posição e pneu vêm do tick atual (discretos).
      const cars: RenderCar[] = a.cars.map((ca) => {
        const cb = nextById.get(ca.id) ?? ca
        const meta = drivers.get(ca.id)
        return {
          ...ca,
          x: ca.x + (cb.x - ca.x) * alpha,
          y: ca.y + (cb.y - ca.y) * alpha,
          color: meta?.teamColor ?? "#888888",
          code: meta?.code ?? ca.id,
        }
      })

      layer
        .selectAll<SVGGElement, RenderCar>("g.car")
        .data(cars, (d) => d.id)
        .join((enter) => {
          const g = enter.append("g").attr("class", "car")
          g.append("circle")
          g.append("text")
            .attr("text-anchor", "middle")
            .attr("font-weight", 900)
            .attr("fill", "#fff")
            .attr("pointer-events", "none")
          return g
        })
        .attr("transform", (d) => `translate(${proj.x(d.x)},${proj.y(d.y)})`)
        .style("opacity", (d) => (d.inPit ? 0.5 : 1))
        // Líder por último, para ficar por cima dos demais.
        .sort((a, b) => b.position - a.position)
        .order()
        .each(function (d) {
          const g = d3.select(this)
          g.select("circle")
            .attr("r", r)
            .attr("fill", d.color)
            .attr("stroke", "#000")
            .attr("stroke-width", r * 0.25)
          g.select("text")
            .attr("dy", fontSize * 0.35)
            .attr("font-size", fontSize)
            .text(d.code)
        })
    }

    const unsubscribe = tickPlayer.subscribeFrame(render)
    render()
    return unsubscribe
  }, [race])

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      className="h-full w-full"
      role="img"
      aria-label="Posição dos carros na pista"
    >
      <path
        className="track"
        fill="none"
        stroke="#3f3f46"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <g className="cars" />
    </svg>
  )
}