import { Matrix4, Quaternion, Vector3 } from 'three'
import { sampleAt, toWorld } from '../track/frame'
import type { Sample, TrackFrame } from '../track/frame'

/**
 * Reused across calls. Placement runs once per car per frame, so it allocates
 * nothing — same reason `frame.ts` keeps a module-level `scratch`.
 */
const scratch: Sample = {
  position: new Vector3(),
  tangent: new Vector3(),
  right: new Vector3(),
  up: new Vector3(),
}
const backward = new Vector3()
const basis = new Matrix4()

/**
 * Rotation that takes a car mesh from local axes to track axes at arc length `s`.
 *
 * Local **-Z is forward**, which is Three.js' convention for anything with a
 * facing, so the columns are `(right, up, -tangent)`.
 *
 * The negation is not cosmetic. `(right, up, tangent)` is left-handed — with
 * `tangent` along -z the columns are `(x, y, -z)` and the determinant is -1, so
 * the matrix mirrors the mesh as well as rotating it. Negating the third column
 * makes it +1. That is the same failure `TrackRibbon`'s determinant check exists
 * to catch, one level down: a mirrored car looks fine on a symmetric box and
 * starts lying the moment the box is replaced by a model, or the moment anything
 * reads `right` off the car rather than off the frame.
 *
 * Passing the frame's own orthonormal `(right, up)` means there is no
 * re-derivation here: handedness is still decided in `frame.ts` and nowhere else.
 */
export function carBasis(frame: TrackFrame, s: number, out = new Matrix4()): Matrix4 {
  const sample = sampleAt(frame, s, scratch)
  backward.copy(sample.tangent).negate()
  return out.makeBasis(sample.right, sample.up, backward)
}

/**
 * Put a car on the track at `(s, d)`, `h` metres above the surface.
 *
 * Position goes through `toWorld` and only `toWorld` — `frame.ts` stays the one
 * place `(s, d)` becomes world coordinates. The orientation needs the basis
 * vectors, which `toWorld` does not return, so `carBasis` evaluates the frame a
 * second time rather than reconstructing a position from vectors it already has.
 * That is a second *evaluation*, not a second conversion, and it costs one more
 * binary search over 1151 samples per frame.
 */
export function placeCar(
  frame: TrackFrame,
  s: number,
  d: number,
  h: number,
  outPos: Vector3,
  outQuat: Quaternion,
): void {
  toWorld(frame, s, d, h, outPos)
  outQuat.setFromRotationMatrix(carBasis(frame, s, basis))
}
