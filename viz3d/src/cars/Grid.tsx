import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useGLTF } from '@react-three/drei'
import { Color, DynamicDrawUsage, InstancedMesh, Matrix4 } from 'three'
import type { MeshBasicMaterial } from 'three'
import { wrapS } from '../track/frame'
import type { TrackFrame } from '../track/frame'
import type { FollowState } from '../cameras/rig'
import { RACE_CAR_RED, carGeometry } from './model'
import type { CarPart } from './model'
import { carMatrix, poseMatrix, wheelAngle, wheelMatrix } from './instance'
import { newMotionState } from './motion'
import { wheelMarkerGeometry, wheelMarkerMaterial } from './wheelMarker'
import type { CarIdentity, MotionSource } from './motion'
import { stepClock } from '../replay/clock'
import type { ClockState } from '../replay/clock'

/**
 * Clearance between the tyres and the track surface, metres.
 *
 * **This constant owns the clearance**, and `model.ts` owns the datum. The
 * adapter's job is to say where the model's lowest point is — it puts it at
 * exactly y = 0, which is a fact about the *model* and stays exactly testable.
 * How far off a surface the car then sits is a fact about *placement*, which is
 * what `h` means in `placeCar`. One number to change, not two that must agree.
 *
 * Not zero. The tyres end in flat facets — 64 of the model's vertices sit at
 * exactly the lowest point, 16 per wheel — so at y = 0 they are coplanar with
 * the ribbon. No z-fighting could actually be produced from that (the facet is
 * the underside of an opaque wheel, occluded in every view), so this is cheap
 * insurance rather than a measured fix, and a plausible ride height besides.
 */
const RIDE_HEIGHT_M = 0.01

interface Props {
  frame: TrackFrame
  /** Who the cars are. Identity only; where they are comes from `source`. */
  cars: CarIdentity[]
  /** Where they are, at a time. Synthetic field or telemetry replay. */
  source: MotionSource
  /** Replay time. Advanced here, read by the timeline and the camera rig. */
  clock: { current: ClockState }
  /** Index of the car the panel is following. */
  selected: number
  /**
   * Written every frame for `CarPanel` to read and for `CameraRig` to follow,
   * without re-rendering React either way.
   */
  readout: { current: FollowState }
  /**
   * Debug: one contrasting stripe per wheel, so spin is visible on the uniform
   * grey Kenney tyres. Off by default. See `wheelMarker.ts`.
   */
  wheelMarkers?: boolean
}

/** One `InstancedMesh` per primitive: geometry and material are already final. */
function instanced(part: CarPart, count: number): InstancedMesh {
  const mesh = new InstancedMesh(part.geometry, part.material, count)
  mesh.instanceMatrix.setUsage(DynamicDrawUsage)
  // The field is spread around the whole lap, so the instance bounding volume
  // spans the circuit and culling it as one object can only ever be wrong.
  mesh.frustumCulled = false
  return mesh
}

/**
 * The field on track.
 *
 * **This component integrates nothing.** It used to keep two `Float64Array`s per
 * frame — a wrapped arc length and an unwrapped odometer — and advance both by
 * `speed * delta` for every car. Now there is one clock, and position is a pure
 * function of it: `source.sampleInto(t, car)`. Three things follow, and they are
 * the reason the refactor was worth doing rather than bolting a replay on beside
 * the synthetic field.
 *
 * The wheel odometer is **derived**, `sUnwrapped - originM(car)`, not
 * accumulated. So wheel phase is a function of position, and scrubbing a replay
 * backwards rewinds the wheels instead of leaving them wherever an accumulator
 * had got to.
 *
 * `MAX_DELTA_S` is applied once, by the clock, instead of twenty times a frame —
 * and `rig.ts` no longer has to agree with a constant `Grid` also uses.
 *
 * And the two sources are interchangeable here, so the synthetic field stays
 * selectable as a comparison rather than being replaced. That matters more than
 * it sounds: real telemetry against this centreline turns out to carry almost no
 * lateral information, so the synthetic field is the only thing on screen that
 * exercises `d` across the width of the ribbon.
 */
