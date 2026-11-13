import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { MathUtils, Sphere, Vector3 } from 'three'
import { loadTrack } from './track/load'
import { buildFrame } from './track/frame'
import { TrackRibbon } from './track/TrackRibbon'
import { OrientationAids } from './track/OrientationAids'
import { Grid } from './cars/Grid'
import { CarPanel } from './cars/CarPanel'
import { buildField, syntheticSource } from './cars/field'
import type { SourceKind } from './cars/motion'
import { lapAt, loadReplay } from './replay/load'
import { replaySource } from './replay/source'
import { newClock, seekClock, togglePlay } from './replay/clock'
import { Timeline } from './replay/Timeline'
import type { Replay } from './replay/types'
import { CameraRig } from './cameras/CameraRig'
import { CameraPanel } from './cameras/CameraPanel'
import { CAMERA_MODES } from './cameras/rig'
import type { CameraMode, FollowState } from './cameras/rig'
import { RACE_CAR_RED } from './cars/model'
import { logChecks, verifyOrientation } from './track/verify'
import type { CheckResult } from './track/verify'
import type { Track } from './track/types'
import { trackTitle } from './track/types'
import { TRACKS, recordingUrlFor, selectedTrack, urlForTrack } from './track/registry'
import { loadRecording, trackFromRecording } from './engine/load'
import { engineSource, lapAtTime, positionAt } from './engine/source'
import type { Recording } from './engine/types'
import { PROBE_ENABLED, Probe } from './probe'

/**
 * Which track, from `?track=` (src/track/registry.ts). Read once: switching
 * track navigates to a new URL rather than swapping state in place. A reload is
 * the one reset that cannot miss anything - the clock, the replay, the fitted
 * camera and `OrbitControls`' saved home pose all depend on the track, and the
 * last of those has already cost time once (docs/3d-design.md section 7).
 */
const { entry: TRACK, unknown: UNKNOWN_TRACK } = selectedTrack(window.location.search)
/** Set for a track that comes from an engine recording rather than a track JSON. */
const RECORDING_URL = recordingUrlFor(TRACK, window.location.search)
/** What the loading and error overlays name. */
const TRACK_SOURCE_URL = RECORDING_URL ?? TRACK.url ?? '(no url)'
/**
 * The sources this track offers. Synthetic everywhere; the replay only on our
 * Monza, the engine recording only on the track built from it.
 */
const KINDS: SourceKind[] = ['synthetic', RECORDING_URL ? 'engine' : 'replay']

const FOV_DEG = 45
/**
 * Direction from target to camera. Near plan-view by default: it is the view
 * that can be held next to a circuit map, which is what makes a mirrored track
 * obvious. Enough tilt to keep `OrbitControls` out of its polar singularity and
 * to show the surface is a surface. Drag to orbit.
 */
const VIEW_DIR = new Vector3(0, 1, 0.3).normalize()

/**
 * Frame the whole circuit. Fitting the bounding *sphere* rather than the box
 * means the framing holds at any orbit angle, and taking the narrower of the
 * two half-angles keeps it correct on a tall window as well as a wide one.
 */
function fitCamera(track: Track) {
  const sphere = new Sphere().setFromPoints(track.points)
  const aspect = window.innerWidth / Math.max(window.innerHeight, 1)
  const halfV = MathUtils.degToRad(FOV_DEG) / 2
  const halfH = Math.atan(Math.tan(halfV) * aspect)
  const dist = (sphere.radius / Math.sin(Math.min(halfV, halfH))) * 1.12
  return {
    target: sphere.center,
    position: sphere.center.clone().addScaledVector(VIEW_DIR, dist),
    far: dist * 8,
  }
}

