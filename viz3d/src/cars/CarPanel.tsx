import { useEffect, useRef } from 'react'
import type { CarIdentity } from './motion'

interface Props {
  cars: CarIdentity[]
  selected: number
  onSelect: (index: number) => void
  /** Written every frame by `Grid`; read here on a timer, never on a render. */
  readout: { current: { s: number; sUnwrapped: number; d: number; speedMps: number } }
  lengthM: number
  widthM: number
  /**
   * The followed car's lap number at an unwrapped arc length.
   *
   * A function rather than a number, because the two sources answer it
   * differently: the synthetic field counts laps geometrically, while a replay
   * uses the *official* timing boundaries — which sit up to 13 m from the
   * geometric `s = 0` crossing, so near the line the two genuinely disagree.
   * Passing the question rather than an offset is also what keeps the timeline
   * and this panel from showing different laps at the same moment.
   *
   * Supplied by `App`, which is the only place that knows which source is
   * running — so lap number never has to enter `FollowState`, and `rig.ts` stays
   * untouched.
   */
  lapAt: (carIndex: number, sUnwrapped: number) => number
  /** What is driving the cars, for the one line of prose at the bottom. */
  sourceKind: string
  /** Debug toggle: a stripe on every wheel, so spin can be seen. */
  wheelMarkers: boolean
  onWheelMarkers: (on: boolean) => void
}

/**
 * Pick a car and watch its `(s, d)`.
 *
 * `s` changes sixty times a second, so it is deliberately *not* React state:
 * the panel polls the ref on an interval and writes `textContent` directly.
 * Re-rendering this component at frame rate would drag the whole Canvas subtree
 * through React's reconciler for the sake of a number nobody can read that
 * fast. 12 Hz is well past the point where the readout looks live.
 */
const READOUT_HZ = 12

export function CarPanel({
  cars,
  selected,
  onSelect,
  readout,
  lengthM,
  widthM,
  lapAt,
  sourceKind,
  wheelMarkers,
  onWheelMarkers,
}: Props) {
  const sRef = useRef<HTMLSpanElement>(null)
  const dRef = useRef<HTMLSpanElement>(null)
  const lapRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const tick = () => {
      const { s, sUnwrapped, d, speedMps } = readout.current
      if (sRef.current) sRef.current.textContent = `${s.toFixed(1)} m`
      if (dRef.current) dRef.current.textContent = `${d >= 0 ? '+' : ''}${d.toFixed(2)} m`
      if (lapRef.current) {
        // Live speed and a real lap count. The old line here estimated a lap time
        // as `lengthM / speedMps`, which assumed a constant speed — true of the
        // synthetic field and not of a replay, where it would read as a lap time
        // that swings by a factor of five through every braking zone.
        lapRef.current.textContent =
          `${speedMps.toFixed(1)} m/s · lap ${lapAt(selected, sUnwrapped)} · ` +
          `${((s / lengthM) * 100).toFixed(1)}% round`
      }
    }
    tick()
    const id = setInterval(tick, 1000 / READOUT_HZ)
    return () => clearInterval(id)
  }, [readout, lengthM, selected, lapAt])

  const car = cars[selected]

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 12,
        left: 12,
        width: 300,
        padding: '8px 12px',
        background: 'rgba(12,12,18,0.82)',
        border: '1px solid #2c2c38',
        borderRadius: 4,
        color: '#d8d8e0',
        font: '12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace',
      }}
    >
      <div style={{ color: '#fff', marginBottom: 6 }}>
        {cars.length} cars · following{' '}
        <span style={{ color: car?.hex }}>
          {car?.label} {car?.name ?? car?.colourName}
        </span>
      </div>

      {/* One swatch per car. A <select> would hide the colours, which are the
          only thing distinguishing one car from another on track. Under a replay
          the label is the driver's own code, so the swatch row doubles as the
          running order — the extractor writes the cars out in race order. */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
        {cars.map((c) => (
          <button
            key={c.index}
            onClick={() => onSelect(c.index)}
            /* Identity only. `d` and speed used to be in here as static numbers
               from the car's spec; under a replay both vary every frame, and both
               are live in the readout below. */
            title={[c.label, c.name, c.colourName].filter(Boolean).join(' · ')}
            style={{
              all: 'unset',
              cursor: 'pointer',
              width: 22,
              height: 18,
              background: c.hex,
              borderRadius: 2,
              outline: c.index === selected ? '2px solid #fff' : '1px solid #00000060',
              outlineOffset: c.index === selected ? 1 : 0,
            }}
          />
        ))}
      </div>

      <div>
        s <span ref={sRef} style={{ color: '#fff' }} /> · d{' '}
        <span ref={dRef} style={{ color: '#ff8a5f' }} />
      </div>
      <div style={{ opacity: 0.6, marginTop: 4 }}>
        <span ref={lapRef} />
      </div>
      <p style={{ margin: '6px 0 0', opacity: 0.6 }}>
        positive d = right of the direction of travel. Ribbon is {widthM.toFixed(1)} m wide.{' '}
        {sourceKind === 'replay'
          ? 'Real telemetry: d is measured against a centreline that is the median ' +
            'of racing lines, so it stays within a metre and the field runs nearly ' +
            'single file.'
          : 'Cars hold a fixed d and a fixed speed, so the order changes only ' +
            'because the speeds differ — there is no overtaking logic.'}
      </p>
      {/* Debug. The tyres are uniform grey, so without this a wheel spinning
          the wrong way, or not at all, looks exactly like a correct one. Watch
          it at 0.25x: at 1x the wheel turns ~150° a frame and aliases. */}
      <label style={{ display: 'flex', gap: 6, marginTop: 6, opacity: 0.75, cursor: 'pointer' }}>
        <input
          type="checkbox"
          checked={wheelMarkers}
          onChange={(e) => onWheelMarkers(e.currentTarget.checked)}
          style={{ margin: 0, accentColor: '#ffe600' }}
        />
        debug: wheel markers (w)
      </label>
    </div>
  )
}
