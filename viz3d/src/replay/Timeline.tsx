import { useEffect, useRef } from 'react'
import type { SourceKind } from '../cars/motion'
import type { Recording } from '../engine/types'
import { lapAtTime, pitStateAt, positionAt } from '../engine/source'
import { seekClock, setRate, togglePlay } from './clock'
import type { ClockState } from './clock'
import type { Replay } from './types'

const LABEL: Record<SourceKind, string> = {
  synthetic: 'synthetic',
  replay: 'replay',
  engine: 'engine',
}

const BLURB: Record<SourceKind, string> = {
  synthetic:
    'Twenty cars at a constant speed with fixed lateral offsets, spread across ' +
    'the ribbon. Deterministic, so a screenshot means something.',
  replay:
    'Real position samples from the race, projected onto the centreline to ' +
    'recover (s, d). Cars run almost single file: the centreline is the median ' +
    'of racing lines, so the field sits within centimetres of it.',
  engine:
    "A race recorded from the group's engine: ten cars under the rule-based " +
    "controller, placed at the engine's own position and heading every tick.",
}

const RATES = [0.25, 0.5, 1, 2]

/**
 * Transport for the replay, and the switch between motion sources.
 *
 * Polled rather than reactive, like `CarPanel`: the clock advances sixty times a
 * second and putting it in React state would drag the whole Canvas subtree
 * through the reconciler for a number nobody can read that fast. The slider is
 * **uncontrolled** — its `value` is written on the tick — so dragging it is not a
 * render either.
 */
const TICK_HZ = 12

interface Props {
  kind: SourceKind
  /** The sources this track offers, in button order. */
  kinds: readonly SourceKind[]
  onKind: (kind: SourceKind) => void
  /** Advanced by `Grid`; written here on a scrub. */
  clock: { current: ClockState }
  /** `null` while the replay is still loading, or if it failed. */
  replay: Replay | null
  replayError: string | null
  /** The engine recording, on the track built from one. */
  recording: Recording | null
  /** Seconds of content for the current source; `Infinity` for synthetic. */
  durationS: number
  /** The followed car, so the lap readout can name a driver. */
  selected: number
  onCut: () => void
}

