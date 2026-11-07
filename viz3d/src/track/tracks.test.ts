import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { buildFrame } from './frame'
import { parseTrack } from './load'
import { TRACKS } from './registry'
import type { TrackJson } from './types'
import { checkVerdict, verifyOrientation } from './verify'
import expected from './expected-verdicts.json'

/**
 * The viewer's own orientation checks, run on every committed track through
 * the real `parseTrack` / `buildFrame` / `verifyOrientation` — the same code
 * the probe logs in the browser.
 *
 * `expected-verdicts.json` pins what each check *does* say about each track,
 * known failures included (docs/phase0-geometry-report.md explains each one).
 * Pinning is not loosening: no tolerance in `verify.ts` or `reference.ts` was
 * touched, the failures still show red in the viewer, and a check that changes
 * its verdict in *either* direction fails here. `scripts/snapshot.mjs` reads
 * the same file, so there is one list of known failures, not two.
 */
function load(url: string): TrackJson {
  const path = fileURLToPath(new URL(`../../public${url}`, import.meta.url))
  return JSON.parse(readFileSync(path, 'utf8')) as TrackJson
}

const pinned = expected as unknown as Record<string, { verdicts: Record<string, string> }>

describe('orientation checks on every committed track', () => {
  for (const entry of TRACKS) {
    it(`${entry.id}: verdicts match expected-verdicts.json`, () => {
      const track = parseTrack(load(entry.url))
      const checks = verifyOrientation(track, buildFrame(track))
      for (const c of checks) console.log(`${entry.id}  ${checkVerdict(c)}  [${c.id}] ${c.detail}`)
      const got = Object.fromEntries(checks.map((c) => [c.id, checkVerdict(c)]))
      expect(got).toEqual(pinned[entry.id]?.verdicts)
    })
  }

  it('our Monza passes all seven, and nothing is pinned as failing there', () => {
    expect(Object.values(pinned.monza.verdicts)).toEqual(Array(7).fill('PASS'))
  })

  it('the circuit id, not the display name, selects the reference', () => {
    const raw = load('/tracks/monza_v1.json')
    expect(raw.circuit).toBe('monza')
    const renamed = parseTrack({ ...raw, name: 'Something else entirely' })
    const checks = verifyOrientation(renamed, buildFrame(renamed))
    expect(checks.map((c) => c.id)).toEqual(['A', 'B', 'C', 'D', 'E', 'F', 'G'])
  })
})
