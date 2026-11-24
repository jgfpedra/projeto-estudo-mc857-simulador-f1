import { test } from "node:test"
import { readFileSync } from "node:fs"
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
import { CHASE, chasePose, newFollowState, newPose, newRigState, stepRig } from "../src/components/race/view-3d/scene/camera-math.ts"
import { PIN_FADE, pinOpacity } from "../src/components/race/view-3d/scene/pin-fade.ts"
import { buildFrame, nearestS, sampleAt, toWorld } from "../src/components/race/view-3d/scene/track-frame.ts"
import { buildRibbonGeometry } from "../src/components/race/view-3d/scene/geometry.ts"
import { cornerPeaks, kappaAt, robustCurvature } from "../src/components/race/view-3d/scene/environment/curvature.ts"
import { MODELS, PEAK_SEPARATION_M, PROP_KINDS, buildLayout, propMatrix } from "../src/components/race/view-3d/scene/environment/layout.ts"
import { LAYERS, bandGeometry } from "../src/components/race/view-3d/scene/environment/surfaces.ts"
import { QUALITY } from "../src/components/race/view-3d/scene/environment/quality.ts"
import { PLAYBACK, PlaybackClock } from "../src/components/race/view-3d/scene/playback.ts"
import { smoothness } from "../src/components/race/view-3d/scene/smoothness.ts"

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

// --- environment (scene/environment/) ------------------------------------------

const TRACKS_DIR = new URL("../../backend/config/tracks/", import.meta.url)
const MODELS_DIR = new URL("../public/models/", import.meta.url)

/**
 * Port of backend/domain/pit_lane.py `ensure_pit_lane` (the estimated lane the
 * backend serves when it has no measured one), in backend (x, y) metres.
 */
function estimatePitLane(points, sf, widthM) {
  const n = points.length
  const lengths = points.map((a, i) => Math.hypot(points[(i + 1) % n][0] - a[0], points[(i + 1) % n][1] - a[1]))
  const starts = [0]
  for (const l of lengths) starts.push(starts[starts.length - 1] + l)
  const total = starts[n]
  const sfS = starts[sf]
  let before = Math.min(500, total * 0.18)
  const after = Math.min(140, total * 0.06)
  const idxAt = (s) => {
    let lo = 0
    while (lo < n - 1 && starts[lo + 1] <= s) lo++
    return lo
  }
  const pointAt = (rel) => {
    const s = (((sfS + rel) % total) + total) % total
    const i = idxAt(s)
    const a = points[i]
    const b = points[(i + 1) % n]
    const t = (s - starts[i]) / lengths[i]
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
  }
  let lastSharp = null
  for (let rel = -before; rel <= -40; rel += 5) {
    const [a, b, c] = [pointAt(rel - 10), pointAt(rel), pointAt(rel + 10)]
    const [ux, uy, vx, vy] = [b[0] - a[0], b[1] - a[1], c[0] - b[0], c[1] - b[1]]
    if (Math.abs(Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)) / 10 > 0.02) lastSharp = rel
  }
  if (lastSharp !== null) before = Math.min(before, Math.max(40, -lastSharp - 25))
  const span = before + after
  const count = Math.max(20, Math.ceil(span / 5))
  const lane = []
  for (let i = 0; i <= count; i++) {
    const rel = -before + (span * i) / count
    const s = (((sfS + rel) % total) + total) % total
    const k = idxAt(s)
    const [a, b, seg] = [points[k], points[(k + 1) % n], lengths[k]]
    const t = (s - starts[k]) / seg
    const [dx, dy] = [(b[0] - a[0]) / seg, (b[1] - a[1]) / seg]
    const ramp = Math.min(120, span * 0.25)
    let blend = Math.min(Math.min(1, Math.max(0, (rel + before) / ramp)), Math.min(1, Math.max(0, (after - rel) / ramp)))
    blend = blend * blend * (3 - 2 * blend)
    const off = (widthM / 2 + 4) * blend
    lane.push([a[0] + (b[0] - a[0]) * t + dy * off, a[1] + (b[1] - a[1]) * t - dx * off])
  }
  return { waypoints: lane, widthM: 6, source: "estimated" }
}

/** A served track as the frontend types it (`RaceTrack`), with the backend's estimated pit lane. */
function servedTrack(name, waypoints, sf, widthM) {
  return {
    name,
    lengthM: 0,
    startFinishWaypoint: sf,
    widthM,
    waypoints,
    pitLane: estimatePitLane(waypoints, sf, widthM ?? 12),
  }
}

function fileTrack(file) {
  const j = JSON.parse(readFileSync(new URL(file, TRACKS_DIR), "utf8"))
  return servedTrack(j.name, j.waypoints, j.sf_idx, j.width_m)
}

/**
 * Interlagos as OpenF1 serves it (race_3ed33fe9..., `track_source: "openf1"`,
 * GET /races/{id} on 24/11/2026): 280 points, 3.4–42.3 m apart (median 13.8 m),
 * width null, rounded to 0.1 m.
 */
