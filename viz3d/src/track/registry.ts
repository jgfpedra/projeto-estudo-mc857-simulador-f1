/**
 * The tracks the viewer can show, selected with `?track=<id>`.
 *
 * Phase 0 (docs/phase0-geometry-report.md) renders the simulation engine's
 * frozen tracks beside our telemetry centreline to compare them. Each entry is
 * one committed JSON under `public/tracks/`; `circuit` inside that file, not
 * the id here, decides which reference facts it is checked against.
 *
 * Phase 0b adds our own Interlagos centrelines, extracted offline from the 2023
 * (dry, kept) and 2024 (wet) races; `interlagos_2024` is there as the second
 * extraction the report compares against, not as a second supported layout.
 *
 * Only our own Monza has a replay: `monza-2024-race.json` was projected onto
 * that exact centreline, and `parseReplay` refuses any other (it checks the
 * lap length). Re-projecting the telemetry onto an engine track is a separate
 * piece of work, so those run the synthetic field only.
 *
 * Phase 3 adds `engine`: a race recorded from the group's engine
 * (`scripts/record_race.py`). It has no track JSON - the track is built from the
 * recording's own race block (`trackFromRecording`), so the cars and the
 * centreline cannot come from two different geometries. `?recording=<url>`
 * swaps in another recording, e.g. a full one under `.cache/` through Vite's
 * `/@fs/` in `npm run dev`.
 *
 * Phase 3b adds `engine_ours`: a 15-lap race of the same grid and seed on our
 * own Interlagos export (`exports/interlagos_2023_v1.json`, the controller's
 * Interlagos tuning off by construction), trimmed to a window around the first
 * pit stop (docs/phase3b-longer-races.md).
 */
export interface TrackEntry {
  id: string
  /** Button text in the checks panel. */
  label: string
  /** Track JSON. Absent when the track comes from a recording's race block. */
  url?: string
  replayUrl?: string
  /** Engine recording (JSONL). The track is built from its first line. */
  recordingUrl?: string
}

export const TRACKS: TrackEntry[] = [
  {
    id: 'monza',
    label: 'Monza · telemetry',
    url: '/tracks/monza.json',
    replayUrl: '/replays/monza-2024-race.json',
  },
  { id: 'monza_v1', label: 'Monza_v1 · engine', url: '/tracks/monza_v1.json' },
  {
    id: 'interlagos',
    label: 'Interlagos 2023 · telemetry',
    url: '/tracks/interlagos.json',
  },
  {
    id: 'interlagos_2024',
    label: 'Interlagos 2024 (wet) · telemetry',
    url: '/tracks/interlagos_2024.json',
  },
  { id: 'interlagos_v2', label: 'interlagos_v2 · engine', url: '/tracks/interlagos_v2.json' },
  {
    id: 'engine',
    label: 'Engine race · seed 42',
    recordingUrl: '/recordings/engine-interlagos-seed42.jsonl',
  },
  {
    id: 'engine_ours',
    label: 'Engine race · our Interlagos · pit',
    recordingUrl: '/recordings/engine-interlagos2023-seed42-pit.jsonl',
  },
]

export const DEFAULT_TRACK = TRACKS[0]

/** The entry named by `?track=`, or the default. Unknown ids fall back loudly. */
export function selectedTrack(search: string): { entry: TrackEntry; unknown: string | null } {
  const id = new URLSearchParams(search).get('track')
  if (id === null) return { entry: DEFAULT_TRACK, unknown: null }
  const entry = TRACKS.find((t) => t.id === id)
  return entry ? { entry, unknown: null } : { entry: DEFAULT_TRACK, unknown: id }
}

/** The recording to load for an entry: `?recording=` overrides the entry's own. */
export function recordingUrlFor(entry: TrackEntry, search: string): string | undefined {
  if (!entry.recordingUrl) return undefined
  return new URLSearchParams(search).get('recording') ?? entry.recordingUrl
}

/** Same page, other track: keeps every other parameter (`probe` included). */
export function urlForTrack(id: string, search: string): string {
  const params = new URLSearchParams(search)
  params.set('track', id)
  return `?${params.toString()}`
}
