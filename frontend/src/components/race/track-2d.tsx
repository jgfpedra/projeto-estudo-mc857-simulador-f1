import { useEffect, useRef } from "react"
import * as d3 from "d3"

import {
  TRACK_WIDTH_M,
  boundsOf,
  driverColor,
  interpolateCars,
  recentDriverIds,
} from "@/helpers/race-live"
import { createTrackProjection } from "@/services/track-projection"
import { useLiveRaceStore } from "@/stores/live-race-store"
import type { RaceInfo } from "@/types/race"

const VIEW_W = 1000
const VIEW_H = 700
const FOCUS_ZOOM = 5
/** Raio do carro em unidades da viewBox, antes do zoom. */
const CAR_RADIUS = 6
/** Tempo de simulação em que um evento destaca os carros envolvidos. */
const HIGHLIGHT_S = 3

type Point = { x: number; y: number }

type CarView = {
  id: string
  code: string
  color: string
  position: number
  pitting: boolean
  selected: boolean
  highlighted: boolean
  vx: number
  vy: number
}

export function Track2D({ race }: { race: RaceInfo }) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svgEl = svgRef.current
    if (!svgEl) return

    const svg = d3.select(svgEl)
    const world = svg.select<SVGGElement>("g.world")
    const layer = world.select<SVGGElement>("g.cars")
    const pitLane = race.track.pitLane
    const points = [...race.track.waypoints, ...(pitLane?.waypoints ?? [])]
    const proj = createTrackProjection(boundsOf(points), VIEW_W, VIEW_H)
    const drivers = new Map(race.drivers.map((d, i) => [d.driverId, { d, i }]))

    const line = d3
      .line<[number, number]>()
      .x(([x]) => proj.x(x))
      .y(([, y]) => proj.y(y))

    world
      .select<SVGPathElement>("path.track")
      .attr("d", `${line(race.track.waypoints) ?? ""}Z`)
      .attr("stroke-width", (race.track.widthM ?? TRACK_WIDTH_M) * proj.scale)

    // A via dos boxes é uma linha aberta na mesma projeção e escala da pista.
    world
      .select<SVGPathElement>("path.pit-lane-border")
      .attr("d", pitLane ? line(pitLane.waypoints) : null)
      .attr("stroke-width", pitLane ? (pitLane.widthM + 1.5) * proj.scale : 0)
    world
      .select<SVGPathElement>("path.pit-lane")
      .attr("d", pitLane ? line(pitLane.waypoints) : null)
      .attr("stroke-width", pitLane ? pitLane.widthM * proj.scale : 0)

    const toView = (p: Point) => ({ x: proj.x(p.x), y: proj.y(p.y) })

    const centerOn = (p: Point, k: number) => {
      const v = toView(p)
      return d3.zoomIdentity.translate(VIEW_W / 2 - k * v.x, VIEW_H / 2 - k * v.y).scale(k)
    }

    const pitMarker = world.select<SVGGElement>("g.pit-marker")
    const pitMidpoint = pitLane?.waypoints[Math.floor(pitLane.waypoints.length / 2)]
    const positionPitMarker = (k: number) => {
      if (!pitMidpoint) return
      pitMarker.attr("transform", `translate(${proj.x(pitMidpoint[0])},${proj.y(pitMidpoint[1])}) scale(${1 / k})`)
    }
    positionPitMarker(1)

    let zoomK = 1
    /** Piloto que a câmera acompanha depois que a transição de foco termina. */
    let following: string | null = null
    let positions = new Map<string, Point>()
    let pendingFocus = useLiveRaceStore.getState().selectedDriverId

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 12])
      .on("zoom", (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        world.attr("transform", event.transform.toString())
        zoomK = event.transform.k
        positionPitMarker(zoomK)
        // Arrastar ou rolar pelo usuário solta o seguimento do carro.
        if (event.sourceEvent) following = null
      })

    svg.call(zoom)

    const focus = (driverId: string | null) => {
      // Cancela qualquer seguimento anterior; senão o frame loop interrompe a nova transição.
      following = null

      if (driverId === null) {
        svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity)
        return
      }

      const p = positions.get(driverId)
      if (!p) return

      svg
        .transition()
        .duration(700)
        .call(zoom.transform, centerOn(p, FOCUS_ZOOM))
        .on("end", () => {
          following = driverId
        })
    }

    const unsubscribe = useLiveRaceStore.subscribe((state, prev) => {
      if (state.selectedDriverId !== prev.selectedDriverId) focus(state.selectedDriverId)
    })

    let raf = 0
    const tickFrame = (now: number) => {
      const s = useLiveRaceStore.getState()

      if (s.frame) {
        const alpha = Math.min(1, Math.max(0, (now - s.frameAt) / s.tickIntervalMs))
        positions = interpolateCars(s.prevFrame, s.frame, alpha)

        // Seleção feita antes do primeiro frame: aplica assim que a posição existir.
        if (pendingFocus && positions.has(pendingFocus)) {
          focus(pendingFocus)
          pendingFocus = null
        }

        if (following) {
          const p = positions.get(following)
          if (p) zoom.transform(svg, centerOn(p, zoomK))
        }

        const highlighted = recentDriverIds(s.feed, s.frame.simTs, HIGHLIGHT_S)
        const views: CarView[] = s.frame.cars.map((c) => {
          const meta = drivers.get(c.driverId)
          const p = positions.get(c.driverId) ?? { x: c.x, y: c.y }
          const v = toView(p)
          return {
            id: c.driverId,
            code: meta?.d.abbreviation ?? c.driverId.slice(0, 3).toUpperCase(),
            color: driverColor(meta?.d, meta?.i ?? 0),
            position: c.position,
            pitting: c.pitting,
            selected: c.driverId === s.selectedDriverId,
            highlighted: highlighted.has(c.driverId),
            vx: v.x,
            vy: v.y,
          }
        })

        const r = CAR_RADIUS / zoomK

        layer
          .selectAll<SVGGElement, CarView>("g.car")
          .data(views, (d) => d.id)
          .join((enter) => {
            const g = enter.append("g").attr("class", "car")
            g.append("circle").attr("class", "ring").attr("fill", "none").attr("stroke", "#fff")
            g.append("circle").attr("class", "body")
            g.append("text")
              .attr("text-anchor", "middle")
              .attr("font-weight", 900)
              .attr("fill", "#fff")
              .attr("pointer-events", "none")
            return g
          })
          .attr("transform", (d) => `translate(${d.vx},${d.vy})`)
          .style("opacity", (d) => (d.pitting ? 0.5 : 1))
          // Líder por último, para ficar por cima dos demais.
          .sort((a, b) => b.position - a.position)
          .order()
          .each(function (d) {
            const g = d3.select(this)
            g.select("circle.ring")
              .attr("r", r * 2)
              .attr("stroke-width", 2 / zoomK)
              .attr("opacity", d.highlighted ? 1 : 0)
            g.select("circle.body")
              .attr("r", r)
              .attr("fill", d.color)
              .attr("stroke", d.selected ? "#fff" : "#000")
              .attr("stroke-width", (d.selected ? 3 : 1.5) / zoomK)
            g.select("text")
              .attr("dy", r * 0.4)
              .attr("font-size", r * 1.1)
              .text(d.code)
          })
      }

      raf = requestAnimationFrame(tickFrame)
    }

    raf = requestAnimationFrame(tickFrame)

    return () => {
      cancelAnimationFrame(raf)
      unsubscribe()
      svg.on(".zoom", null)
    }
  }, [race])

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      className="h-full w-full touch-none select-none"
      role="img"
      aria-label="Mapa 2D da corrida"
    >
      <g className="world">
        <path
          className="track"
          fill="none"
          stroke="#3f3f46"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {race.track.pitLane && (
          <>
            <path className="pit-lane-border" fill="none" stroke="#18181b" strokeLinecap="round" strokeLinejoin="round" />
            <path className="pit-lane" fill="none" stroke="#facc15" strokeLinecap="round" strokeLinejoin="round">
              <title>{race.track.pitLane.source === "estimated" ? "Via dos boxes (estimada)" : "Via dos boxes"}</title>
            </path>
            <g className="pit-marker" pointerEvents="none" aria-hidden="true">
              <circle r="4" fill="#facc15" stroke="#18181b" strokeWidth="1.5" />
              <path d="M 4 -4 L 13 -15" fill="none" stroke="#facc15" strokeWidth="1.5" />
              <rect x="13" y="-29" width="57" height="20" rx="3" fill="#18181b" stroke="#facc15" />
              <text x="41.5" y="-15" textAnchor="middle" fontSize="11" fontWeight="700" fill="#facc15">BOXES</text>
            </g>
          </>
        )}
        <g className="cars" />
      </g>
      {!race.track.pitLane && (
        <text x="20" y={VIEW_H - 20} fontSize="13" fill="#a1a1aa">
          Boxes indisponíveis para esta corrida
        </text>
      )}
    </svg>
  )
}
