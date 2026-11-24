import { test } from "node:test"
import assert from "node:assert/strict"
import { Matrix4, Vector3 } from "three"

import { interpolateCars } from "../src/helpers/race-live.ts"
import {
  LapUnwrapper,
  WheelOdometer,
  engineYaw,
  frameAlpha,
  interpolatePoses,
  lerpAngle,
  toThreeX,
  toThreeZ,
} from "../src/components/race/view-3d/scene/live-pose.ts"
import { carColors } from "../src/components/race/view-3d/scene/car-colors.ts"
import { overviewPose, pitLaneFromRace, rotateToStart, trackFromRace } from "../src/components/race/view-3d/scene/race-track.ts"
import { poseMatrix } from "../src/components/race/view-3d/scene/car-model.ts"

const deg = (d) => (d * Math.PI) / 180
const close = (a, b, eps = 1e-9, msg) => assert.ok(Math.abs(a - b) <= eps, msg ?? `${a} != ${b} (eps ${eps})`)
/** Distância angular, sem depender da representação (+pi ou -pi). */
const angleGap = (a, b) => Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b)))

const car = (driverId, x, y, extra = {}) => ({
  driverId,
  position: 1,
  lap: 0,
  x,
  y,
  speedKmh: 180,
  tyre: "SOFT",
  tyreLifePct: null,
  pitting: false,
  gapToLeaderS: null,
  lapsBehind: 0,
  headingDeg: 0,
  progressM: null,
  sM: null,
  dM: null,
  ...extra,
})
const frame = (simTs, cars) => ({ simTs, lap: 0, weather: null, cars })

// --- heading -----------------------------------------------------------------

test("heading takes the short way across +-180 degrees", () => {
  close(angleGap(lerpAngle(deg(179), deg(-179), 0.5), Math.PI), 0)
  close(angleGap(lerpAngle(deg(-179), deg(179), 0.5), Math.PI), 0)
  close(lerpAngle(deg(170), deg(-170), 0.25), deg(175))
  close(lerpAngle(deg(-170), deg(170), 0.25), deg(-175))
  // Not across the seam: plain lerp.
  close(lerpAngle(deg(10), deg(30), 0.5), deg(20))
})

test("interpolated car heading goes through 180, never through 0", () => {
  const prev = frame(1, [car("a", 0, 0, { headingDeg: 170 })])
  const cur = frame(1.1, [car("a", -1, 0, { headingDeg: -170 })])
  for (const alpha of [0, 0.25, 0.5, 0.75, 1]) {
    const h = interpolatePoses(prev, cur, alpha).get("a").headingRad
    // Always within 10 degrees of 180, i.e. on the short arc.
    assert.ok(angleGap(h, Math.PI) <= deg(10) + 1e-9, `alpha ${alpha}: ${(h * 180) / Math.PI} deg`)
  }
  close(angleGap(interpolatePoses(prev, cur, 0.5).get("a").headingRad, Math.PI), 0, 1e-12)
})

test("missing heading falls back to the direction of motion, then to the last one", () => {
  const last = new Map()
  const prev = frame(1, [car("a", 0, 0, { headingDeg: null })])
  const cur = frame(1.1, [car("a", 0, 5, { headingDeg: null })])
  close(interpolatePoses(prev, cur, 0.5, last).get("a").headingRad, Math.PI / 2)
  const still = frame(1.2, [car("a", 0, 5, { headingDeg: null })])
  close(interpolatePoses(cur, still, 0.5, last).get("a").headingRad, Math.PI / 2)
})

test("engine heading maps to the model yaw: heading 90 deg (+y) faces three -z", () => {
  // The model faces local -Z; a yaw phi turns -Z into (-sin phi, 0, -cos phi).
  for (const h of [0, 45, 90, 180, -90, -135]) {
    const yaw = engineYaw(deg(h))
    const nose = new Vector3(-Math.sin(yaw), 0, -Math.cos(yaw))
    close(nose.x, Math.cos(deg(h)), 1e-12)
    close(nose.z, -Math.sin(deg(h)), 1e-12)
  }
})

// --- same instant as the 2D -----------------------------------------------------

