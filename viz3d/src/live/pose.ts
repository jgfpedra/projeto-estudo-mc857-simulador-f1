import type { MotionState } from '../cars/motion'
import { engineYaw } from '../engine/source'

/** A pose in the engine's world frame, in metres and degrees. */
export interface LivePose {
  position_xy: [number, number]
  heading_deg: number
  velocity_mps: number
  progress_m: number
}

export function applyLivePose(pose: LivePose, out: MotionState): MotionState {
  out.posed = true
  out.x = pose.position_xy[0]
  out.z = -pose.position_xy[1]
  out.yawRad = engineYaw(pose.heading_deg * Math.PI / 180)
  out.sUnwrapped = pose.progress_m
  out.d = 0
  out.speedMps = pose.velocity_mps
  return out
}