export function Grid({
  frame,
  cars,
  source,
  clock,
  selected,
  readout,
  wheelMarkers = false,
}: Props) {
  const { scene } = useGLTF(RACE_CAR_RED.url)
  const parts = useMemo(() => carGeometry(scene), [scene])
  const checked = useRef(false)

  const meshes = useMemo(() => {
    const body = parts.body.map((p) => instanced(p, cars.length))
    const wheels = parts.wheels.map((w) => ({
      wheel: w,
      meshes: w.parts.map((p) => instanced(p, cars.length)),
      // Built always, drawn and updated only when the toggle is on. Driven by
      // the same `wheelMatrix` as the tyre, so it cannot disagree with it.
      marker: instanced(
        { name: `${w.name}-marker`, geometry: wheelMarkerGeometry(w), material: wheelMarkerMaterial(), paint: false },
        cars.length,
      ),
    }))
    // Paint, once. Everything else stays the material's own colour.
    const colour = new Color()
    body.forEach((mesh, i) => {
      if (!parts.body[i].paint) return
      cars.forEach((car, k) => mesh.setColorAt(k, colour.set(car.hex)))
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
    })
    return { body, wheels }
  }, [parts, cars])

  useEffect(() => {
    checked.current = false
  }, [source])

  useEffect(
    () => () => {
      for (const m of meshes.body) m.dispose()
      for (const w of meshes.wheels) for (const m of w.meshes) m.dispose()
      for (const w of meshes.wheels) {
        w.marker.dispose()
        w.marker.geometry.dispose()
        ;(w.marker.material as MeshBasicMaterial).dispose()
      }
      for (const p of parts.body) p.geometry.dispose()
      for (const w of parts.wheels) for (const p of w.parts) p.geometry.dispose()
    },
    [meshes, parts],
  )

  const car = useMemo(() => new Matrix4(), [])
  const wheel = useMemo(() => new Matrix4(), [])
  /** Reused every car every frame; `sampleInto` writes into it. */
  const motion = useMemo(() => newMotionState(), [])

  useFrame((_, delta) => {
    stepClock(clock.current, delta, source.durationS)
    const tS = clock.current.tS
    let worstDet = Infinity

    for (let i = 0; i < cars.length; i++) {
      source.sampleInto(tS, i, motion)
      const arc = wrapS(frame, motion.sUnwrapped)
      // The engine knows where its cars are; everything else is `(s, d)`.
      if (motion.posed) poseMatrix(motion.x, motion.z, motion.yawRad, RIDE_HEIGHT_M, car)
      else carMatrix(frame, arc, motion.d, RIDE_HEIGHT_M, car)
      if (!checked.current) worstDet = Math.min(worstDet, car.determinant())
      for (const m of meshes.body) m.setMatrixAt(i, car)

      // Distance travelled, not elapsed time: the wheels must stay tied to the
      // ground speed, so they slow when the car does. Derived from `sUnwrapped`
      // rather than accumulated, so it survives a scrub.
      const travelled = motion.sUnwrapped - source.originM(i)
      for (const w of meshes.wheels) {
        wheelMatrix(car, w.wheel, wheelAngle(travelled, w.wheel.radiusM), wheel)
        if (!checked.current) worstDet = Math.min(worstDet, wheel.determinant())
        for (const m of w.meshes) m.setMatrixAt(i, wheel)
        if (wheelMarkers) w.marker.setMatrixAt(i, wheel)
      }

      if (i === selected) {
        // Mutated in place rather than replaced: this runs sixty times a second
        // and the consumers only ever read fields off it.
        const out = readout.current
        out.s = arc
        out.sUnwrapped = motion.sUnwrapped
        out.d = motion.d
        out.speedMps = motion.speedMps
        out.carIndex = selected
      }
    }

    for (const m of meshes.body) m.instanceMatrix.needsUpdate = true
    for (const w of meshes.wheels) for (const m of w.meshes) m.instanceMatrix.needsUpdate = true
    if (wheelMarkers) for (const w of meshes.wheels) w.marker.instanceMatrix.needsUpdate = true

    /*
     * Check J, the instanced sibling of `TrackRibbon`'s determinant check. Every
     * instance matrix here is *composed* rather than assigned, and composition
     * is where a mirror gets back in — one negative scale component and the
     * whole field is inside out while every data check still passes. Once per
     * source, on the first populated frame, over every matrix handed to the GPU.
     */
    if (!checked.current && cars.length > 0) {
      checked.current = true
      const n = cars.length * (1 + meshes.wheels.length)
      console.log(
        `${worstDet > 0 ? 'PASS' : 'FAIL'}  [J] Instance matrices apply no mirroring — ` +
          `${n} matrices from the ${source.kind} source, smallest determinant ` +
          `${worstDet.toFixed(3)} (expect > 0)`,
      )
    }
  })

  return (
    <>
      {meshes.body.map((m, i) => (
        <primitive key={`body${i}`} object={m} />
      ))}
      {meshes.wheels.map((w, i) =>
        w.meshes.map((m, k) => <primitive key={`wheel${i}-${k}`} object={m} />),
      )}
      {wheelMarkers &&
        meshes.wheels.map((w, i) => <primitive key={`marker${i}`} object={w.marker} />)}
    </>
  )
}
