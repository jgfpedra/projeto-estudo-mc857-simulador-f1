import { useLayoutEffect, useRef } from 'react'
import type { ElementRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { PerspectiveCamera } from 'three'
import type { Camera, Vector3 } from 'three'
import type { TrackFrame } from '../track/frame'
import {
  CHASE,
  ONBOARD,
  chasePose,
  newPose,
  newRigState,
  onboardPose,
  stepRig,
} from './rig'
import type { CameraMode, FollowState } from './rig'
import type { ClockState } from '../replay/clock'

interface Props {
  frame: TrackFrame
  mode: CameraMode
  /** Written every frame by `Grid`; read here, never rendered. */
  readout: { current: FollowState }
  /** The whole-circuit framing computed once in `App`. */
  fitted: { position: Vector3; target: Vector3; far: number }
  orbitFovDeg: number
  /**
   * The replay clock, read for its rate and whether it is running.
   *
   * Read here rather than passed as a number, because pausing mutates a ref and
   * so causes no re-render: a `rate` prop would hold whatever it was at the last
   * commit and the camera would keep feeding forward through a paused replay.
   */
  clock: { current: ClockState }
  /**
   * Bumped by `App` on anything that moves the followed car discontinuously: a
   * scrub, a loop back to the start, a change of motion source. The rig cuts
   * instead of damping, exactly as it already does when the selected car changes.
   */
  cutKey: number
}

/**
 * `<Canvas camera={{ … }}>` is applied exactly once and is not reactive — r3f
 * compares `state.camera` (the instance) against the options *object*, which can
 * never match, so the re-apply branch is dead after the first commit. Per-mode
 * field of view therefore has to be mutated here, and mutating `fov` without
 * `updateProjectionMatrix` is the kind of bug that only appears when someone
 * drags the window edge: r3f's resize handler calls it for the aspect ratio and
 * silently commits whatever else was left pending.
 */
function setFov(camera: Camera, fovDeg: number): void {
  if (!(camera instanceof PerspectiveCamera) || camera.fov === fovDeg) return
  camera.fov = fovDeg
  camera.updateProjectionMatrix()
}

/**
 * Owns the camera: orbit for inspection, chase and T-cam for following a car.
 *
 * Mounted *inside* the `<Suspense>` that wraps `Grid`, immediately after it, so
 * its `useFrame` subscribes second and reads this frame's follow state rather
 * than last frame's. r3f sorts subscribers by priority with a stable sort and
 * subscribes from a layout effect, so sibling order decides among equal
 * priorities. Reading a frame late would put the car a constant `speed * delta`
 * — about a metre — too far forward in shot, which is invisible from the chase
 * camera and not invisible from the T-cam, where the car fills the frame.
 *
 * Everything here stays at priority 0. Any subscriber with a positive priority
 * switches r3f's loop to manual rendering for the whole scene
 * (`if (!state.internal.priority) gl.render(...)`, where `priority` is a count),
 * which is a large thing to take on in exchange for an ordering guarantee that
 * sibling order already gives.
 */
export function CameraRig({
  frame,
  mode,
  readout,
  fitted,
  orbitFovDeg,
  clock,
  cutKey,
}: Props) {
  const camera = useThree((s) => s.camera)
  /**
   * A ref on the component rather than `useThree(s => s.controls)`: `makeDefault`
   * publishes the instance from a *passive* effect, so the store slice is still
   * null on the first commit, and it is typed as a bare `EventDispatcher`.
   * `ElementRef` reads the real type off drei's own `ForwardRefComponent`
   * without importing `three-stdlib`, which is drei's transitive dependency and
   * not one of ours.
   */
  const controls = useRef<ElementRef<typeof OrbitControls>>(null)
  const rig = useRef(newRigState())
  const pose = useRef(newPose())
  const previous = useRef<CameraMode>(mode)

  /**
   * Establish the pose `reset()` returns to, once.
   *
   * `OrbitControls` captures `this.target0 = this.target.clone()` in its
   * constructor, and drei constructs it in `useMemo` during render — before the
   * `target` prop reaches it at commit. So `target0` is the world origin, while
   * Monza's fitted target is (478, 0, -504). Any later `reset()` would throw the
   * view half a kilometre across the map, and `position0` happens to be correct,
   * which makes the failure look half-right rather than obviously broken.
   *
   * The position is *written* rather than read, which is not belt and braces.
   * `saveState` stores whatever the camera happens to be at, and this component
   * can mount with the camera somewhere else entirely: it sits inside the
   * `<Suspense>` that waits on the car model, and during development Vite
   * remounts it on every edit while `<Canvas>` and its camera survive untouched.
   * Reading the pose there captures whatever the T-cam was last looking at and
   * enshrines it as home — which is how this was found.
   */
  useLayoutEffect(() => {
    const c = controls.current
    if (!c) return
    camera.position.copy(fitted.position)
    camera.up.set(0, 1, 0)
    c.target.copy(fitted.target)
    c.update()
    c.saveState()
  }, [fitted, camera])

  /**
   * Hand the camera between `OrbitControls` and the rig.
   *
   * A layout effect, not a passive one: passive effects in React 18 can be
   * deferred into a scheduler task and a `requestAnimationFrame` can land in
   * between, which is one frame of `OrbitControls.update()` running from the
   * cockpit pose, or of the rig writing the camera before the orbit pose was
   * saved.
   */
  useLayoutEffect(() => {
    const was = previous.current
    previous.current = mode
    if (was === mode) return
    const c = controls.current

    if (was === 'orbit') c?.saveState()

    if (mode === 'orbit') {
      /**
       * `OrbitControls` rebuilds its entire spherical basis from `camera.up` on
       * every `update()` (`quat.setFromUnitVectors(object.up, up)`). Leave the
       * T-cam's six degrees of roll on it and the orbit camera orbits a tilted
       * axis with a permanently tilted horizon — and nothing ever puts it back.
       */
      camera.up.set(0, 1, 0)
      setFov(camera, orbitFovDeg)
      c?.reset()
    } else {
      setFov(camera, mode === 'chase' ? CHASE.fovDeg : ONBOARD.fovDeg)
      // Re-seed, so entering a follow mode cuts to the car instead of damping
      // towards it from wherever the rig was left last time.
      rig.current.carIndex = -1
    }
  }, [mode, camera, orbitFovDeg])

  /**
   * Cut on a replay discontinuity.
   *
   * The same one-line mechanism as entering a follow mode above, and it needs to
   * be a *layout* effect for the same reason: layout effects run before the next
   * `requestAnimationFrame`, so `stepRig` re-seeds and the pose is applied on the
   * same frame the scrub lands on. Deferred, the camera would render one frame
   * from the old anchor — which after a scrub of a whole lap is a frame filmed
   * from the other side of the circuit.
   *
   * Invalidating `carIndex` rather than adding a field to `FollowState` keeps
   * this entirely inside the viewer: `rig.ts` already treats an unrecognised car
   * as "cut, do not damp", and a seek is the same situation — the anchor it is
   * holding describes somewhere the car no longer is.
   */
  useLayoutEffect(() => {
    rig.current.carIndex = -1
  }, [cutKey])

  useFrame((_, delta) => {
    if (mode === 'orbit') return
    const follow = readout.current
    /*
     * **The replay rate is applied here, to `dtS`, and not to `speedMps`.**
     *
     * `stepRig` uses the reported speed twice, and the two uses want different
     * things once playback is not realtime. Its feed-forward term, `u += speed *
     * dt`, wants the rate the car's arc length advances *in wall-clock time*,
     * which must go to zero when the replay is paused. `targetRoll` wants the
     * car's physical speed, because it banks on `curvature * v^2` and a corner
     * taken slowly should bank less than one taken flat.
     *
     * Scaling `dt` satisfies both at once and needs no change to `rig.ts`. The
     * feed-forward becomes `v_physical * rate * dt`, which is exactly
     * `d(sUnwrapped)/d(wall clock) * dt`; the roll keeps the physical speed; and
     * at `rate = 0` the step is zero, so both damps are no-ops and nothing
     * creeps. Reporting a rate-scaled speed instead would have fixed the
     * feed-forward and broken the roll — and paused, reporting the physical speed
     * would settle the chase camera `v * tau` (about 18 m) ahead of its target,
     * putting the car behind the camera.
     *
     * The one side effect is that the damping time constant stretches to
     * `tau / rate` in wall clock. At rate 1 and rate 0 that is exactly right, and
     * in slow motion it is arguably what you want — a camera that snaps while the
     * cars crawl is the wrong artefact. Separating them would need two quantities
     * inside `stepRig` and cannot be done from here.
     */
    const c = clock.current
    stepRig(rig.current, frame, follow, delta * (c.playing ? c.rate : 0))
    // Still `-1` means `stepRig` refused to seed off a readout that is not live
    // yet. Leave the camera where it is rather than pointing it at the origin.
    if (rig.current.carIndex < 0) return

    const p =
      mode === 'chase'
        ? chasePose(frame, rig.current, follow, CHASE, pose.current)
        : onboardPose(frame, rig.current, follow, ONBOARD, pose.current)

    camera.position.copy(p.position)
    camera.up.copy(p.up)
    camera.lookAt(p.target)
  })

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      /**
       * Not a drei prop — it falls through to `controls.enabled`, which makes
       * every pointer and wheel handler early-return *and* makes drei skip its
       * own `update()`. That is what lets the rig own the camera uncontested
       * instead of fighting a controller that recomputes position every frame.
       */
      enabled={mode === 'orbit'}
      target={fitted.target.toArray()}
      maxDistance={fitted.far * 0.4}
    />
  )
}
