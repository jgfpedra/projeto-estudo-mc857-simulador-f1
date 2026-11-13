import type { MotionSource, MotionState } from '../cars/motion'
import type { Replay, ReplayCar } from './types'

/**
 * Minimum speed reported for a stationary car, m/s.
 *
 * `stepRig` returns early on `speedMps <= 0`, which it does because `Grid`'s first
 * frames can arrive before its arrays are seeded and seeding the camera off a
 * zeroed readout would put it at the world origin. A genuinely stationary car —
 * parked, or retired — would trip the same guard and freeze the camera on it
 * instead of seeding.
 *
 * A floor rather than a change to `rig.ts`: at 1e-3 m/s the feed-forward term
 * contributes 17 micrometres per frame and the roll target is curvature times
 * 1e-6, so nothing moves, but the rig seeds and the car can be followed. It costs
 * nothing in the committed window, where every car is racing — it is there so
 * that a window containing a retirement does not need a different code path.
 */
const MIN_REPORTED_MPS = 1e-3

/**
 * A replay as a `MotionSource`.
 *
 * Interpolation is a direct index, no search: the grid is uniform by
 * construction, which is most of the reason the extractor resamples onto one.
 *
 * Interpolating `(s, d)` rather than world coordinates is what keeps the replay
 * on the track between samples. At 5 Hz a car covers about 19 m on average, and
 * a straight line between two world points would cut the corner by up to 30 cm
 * in this replay (measured worst case: a 13.4 m step through the exit of
 * Ascari, T10; the tighter chicanes are taken too slowly for the chord to
 * matter as much); interpolating arc length instead means the intermediate
 * positions are evaluated on the spline by `toWorld` and lie exactly on it. The
 * cost is a sixth of a car length of longitudinal error where the car is braking
 * hardest, which is the price of a 5 Hz grid rather than of this choice.
 */
export function replaySource(replay: Replay): MotionSource {
  const { cars, dtS, samples, durationS } = replay
  const last = samples - 1

  return {
    kind: 'replay',
    cars,
    durationS,
    sampleInto(tSeconds: number, carIndex: number, out: MotionState): MotionState {
      const car: ReplayCar | undefined = cars[carIndex]
      if (!car) {
        out.sUnwrapped = 0
        out.d = 0
        out.speedMps = 0
        out.posed = false
        return out
      }

      // Hold at both ends rather than extrapolating. The clock clamps and loops,
      // so this only catches the exact endpoint and any rounding at it.
      const x = tSeconds / dtS
      const i = Math.min(Math.max(Math.floor(x), 0), last - 1)
      const f = Math.min(Math.max(x - i, 0), 1)

      out.sUnwrapped = car.sUnwrapped[i] + (car.sUnwrapped[i + 1] - car.sUnwrapped[i]) * f
      out.d = car.d[i] + (car.d[i + 1] - car.d[i]) * f
      const speed = car.speedMps[i] + (car.speedMps[i + 1] - car.speedMps[i]) * f
      out.speedMps = Math.max(speed, MIN_REPORTED_MPS)
      out.posed = false
      return out
    },
    originM(carIndex: number): number {
      return cars[carIndex]?.sUnwrapped[0] ?? 0
    },
  }
}