const OPENF1_INTERLAGOS = [
  -352.6, -585.1, -346.8, -607, -345, -613.7, -335.5, -649.1, -326.9, -681, -322.4, -697.7, -318.3, -712.7, -311,
  -738.8, -307.4, -751.3, -304.7, -760.3, -295.5, -788.2, -291.6, -798.3, -286.9, -808.8, -280.4, -821.3, -272.9,
  -832.5, -262.8, -843, -259.4, -845.4, -251.8, -849.5, -244.3, -851.5, -238.6, -851.9, -233.7, -851.5, -228.4,
  -850.2, -221.8, -847.3, -214.8, -842.8, -207.2, -836.7, -202.9, -832.9, -196.3, -826.9, -191.2, -822.6, -185.6,
  -818.2, -171.4, -809.9, -153, -807.5, -144.8, -809.4, -136.5, -812.5, -120.4, -819.4, -111.6, -823, -104.1, -825.8,
  -91.4, -830, -76.2, -833.4, -61.9, -835.3, -52.2, -835.4, -31.2, -833.7, -3.6, -826.6, 17, -817, 34.2, -805.8, 56.1,
  -786.1, 76.2, -759.8, 80.7, -752.3, 86.8, -740.5, 94.2, -722.6, 97.2, -713.4, 104.6, -687.1, 108, -673.7, 113.6,
  -651.1, 117.5, -635.8, 120.7, -623.5, 124.2, -609.6, 127.2, -597, 134.3, -567, 139.3, -546.3, 143.1, -530.2, 148.3,
  -509.2, 151.9, -494.9, 157.1, -474.5, 160.6, -460.6, 167.4, -434.2, 176.3, -399.3, 181.5, -379.3, 190.8, -344,
  193.9, -332.2, 198.6, -314.9, 203.7, -295.3, 208.3, -278.3, 216.4, -248, 224.1, -220.3, 231.7, -193.3, 236.8, -174,
  238.9, -163.5, 240.5, -143.7, 239.4, -129.2, 237.8, -121.2, 230.2, -103, 225.7, -97, 220.1, -91.7, 208.3, -83.5,
  197.9, -78.6, 181.9, -73.7, 175.5, -72.1, 159.9, -69, 147.7, -67.5, 133.8, -66.9, 117.1, -66.9, 104.8, -67.8, 83.4,
  -71.2, 69.7, -75.5, 59.9, -79.7, 37.5, -92.9, 26.3, -101.3, 9.4, -116.3, -0.2, -126.7, -7.5, -135.6, -19.4, -152.5,
  -30.4, -168.2, -49.6, -195.3, -59.3, -209, -70.9, -225.3, -86, -247, -92, -256.1, -101.6, -270.4, -118.4, -295.2,
  -132.5, -316.2, -140.8, -328.6, -152.3, -345.5, -156.1, -351.2, -173.6, -373.7, -182.4, -382.7, -194.5, -392.2,
  -203.1, -397.4, -217.9, -403.5, -233.6, -407, -243.2, -408.3, -258.4, -408.4, -280.8, -404.1, -287.4, -401.5,
  -297.9, -396.3, -309.3, -388.9, -325.1, -373.4, -335.3, -359.3, -340.4, -350.1, -348.4, -330.2, -354.6, -305.9,
  -356.9, -294, -359.4, -277.2, -360.4, -265.4, -360.6, -257.3, -360.3, -250.1, -359.6, -243.3, -358.6, -237.1,
  -356.2, -228, -354.5, -223.2, -351, -216.1, -344.6, -208.9, -338.5, -205.7, -331.8, -204.5, -326.1, -204.6, -321.6,
  -205.5, -316, -207.3, -311.3, -209.4, -305.5, -212.2, -299, -215.7, -293.7, -218.4, -289.8, -220.4, -281.4, -224.3,
  -270.3, -227.9, -261.1, -229.3, -249.3, -228.5, -244.1, -227, -232.1, -219.2, -228, -214.4, -223.9, -206.2, -222.2,
  -199.8, -221.6, -194.4, -221.7, -188.4, -222.2, -184.1, -226, -170.5, -229.9, -162.1, -234.3, -154.5, -236.9,
  -150.5, -242.5, -143.1, -247.6, -137, -257.2, -126.7, -264.1, -119.5, -273.3, -109.6, -288.5, -90.9, -296.6, -79.6,
  -308.2, -60, -322.2, -20.1, -323.1, -9.2, -322.8, -1.7, -322.3, 3.1, -320.5, 11, -318.1, 16.3, -315.4, 20.2, -308.9,
  25.3, -305.7, 26.4, -299.9, 27.1, -291.2, 25.6, -284.1, 22.6, -277.9, 18.9, -271.9, 14.3, -265.2, 8, -256.1, -1.9,
  -249.7, -10.1, -243.4, -18.4, -235.8, -28.4, -224.6, -41.4, -213.5, -52.2, -201.1, -60.5, -197.1, -62.4, -181.8,
  -67.5, -167.8, -70.1, -155.8, -71.3, -141.3, -71.3, -120.5, -67.9, -105.9, -62.9, -95.3, -57.9, -80.6, -48.8, -64.4,
  -34.4, -55.4, -23.8, -41.2, -2.8, -31.3, 13.7, -17.9, 36.4, -7.9, 53.2, -1.4, 64.4, 1.9, 70.3, 12.8, 90.1, 16.9,
  98.5, 19.8, 105.8, 22.6, 119.1, 22.2, 131.3, 20.2, 137.6, 17.1, 144.1, 13.6, 149.4, 6.7, 156.3, 2.2, 159.6, -1.8,
  162.3, -10.2, 166.9, -17.9, 170.4, -27.2, 174, -36.3, 177.3, -46, 180.5, -65.3, 185.4, -73.6, 186.9, -85.5, 188.1,
  -99.1, 188.7, -112, 188.5, -127.3, 187.3, -134.8, 186.3, -149, 183.9, -160.3, 181.7, -185.2, 175.3, -194.1, 172.6,
  -205.6, 168.7, -231.2, 158.2, -252.7, 147.3, -263.8, 140.8, -275.8, 132.8, -289.8, 122.2, -308.3, 105.2, -324.7,
  86.9, -344.5, 58.1, -351.2, 46, -360, 27.8, -367.8, 9.1, -370.5, 1.7, -379.7, -26.9, -384.6, -45.4, -390.3, -70.6,
  -395.8, -96, -401.4, -121.6, -404.4, -137.9, -407.1, -154.2, -409.3, -170.7, -411, -186.5, -412.5, -204.3, -413.6,
  -225.4, -413.8, -230.5, -414.1, -247.4, -413.9, -264.4, -413.1, -286.6, -411, -313.6, -409.8, -323.8, -404.2,
  -362.9, -400.1, -386.7, -396.8, -403.7, -394.6, -413.8, -386.3, -451, -381.4, -471.2, -377.6, -486.6, -370.2, -516,
  -360.4, -554.8,
]
const openF1Track = () => {
  const pts = []
  for (let i = 0; i < OPENF1_INTERLAGOS.length; i += 2) pts.push([OPENF1_INTERLAGOS[i], OPENF1_INTERLAGOS[i + 1]])
  return servedTrack("Interlagos (OpenF1)", pts, 0, null)
}