export default function App() {
  const [track, setTrack] = useState<Track | null>(null)
  const [error, setError] = useState<string | null>(null)
  /**
   * Which car the panel follows. Lives here rather than in `Grid` so `CarPanel`
   * — plain DOM outside the Canvas — can drive it. Changing it re-renders
   * React once per click, not once per animation frame.
   */
  const [selected, setSelected] = useState(0)
  /** Which camera. Alongside `selected`, because the follow cameras use it. */
  const [mode, setMode] = useState<CameraMode>('orbit')
  /**
   * Which motion source. The synthetic field stays selectable rather than being
   * replaced: it is the only thing on screen that spreads `d` across the ribbon,
   * because real telemetry against a median centreline barely varies laterally.
   */
  const [sourceKind, setSourceKind] = useState<SourceKind>(RECORDING_URL ? 'engine' : 'synthetic')
  const [replay, setReplay] = useState<Replay | null>(null)
  const [replayError, setReplayError] = useState<string | null>(null)
  /** The engine recording, when this track came from one. Loaded before the track. */
  const [recording, setRecording] = useState<Recording | null>(null)
  /** Debug: a stripe on every wheel so spin is visible. Off by default. */
  const [wheelMarkers, setWheelMarkers] = useState(false)
  /**
   * Bumped on anything that moves the followed car discontinuously, so
   * `CameraRig` cuts instead of damping across it. A scrub or a source switch
   * moves the target by a lap or more, and a first-order lag chasing that sweeps
   * the camera across the circuit.
   */
  const [cutKey, setCutKey] = useState(0)
  const cut = useCallback(() => setCutKey((k) => k + 1), [])
  /** Replay time. A ref: `Grid` advances it every frame and the panel polls it. */
  const clock = useRef(newClock())
  /**
   * The followed car's live state. A ref rather than state on purpose: `Grid`
   * writes it every frame while `CarPanel` polls it and `CameraRig` follows it,
   * so neither a moving car nor a moving readout costs a React render.
   *
   * `carIndex: -1` is the unseeded marker the rig checks: the first frames can
   * legitimately arrive before `Grid` has anything to report.
   */
  const readout = useRef<FollowState>({
    s: 0,
    sUnwrapped: 0,
    d: 0,
    speedMps: 0,
    carIndex: -1,
    posed: false,
    x: 0,
    z: 0,
    yawRad: 0,
  })

  const cycleMode = useCallback(
    () => setMode((m) => CAMERA_MODES[(CAMERA_MODES.indexOf(m) + 1) % CAMERA_MODES.length]),
    [],
  )

  const cycleSource = useCallback(
    () =>
      setSourceKind((k) => {
        const next = KINDS[(KINDS.indexOf(k) + 1) % KINDS.length]
        // Nothing to switch to until the replay has loaded.
        return next === 'replay' && !replay ? k : next
      }),
    [replay],
  )

  useEffect(() => {
    if (RECORDING_URL) {
      // The track comes from the recording's own race block, never from a local
      // track JSON: the cars were driven on exactly those waypoints.
      loadRecording(RECORDING_URL).then(
        (rec) => {
          const built = trackFromRecording(rec)
          // Rolled to the start/finish waypoint, the frame must measure exactly
          // the engine's lap: `progress_m` is an unwrapped `s` on it only then.
          const lengthM = buildFrame(built).lengthM
          if (Math.abs(lengthM - rec.track.lengthM) > 1e-6) {
            setError(`race block says ${rec.track.lengthM} m, frame measures ${lengthM} m`)
            return
          }
          setRecording(rec)
          setTrack(built)
        },
        (e: Error) => setError(e.message),
      )
      return
    }
    if (!TRACK.url) {
      setError('registry entry has neither a track JSON nor a recording')
      return
    }
    loadTrack(TRACK.url).then(setTrack, (e: Error) => setError(e.message))
  }, [])


  const scene = useMemo(() => {
    if (!track) return null
    const frame = buildFrame(track)
    return {
      frame,
      checks: verifyOrientation(track, frame),
      camera: fitCamera(track),
      // The field needs the car's width to keep itself inside the ribbon, and
      // that is a property of the model spec, not of the mesh.
      field: buildField(frame.lengthM, track.widthM, RACE_CAR_RED.fit.metres),
    }
  }, [track])

  // The replay needs the frame's measured lap length to cross-check that it was
  // projected against this centreline, so it loads after the track rather than
  // beside it. Failure is not fatal: the synthetic field still works, and the
  // timeline shows why the replay button is disabled.
  useEffect(() => {
    if (!scene || RECORDING_URL) return
    if (!TRACK.replayUrl) {
      setReplayError(
        'none for this track - the 2024 replay was projected onto our Monza centreline',
      )
      return
    }
    loadReplay(TRACK.replayUrl, scene.frame.lengthM).then(setReplay, (e: Error) =>
      setReplayError(e.message),
    )
  }, [scene])

  /**
   * The running source, and the lap offset the panel needs to show a real lap.
   *
   * Switching source resets the clock and forces a camera cut: the two sources
   * place car `i` kilometres apart, and the car count differs too.
   */
  const motion = useMemo(() => {
    if (!scene) return null
    if (sourceKind === 'engine' && recording) {
      return {
        source: engineSource(recording),
        // Both read the clock, not `sUnwrapped`: the engine's lap counter and its
        // running order are per tick, and the panel polls between frames. The
        // engine counts *completed* laps; the panel shows the lap being driven.
        lapOf: (car: number) => lapAtTime(recording, clock.current.tS, car) + 1,
        rankOf: (car: number) => positionAt(recording, clock.current.tS, car),
      }
    }
    if (sourceKind === 'replay' && replay) {
      return {
        source: replaySource(replay),
        // Per car, because the official boundary is per car — at any instant the
        // field is spread across two lap numbers.
        lapOf: (car: number, s: number) =>
          replay.cars[car] ? lapAt(replay.cars[car], s) : 0,
      }
    }
    // Lap 1 at t = 0 for the synthetic field: its `s0` is a grid offset rather
    // than distance covered, so the lap it is "on" starts at one.
    const lengthM = scene.frame.lengthM
    return {
      source: syntheticSource(scene.field),
      lapOf: (_car: number, s: number) => 1 + Math.floor(s / lengthM),
    }
  }, [scene, sourceKind, replay, recording])

  useEffect(() => {
    clock.current.tS = 0
    cut()
  }, [motion, cut])

  // The two sources do not have the same number of cars — the replay drops any
  // car that pitted inside its window — so a selection made under one can be out
  // of range under the other.
  const carCount = motion?.source.cars.length ?? 0
  useEffect(() => {
    if (carCount > 0 && selected >= carCount) setSelected(carCount - 1)
  }, [carCount, selected])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const duration = motion?.source.durationS ?? Infinity
      switch (e.key) {
        case 'c':
          cycleMode()
          return
        case 'm':
          cycleSource()
          return
        case 'w':
          setWheelMarkers((on) => !on)
          return
        case ' ':
          // Space would otherwise re-click whichever swatch or mode button was
          // last pressed, because a focused <button> treats it as activation.
          e.preventDefault()
          ;(document.activeElement as HTMLElement | null)?.blur()
          togglePlay(clock.current)
          return
        case 'ArrowLeft':
        case 'ArrowRight': {
          const tick = sourceKind === 'engine' ? recording?.dtS : replay?.dtS
          const step = (tick ?? 0.2) * (e.key === 'ArrowRight' ? 1 : -1)
          seekClock(clock.current, clock.current.tS + step, duration)
          cut()
          return
        }
        case '[':
        case ']': {
          // Jump to the previous or next lap boundary of the followed car. The
          // boundaries are per car, because at any instant the cars are on
          // different laps.
          const car = replay?.cars[selected]
          if (!car) return
          const marks = Array.from(car.lapStartT)
          const target =
            e.key === ']'
              ? marks.find((t) => t > clock.current.tS + 1e-6)
              : [...marks].reverse().find((t) => t < clock.current.tS - 1e-6)
          if (target === undefined) return
          seekClock(clock.current, target, duration)
          cut()
          return
        }
      }
      const picked = CAMERA_MODES[Number(e.key) - 1]
      if (picked) setMode(picked)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [cycleMode, cycleSource, motion, replay, recording, sourceKind, selected, cut])

  // Logged from an effect, and guarded, so StrictMode's double render doesn't
  // print the table four times.
  const logged = useRef<unknown>(null)
  useEffect(() => {
    if (!track || !scene || logged.current === scene) return
    logged.current = scene
    logChecks(track, scene.checks)
  }, [track, scene])

  if (error) return <Overlay>Failed to load {TRACK_SOURCE_URL}: {error}</Overlay>
  if (!track || !scene || !motion) return <Overlay>Loading {TRACK_SOURCE_URL}…</Overlay>

  const { frame, checks, camera } = scene
  const { source, lapOf } = motion
  const rankOf = 'rankOf' in motion ? motion.rankOf : undefined
  const cars = source.cars

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#15151e' }}>
      {/* `fov` from `FOV_DEG`, not a second literal 45: `fitCamera` frames the
          circuit with it, and `CameraRig` now mutates it per mode. */}
      <Canvas
        camera={{ position: camera.position.toArray(), fov: FOV_DEG, near: 1, far: camera.far }}
      >
        <hemisphereLight args={['#ffffff', '#30303c', 1.1]} />
        <directionalLight position={[600, 1200, 400]} intensity={1.2} />
        <TrackRibbon frame={frame} widthM={track.widthM} />
        <OrientationAids track={track} frame={frame} />
        {/* The car model is fetched, so it suspends. `null` rather than a
            stand-in mesh: the track is up either way, and a placeholder that
            flashes for a frame is worse than a car that simply appears. */}
        <Suspense fallback={null}>
          <Grid
            frame={frame}
            cars={cars}
            source={source}
            clock={clock}
            selected={selected}
            readout={readout}
            wheelMarkers={wheelMarkers}
          />
          {/* After `Grid`, and inside the same boundary: r3f runs equal-priority
              `useFrame` callbacks in subscription order, so this reads the car
              state written a few lines above rather than last frame's. */}
          <CameraRig
            frame={frame}
            mode={mode}
            readout={readout}
            fitted={camera}
            orbitFovDeg={FOV_DEG}
            clock={clock}
            cutKey={cutKey}
          />
        </Suspense>
        {/* x red, y green, z blue: which way is +z on screen is the whole
            mirror question, so keep the axes visible while checking. */}
        <axesHelper args={[250]} />
        {PROBE_ENABLED && <Probe clock={clock} readout={readout} />}
      </Canvas>
      <ChecksPanel track={track} checks={checks} />
      <CameraPanel mode={mode} onSelect={setMode} car={cars[selected]} />
      <CarPanel
        cars={cars}
        selected={selected}
        onSelect={setSelected}
        readout={readout}
        lengthM={frame.lengthM}
        widthM={track.widthM}
        lapAt={lapOf}
        rankAt={rankOf}
        sourceKind={source.kind}
        wheelMarkers={wheelMarkers}
        onWheelMarkers={setWheelMarkers}
      />
      <Timeline
        kind={sourceKind}
        kinds={KINDS}
        onKind={setSourceKind}
        clock={clock}
        replay={replay}
        replayError={replayError}
        recording={recording}
        durationS={source.durationS}
        selected={selected}
        onCut={cut}
      />
    </div>
  )
}