export function Timeline({
  kind,
  kinds,
  onKind,
  clock,
  replay,
  replayError,
  recording,
  durationS,
  selected,
  onCut,
}: Props) {
  const slider = useRef<HTMLInputElement>(null)
  const time = useRef<HTMLSpanElement>(null)
  const lap = useRef<HTMLSpanElement>(null)
  const play = useRef<HTMLButtonElement>(null)
  const finite = Number.isFinite(durationS)

  useEffect(() => {
    const tick = () => {
      const c = clock.current
      if (slider.current && document.activeElement !== slider.current) {
        slider.current.value = String(c.tS)
      }
      if (time.current) {
        time.current.textContent = finite
          ? `${c.tS.toFixed(1)} / ${durationS.toFixed(1)} s`
          : `${c.tS.toFixed(1)} s`
      }
      if (play.current) play.current.textContent = c.playing ? '⏸' : '▶'
      if (lap.current && kind === 'engine' && recording?.cars[selected]) {
        // The engine counts completed laps; shown here as the lap being driven,
        // for the followed car and for the leader.
        const n = recording.cars.length
        let leader = 0
        for (let k = 0; k < n; k++) leader = Math.max(leader, lapAtTime(recording, c.tS, k))
        const pit = pitStateAt(recording, c.tS, selected)
        lap.current.textContent =
          `lap ${lapAtTime(recording, c.tS, selected) + 1} (leader ` +
          `${Math.min(leader + 1, recording.numLaps)}/${recording.numLaps}) · ` +
          `${recording.cars[selected].label} P${positionAt(recording, c.tS, selected)}` +
          (pit.active ? ` · PIT +${pit.penaltyPendingS.toFixed(0)} s` : pit.pitting ? ' · PITTING' : '')
      } else if (lap.current) {
        const car = kind === 'replay' ? replay?.cars[selected] : undefined
        if (!car) {
          lap.current.textContent = ''
        } else {
          // The lap the *followed* car is on, from the official boundaries. At
          // any instant the cars are on different laps, which is why the scrub
          // axis is time and the lap is only a label on it. Seeded one below the
          // first boundary for the same reason as `lapAt`: the window opens
          // partway through a lap.
          let n = (car.lapNumber[0] ?? 1) - 1
          for (let i = 0; i < car.lapStartT.length; i++) {
            if (car.lapStartT[i] <= c.tS) n = car.lapNumber[i]
          }
          lap.current.textContent = `lap ${n} · ${car.code}`
        }
      }
    }
    tick()
    const id = setInterval(tick, 1000 / TICK_HZ)
    return () => clearInterval(id)
  }, [clock, durationS, finite, replay, recording, selected, kind])

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 12,
        right: 12,
        width: 330,
        padding: '8px 12px',
        background: 'rgba(12,12,18,0.82)',
        border: '1px solid #2c2c38',
        borderRadius: 4,
        color: '#d8d8e0',
        font: '12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace',
      }}
    >
      <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
        {kinds.map((k) => (
          <button
            key={k}
            onClick={() => onKind(k)}
            disabled={k === 'replay' && !replay}
            title={BLURB[k]}
            style={{
              all: 'unset',
              cursor: k === 'replay' && !replay ? 'not-allowed' : 'pointer',
              padding: '3px 8px',
              borderRadius: 3,
              background: k === kind ? '#3a3a4c' : 'transparent',
              border: '1px solid #2c2c38',
              color: k === kind ? '#fff' : k === 'replay' && !replay ? '#55556a' : '#b8b8c4',
            }}
          >
            {LABEL[k]}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <span style={{ opacity: 0.6, alignSelf: 'center' }}>m</span>
      </div>

      {replayError && (
        <div style={{ color: '#ff8a5f', marginBottom: 6 }}>replay: {replayError}</div>
      )}

      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <button
          ref={play}
          onClick={() => togglePlay(clock.current)}
          title="play / pause (space)"
          style={{
            all: 'unset',
            cursor: 'pointer',
            width: 20,
            textAlign: 'center',
            color: '#fff',
          }}
        >
          ⏸
        </button>
        <input
          ref={slider}
          type="range"
          min={0}
          max={finite ? durationS : 1}
          step={kind === 'engine' && recording ? recording.dtS : replay ? replay.dtS : 0.1}
          defaultValue={0}
          disabled={!finite}
          onInput={(e) => {
            seekClock(clock.current, Number(e.currentTarget.value), durationS)
            onCut()
          }}
          style={{ flex: 1, accentColor: '#ff8a5f' }}
        />
      </div>
      {kind === 'engine' && recording && recording.pitEvents.length > 0 && (
        <PitMarks recording={recording} selected={selected} durationS={durationS} />
      )}

      <div style={{ marginTop: 4, display: 'flex', gap: 8 }}>
        <span ref={time} style={{ color: '#fff' }} />
        <span ref={lap} data-testid="timeline-lap" style={{ opacity: 0.75 }} />
        <span style={{ flex: 1 }} />
        {RATES.map((r) => (
          <button
            key={r}
            onClick={() => setRate(clock.current, r)}
            title={`playback rate ${r}x`}
            style={{
              all: 'unset',
              cursor: 'pointer',
              opacity: 0.7,
              color: '#b8b8c4',
            }}
          >
            {r}x
          </button>
        ))}
      </div>

      <p style={{ margin: '6px 0 0', opacity: 0.6 }}>
        {kind === 'replay' && replay
          ? `${replay.name} ${replay.year}, laps ${replay.fromLap}-${replay.toLap}, ` +
            `${replay.cars.length} cars at ${replay.hz} Hz. ` +
            BLURB.replay.slice(BLURB.replay.indexOf('Cars run'))
          : kind === 'engine' && recording
            ? `${recording.track.name}, ${recording.cars.length} cars, ` +
              `${recording.ticks} ticks at ${(1 / recording.dtS).toFixed(0)} Hz ` +
              `(sim ${recording.t0S.toFixed(1)}-${(recording.t0S + recording.durationS).toFixed(1)} s of a ` +
              `${recording.numLaps}-lap race). ` +
              BLURB.engine
            : BLURB.synthetic}
      </p>
    </div>
  )
}

/**
 * One mark per pit stop inside the recording, under the scrub bar: the
 * followed car's in amber and labelled, the rest dim. A stop is a single tick
 * in the engine, so each is a line, not a span. Positioned against the slider's
 * own width (the play button sits left of it), which is close enough for a
 * cue: the exact tick is in the hover text and the car panel.
 */
function PitMarks({
  recording,
  selected,
  durationS,
}: {
  recording: Recording
  selected: number
  durationS: number
}) {
  return (
    <div
      data-testid="timeline-pits"
      style={{ position: 'relative', height: 12, marginLeft: 26, marginTop: 2 }}
    >
      {recording.pitEvents.map((e) => {
        const mine = e.car === selected
        const car = recording.cars[e.car]
        return (
          <span
            key={`${e.car}-${e.tick}`}
            title={
              `${car.label} pit, end of lap ${e.lap}: ${e.compoundBefore} ` +
              `(${e.lifeBefore.toFixed(1)}% before that lap) → ${e.compoundAfter} ${e.lifeAfter.toFixed(1)}%, ` +
              `+${e.penaltyS.toFixed(1)} s (sim ${(recording.t0S + e.tS).toFixed(1)} s)`
            }
            style={{
              position: 'absolute',
              left: `${(e.tS / durationS) * 100}%`,
              top: 0,
              width: 2,
              height: mine ? 12 : 7,
              background: mine ? '#ffb020' : '#6a6a7a',
            }}
          />
        )
      })}
    </div>
  )
}