/**
 * Coarse resampling of a 4 m track, the way OpenF1 position samples fall:
 * 14 m apart in slow corners up to 42 m on straights (~2.2 sqrt(R)), with
 * 0.4 m of lateral jitter. Same coordinates as the source, so corners can be
 * compared point for point.
 */
function coarsen(track) {
  const P = track.waypoints
  const n = P.length
  const radius = (i) => {
    const [a, b, c] = [P[(i - 3 + n) % n], P[i], P[(i + 3) % n]]
    const cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]) * Math.hypot(c[0] - b[0], c[1] - b[1]) * Math.hypot(c[0] - a[0], c[1] - a[1])
    return Math.abs(cr) > 1e-9 ? d / (2 * Math.abs(cr)) : Infinity
  }
  let seed = 12345
  const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647
  const out = []
  let i = track.startFinishWaypoint
  let walked = 0
  let next = 0
  for (let k = 0; k < n; k++, i = (i + 1) % n) {
    if (walked >= next) {
      const R = Math.min(radius(i), 1e6)
      const j = (i + 1) % n
      const [tx, ty] = [P[j][0] - P[i][0], P[j][1] - P[i][1]]
      const len = Math.hypot(tx, ty) || 1
      const e = (rand() - 0.5) * 0.8
      out.push([P[i][0] - (ty / len) * e, P[i][1] + (tx / len) * e])
      next = walked + Math.min(42, Math.max(14, 2.2 * Math.sqrt(R)))
    }
    walked += Math.hypot(P[(i + 1) % n][0] - P[i][0], P[(i + 1) % n][1] - P[i][1])
  }
  return servedTrack(`${track.name} (coarse)`, out, 0, null)
}

function sceneOf(raw) {
  const track = trackFromRace(raw)
  const frame = buildFrame(track.points)
  const pit = pitLaneFromRace(raw.pitLane)
  return { track, frame, pit, layout: buildLayout(frame, track.widthM, pit) }
}

const memo = new Map()
const scene = (key, make) => {
  if (!memo.has(key)) memo.set(key, sceneOf(make()))
  return memo.get(key)
}
const interlagos = () => scene("interlagos", () => fileTrack("interlagos_2023_v1.json"))
const monza = () => scene("monza", () => fileTrack("monza_2024_v1.json"))
const openf1 = () => scene("openf1", openF1Track)
const monzaCoarse = () => scene("monza-coarse", () => coarsen(fileTrack("monza_2024_v1.json")))