function ChecksPanel({ track, checks }: { track: Track; checks: CheckResult[] }) {
  const [open, setOpen] = useState(true)
  const ran = checks.filter((c) => !c.skipped)
  const failed = ran.filter((c) => !c.pass).length
  const skipped = checks.length - ran.length
  const colour = failed === 0 ? '#3ecf5a' : '#ff5252'
  return (
    <div
      style={{
        position: 'absolute',
        top: 12,
        left: 12,
        maxWidth: 440,
        padding: '8px 12px',
        background: 'rgba(12,12,18,0.82)',
        border: '1px solid #2c2c38',
        borderRadius: 4,
        color: '#d8d8e0',
        font: '12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace',
      }}
    >
      {/* Collapsible: the panel sits over the track, and once the checks are
          green the geometry underneath is the more interesting thing. */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          all: 'unset',
          cursor: 'pointer',
          display: 'block',
          color: '#fff',
          font: 'inherit',
        }}
      >
        {open ? '▾' : '▸'} {trackTitle(track)} · {track.points.length} pts ·{' '}
        {track.lengthM.toFixed(1)} m · {track.widthM.toFixed(1)} m wide ·{' '}
        <span style={{ color: colour }}>
          {ran.length - failed}/{ran.length} checks
          {skipped > 0 && <span style={{ color: '#9a9aa8' }}> · {skipped} not run</span>}
        </span>
      </button>
      <div><a href="?live=1">Corrida ao vivo</a></div>
      <TrackPicker />
      {open && (
        <div style={{ marginTop: 6 }}>
          {checks.map((c) => (
            <div key={c.id} style={{ display: 'flex', gap: 6 }}>
              <span style={{ color: c.skipped ? '#9a9aa8' : c.pass ? '#3ecf5a' : '#ff5252' }}>
                {c.skipped ? '–' : c.pass ? '✓' : '✗'}
              </span>
              <span>
                <span style={{ color: '#fff' }}>{c.label}</span>
                <br />
                <span style={{ opacity: 0.6 }}>{c.detail}</span>
              </span>
            </div>
          ))}
          <div style={{ marginTop: 6, color: colour }}>
            {failed === 0 ? 'all checks that ran pass' : `${failed} check(s) FAILED`}
            {skipped > 0 && (
              <span style={{ color: '#9a9aa8' }}> · {skipped} not run: no sourced reference</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * One link per registered track. Plain links rather than state: see `TRACK`
 * above for why switching reloads. `?probe` and anything else survive.
 */
function TrackPicker() {
  const search = window.location.search
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
      {UNKNOWN_TRACK && (
        <span style={{ color: '#ff8a5f', width: '100%' }}>
          unknown track "{UNKNOWN_TRACK}", showing {TRACK.id}
        </span>
      )}
      {TRACKS.map((t) => {
        const current = t.id === TRACK.id
        return (
          <a
            key={t.id}
            href={urlForTrack(t.id, search)}
            aria-current={current ? 'page' : undefined}
            style={{
              padding: '1px 6px',
              border: `1px solid ${current ? '#d8d8e0' : '#3a3a48'}`,
              borderRadius: 3,
              color: current ? '#fff' : '#9a9aa8',
              textDecoration: 'none',
            }}
          >
            {t.label}
          </a>
        )
      })}
    </div>
  )
}

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'grid',
        placeItems: 'center',
        background: '#15151e',
        color: '#d8d8e0',
        font: '13px ui-monospace, SFMono-Regular, Menlo, monospace',
      }}
    >
      <div>{children}</div>
    </div>
  )
}
