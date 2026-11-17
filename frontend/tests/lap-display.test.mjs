import { test } from "node:test"
import assert from "node:assert/strict"
import { currentLap } from "../src/helpers/race-live.ts"

test("shows the current lap based on completed laps and caps it at the finish", () => {
  assert.equal(currentLap(0, 10), 1)
  assert.equal(currentLap(1, 10), 2)
  assert.equal(currentLap(9, 10), 10)
  assert.equal(currentLap(10, 10), 10)
})
