import type { TrackFrame } from './frame'
import { curvatureAt } from './frame'
import { referenceFor } from './reference'
import type { CircuitReference } from './reference'
import type { Track } from './types'

export interface CheckResult {
  id: string
  label: string
  pass: boolean
  /** Measured value, so a failure says what it saw and not just "failed". */
  detail: string
}

/** Shoelace area of the loop projected onto the ground plane, (x, z). */
function signedAreaXZ(frame: TrackFrame): number {
  const p = frame.points
  let a = 0
  for (let i = 0; i < p.length; i++) {
    const q = p[(i + 1) % p.length]
    a += p[i].x * q.z - q.x * p[i].z
  }
  return a / 2
}

/**
 * Geometric checks run at load time.
 *
 * Every expected value comes from `reference.ts` — published circuit facts —
 * or is a mathematical invariant that holds for any closed loop. None is read
 * out of the JSON being checked. Checks A, B and D previously compared the
 * file against itself and so could not fail on geometry; that is fixed.
 *
 * Continuity of `sampleAt` across the start/finish seam is a property of a
 * pure function rather than of this artifact, so it is a unit test
 * (`frame.test.ts`) and not a check here.
 *
 * Re-running these in the viewer is not redundant with `extract_track.py`.
 * Those checks prove the JSON was right when it was *written*; these prove the
 * viewer's own frame convention agrees with it. Everything downstream — car
 * placement, chase cameras, overtake detection — reads `right` out of
 * `buildFrame`, so a correct JSON buys nothing if that sign is wrong.
 */
export function verifyOrientation(track: Track, frame: TrackFrame): CheckResult[] {
  const ref = referenceFor(track.name)
  if (!ref) {
    return [
      {
        id: '!',
        label: 'No reference data for this circuit',
        pass: false,
        detail:
          `reference.ts has no entry for "${track.name}", so there is nothing ` +
          'external to check the geometry against. Add one before trusting it.',
      },
    ]
  }
  return referenceChecks(track, frame, ref)
}

