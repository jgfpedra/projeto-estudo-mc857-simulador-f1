import { CAMERA_MODES } from './rig'
import type { CameraMode } from './rig'
import type { CarIdentity } from '../cars/motion'

interface Props {
  mode: CameraMode
  onSelect: (mode: CameraMode) => void
  /** The car the two follow cameras track — the one `CarPanel` is showing. */
  car: CarIdentity | undefined
}

const LABEL: Record<CameraMode, string> = {
  orbit: 'orbit',
  chase: 'chase',
  onboard: 'T-cam',
}

const BLURB: Record<CameraMode, string> = {
  orbit: 'drag to orbit the whole circuit. the development view.',
  chase: 'behind and above, damped along the track so it lags into corners rather than cutting across them.',
  onboard: 'over the airbox, rolling into corners with lateral acceleration.',
}

/**
 * Pick a camera.
 *
 * Plain DOM outside the Canvas, like the other two panels: a mode change is one
 * React render per click, and nothing here reads anything that moves.
 */
export function CameraPanel({ mode, onSelect, car }: Props) {
  return (
    <div
      style={{
        position: 'absolute',
        top: 12,
        right: 12,
        width: 240,
        padding: '8px 12px',
        background: 'rgba(12,12,18,0.82)',
        border: '1px solid #2c2c38',
        borderRadius: 4,
        color: '#d8d8e0',
        font: '12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace',
      }}
    >
      <div style={{ display: 'flex', gap: 4 }}>
        {CAMERA_MODES.map((m, i) => (
          <button
            key={m}
            onClick={() => onSelect(m)}
            title={`${i + 1} — ${BLURB[m]}`}
            style={{
              all: 'unset',
              cursor: 'pointer',
              flex: 1,
              textAlign: 'center',
              padding: '3px 0',
              borderRadius: 2,
              color: m === mode ? '#fff' : '#d8d8e0',
              background: m === mode ? '#2c2c38' : 'transparent',
              outline: m === mode ? '1px solid #6a6a80' : '1px solid #00000060',
            }}
          >
            {LABEL[m]}
          </button>
        ))}
      </div>

      <div style={{ marginTop: 6 }}>
        {mode === 'orbit' ? (
          <span style={{ opacity: 0.6 }}>free camera</span>
        ) : (
          <>
            following{' '}
            <span style={{ color: car?.hex }}>
              {car?.label} {car?.name ?? car?.colourName}
            </span>
          </>
        )}
      </div>

      <p style={{ margin: '4px 0 0', opacity: 0.6 }}>
        {BLURB[mode]} keys 1/2/3, or c to cycle.
      </p>
    </div>
  )
}
