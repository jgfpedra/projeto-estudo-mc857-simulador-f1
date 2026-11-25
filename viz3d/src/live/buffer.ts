import type { MotionState } from '../cars/motion'
import { signedWheelTravel } from '../cars/odometry'
import { engineYaw } from '../engine/source'
import type { LivePose } from './pose'

export interface LivePosition extends LivePose {
  driver_id: string
  position: number
  lap: number
}

export interface LiveTick {
  type: 'tick'
  sim_ts: number
  positions: LivePosition[]
  collisions: { drv_a: string; drv_b: string }[]
}

/** Keep a short history of authoritative ticks; never predict beyond the last one. */
export class LiveBuffer {
  private frames: LiveTick[] = []
  private readonly wheelTravel = new WeakMap<LiveTick, Map<string, number>>()
  private readonly displayedWheelTravel = new Map<string, number>()
  private cursor = 0
  private lastWallMs: number | null = null
  private buffering = true
  private resetOnNextTick = false
  private finished = false
  revision = 0

  constructor(private readonly delayS = 0.15) {}

  push(tick: LiveTick): boolean {
    const previous = this.frames[this.frames.length - 1]
    if (previous && tick.sim_ts <= previous.sim_ts) return false
    // A missed span or a reconnect cannot safely be interpolated as one chord.
    const reset = !previous || this.resetOnNextTick || tick.sim_ts - previous.sim_ts > 0.5 || this.frames.length >= 50
    const travel = new Map(previous ? this.wheelTravel.get(previous) : undefined)
    if (reset && previous) {
      for (const [driver, distance] of this.displayedWheelTravel) travel.set(driver, distance)
    }
    for (const pos of tick.positions) {
      const earlier = previous?.positions.find((item) => item.driver_id === pos.driver_id)
      let distance = travel.get(pos.driver_id) ?? 0
      if (earlier && !reset) {
        distance += signedWheelTravel(earlier.position_xy[0], earlier.position_xy[1], earlier.heading_deg * Math.PI / 180,
          pos.position_xy[0], pos.position_xy[1], pos.heading_deg * Math.PI / 180)
      }
      travel.set(pos.driver_id, distance)
    }
    this.wheelTravel.set(tick, travel)
    if (reset) {
      this.frames = [tick]
      this.revision++
      this.finished = false
      this.cursor = tick.sim_ts
      this.lastWallMs = null
      this.buffering = true
      this.resetOnNextTick = false
    } else {
      this.frames.push(tick)
    }
    return true
  }

  disconnected(): void {
    // Preserve the last visible state until a newer authoritative tick arrives.
    this.resetOnNextTick = true
  }

  finish(): void {
    this.finished = true
  }

  private advance(nowMs: number): void {
    if (!this.frames.length) return
    const elapsed = this.lastWallMs === null ? 0 : Math.max(0, (nowMs - this.lastWallMs) / 1000)
    this.lastWallMs = nowMs
    const newest = this.frames[this.frames.length - 1].sim_ts
    if (this.buffering && (newest - this.cursor + 1e-9 >= this.delayS || (this.finished && newest > this.cursor))) this.buffering = false
    if (!this.buffering) {
      this.cursor = Math.min(this.cursor + elapsed, newest)
      if (this.cursor >= newest) this.buffering = true
    }
    while (this.frames.length > 2 && this.frames[1].sim_ts <= this.cursor) this.frames.shift()
  }

  /** The last tick reached by the display clock, for the HUD and contact events. */
  displayTick(nowMs: number): LiveTick | null {
    this.advance(nowMs)
    if (!this.frames.length) return null
    return this.frames[1] && this.frames[1].sim_ts <= this.cursor ? this.frames[1] : this.frames[0]
  }

  sampleInto(driverId: string, nowMs: number, out: MotionState): MotionState {
    this.advance(nowMs)
    const a = this.frames[0]
    const b = this.frames[1]
    const first = a?.positions.find((p) => p.driver_id === driverId)
    if (!first) { out.wheelTravelM = undefined; out.posed = false; return out }
    const second = b?.positions.find((p) => p.driver_id === driverId) ?? first
    const fraction = b ? Math.max(0, Math.min(1, (this.cursor - a.sim_ts) / (b.sim_ts - a.sim_ts))) : 0
    const mix = (x: number, y: number) => x + (y - x) * fraction
    const angleA = first.heading_deg * Math.PI / 180
    const angleB = second.heading_deg * Math.PI / 180
    const angleDiff = Math.atan2(Math.sin(angleB - angleA), Math.cos(angleB - angleA))
    out.posed = true
    out.x = mix(first.position_xy[0], second.position_xy[0])
    out.z = -mix(first.position_xy[1], second.position_xy[1])
    out.yawRad = engineYaw(angleA + angleDiff * fraction)
    out.sUnwrapped = mix(first.progress_m, second.progress_m)
    const travelA = this.wheelTravel.get(a)?.get(driverId) ?? 0
    const travelB = b ? (this.wheelTravel.get(b)?.get(driverId) ?? travelA) : travelA
    out.wheelTravelM = mix(travelA, travelB)
    this.displayedWheelTravel.set(driverId, out.wheelTravelM)
    out.speedMps = mix(first.velocity_mps, second.velocity_mps)
    out.d = 0
    return out
  }
}