function referenceChecks(
  track: Track,
  frame: TrackFrame,
  ref: CircuitReference,
): CheckResult[] {
  const checks: CheckResult[] = []
  const senseName = (sign: number) =>
    sign * ref.sense > 0 ? 'clockwise' : 'anti-clockwise'

  // --- A. length against the published figure ----------------------------
  // Measured on the ground plane (x, z) and not (x, y): y is up in Three.js,
  // so measuring with columns [0, 1] reports roughly half the lap on a flat
  // circuit instead of erroring.
  const devPct = (100 * (frame.lengthM - ref.lengthM)) / ref.lengthM
  const declaredPct = (100 * (track.lengthM - ref.lengthM)) / ref.lengthM
  const sign = (v: number) => (v >= 0 ? '+' : '')
  checks.push({
    id: 'A',
    label: 'Lap length matches the published circuit length',
    pass: Math.abs(devPct) <= ref.lengthTol * 100,
    detail:
      `${frame.lengthM.toFixed(1)} m measured vs ${ref.lengthM.toFixed(1)} m published: ` +
      `${sign(devPct)}${devPct.toFixed(2)}% (tol ${(ref.lengthTol * 100).toFixed(0)}%, ` +
      (devPct < 0
        ? 'short, as expected from smoothing and apex-cutting). '
        : 'LONG — the centreline should come in short). ') +
      `JSON declares ${track.lengthM.toFixed(1)} m, ${sign(declaredPct)}${declaredPct.toFixed(2)}%.`,
  })

  // --- B. corner count ---------------------------------------------------
  checks.push({
    id: 'B',
    label: 'Corner count matches the official circuit map',
    pass: track.corners.length === ref.cornerCount,
    detail: `${track.corners.length} corners, reference says ${ref.cornerCount}`,
  })

  // --- C. corner ordering ------------------------------------------------
  // No external value needed: this is a property of the sequence, not a
  // measurement, so checking it against itself is legitimate.
  const nums = track.corners.map((c) => c.number)
  const ss = track.corners.map((c) => c.s)
  const ordered =
    nums[0] === 1 &&
    nums.every((v, i) => i === 0 || v === nums[i - 1] + 1) &&
    ss.every((v, i) => i === 0 || v > ss[i - 1])
  checks.push({
    id: 'C',
    label: 'Corner s increases with corner number, numbered from 1',
    pass: ordered,
    detail:
      `T${nums[0]} at ${ss[0].toFixed(0)} m .. ` +
      `T${nums[nums.length - 1]} at ${ss[ss.length - 1].toFixed(0)} m`,
  })

  // --- D. not reversed ---------------------------------------------------
  // Absolute metres from reference.ts, not a fraction of the measured lap: a
  // fraction is satisfied by a uniformly scaled track. A reversed lap keeps
  // the shape and the sequence but runs it backwards, putting Parabolica
  // (~5180 m) where the Rettifilo chicane (~875 m) belongs.
  const first = track.corners[0]
  const [lo, hi] = ref.firstCornerS
  checks.push({
    id: 'D',
    label: 'Not reversed: first corner is where the reference puts it',
    pass: first.s >= lo && first.s <= hi,
    detail:
      `T${first.number} ${first.name} at ${first.s.toFixed(1)} m; ` +
      `expected ${ref.firstCornerName} in ${lo}–${hi} m`,
  })

  // --- E. not mirrored ---------------------------------------------------
  // Viewed down +y with x right and z towards the viewer, a clockwise loop has
  // positive shoelace area. Dropping the minus in `three.z = -ff1.Y` flips
  // this sign and nothing else.
  const area = signedAreaXZ(frame)
  checks.push({
    id: 'E',
    label: `Not mirrored: loop runs ${senseName(1)} seen from above`,
    pass: Math.sign(area) === ref.sense,
    detail: `signed area ${(area / 1e6).toFixed(3)} km2 -> ${senseName(Math.sign(area))}`,
  })

  // --- F. total turning --------------------------------------------------
  // An invariant: any simple closed loop turns through exactly one revolution.
  // The sign carries the information, and it is derived from `right` in
  // `buildFrame`, so this fails if the viewer's handedness convention
  // disagrees with the geometry.
  let turn = 0
  for (let i = 0; i < frame.points.length; i++) {
    const next = (i + 1) % frame.points.length
    const ds = (frame.s[next] - frame.s[i] + frame.lengthM) % frame.lengthM
    turn += 0.5 * (frame.curvature[i] + frame.curvature[next]) * ds
  }
  const turns = (turn / (2 * Math.PI)) * ref.sense
  checks.push({
    id: 'F',
    label: `Total signed turn is one ${senseName(1)} revolution`,
    pass: Math.abs(turns - 1) < 0.05,
    detail: `${sign(turns)}${turns.toFixed(3)} turns in the ${senseName(1)} sense (expect +1.000)`,
  })

  // --- G. per-corner handedness -----------------------------------------
  const wrong: string[] = []
  let compared = 0
  for (const c of track.corners) {
    const want = ref.handedness[c.number]
    if (!want) continue
    compared++
    // Average over +/-35 m: a single sample at the entry of a chicane can
    // still be curving the other way.
    let k = 0
    let n = 0
    for (let ds = -35; ds <= 35; ds += 5) {
      k += curvatureAt(frame, c.s + ds)
      n++
    }
    const got = k / n > 0 ? 'R' : 'L'
    if (got !== want) wrong.push(`T${c.number} ${got} not ${want}`)
  }
  const expectedSeq = Object.keys(ref.handedness)
    .map(Number)
    .sort((a, b) => a - b)
    .map((k) => ref.handedness[k])
    .join('')
  checks.push({
    id: 'G',
    label: 'Each corner turns the way the real circuit does',
    pass: wrong.length === 0 && compared === ref.cornerCount,
    detail:
      wrong.length === 0
        ? `${compared}/${ref.cornerCount} corners compared, all match (expected ${expectedSeq})`
        : `mismatched: ${wrong.join(', ')} (expected ${expectedSeq})`,
  })

  return checks
}

/** Console table, so a failure is visible without opening the overlay. */
export function logChecks(track: Track, checks: CheckResult[]): void {
  const failed = checks.filter((c) => !c.pass)
  const style = failed.length === 0 ? 'color:#3ecf5a' : 'color:#ff5252;font-weight:bold'
  console.groupCollapsed(
    `%c${track.name} ${track.year}: ${checks.length - failed.length}/${checks.length} orientation checks passed`,
    style,
  )
  for (const c of checks) {
    console.log(`${c.pass ? 'PASS' : 'FAIL'}  [${c.id}] ${c.label} — ${c.detail}`)
  }
  console.groupEnd()
}
