import { useMemo } from "react"
import type { TrackWaypoint } from "@/data/circuits"

type CircuitTrackPreviewProps = {
  waypoints: TrackWaypoint[]
  className?: string
}

function catmullRom(
  points: TrackWaypoint[],
  samplesPerSegment = 10,
): TrackWaypoint[] {
  if (points.length < 3) return points

  const result: TrackWaypoint[] = []
  const count = points.length

  for (let i = 0; i < count; i++) {
    const p0 = points[(i - 1 + count) % count]
    const p1 = points[i]
    const p2 = points[(i + 1) % count]
    const p3 = points[(i + 2) % count]

    for (let j = 0; j < samplesPerSegment; j++) {
      const t = j / samplesPerSegment

      const t2 = t * t
      const t3 = t2 * t

      const c1 = 2 * t3 - 3 * t2 + 1
      const c2 = t3 - 2 * t2 + t
      const c3 = -2 * t3 + 3 * t2
      const c4 = t3 - t2

      const tension = 0.5

      const x =
        c1 * p1[0] +
        c3 * p2[0] +
        tension *
          (
            c2 * (p2[0] - p0[0]) +
            c4 * (p3[0] - p1[0])
          )

      const y =
        c1 * p1[1] +
        c3 * p2[1] +
        tension *
          (
            c2 * (p2[1] - p0[1]) +
            c4 * (p3[1] - p1[1])
          )

      result.push([x, y])
    }
  }

  return result
}

function getViewBox(points: TrackWaypoint[], padding = 45) {
  if (!points.length) {
    return "0 0 100 100"
  }

  const xs = points.map(([x]) => x)
  const ys = points.map(([, y]) => y)

  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  return [
    minX - padding,
    -(maxY + padding),
    maxX - minX + padding * 2,
    maxY - minY + padding * 2,
  ].join(" ")
}

function createPath(points: TrackWaypoint[]) {
  if (!points.length) return ""

  const commands = points.map(([x, y], index) => {
    const command = index === 0 ? "M" : "L"
    return `${command} ${x} ${-y}`
  })

  return commands.join(" ")
}

export function CircuitTrackPreview({
  waypoints,
  className,
}: CircuitTrackPreviewProps) {
  const smoothedPoints = useMemo(
    () => catmullRom(waypoints, 12),
    [waypoints],
  )

  const viewBox = useMemo(
    () => getViewBox(smoothedPoints),
    [smoothedPoints],
  )

  const path = useMemo(
    () => createPath(smoothedPoints),
    [smoothedPoints],
  )

  return (
    <svg
      viewBox={viewBox}
      className={className}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Traçado do circuito"
    >
      <path
        d={`${path} Z`}
        fill="none"
        stroke="currentColor"
        strokeWidth="10"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}