// Independent 2D geometry for the overlap test (does not use layout.ts helpers).
const ptSeg = (p, a, b) => {
  const [abx, abz] = [b[0] - a[0], b[1] - a[1]]
  const l2 = abx * abx + abz * abz
  const t = l2 > 0 ? Math.min(1, Math.max(0, ((p[0] - a[0]) * abx + (p[1] - a[1]) * abz) / l2)) : 0
  return Math.hypot(a[0] + abx * t - p[0], a[1] + abz * t - p[1])
}
const orient = (a, b, c) => Math.sign((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
const crosses = (a, b, c, d) => orient(a, b, c) * orient(a, b, d) < 0 && orient(c, d, a) * orient(c, d, b) < 0
const inside = (poly, p) => {
  const s = poly.map((v, i) => orient(v, poly[(i + 1) % poly.length], p))
  return s.every((x) => x >= 0) || s.every((x) => x <= 0)
}
/** Exact distance between a convex polygon and a segment. */
function polySeg(poly, a, b) {
  if (inside(poly, a) || inside(poly, b)) return 0
  let best = Infinity
  for (let i = 0; i < poly.length; i++) {
    const [c, d] = [poly[i], poly[(i + 1) % poly.length]]
    if (crosses(c, d, a, b)) return 0
    best = Math.min(best, ptSeg(a, c, d), ptSeg(b, c, d), ptSeg(c, a, b), ptSeg(d, a, b))
  }
  return best
}
/** Ground footprint(s) of a placed prop, from the same matrix the renderer uses. */
function groundFootprints(kind, p) {
  const m = MODELS[kind]
  const mat = propMatrix(kind, p)
  const spans = m.legs ?? [[m.min[0], m.max[0]]]
  return spans.map(([x0, x1]) =>
    [
      [x0, m.min[2]],
      [x1, m.min[2]],
      [x1, m.max[2]],
      [x0, m.max[2]],
    ].map(([x, z]) => {
      const v = new Vector3(x, m.min[1], z).applyMatrix4(mat)
      close(v.y, 0, 1e-6, `${kind} base must sit on the ground`)
      return [v.x, v.z]
    }),
  )
}
const segmentsOf = (points, closed) => {
  const out = []
  for (let i = 0; i < (closed ? points.length : points.length - 1); i++) {
    const [a, b] = [points[i], points[(i + 1) % points.length]]
    out.push([[a.x, a.z], [b.x, b.z]])
  }
  return out
}
/** Smallest gap (m) between a prop and a band of half-width `half` around `segs`; negative = overlap. */
function bandGap(poly, segs, half) {
  const minX = Math.min(...poly.map((v) => v[0])) - half
  const maxX = Math.max(...poly.map((v) => v[0])) + half
  const minZ = Math.min(...poly.map((v) => v[1])) - half
  const maxZ = Math.max(...poly.map((v) => v[1])) + half
  let best = Infinity
  for (const [a, b] of segs) {
    if (Math.max(a[0], b[0]) < minX - 50 || Math.min(a[0], b[0]) > maxX + 50) continue
    if (Math.max(a[1], b[1]) < minZ - 50 || Math.min(a[1], b[1]) > maxZ + 50) continue
    best = Math.min(best, polySeg(poly, a, b) - half)
  }
  return best
}

test("Kenney model boxes in layout.ts match the GLB files; gantry touches the ground only at its legs", () => {
  for (const kind of PROP_KINDS) {
    const buf = readFileSync(new URL(`${kind}.glb`, MODELS_DIR))
    const len = buf.readUInt32LE(12)
    const json = JSON.parse(buf.subarray(20, 20 + len).toString("utf8"))
    const bin = 20 + len + 8
    const min = [Infinity, Infinity, Infinity]
    const max = [-Infinity, -Infinity, -Infinity]
    const low = []
    const walk = (ni, t) => {
      const node = json.nodes[ni]
      const identity = (v, id) => !v || v.every((x, i) => Math.abs(x - id[i]) < 1e-9)
      assert.ok(identity(node.rotation, [0, 0, 0, 1]) && identity(node.scale, [1, 1, 1]) && !node.matrix, `${kind}: only translations are handled`)
      const tt = (node.translation ?? [0, 0, 0]).map((v, i) => v + t[i])
      if (node.mesh !== undefined)
        for (const prim of json.meshes[node.mesh].primitives) {
          const acc = json.accessors[prim.attributes.POSITION]
          for (let i = 0; i < 3; i++) {
            min[i] = Math.min(min[i], acc.min[i] + tt[i])
            max[i] = Math.max(max[i], acc.max[i] + tt[i])
          }
          const view = json.bufferViews[acc.bufferView]
          const stride = view.byteStride ?? 12
          const off = bin + (view.byteOffset ?? 0) + (acc.byteOffset ?? 0)
          for (let k = 0; k < acc.count; k++) {
            const y = buf.readFloatLE(off + k * stride + 4) + tt[1]
            if (y < 0.1) low.push(buf.readFloatLE(off + k * stride) + tt[0])
          }
        }
      for (const c of node.children ?? []) walk(c, tt)
    }
    for (const r of json.scenes[json.scene ?? 0].nodes) walk(r, [0, 0, 0])
    for (let i = 0; i < 3; i++) {
      close(MODELS[kind].min[i], min[i], 0.006, `${kind} min[${i}]: table ${MODELS[kind].min[i]}, file ${min[i]}`)
      close(MODELS[kind].max[i], max[i], 0.006, `${kind} max[${i}]: table ${MODELS[kind].max[i]}, file ${max[i]}`)
    }
    if (MODELS[kind].legs)
      for (const x of low)
        assert.ok(
          MODELS[kind].legs.some(([a, b]) => x >= a - 0.006 && x <= b + 0.006),
          `${kind}: vertex at ground level x=${x} is outside the legs`,
        )
  }
})

test("curvature is measured in metres: a circle gives 1/R at 4 m and at 14-42 m spacing", () => {
  const R = 90
  for (const spacing of [() => 4, (k) => [14, 42, 23, 31][k % 4]]) {
    const pts = []
    for (let a = 0, k = 0; a < Math.PI * 2 - 1e-6; k++) {
      pts.push(new Vector3(R * Math.cos(a), 0, R * Math.sin(a)))
      a += spacing(k) / R
    }
    const frame = buildFrame(pts)
    const kappa = robustCurvature(frame)
    for (let i = 0; i < pts.length; i++) {
      close(Math.abs(kappa[i]), 1 / R, 0.03 / R, `|kappa| ${kappa[i]} at ${i}`)
      // Positive = turning right: the centre is on the right.
      const toCentre = pts[i].clone().negate()
      assert.equal(Math.sign(kappa[i]), Math.sign(toCentre.dot(frame.right[i])))
    }
  }
})

test("coarse OpenF1-style Monza finds the same corners and kerbs as the 4 m file", () => {
  const fine = monza()
  const coarse = monzaCoarse()
  const gaps = coarse.frame.points.map((p, i, a) => p.distanceTo(a[(i + 1) % a.length]))
  // 14-42 m, plus at most one 4 m source step of overshoot.
  assert.ok(Math.min(...gaps) >= 13 && Math.max(...gaps) <= 46, `coarse spacing ${Math.min(...gaps)}..${Math.max(...gaps)}`)
  // Every corner tighter than R = 120 m, on both resolutions: same place, similar radius.
  // (Apexes right at the 1/70 cut-off can land on either side of it, so compare below it.)
  const corners = (sc) =>
    cornerPeaks(sc.frame, sc.layout.kappa, 1 / 120, PEAK_SEPARATION_M).map((s) => ({
      s,
      at: toWorld(sc.frame, s),
      r: 1 / Math.abs(kappaAt(sc.frame, sc.layout.kappa, s)),
    }))
  const cf = corners(fine)
  const cc = corners(coarse)
  assert.ok(cf.length >= 6, `corners on the 4 m file: ${cf.length}`)
  assert.equal(cc.length, cf.length, "same number of corners")
  for (const c of cf) {
    const m = cc.reduce((best, o) => (o.at.distanceTo(c.at) < best.at.distanceTo(c.at) ? o : best))
    assert.ok(m.at.distanceTo(c.at) < 30, `corner at s=${c.s.toFixed(0)}: nearest coarse apex ${m.at.distanceTo(c.at).toFixed(0)} m away`)
    close(m.r, c.r, 0.25 * c.r, `corner at s=${c.s.toFixed(0)}: R ${m.r.toFixed(0)} (coarse) vs ${c.r.toFixed(0)} m (4 m)`)
  }
  // Every apex the layout uses (|kappa| > 1/70) is a real corner on the other resolution too.
  for (const [x, other] of [
    [fine, cc],
    [coarse, cf],
  ])
    for (const s of x.layout.peaks) {
      const p = toWorld(x.frame, s)
      assert.ok(Math.min(...other.map((o) => o.at.distanceTo(p))) < 30, `apex at s=${s.toFixed(0)} missing on the other resolution`)
    }
  const kerbM = (sc) => sc.layout.kerbs.reduce((sum, [a, b]) => sum + b - a, 0) / sc.frame.lengthM
  close(kerbM(coarse), kerbM(fine), 0.25 * kerbM(fine), `kerb share of the lap: coarse ${kerbM(coarse)}, fine ${kerbM(fine)}`)
  // The main straight has no kerbs on either resolution.
  for (const sc of [fine, coarse]) for (const [a, b] of sc.layout.kerbs) assert.ok(a > 0 && b < sc.frame.lengthM, `kerb across the start line: ${a}..${b}`)
})

test("real OpenF1 Interlagos (280 points, width null) gets the corners of the 4 m Interlagos", () => {
  const coarse = openf1()
  assert.equal(coarse.track.widthM, 12)
  const fine = interlagos()
  assert.ok(Math.abs(coarse.layout.peaks.length - fine.layout.peaks.length) <= 1, `peaks ${coarse.layout.peaks.length} vs ${fine.layout.peaks.length}`)
  const share = (sc) => sc.layout.kerbs.reduce((sum, [a, b]) => sum + b - a, 0) / sc.frame.lengthM
  close(share(coarse), share(fine), 0.25 * share(fine), `kerb share: OpenF1 ${share(coarse)}, 4 m ${share(fine)}`)
})

test("no prop overlaps the asphalt or the pit lane (Interlagos, Monza, OpenF1 Interlagos)", () => {
  for (const [name, get] of [
    ["interlagos", interlagos],
    ["monza", monza],
    ["openf1-interlagos", openf1],
  ]) {
    const { track, frame, pit, layout } = get()
    assert.ok(pit, `${name}: pit lane`)
    const trackSegs = segmentsOf(frame.points, true)
    const pitSegs = segmentsOf(pit.points, false)
    const p = layout.props
    // The rules must actually place things, or the overlap check proves nothing.
    assert.equal(p.overheadLights.length, 1, `${name}: gantry`)
    assert.ok(p.pitsGarage.length + p.pitsOffice.length >= 15, `${name}: garages ${p.pitsGarage.length + p.pitsOffice.length}`)
    assert.ok(p.grandStandCovered.length >= 10, `${name}: main-straight grandstands ${p.grandStandCovered.length}`)
    assert.ok(p.grandStandCoveredRound.length >= 2, `${name}: corner grandstands ${p.grandStandCoveredRound.length}`)
    assert.ok(p.treeLarge.length + p.treeSmall.length >= 1500, `${name}: trees ${p.treeLarge.length + p.treeSmall.length}`)

    let worst = { gap: Infinity }
    for (const kind of PROP_KINDS)
      for (const pl of p[kind])
        for (const poly of groundFootprints(kind, pl)) {
          const gT = bandGap(poly, trackSegs, track.widthM / 2)
          const gP = bandGap(poly, pitSegs, pit.widthM / 2)
          assert.ok(gT > 0, `${name}: ${kind} at (${pl.x.toFixed(1)}, ${pl.z.toFixed(1)}) overlaps the asphalt by ${(-gT).toFixed(2)} m`)
          assert.ok(gP > 0, `${name}: ${kind} at (${pl.x.toFixed(1)}, ${pl.z.toFixed(1)}) overlaps the pit lane by ${(-gP).toFixed(2)} m`)
          if (Math.min(gT, gP) < worst.gap) worst = { gap: Math.min(gT, gP), kind }
        }
    assert.ok(worst.gap > 0.2, `${name}: tightest prop ${worst.kind} only ${worst.gap.toFixed(2)} m clear`)

    for (const kind of ["treeLarge", "treeSmall"])
      for (const t of p[kind]) {
        const d = Math.min(...trackSegs.map(([a, b]) => ptSeg([t.x, t.z], a, b)))
        assert.ok(d >= 55, `${name}: tree ${d.toFixed(1)} m from the centreline`)
      }
  }
})

test("gantry spans the track at s = 0; garages face the pit lane; main-straight stands face the track", () => {
  for (const get of [interlagos, monza, openf1]) {
    const { track, frame, pit, layout } = get()
    const g = layout.props.overheadLights[0]
    const legs = groundFootprints("overheadLights", g).map((q) => q.map(([x, z]) => new Vector3(x, 0, z)))
    const start = sampleAt(frame, 0)
    const side = legs.map((q) => Math.sign(q[0].clone().sub(start.position).dot(start.right)))
    assert.deepEqual(side.sort(), [-1, 1], "one leg on each side of the track")
    const centre = new Vector3(g.x, 0, g.z)
    assert.ok(Math.abs(centre.clone().sub(start.position).dot(start.tangent)) < 1, "gantry at s = 0")

    const facing = (kind, pl, target) => {
      const f = MODELS[kind].front
      const dir = new Vector3(f[0], 0, f[1]).applyAxisAngle(new Vector3(0, 1, 0), pl.yaw)
      return dir.dot(target.clone().sub(new Vector3(pl.x, 0, pl.z)).normalize())
    }
    const nearestOn = (points, p) => points.reduce((best, q) => (q.distanceTo(p) < best.distanceTo(p) ? q : best))
    for (const kind of ["pitsGarage", "pitsOffice"])
      for (const pl of layout.props[kind]) {
        const here = new Vector3(pl.x, 0, pl.z)
        assert.ok(facing(kind, pl, nearestOn(pit.points, here)) > 0.9, `${kind} faces the pit lane`)
        // Garages are on the far side of the pit lane, away from the racing line.
        const dPit = nearestOn(pit.points, here).distanceTo(here)
        const dTrack = nearestOn(frame.points, here).distanceTo(here)
        assert.ok(dTrack > dPit, `${kind} on the far side of the pit lane`)
      }
    for (const pl of layout.props.grandStandCovered) {
      const here = new Vector3(pl.x, 0, pl.z)
      const s = sampleAt(frame, nearestS(frame, pl.x, pl.z))
      assert.ok(facing("grandStandCovered", pl, s.position) > 0.95, "grandstand faces the track")
      // Opposite the pits.
      assert.equal(Math.sign(here.clone().sub(s.position).dot(s.right)), -layout.pitSide)
    }
    assert.ok(track.widthM > 0)
  }
})

test("layout is seeded by the track: same input, same scene; another track, another seed", () => {
  const a = sceneOf(fileTrack("monza_2024_v1.json")).layout
  const b = monza().layout
  assert.equal(a.seed, b.seed)
  assert.deepEqual(a.props, b.props)
  assert.notEqual(interlagos().layout.seed, b.seed)
})

test("kerb and sand bands start exactly at the asphalt edge, also on a coarse track", () => {
  const { track, frame, layout } = openf1()
  const h = track.widthM / 2
  const asphalt = buildRibbonGeometry(frame, track.widthM)
  const ap = asphalt.getAttribute("position")
  const n = frame.points.length
  // Right edge of the asphalt as segments (vertex 2i + 1).
  const edge = []
  for (let i = 0; i < n; i++) {
    const a = 2 * i + 1
    const b = 2 * ((i + 1) % n) + 1
    edge.push([
      [ap.getX(a), ap.getZ(a)],
      [ap.getX(b), ap.getZ(b)],
    ])
  }
  const kerb = bandGeometry(frame, h, h + 1.3, layout.kerbs, { y: LAYERS.kerb.y })
  const kp = kerb.getAttribute("position")
  assert.ok(kp.count > 20, "kerbs exist on the OpenF1 track")
  for (let v = 0; v < kp.count; v += 2) {
    const d = Math.min(...edge.map(([a, b]) => ptSeg([kp.getX(v), kp.getZ(v)], a, b)))
    assert.ok(d < 1e-3, `kerb inner edge ${d.toFixed(4)} m off the asphalt edge`)
    close(kp.getY(v), LAYERS.kerb.y, 1e-6)
  }
})

test("surface layers are stacked: distinct heights in order, nothing coplanar", () => {
  const order = ["ground", "verge", "sand", "asphalt", "lines", "kerb", "pit", "pitLines"]
  for (let i = 1; i < order.length; i++)
    assert.ok(LAYERS[order[i]].y > LAYERS[order[i - 1]].y, `${order[i]} above ${order[i - 1]}`)
  // Layers that overlap in plan also differ in polygon offset (depth order at overview distance).
  for (const [lo, hi] of [
    ["ground", "verge"],
    ["verge", "sand"],
    ["sand", "asphalt"],
    ["asphalt", "lines"],
    ["asphalt", "pit"],
    ["pit", "pitLines"],
    ["verge", "kerb"],
  ])
    assert.ok(LAYERS[hi].offset < LAYERS[lo].offset, `${hi} pulled in front of ${lo}`)
})

test("low quality: no shadows and a third of the trees; off: no environment", () => {
  assert.equal(QUALITY.high.shadows, true)
  assert.equal(QUALITY.low.shadows, false)
  assert.ok(QUALITY.low.treeFraction > 0 && QUALITY.low.treeFraction < 0.5)
  assert.equal(QUALITY.high.treeFraction, 1)
  assert.equal(QUALITY.off.environment, false)
})

// --- chase camera off-axis cap and marker fade -----------------------------------

test("chase camera keeps a settled, stopped car within 8 degrees of the view axis, even in a 25 m hairpin", () => {
  const R = 25
  const pts = []
  for (let k = 0; k < 40; k++) {
    const a = (k / 40) * Math.PI * 2
    pts.push(new Vector3(R * Math.cos(a), 0, R * Math.sin(a)))
  }
  const frame = buildFrame(pts)
  const offAxis = (cfg) => {
    const follow = newFollowState()
    const s = 40
    const at = toWorld(frame, s)
    Object.assign(follow, { sUnwrapped: s, speedMps: 0, carIndex: 0, posed: true, x: at.x, z: at.z })
    const rig = newRigState()
    for (let i = 0; i < 200; i++) stepRig(rig, frame, follow, 1 / 60, cfg)
    const p = chasePose(frame, rig, follow, cfg, newPose())
    const yaw = (v) => Math.atan2(v.x, v.z)
    const toCar = p.anchor.clone().sub(p.position)
    const toTarget = p.target.clone().sub(p.position)
    return { gap: angleGap(yaw(toCar), yaw(toTarget)), behind: Math.abs(rig.u - (s - cfg.trailM)) }
  }
  const free = offAxis({ ...CHASE, maxOffAxisRad: Math.PI })
  assert.ok(free.gap > deg(20), `uncapped the car is ${(free.gap * 180) / Math.PI} deg off axis (test must be meaningful)`)
  const capped = offAxis(CHASE)
  assert.ok(capped.gap <= CHASE.maxOffAxisRad + 1e-9, `capped: ${(capped.gap * 180) / Math.PI} deg`)
  // Speed 0 (a frozen clock): the rig settles exactly trailM behind the car.
  assert.ok(capped.behind < 1e-6, `rig ${capped.behind} m off the trail`)
})

test("car markers fade in only far from the cars: opaque at overview distance, gone in close views", () => {
  const D = 1500
  assert.equal(pinOpacity(D * 0.63, D), 1, "nearest car in the overview is >= 0.63 D away")
  assert.equal(pinOpacity(D, D), 1)
  assert.equal(pinOpacity(110, D), 0, "grid view")
  assert.equal(pinOpacity(40, D), 0, "corner / chase")
  const mid = pinOpacity(((PIN_FADE.from + PIN_FADE.to) / 2) * D, D)
  close(mid, 0.5, 1e-9)
  // Monotonic in between.
  let prev = -1
  for (let k = 0; k <= 20; k++) {
    const v = pinOpacity((PIN_FADE.from + ((PIN_FADE.to - PIN_FADE.from) * k) / 20) * D, D)
    assert.ok(v >= prev)
    prev = v
  }
})

// --- buffered playback ------------------------------------------------------------

/**
 * A car lapping a 150 m circle at 45-75 m/s (speed changing like braking and
 * accelerating), ticks every 0.1 s of sim time. `arrivals(k)` gives the wall
 * time (ms) at which tick k reaches the page; the render loop runs at 60 Hz
 * (`renderAt` can drop frames for a stalled main thread). Each rendered
 * frame pushes the ticks that arrived, samples the clock (or, for the old
 * path, the live-edge alpha) and records the followed car's drawn pose.
 */
function simulatePlayback({ arrivals, seconds = 60, mode = "buffered", renderAt = () => true, simRate = 1, skipS = 2 }) {
  const R = 150
  const speed = (s) => 60 + 15 * Math.sin(s * 0.7)
  const angleAt = (s) => (60 * s - (15 / 0.7) * (Math.cos(s * 0.7) - 1)) / R
  const tick = (k) => {
    const s = Math.round(k) / 10
    const th = angleAt(s)
    return frame(s, [
      car("ver", R * Math.cos(th), R * Math.sin(th), { headingDeg: ((th + Math.PI / 2) * 180) / Math.PI, speedKmh: speed(s) * 3.6 }),
    ])
  }
  const nTicks = Math.ceil((seconds * 10) * simRate) + 20
  const arr = Array.from({ length: nTicks }, (_, k) => arrivals(k))
  const clock = new PlaybackClock()
  const store = { frame: null, prevFrame: null, frameAt: 0, tickIntervalMs: 100 }
  const trace = []
  const drawn = []
  let next = 0
  for (let w = 0; w < seconds * 1000; w += 1000 / 60) {
    if (!renderAt(w)) continue
    while (next < nTicks && arr[next] <= w) {
      const at = arr[next]
      const f = tick(next)
      // The store's tick handler, as in live-race-store.ts.
      const measured = store.frameAt > 0 ? at - store.frameAt : 0
      if (measured > 0 && measured < 1000) store.tickIntervalMs = 0.8 * store.tickIntervalMs + 0.2 * measured
      store.prevFrame = store.frame
      store.frame = f
      store.frameAt = at
      clock.push(f, at)
      next++
    }
    if (!store.frame) continue
    let prev, cur, alpha, resyncs, s
    if (mode === "buffered") {
      s = clock.sample(w)
      ;({ prev, cur, alpha, resyncs } = s)
    } else {
      prev = store.prevFrame
      cur = store.frame
      alpha = frameAlpha(w, store.frameAt, store.tickIntervalMs)
      resyncs = 0
    }
    const pose = interpolatePoses(prev, cur, alpha).get("ver")
    trace.push({ wallMs: w, x: pose.x, y: pose.y, headingRad: pose.headingRad, resyncs })
    drawn.push({ w, s, newestTs: store.frame.simTs })
  }
  return { stats: smoothness(trace.filter((t) => t.wallMs >= skipS * 1000)), trace, drawn, clock }
}

/** Seeded uniform in [-1, 1). */
function rng(seed) {
  let x = seed
  return () => ((x = (x * 16807) % 2147483647) / 2147483647) * 2 - 1
}

/** +-30 ms jitter around a 100 ms tick; every 20 ticks the server flushes 3 ticks at once. */
function jitterWithBursts(seed) {
  const r = rng(seed)
  const jitter = Array.from({ length: 2000 }, () => 30 * r())
  return (k) => {
    // Burst: ticks 20m+1 and 20m+2 arrive 1 ms and 2 ms after tick 20m.
    const pos = k % 20
    if (k >= 20 && (pos === 1 || pos === 2)) return 100 * (k - pos) + jitter[k - pos] + pos
    return 100 * k + jitter[k]
  }
}

test("live-edge baseline: +-30 ms tick jitter makes the followed car stall and jump", () => {
  const { stats } = simulatePlayback({ arrivals: jitterWithBursts(11), mode: "live" })
  assert.ok(stats.spread > 0.1, `baseline spread ${stats.spread}`)
  assert.ok(stats.stalls + stats.jumps > 0, JSON.stringify(stats))
})

test("buffered playback: +-30 ms jitter plus 3-tick bursts -> spread < 0.05, no stalls, jumps or backwards steps", () => {
  for (const seed of [11, 12, 13]) {
    const { stats, drawn } = simulatePlayback({ arrivals: jitterWithBursts(seed) })
    assert.ok(stats.frames > 3000, JSON.stringify(stats))
    assert.ok(stats.spread < 0.05, `seed ${seed}: ${JSON.stringify(stats)}`)
    assert.equal(stats.stalls, 0, JSON.stringify(stats))
    assert.equal(stats.jumps, 0, JSON.stringify(stats))
    assert.equal(stats.backwards, 0, JSON.stringify(stats))
    // Sim time only moves forward, never past the newest tick, and settles ~150 ms behind it.
    for (let i = 1; i < drawn.length; i++) {
      assert.ok(drawn[i].s.simTs >= drawn[i - 1].s.simTs, "sim time went backwards")
      assert.ok(drawn[i].s.simTs <= drawn[i].newestTs + 1e-12, "extrapolated past the newest tick")
    }
    const tail = drawn.slice(600)
    assert.equal(tail.filter((d) => d.s.held).length, 0, "held at the newest tick")
    const meanLag = tail.reduce((a, d) => a + d.s.lagMs, 0) / tail.length
    assert.ok(Math.abs(meanLag - PLAYBACK.delayMs) < 10, `mean lag ${meanLag} ms`)
    assert.ok(tail.every((d) => Math.abs(d.s.rate - 1) <= PLAYBACK.maxNudge + 0.01), "rate nudge outside +-5%")
  }
})

test("buffered playback: a 250 ms main-thread stall (render loop paused, 3 ticks queued) is absorbed", () => {
  const r = rng(5)
  const jitter = Array.from({ length: 2000 }, () => 30 * r())
  // Every 4 s the page renders nothing for 250 ms; the ticks that arrive meanwhile are handled together.
  const { stats } = simulatePlayback({ arrivals: (k) => 100 * k + jitter[k], renderAt: (w) => w % 4000 < 3750 })
  assert.ok(stats.spread < 0.05, JSON.stringify(stats))
  assert.equal(stats.stalls + stats.jumps + stats.backwards, 0, JSON.stringify(stats))
})

test("buffered playback: ticks queued behind a 1.5 s busy page (e.g. mounting the 3D) do not speed it up", () => {
  const r = rng(21)
  const jitter = Array.from({ length: 2000 }, () => 30 * r())
  // 6 s in: the page renders nothing for 1.5 s and the ticks of that time are handled together at the end.
  const busy = (w) => w >= 6000 && w < 7500
  const arrivals = (k) => (busy(100 * k + jitter[k]) ? 7500 : 100 * k + jitter[k])
  const { drawn, clock } = simulatePlayback({ arrivals, renderAt: (w) => !busy(w), seconds: 20 })
  close(clock.rate, 1, 0.01)
  const after = drawn.filter((d) => d.w >= 9000)
  assert.equal(after.filter((d) => d.s.held).length, 0, "held at the newest tick after the stall")
  const meanLag = after.reduce((a, d) => a + d.s.lagMs, 0) / after.length
  assert.ok(Math.abs(meanLag - PLAYBACK.delayMs) < 15, `mean lag ${meanLag} ms`)
})

test("buffered playback: a tick later than the buffer can absorb holds at the newest tick, never extrapolates or goes back", () => {
  const r = rng(9)
  const jitter = Array.from({ length: 2000 }, () => 10 * r())
  // Every 3 s, tick k is 200 ms late and tick k+1 100 ms late: both arrive with k+2.
  const arrivals = (k) => (k % 30 === 10 ? 100 * (k + 2) : k % 30 === 11 ? 100 * (k + 1) : 100 * k + jitter[k])
  const { stats, drawn } = simulatePlayback({ arrivals })
  assert.equal(stats.backwards, 0)
  assert.ok(drawn.some((d) => d.s.held), "expected the clock to hold")
  for (let i = 1; i < drawn.length; i++) {
    assert.ok(drawn[i].s.simTs >= drawn[i - 1].s.simTs)
    assert.ok(drawn[i].s.simTs <= drawn[i].newestTs + 1e-12)
  }
  // No resync for a short hold: the clock slows down by at most 5% and rebuilds the delay.
  assert.equal(drawn.at(-1).s.resyncs, drawn[0].s.resyncs)
})

test("buffered playback follows a simulation slower than real time (0.9x)", () => {
  const r = rng(3)
  const jitter = Array.from({ length: 2000 }, () => 30 * r())
  // The rate starts at 1 (the engine runs in real time) and is learned from 2 s of ticks: measured from 4 s on.
  const { stats, drawn, clock } = simulatePlayback({ arrivals: (k) => (100 * k) / 0.9 + jitter[k], simRate: 0.9, skipS: 4 })
  close(clock.rate, 0.9, 0.02)
  assert.ok(stats.spread < 0.05, JSON.stringify(stats))
  assert.equal(stats.stalls + stats.jumps + stats.backwards, 0, JSON.stringify(stats))
  const tail = drawn.slice(1200)
  const meanLag = tail.reduce((a, d) => a + d.s.lagMs, 0) / tail.length
  assert.ok(Math.abs(meanLag - PLAYBACK.delayMs) < 20, `mean lag ${meanLag} ms`)
})

test("buffered playback starts the target delay behind the newest tick on its first frame, however long the scene took to load", () => {
  const f = (ts) => frame(ts, [car("ver", ts * 50, 0)])
  const clock = new PlaybackClock()
  // Ticks from the mount on; the first rendered frame comes 0.8 s later (models, shaders).
  for (let k = 0; k <= 8; k++) clock.push(f(k / 10), k * 100)
  const s = clock.sample(816)
  close(s.lagMs, PLAYBACK.delayMs, 1e-6)
  assert.equal(s.held, false)
})

test("buffered playback resyncs on a snapshot, a sim-time gap, time going back, or a lag over 1 s", () => {
  const f = (ts) => frame(ts, [car("ver", ts * 50, 0)])
  const clock = new PlaybackClock()
  assert.equal(clock.sample(0), null)
  let s
  for (let k = 0; k <= 20; k++) {
    clock.push(f(k / 10), k * 100)
    s = clock.sample(k * 100 + 16)
  }
  assert.equal(s.resyncs, 2)
  // Same simTs replaces the frame (e.g. a weather change), no resync.
  clock.push(f(2), 2010)
  assert.equal(clock.sample(2016).resyncs, 2)
  // Snapshot (the store clears prevFrame).
  clock.push(f(2.1), 2100, true)
  s = clock.sample(2116)
  assert.equal(s.resyncs, 3)
  assert.equal(s.prev, null, "nothing older than the snapshot is kept")
  // Gap of more than 1 s of sim time.
  clock.push(f(5), 2200)
  assert.equal(clock.sample(2216).resyncs, 4)
  // Time going back (another race on the same socket).
  clock.push(f(1), 2300)
  assert.equal(clock.sample(2316).resyncs, 5)
  // No frames for 2 s: the clock holds at the newest...
  for (let k = 1; k <= 10; k++) {
    clock.push(f(Math.round(10 + k) / 10), 2300 + k * 100)
    clock.sample(2316 + k * 100)
  }
  s = clock.sample(5400)
  assert.ok(s.held)
  close(s.simTs, 2, 1e-9)
  // ...and when ticks resume more than 1 s ahead of it, it jumps instead of crawling at +5%.
  for (let k = 1; k <= 9; k++) clock.push(f(Math.round(20 + k) / 10), 5400 + k * 10)
  assert.equal(clock.sample(5500).resyncs, 5, "0.9 s behind: still within the 1 s budget")
  for (let k = 0; k <= 4; k++) clock.push(f(Math.round(30 + k) / 10), 5600 + k * 10)
  s = clock.sample(5716)
  assert.equal(s.resyncs, 6, `${3.4 - s.simTs} s behind`)
  close(s.simTs, 3.4 - PLAYBACK.delayMs / 1000, 1e-9)
})

test("smoothness metric: uniform motion is 0 spread; a 3-frame stall counts 3 stalls and its catch-up jump", () => {
  const line = (n, stall = -1) => {
    const out = []
    let x = 0
    for (let i = 0; i < n; i++) {
      if (!(i >= stall && i < stall + 3)) x += 1
      if (i === stall + 3) x += 3
      out.push({ wallMs: i * 16, x, y: 0, headingRad: 0, resyncs: 0 })
    }
    return out
  }
  const smooth = smoothness(line(200))
  close(smooth.spread, 0, 1e-12)
  assert.equal(smooth.stalls + smooth.jumps + smooth.backwards, 0)
  const bumpy = smoothness(line(200, 100))
  assert.equal(bumpy.stalls, 3)
  assert.equal(bumpy.jumps, 1)
  const back = line(100)
  back[50].x -= 2
  assert.equal(smoothness(back).backwards, 1)
})