test("alpha is the 2D formula: clamp((now - frameAt) / tickIntervalMs, 0, 1)", () => {
  const twoD = (now, at, dt) => Math.min(1, Math.max(0, (now - at) / dt))
  for (const [now, at, dt] of [[1000, 950, 100], [1000, 1000, 100], [900, 1000, 100], [5000, 1000, 100], [1033.3, 1000, 97.5]]) {
    assert.equal(frameAlpha(now, at, dt), twoD(now, at, dt))
  }
})

test("pose position is exactly the 2D interpolation, mapped to three as (x, -y)", () => {
  // Deterministic pseudo-random field, with a car that is new in `cur`.
  let seed = 7
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647) * 2 - 1
  const ids = ["ver", "nor", "lec", "pia", "ham", "rus", "sai", "alo", "str", "gas"]
  const prev = frame(10, ids.slice(0, 9).map((id) => car(id, rnd() * 2000, rnd() * 2000, { headingDeg: rnd() * 180 })))
  const cur = frame(10.1, ids.map((id) => car(id, rnd() * 2000, rnd() * 2000, { headingDeg: rnd() * 180, progressM: 100 })))
  for (const alpha of [0, 0.1, 0.37, 0.5, 0.99, 1]) {
    const twoD = interpolateCars(prev, cur, alpha)
    const poses = interpolatePoses(prev, cur, alpha)
    assert.equal(poses.size, twoD.size)
    for (const [id, p] of twoD) {
      const pose = poses.get(id)
      assert.equal(pose.x, p.x)
      assert.equal(pose.y, p.y)
      // What the GPU gets: the instance matrix translation.
      const m = poseMatrix(toThreeX(pose.x), toThreeZ(pose.y), engineYaw(pose.headingRad), 0.01, new Matrix4())
      const t = new Vector3().setFromMatrixPosition(m)
      close(t.x, p.x, 1e-9)
      close(-t.z, p.y, 1e-9)
      close(t.y, 0.01, 1e-12)
      close(m.determinant(), 1, 1e-9, "pose matrix must not mirror")
    }
  }
})

test("progress is interpolated when both ticks have it, otherwise the current value", () => {
  const prev = frame(1, [car("a", 0, 0, { progressM: 100 }), car("b", 0, 0, { progressM: null })])
  const cur = frame(1.1, [car("a", 0, 0, { progressM: 110 }), car("b", 0, 0, { progressM: 50 })])
  const poses = interpolatePoses(prev, cur, 0.3)
  close(poses.get("a").progressM, 103)
  assert.equal(poses.get("b").progressM, 50)
  assert.equal(interpolatePoses(null, frame(1, [car("c", 0, 0)]), 0.5).get("c").progressM, null)
})

// --- wheels and camera helpers -----------------------------------------------------

test("wheel odometer follows ground travel and keeps its phase across a resync", () => {
  const odo = new WheelOdometer()
  const f0 = frame(0, [car("a", 0, 0, { headingDeg: 0 })])
  const f1 = frame(0.1, [car("a", 6, 0, { headingDeg: 0 })])
  const f2 = frame(0.2, [car("a", 12, 0, { headingDeg: 0 })])
  odo.update(null, f0)
  close(odo.sample("a", 1), 0)
  odo.update(f0, f1)
  close(odo.sample("a", 0.5), 3)
  close(odo.sample("a", 1), 6)
  odo.update(f1, f2)
  close(odo.sample("a", 1), 12)
  // Resync (prevFrame null) somewhere else: no jump, wheels keep the shown phase.
  const far = frame(9, [car("a", 900, 40, { headingDeg: 0 })])
  odo.update(null, far)
  close(odo.sample("a", 0), 12)
  close(odo.sample("a", 1), 12)
  // Reversing turns the wheels backwards.
  const back = frame(9.1, [car("a", 897, 40, { headingDeg: 0 })])
  odo.update(far, back)
  close(odo.sample("a", 1), 9)
})

test("lap unwrapper grows through the start/finish line", () => {
  const u = new LapUnwrapper()
  assert.equal(u.next(4290, 4300), 4290)
  close(u.next(5, 4300), 4305)
  close(u.next(20, 4300), 4320)
  close(u.next(4295, 4300), 4295)
})

