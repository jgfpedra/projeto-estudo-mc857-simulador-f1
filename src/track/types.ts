import type { Vector3 } from 'three'

/**
 * Raw JSON as written by `scripts/extract_track.py`. Schema is documented in
 * docs/3d-design.md section 5. Nothing outside `load.ts` should touch this
 * type: angles here are degrees and the loop is a plain number[][].
 */
export interface TrackJson {
  name: string
  year: number
  lengthM: number
  spacingM: number
  widthM: number
  rotationDeg: number
  /** Three.js space, metres, arc-length ordered, loop NOT duplicated. */
  centerline: number[][]
  corners: { number: number; name: string; s: number }[]
  startFinishS: number
}

export interface Corner {
  number: number
  name: string
  /** Arc length along the lap, metres. */
  s: number
}

/** Parsed track. Metres and radians throughout. */
export interface Track {
  name: string
  year: number
  /** Lap length as declared by the extractor. */
  lengthM: number
  spacingM: number
  widthM: number
  /** `rotationDeg` from the JSON, converted at the load boundary. */
  rotationRad: number
  /** Centreline samples, Three.js space. The loop is open: last != first. */
  points: Vector3[]
  corners: Corner[]
  startFinishS: number
}
