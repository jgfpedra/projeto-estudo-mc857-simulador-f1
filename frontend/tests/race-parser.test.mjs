import { test } from "node:test"
import assert from "node:assert/strict"
import { parseFrame, parseLiveMessage, parseRaceInfo } from "../src/services/race-parser.ts"

const race = (track) => ({ race_id: "race-1", num_laps: 3, track })
const track = { name: "Interlagos", waypoints: [[0, 0], [100, 0], [100, 100]], width_m: 14 }

test("preserves the backend's open pit lane and track widths", () => {
  const pit = { waypoints: [[0, 0], [15, -8], [75, -8], [100, 0]], width_m: 6, source: "estimated" }
  const parsed = parseRaceInfo(race({ ...track, pit_lane: pit }))
  assert.deepEqual(parsed.track.pitLane, { waypoints: pit.waypoints, widthM: 6, source: "estimated" })
  assert.equal(parsed.track.widthM, 14)
})

test("accepts older races without a pit lane or width", () => {
  const parsed = parseRaceInfo(race({ waypoints: track.waypoints }))
  assert.equal(parsed.track.pitLane, null)
  assert.equal(parsed.track.widthM, null)
})

test("does not draw an incomplete or invalid pit lane", () => {
  for (const pit_lane of [
    { waypoints: [[1, 2]], width_m: 6 },
    { waypoints: [[1, 2], [null, 3], [4, 5]], width_m: 6 },
    { waypoints: [[1, 2], [4, 5]], width_m: 0 },
    { waypoints: [[1, 2], [4, 5]] },
  ]) {
    assert.equal(parseRaceInfo(race({ ...track, pit_lane })).track.pitLane, null)
  }
})


test("uses the leader lap in an older snapshot and falls back for legacy ticks", () => {
  assert.equal(parseFrame({ sim_ts: 200, lap: 1, leader_lap: 2, positions: [] }).lap, 2)
  assert.equal(parseFrame({ sim_ts: 200, lap: 1, positions: [] }).lap, 1)
})

const tick = (car) => ({ sim_ts: 12.5, leader_lap: 1, positions: [car] })
const baseCar = { driver_id: "ver", position: 1, lap: 1, position_xy: [10, -4], heading_deg: 90 }

test("reads progress, s and d of each car for the 3D view", () => {
  const [car] = parseFrame(tick({ ...baseCar, progress_m: 5123.5, s_m: 812.25, d_m: -1.5 })).cars
  assert.equal(car.progressM, 5123.5)
  assert.equal(car.sM, 812.25)
  assert.equal(car.dM, -1.5)
  // Zero is a real value, not a missing one.
  const [atLine] = parseFrame(tick({ ...baseCar, progress_m: 0, s_m: 0, d_m: 0 })).cars
  assert.deepEqual([atLine.progressM, atLine.sM, atLine.dM], [0, 0, 0])
})

test("keeps progress, s and d null when absent, null or invalid", () => {
  for (const extra of [{}, { progress_m: null, s_m: null, d_m: null }, { progress_m: "1", s_m: Number.NaN, d_m: Infinity }]) {
    const [car] = parseFrame(tick({ ...baseCar, ...extra })).cars
    assert.equal(car.progressM, null)
    assert.equal(car.sM, null)
    assert.equal(car.dM, null)
    // The 2D fields are unchanged.
    assert.deepEqual([car.x, car.y, car.headingDeg], [10, -4, 90])
  }
})

test("reads the chassis geometry and rejects incomplete or non-positive boxes", () => {
  const ok = parseRaceInfo({ ...race(track), car_geometry: { length_m: 5, width_m: 1.8, height_m: 0.7 } })
  assert.deepEqual(ok.carGeometry, { lengthM: 5, widthM: 1.8, heightM: 0.7 })
  assert.equal(parseRaceInfo(race(track)).carGeometry, null)
  for (const car_geometry of [
    null,
    { length_m: 5, width_m: 1.8 },
    { length_m: 5, width_m: 0, height_m: 0.7 },
    { length_m: -5, width_m: 1.8, height_m: 0.7 },
    { length_m: "5", width_m: 1.8, height_m: 0.7 },
  ]) {
    assert.equal(parseRaceInfo({ ...race(track), car_geometry }).carGeometry, null)
  }
})

test("reads the team colour source and keeps it null when absent", () => {
  const drivers = [
    { driver_id: "ver", team_color: "#3671C6", team_color_source: "openf1" },
    { driver_id: "p01", team_color: "#808080", team_color_source: "unknown" },
    { driver_id: "ham", team_color: "#27F4D2" },
    { driver_id: "nor", team_color: null, team_color_source: null },
  ]
  const parsed = parseRaceInfo({ ...race(track), drivers }).drivers
  assert.deepEqual(parsed.map((d) => d.teamColorSource), ["openf1", "unknown", null, null])
  assert.deepEqual(parsed.map((d) => d.teamColor), ["#3671C6", "#808080", "#27F4D2", null])
})

test("preserves the race id when parsing a recovery event", () => {
  assert.deepEqual(
    parseLiveMessage({ type: "race_recovered", sim_ts: 42.5, race_id: "race-1" }),
    { kind: "race_recovered", simTs: 42.5, raceId: "race-1" },
  )
  assert.equal(parseLiveMessage({ type: "race_recovered", sim_ts: 42.5 }), null)
})
