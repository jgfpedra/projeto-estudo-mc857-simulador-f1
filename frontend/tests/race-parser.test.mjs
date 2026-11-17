import { test } from "node:test"
import assert from "node:assert/strict"
import { parseFrame, parseRaceInfo } from "../src/services/race-parser.ts"

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
