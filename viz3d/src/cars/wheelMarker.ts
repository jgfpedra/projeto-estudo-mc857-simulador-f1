import { Box3, BoxGeometry, Matrix4, MeshBasicMaterial, Vector3 } from 'three'
import type { BufferGeometry } from 'three'
import type { CarWheel } from './model'

/**
 * Debug aid: one contrasting stripe per wheel, so wheel spin can be seen.
 *
 * The Kenney wheels are uniform grey with no tread, so a correctly spinning
 * wheel, a stopped one and a backwards one all look the same. This puts one
 * stripe on each: a bar from the hub out past the rim, across the full width
 * of the tyre, so it shows on both side faces and crosses the tread once a
 * turn.
 *
 * **One-sided on purpose.** A bar across the whole diameter would look the same
 * after half a turn, which halves the rotation an observer can tell apart and
 * makes the aliasing below worse. Hub to rim only, so the pattern repeats once
 * per turn and no sooner.
 *
 * Watch it at 0.25x, not 1x. At 60 m/s the 0.387 m wheel turns ~148 deg per
 * 60 fps frame, which reads as slow backwards rotation (the wagon-wheel effect)
 * whatever the wheel is really doing.
 *
 * Off by default. Geometry is built in the same wheel-centred, car-local space
 * as the wheel parts, so `wheelMatrix` places it with no extra transform and it
 * cannot drift from the wheel it marks.
 */
export const WHEEL_MARKER_COLOUR = '#ffe600'

/** How far the stripe pokes out past the tyre, so it never z-fights with it. */
const OVERHANG = 1.04

export function wheelMarkerGeometry(wheel: CarWheel): BufferGeometry {
  // Tyre width along the axle, measured off the wheel's own parts rather than
  // written down, for the same reason `radiusM` is.
  const box = new Box3()
  for (const p of wheel.parts) {
    p.geometry.computeBoundingBox()
    if (p.geometry.boundingBox) box.union(p.geometry.boundingBox)
  }
  const axle = wheel.axle.clone().normalize()
  const size = box.isEmpty() ? new Vector3() : box.getSize(new Vector3())
  const widthM = Math.max(Math.abs(size.dot(axle)), wheel.radiusM * 0.5)

  // Any direction perpendicular to the axle will do for the stripe's length;
  // prefer car-local up so the stripe starts out pointing at the sky.
  const up = new Vector3(0, 1, 0)
  const radial = (Math.abs(axle.dot(up)) > 0.9 ? new Vector3(0, 0, 1) : up)
    .clone()
    .addScaledVector(axle, -axle.dot(up))
    .normalize()
  const tangential = new Vector3().crossVectors(axle, radial)

  const length = wheel.radiusM * OVERHANG
  const geometry = new BoxGeometry(widthM * OVERHANG, length, wheel.radiusM * 0.22)
  geometry.translate(0, length / 2, 0)
  // Box axes (x, y, z) -> (axle, radial, tangential).
  geometry.applyMatrix4(new Matrix4().makeBasis(axle, radial, tangential))
  geometry.computeBoundingSphere()
  return geometry
}

/** Unlit, so the stripe stays the same colour on the shaded side of the car. */
export function wheelMarkerMaterial(): MeshBasicMaterial {
  return new MeshBasicMaterial({ color: WHEEL_MARKER_COLOUR })
}
