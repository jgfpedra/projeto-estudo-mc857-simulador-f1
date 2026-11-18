import { describe, expect, it } from 'vitest'
import { signedWheelTravel } from './odometry'
import { buildField, syntheticSource } from './field'
import { newMotionState } from './motion'

describe('signed wheel travel from engine poses', () => {
  it('rolls forward and backward without interpreting a lateral slide as wheel rotation', () => {
    expect(signedWheelTravel(0, 0, 0, 5, 0, 0)).toBeCloseTo(5)
    expect(signedWheelTravel(5, 0, 0, 2, 0, 0)).toBeCloseTo(-3)
    expect(signedWheelTravel(0, 0, 0, 0, 4, 0)).toBeCloseTo(0)
    expect(signedWheelTravel(0, 0, Math.PI / 2, 0, 4, Math.PI / 2)).toBeCloseTo(4)
  })

  it('clears an engine odometer when switching to a synthetic source', () => {
    const state = newMotionState()
    state.wheelTravelM = 42
    syntheticSource(buildField(4000, 12, 2)).sampleInto(0, 0, state)
    expect(state.wheelTravelM).toBeUndefined()
  })

  it('takes the short turn across the angle seam', () => {
    const a = 179 * Math.PI / 180
    const b = -179 * Math.PI / 180
    expect(signedWheelTravel(0, 0, a, -1, 0, b)).toBeCloseTo(1)
  })
})
