import { MAX_DELTA_S } from '../cars/field'

/**
 * Replay time, owned in one place.
 *
 * Before M6 there was no clock: `Grid` integrated each car's arc length against
 * the frame delta, twenty accumulators advancing in step. A replay cannot work
 * that way — it can be paused, scrubbed and run at a different rate — so time
 * became a quantity of its own and the car path became a pure function of it.
 *
 * The bookkeeping that moved here with it is `MAX_DELTA_S`. `requestAnimationFrame`
 * stops while the tab is hidden, so the first frame back carries the whole
 * away-time in one delta; uncapped, the field would jump several laps, which on
 * screen is indistinguishable from the start/finish discontinuity M3 existed to
 * rule out. The cap used to be applied twenty times a frame, once per car, and
 * `rig.ts` had to agree with it. Now it is applied once, to the one quantity that
 * advances.
 */
export interface ClockState {
  /** Seconds since the start of the replay. */
  tS: number
  /** Playback rate. 1 is realtime, 0 is equivalent to paused. */
  rate: number
  playing: boolean
  /**
   * Incremented on every discontinuity — a seek, or a loop back to the start.
   *
   * `CameraRig` watches this and cuts instead of damping. Without it the chase
   * camera would fly a lap across the map after a scrub, because its anchor is a
   * damped filter on arc length and a scrub moves the target by kilometres.
   */
  cuts: number
}

export function newClock(): ClockState {
  return { tS: 0, rate: 1, playing: true, cuts: 0 }
}

/**
 * Advance by `deltaS` of wall clock. Loops at the end rather than stopping.
 *
 * Looping counts as a cut: `tS` jumps from the end back to 0, which is exactly
 * the discontinuity a seek is. A five-lap window that halted on the last frame
 * would need a button to watch it again, and a camera that damped across the
 * wrap would sweep the whole circuit once per loop.
 */
export function stepClock(clock: ClockState, deltaS: number, durationS: number): void {
  if (!clock.playing || clock.rate === 0) return
  if (!Number.isFinite(durationS) || durationS <= 0) {
    clock.tS += Math.min(deltaS, MAX_DELTA_S) * clock.rate
    return
  }
  const next = clock.tS + Math.min(deltaS, MAX_DELTA_S) * clock.rate
  if (next > durationS) {
    clock.tS = next - durationS
    clock.cuts++
  } else if (next < 0) {
    clock.tS = durationS + next
    clock.cuts++
  } else {
    clock.tS = next
  }
}

/** Jump to a time. Always a cut, even if it lands where we already were. */
export function seekClock(clock: ClockState, tS: number, durationS: number): void {
  const limit = Number.isFinite(durationS) ? durationS : Number.MAX_VALUE
  clock.tS = Math.min(Math.max(tS, 0), limit)
  clock.cuts++
}

export function togglePlay(clock: ClockState): void {
  clock.playing = !clock.playing
}

/**
 * Change the playback rate.
 *
 * Not a cut: `CameraRig` scales its own `dtS` by the rate, so the camera's anchor
 * stays continuous across a rate change and only its damping time constant
 * stretches. A cut here would make every rate change a visible jump.
 */
export function setRate(clock: ClockState, rate: number): void {
  clock.rate = rate
}
