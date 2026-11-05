import { useEffect, useRef } from 'react'
import { SOURCE_KINDS } from '../cars/motion'
import type { SourceKind } from '../cars/motion'
import { seekClock, setRate, togglePlay } from './clock'
import type { ClockState } from './clock'
import type { Replay } from './types'

const LABEL: Record<SourceKind, string> = {
  synthetic: 'synthetic',
  replay: 'replay',
}

const BLURB: Record<SourceKind, string> = {
  synthetic:
    'Twenty cars at a constant speed with fixed lateral offsets, spread across ' +
    'the ribbon. Deterministic, so a screenshot means something.',
  replay:
    'Real position samples from the race, projected onto the centreline to ' +
    'recover (s, d). Cars run almost single file: the centreline is the median ' +
    'of racing lines, so the field sits within centimetres of it.',
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
  onKind: (kind: SourceKind) => void
  /** Advanced by `Grid`; written here on a scrub. */
  clock: { current: ClockState }
  /** `null` while the replay is still loading, or if it failed. */
  replay: Replay | null
  replayError: string | null
  /** Seconds of content for the current source; `Infinity` for synthetic. */
  durationS: number
  /** The followed car, so the lap readout can name a driver. */
  selected: number
  onCut: () => void
}

export function Timeline({
  kind,
  onKind,
  clock,
  replay,
  replayError,
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
      if (lap.current) {
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
  }, [clock, durationS, finite, replay, selected, kind])

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
        {SOURCE_KINDS.map((k) => (
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
          step={replay ? replay.dtS : 0.1}
          defaultValue={0}
          disabled={!finite}
          onInput={(e) => {
            seekClock(clock.current, Number(e.currentTarget.value), durationS)
            onCut()
          }}
          style={{ flex: 1, accentColor: '#ff8a5f' }}
        />
      </div>

      <div style={{ marginTop: 4, display: 'flex', gap: 8 }}>
        <span ref={time} style={{ color: '#fff' }} />
        <span ref={lap} style={{ opacity: 0.75 }} />
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
          : BLURB.synthetic}
      </p>
    </div>
  )
}
