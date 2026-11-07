import type { TrackFrame } from './frame'
import { curvatureAt } from './frame'
import { referenceFor } from './reference'
import type { CircuitReference } from './reference'
import type { Track } from './types'
import { trackTitle } from './types'

export interface CheckResult {
  id: string
  label: string
  /** False for a skipped check too: a check that did not run proved nothing. */
  pass: boolean
  /**
   * The circuit has no sourced reference for this check (or nothing to run it
   * on), so it did not run. Shown and logged as SKIP, never counted as passed.
   */
  skipped?: boolean
  /** Measured value, so a failure says what it saw and not just "failed". */
  detail: string
}

function skip(id: string, label: string, why: string): CheckResult {
  return { id, label, pass: false, skipped: true, detail: `not run: ${why}` }
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
  const ref = referenceFor(track.circuit)
  if (!ref) {
    return [
      {
        id: '!',
        label: 'No reference data for this circuit',
        pass: false,
        detail:
          `reference.ts has no entry for circuit "${track.circuit}", so there is nothing ` +
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
  // Absolute: +1 is clockwise whatever the circuit. This used to be relative
  // to `ref.sense`, which read correctly only while every circuit was
  // clockwise - on Interlagos it labelled a -0.400 km2 loop "clockwise".
  const senseName = (sign: number) => (sign > 0 ? 'clockwise' : 'anti-clockwise')

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
      `JSON declares ${track.lengthM.toFixed(1)} m, ${sign(declaredPct)}${declaredPct.toFixed(2)}%. ` +
      `Reference: ${ref.source}.`,
  })

  const hasCorners = track.corners.length > 0

  // --- B. corner count ---------------------------------------------------
  const labelB = 'Corner count matches the official circuit map'
  checks.push(
    ref.cornerCount === undefined
      ? skip('B', labelB, `no sourced corner count (${track.corners.length} in the file)`)
      : {
          id: 'B',
          label: labelB,
          pass: track.corners.length === ref.cornerCount,
          detail: `${track.corners.length} corners, reference says ${ref.cornerCount}`,
        },
  )

  // --- C. corner ordering ------------------------------------------------
  // No external value needed: this is a property of the sequence, not a
  // measurement, so checking it against itself is legitimate.
  const labelC = 'Corner s increases with corner number, numbered from 1'
  if (!hasCorners) {
    checks.push(skip('C', labelC, 'the file has no corners'))
  } else {
    const nums = track.corners.map((c) => c.number)
    const ss = track.corners.map((c) => c.s)
    const ordered =
      nums[0] === 1 &&
      nums.every((v, i) => i === 0 || v === nums[i - 1] + 1) &&
      ss.every((v, i) => i === 0 || v > ss[i - 1])
    checks.push({
      id: 'C',
      label: labelC,
      pass: ordered,
      detail:
        `T${nums[0]} at ${ss[0].toFixed(0)} m .. ` +
        `T${nums[nums.length - 1]} at ${ss[ss.length - 1].toFixed(0)} m` +
        (ordered ? '' : ` (in s order: ${nums.map((n) => `T${n}`).join(' ')})`),
    })
  }

  // --- D. not reversed ---------------------------------------------------
  // Absolute metres from reference.ts, not a fraction of the measured lap: a
  // fraction is satisfied by a uniformly scaled track. A reversed lap keeps
  // the shape and the sequence but runs it backwards, putting Parabolica
  // (~5180 m) where the Rettifilo chicane (~875 m) belongs.
  const labelD = 'Not reversed: first corner is where the reference puts it'
  if (!ref.firstCornerS) {
    checks.push(skip('D', labelD, 'no sourced first-corner window'))
  } else if (!hasCorners) {
    checks.push(skip('D', labelD, 'the file has no corners'))
  } else {
    const first = track.corners[0]
    const [lo, hi] = ref.firstCornerS
    checks.push({
      id: 'D',
      label: labelD,
      pass: first.s >= lo && first.s <= hi,
      detail:
        `T${first.number} ${first.name} at ${first.s.toFixed(1)} m; ` +
        `expected ${ref.firstCornerName} in ${lo}–${hi} m`,
    })
  }

  // --- E. not mirrored ---------------------------------------------------
  // Viewed down +y with x right and z towards the viewer, a clockwise loop has
  // positive shoelace area. Dropping the minus in `three.z = -ff1.Y` flips
  // this sign and nothing else.
  const area = signedAreaXZ(frame)
  checks.push({
    id: 'E',
    label: `Not mirrored: loop runs ${senseName(ref.sense)} seen from above`,
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
    label: `Total signed turn is one ${senseName(ref.sense)} revolution`,
    pass: Math.abs(turns - 1) < 0.05,
    detail: `${sign(turns)}${turns.toFixed(3)} turns in the ${senseName(ref.sense)} sense (expect +1.000)`,
  })

  // --- G. per-corner handedness -----------------------------------------
  const labelG = 'Each corner turns the way the real circuit does'
  const handedness = ref.handedness
  if (!handedness) {
    checks.push(skip('G', labelG, 'no sourced per-corner handedness'))
    return checks
  }
  if (!hasCorners) {
    checks.push(skip('G', labelG, 'the file has no corners'))
    return checks
  }
  const wrong: string[] = []
  const got: string[] = []
  let compared = 0
  for (const c of track.corners) {
    const want = handedness[c.number]
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
    const side = k / n > 0 ? 'R' : 'L'
    got.push(side)
    if (side !== want) wrong.push(`T${c.number} ${side} not ${want}`)
  }
  const expectedSeq = Object.keys(handedness)
    .map(Number)
    .sort((a, b) => a - b)
    .map((k) => handedness[k])
    .join('')
  const total = Object.keys(handedness).length
  checks.push({
    id: 'G',
    label: labelG,
    pass: wrong.length === 0 && compared === total,
    detail:
      wrong.length === 0
        ? `${compared}/${total} corners compared, all match (expected ${expectedSeq})`
        : `mismatched: ${wrong.join(', ')} (got ${got.join('')}, expected ${expectedSeq})`,
  })

  return checks
}

/** Console table, so a failure is visible without opening the overlay. */
export function checkVerdict(c: CheckResult): 'PASS' | 'FAIL' | 'SKIP' {
  return c.skipped ? 'SKIP' : c.pass ? 'PASS' : 'FAIL'
}

/**
 * Console table, so a failure is visible without opening the overlay.
 *
 * The summary line counts checks that *ran*: "3/5 orientation checks passed
 * (2 not run)". `scripts/snapshot.mjs` parses both it and the per-check lines.
 */
export function logChecks(track: Track, checks: CheckResult[]): void {
  const ran = checks.filter((c) => !c.skipped)
  const failed = ran.filter((c) => !c.pass)
  const skipped = checks.length - ran.length
  const style = failed.length === 0 ? 'color:#3ecf5a' : 'color:#ff5252;font-weight:bold'
  console.groupCollapsed(
    `%c${trackTitle(track)}: ${ran.length - failed.length}/${ran.length} orientation checks passed` +
      (skipped ? ` (${skipped} not run)` : ''),
    style,
  )
  for (const c of checks) {
    console.log(`${checkVerdict(c)}  [${c.id}] ${c.label} — ${c.detail}`)
  }
  console.groupEnd()
}
