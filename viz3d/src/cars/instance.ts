import { Matrix4, Quaternion, Vector3 } from 'three'
import type { TrackFrame } from '../track/frame'
import { placeCar } from './place'
import type { CarWheel } from './model'

/**
 * Reused across calls: this runs once per car per frame, twenty times over, and
 * allocating a Vector3 per car per frame is how a render loop starts stuttering
 * on the garbage collector rather than on the GPU.
 */
const pos = new Vector3()
const quat = new Quaternion()
const ONE = new Vector3(1, 1, 1)
const spin = new Quaternion()
const wheelPos = new Vector3()

/**
 * Placement matrix for one car, for `InstancedMesh.setMatrixAt`.
 *
 * Position and orientation still come from `placeCar` and nowhere else, so the
 * twenty-car path and the one-car path cannot drift apart. The only new step is
 * composing them into a matrix, and `compose` with a unit scale preserves the
 * quaternion's determinant of +1 \u2014 which is exactly the property
 * `grid.test.ts` checks around the lap, because composing matrices by hand is
 * where the mirroring failure gets back in.
 */
export function carMatrix(
  frame: TrackFrame,
  s: number,
  d: number,
  h: number,
  out: Matrix4,
): Matrix4 {
  placeCar(frame, s, d, h, pos, quat)
  return out.compose(pos, quat, ONE)
}

const Y_AXIS = new Vector3(0, 1, 0)

/**
 * Placement matrix for a car whose world pose is known directly - the engine
 * recording's `position_xy` / `heading_deg`, already mapped to Three.js by
 * `engineSource`. A rotation about +y and a translation, composed with unit
 * scale, so the determinant is +1 by construction; check J still verifies it
 * on the matrices actually handed to the GPU.
 *
 * Flat: `h` is above y = 0, which is where `trackFromRecording` puts the
 * engine's centreline. The engine's plan has no elevation either.
 */
export function poseMatrix(x: number, z: number, yawRad: number, h: number, out: Matrix4): Matrix4 {
  pos.set(x, h, z)
  quat.setFromAxisAngle(Y_AXIS, yawRad)
  return out.compose(pos, quat, ONE)
}

/**
 * Placement matrix for one wheel: the car's matrix, then out to the wheel's
 * centre, then a spin about its own axle.
 *
 * The geometry was baked relative to the wheel centre in `carGeometry`, so the
 * rotation here is about the origin of that geometry and needs no correction.
 */
export function wheelMatrix(
  car: Matrix4,
  wheel: CarWheel,
  angleRad: number,
  out: Matrix4,
): Matrix4 {
  spin.setFromAxisAngle(wheel.axle, angleRad)
  wheelPos.copy(wheel.centre)
  out.compose(wheelPos, spin, ONE)
  return out.premultiply(car)
}

/**
 * How far the wheels have turned after travelling `distanceM`, radians.
 *
 * Negative because the car's forward is local -Z: a positive rotation about the
 * axle carries the top of the wheel towards +Z, which is backwards. Rolling
 * without slipping, so the rate falls out of the radius rather than being
 * tuned by eye \u2014 a wheel that visibly scrubs is a sign the radius is wrong.
 */
export function wheelAngle(distanceM: number, radiusM: number): number {
  return -distanceM / radiusM
}