// --- track ---------------------------------------------------------------------------

test("waypoints are rotated so startFinishWaypoint is s = 0, without changing any point", () => {
  const pts = [[0, 0], [10, 0], [10, 10], [0, 10]]
  assert.deepEqual(rotateToStart(pts, 0), pts)
  assert.deepEqual(rotateToStart(pts, 1), [[10, 0], [10, 10], [0, 10], [0, 0]])
  assert.deepEqual(rotateToStart(pts, 3), [[0, 10], [0, 0], [10, 0], [10, 10]])
  assert.deepEqual(rotateToStart(pts, 4), pts)
  assert.deepEqual(rotateToStart(pts, -1), rotateToStart(pts, 3))
  assert.deepEqual(rotateToStart([], 2), [])

  const track = { name: "T", lengthM: 40, startFinishWaypoint: 2, widthM: null, pitLane: null, waypoints: pts }
  const scene = trackFromRace(track)
  assert.equal(scene.points.length, 4)
  assert.deepEqual(scene.points.map((p) => [p.x, p.y, p.z]), [[10, 0, -10], [0, 0, -10], [0, 0, -0], [10, 0, -0]])
  assert.equal(scene.widthM, 12)
  assert.equal(trackFromRace({ ...track, widthM: 14 }).widthM, 14)
})

test("pit lane keeps the served points in the same mapping, minus exact repeats", () => {
  const lane = pitLaneFromRace({ waypoints: [[0, 0], [0, 0], [5, -2], [9, -2]], widthM: 6, source: "estimated" })
  assert.deepEqual(lane.points.map((p) => [p.x, p.z]), [[0, -0], [5, 2], [9, 2]])
  assert.equal(lane.widthM, 6)
  assert.equal(pitLaneFromRace(null), null)
  assert.equal(pitLaneFromRace({ waypoints: [[1, 1], [1, 1]], widthM: 6, source: null }), null)
})

test("overview fits the track in the narrower field of view", () => {
  const c = new Vector3(100, 0, -50)
  const wide = overviewPose(c, 1000, 45, 16 / 9)
  const tall = overviewPose(c, 1000, 45, 9 / 16)
  assert.ok(tall.distance > wide.distance)
  close(wide.position.distanceTo(c), wide.distance, 1e-6)
  assert.ok(wide.position.y > 0)
})

// --- colours -------------------------------------------------------------------------

const driver = (driverId, teamColor, teamColorSource = null) => ({
  driverId,
  abbreviation: driverId.toUpperCase(),
  name: driverId,
  number: null,
  team: null,
  teamColor,
  teamColorSource,
  gridPosition: 0,
})

test("team colour is kept unless null or marked unknown; fallbacks are distinct", () => {
  const drivers = [
    driver("ver", "#3671C6", "openf1"),
    driver("per", "#3671C6", "openf1"),
    driver("ham", "#27F4D2"),
    driver("x1", null),
    driver("x2", "#808080", "unknown"),
    driver("x3", "#808080", "unknown"),
    driver("x4", null, null),
  ]
  const colors = carColors(drivers)
  assert.equal(colors.get("ver"), "#3671C6")
  assert.equal(colors.get("per"), "#3671C6")
  assert.equal(colors.get("ham"), "#27F4D2")

  const fallback = ["x1", "x2", "x3", "x4"].map((id) => colors.get(id).toUpperCase())
  assert.equal(new Set(fallback).size, fallback.length, `fallbacks must differ: ${fallback}`)
  for (const c of fallback) {
    assert.match(c, /^#[0-9A-F]{6}$/)
    assert.notEqual(c, "#808080")
    // Never the backend grey, nor a team colour already on track.
    assert.ok(!["#3671C6", "#27F4D2"].includes(c), `${c} collides with a team colour`)
  }
})

test("a full grey grid still gets 24 distinct colours", () => {
  const drivers = Array.from({ length: 24 }, (_, i) => driver(`p${i}`, "#808080", "unknown"))
  const colors = [...carColors(drivers).values()].map((c) => c.toUpperCase())
  assert.equal(new Set(colors).size, 24)
})
