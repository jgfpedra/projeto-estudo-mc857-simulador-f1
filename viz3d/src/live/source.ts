import type { CarIdentity, MotionSource, MotionState } from '../cars/motion'
import { PALETTE } from '../cars/field'
import { engineYaw } from '../engine/source'
import type { LivePosition } from './types'
import type { LiveStore } from './store'

const MIN_REPORTED_MPS = 1e-3

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value))
}

function lerp(a: number, b: number, f: number): number {
  return a + (b - a) * f
}

function lerpAngle(a: number, b: number, f: number): number {
  const d = Math.atan2(Math.sin(b - a), Math.cos(b - a))
  return a + d * f
}

function progressOf(row: LivePosition | undefined): number {
  return row?.progress_m ?? row?.s_m ?? 0
}

/**
 * A live race as a `MotionSource`, fed by the WebSocket buffer.
 *
 * The clock is the viewer's own `tS`; the source maps it onto the engine's
 * `sim_ts` using the first tick as origin. When the clock runs past the newest
 * tick it clamps there, so the field pauses for a moment between frames instead
 * of extrapolating into the future.
 */
export function liveSource(store: LiveStore): MotionSource {
  const drivers = [...store.meta.drivers].sort((a, b) => a.grid_position - b.grid_position)
  const cars: CarIdentity[] = drivers.map((driver, index) => {
    const colour = PALETTE[Math.floor(index / 2) % PALETTE.length]
    return {
      index,
      label: driver.driver_id,
      name: driver.name,
      colourName: colour.name,
      hex: colour.hex,
    }
  })

  return {
    kind: 'live',
    cars,
    durationS: Infinity,
    sampleInto(tSeconds: number, car: number, out: MotionState): MotionState {
      const ticks = store.ticksList
      if (car < 0 || car >= cars.length || ticks.length === 0) {
        out.sUnwrapped = 0
        out.d = 0
        out.speedMps = 0
        out.posed = false
        return out
      }

      const target = store.t0 + Math.max(0, tSeconds)
      let lo = 0
      let hi = ticks.length - 1
      while (lo < hi) {
        const mid = (lo + hi + 1) >> 1
        if (ticks[mid].simTs <= target) lo = mid
        else hi = mid - 1
      }
      const a = ticks[lo]
      const b = ticks[Math.min(lo + 1, ticks.length - 1)]
      const span = b.simTs - a.simTs
      const f = span > 1e-9 ? clamp01((target - a.simTs) / span) : 0

      const pa = a.rows[car]
      if (!pa) {
        out.sUnwrapped = 0
        out.d = 0
        out.speedMps = 0
        out.posed = false
        return out
      }
      const pb = b.rows[car] ?? pa

      const progressA = progressOf(pa)
      const progressB = progressOf(pb)
      out.sUnwrapped = lerp(progressA, progressB, f)
      out.d = lerp(pa.d_m ?? 0, pb.d_m ?? pa.d_m ?? 0, f)
      out.speedMps = Math.max(
        span > 1e-9
          ? (progressB - progressA) / span
          : (pa.velocity_mps ?? 0),
        MIN_REPORTED_MPS,
      )
      out.posed = true
      out.x = lerp(pa.position_xy[0], pb.position_xy[0], f)
      out.z = -lerp(pa.position_xy[1], pb.position_xy[1], f)
      out.yawRad = engineYaw(
        lerpAngle(
          (pa.heading_deg * Math.PI) / 180,
          (pb.heading_deg * Math.PI) / 180,
          f,
        ),
      )
      return out
    },
    originM(car: number): number {
      return progressOf(store.ticksList[0]?.rows[car])
    },
  }
}
