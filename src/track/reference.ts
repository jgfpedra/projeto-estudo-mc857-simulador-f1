/**
 * Independently-sourced facts about each circuit, for checking extracted
 * geometry against.
 *
 * The point of this file is that **nothing in it comes from the artifact under
 * test**. A check whose expected value is read out of the same JSON it is
 * validating passes no matter what the geometry does — it only proves the file
 * is internally consistent with itself, which it always is, because one script
 * wrote all of it in one pass.
 *
 * Sources are named per field. Where a published figure and our measurement
 * legitimately differ, the tolerance says why.
 */
export interface CircuitReference {
  /**
   * Published circuit length in metres (FIA homologated / circuit operator
   * figure), NOT our measured centreline.
   *
   * Expect to land slightly under it, for two compounding reasons: the
   * centreline is the median of racing lines, which cut apexes, and
   * Savitzky-Golay smoothing shortens a closed loop by pulling it inside its
   * own curvature. Monza 2024 measures 5756.9 m, −0.62%.
   */
  lengthM: number
  /** Tolerance on the above, as a fraction. Generous: see `lengthM`. */
  lengthTol: number
  /** Number of numbered corners on the official circuit map. */
  cornerCount: number
  /** Window, in metres of arc length, the first corner must fall inside. */
  firstCornerS: [number, number]
  /** What the first corner should be, for the failure message. */
  firstCornerName: string
  /**
   * Direction of travel seen from above: +1 clockwise, −1 anti-clockwise.
   * This is the sign of the shoelace area of the loop on the Three.js ground
   * plane `(x, z)`, and the sign of the lap's total signed turn.
   */
  sense: 1 | -1
  /** Which way each numbered corner turns, in the direction of travel. */
  handedness: Record<number, 'R' | 'L'>
}

const MONZA: CircuitReference = {
  // Autodromo Nazionale Monza, 5.793 km — the published figure, quoted on
  // every circuit map and in docs/3d-design.md section 4.
  lengthM: 5793.0,
  lengthTol: 0.02,
  cornerCount: 11,
  // The long main straight suggests ~600 m; it is really ~875 m. FastF1's own
  // telemetry-integrated `Distance` column puts turn 1 at 873.8 m, our
  // projection at 888.9 m — two independent methods, so the window is wide
  // enough to hold both and narrow enough to exclude Parabolica at ~5180 m.
  firstCornerS: [700, 1050],
  firstCornerName: 'Variante del Rettifilo',
  // Monza runs clockwise: seven of its eleven corners are right-handers.
  sense: 1,
  // Facts about the circuit, not about any coordinate convention — which is
  // what makes them the strongest mirror check available. A mirrored track
  // keeps the corner order intact but flips all eleven of these at once.
  handedness: {
    1: 'R', // Rettifilo 1
    2: 'L', // Rettifilo 2
    3: 'R', // Curva Grande
    4: 'L', // Roggia 1
    5: 'R', // Roggia 2
    6: 'R', // Lesmo 1
    7: 'R', // Lesmo 2
    8: 'L', // Ascari 1
    9: 'R', // Ascari 2
    10: 'L', // Ascari 3
    11: 'R', // Parabolica
  },
}

const REFERENCES: Record<string, CircuitReference> = { Monza: MONZA }

export function referenceFor(name: string): CircuitReference | null {
  return REFERENCES[name] ?? null
}
