import type { Vector3 } from 'three'

/**
 * Raw JSON as written by `scripts/extract_track.py` (our telemetry
 * centrelines) or `scripts/convert_frozen_track.py` (the simulation engine's
 * frozen tracks). Schema is documented in docs/3d-design.md section 5. Nothing
 * outside `load.ts` should touch this type: angles here are degrees and the
 * loop is a plain number[][].
 */
export interface TrackJson {
  /**
   * Circuit id, the key into `reference.ts`. Distinct from `name` on purpose:
   * a converted engine track is the *same circuit* as our centreline and must
   * be checked against the same published facts, whatever it is called.
   */
  circuit: string
  name: string
  /** Which geometry of the circuit this is, e.g. "Monza_v1". Absent for ours. */
  variant?: string
  /** Telemetry year. `null` when the source does not record one. */
  year: number | null
  lengthM: number
  /** `lengthM / N`. Only the spacing when `uniformSpacing` is not false. */
  spacingM: number
  /** Engine tracks are 2-4 m and non-uniform; `frame.ts` never assumes otherwise. */
  uniformSpacing?: boolean
  widthM: number
  rotationDeg: number
  /** Three.js space, metres, arc-length ordered, loop NOT duplicated. */
  centerline: number[][]
  corners: { number: number; name: string; s: number }[]
  startFinishS: number
  /** Provenance for converted tracks: repo, commit, hashes, sf_idx. */
  source?: Record<string, unknown>
}

export interface Corner {
  number: number
  name: string
  /** Arc length along the lap, metres. */
  s: number
}

/** Parsed track. Metres and radians throughout. */
export interface Track {
  /** Circuit id; `referenceFor` keys on this, never on `name`. */
  circuit: string
  name: string
  variant: string | null
  year: number | null
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

/** "Monza 2024", "Monza · Monza_v1": how a track names itself on screen. */
export function trackTitle(track: Pick<Track, 'name' | 'variant' | 'year'>): string {
  if (track.variant) return `${track.name} · ${track.variant}`
  return track.year === null ? track.name : `${track.name} ${track.year}`
}
