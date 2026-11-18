import { useMemo } from 'react'
import type { CSSProperties } from 'react'
import { BufferAttribute, BufferGeometry, Vector3 } from 'three'
import { useThree } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import { curvatureAt, toWorld } from './frame'
import type { TrackFrame } from './frame'
import type { Track } from './types'

/** Lift markers off the surface so they don't z-fight with the ribbon. */
const MARKER_H = 0.08
const CHEVRON_SPACING_M = 250

/**
 * Push triangles into a flat array. Vertices are given as `(s, d)` pairs and
 * must be listed anti-clockwise seen from above, which is front-facing for an
 * upward normal — same winding rule as the ribbon.
 */
function pushTri(
  out: number[],
  frame: TrackFrame,
  a: [number, number],
  b: [number, number],
  c: [number, number],
) {
  const v = new Vector3()
  for (const [s, d] of [a, b, c]) {
    toWorld(frame, s, d, MARKER_H, v)
    out.push(v.x, v.y, v.z)
  }
}

function quad(
  out: number[],
  frame: TrackFrame,
  sBack: number,
  sFront: number,
  dLeft: number,
  dRight: number,
) {
  pushTri(out, frame, [sBack, dLeft], [sBack, dRight], [sFront, dRight])
  pushTri(out, frame, [sBack, dLeft], [sFront, dRight], [sFront, dLeft])
}

function geometryFrom(positions: number[]): BufferGeometry {
  const g = new BufferGeometry()
  g.setAttribute('position', new BufferAttribute(new Float32Array(positions), 3))
  g.computeVertexNormals()
  g.computeBoundingSphere()
  return g
}

interface Props {
  track: Track
  frame: TrackFrame
}

/**
 * Everything needed to read orientation off the screen rather than off a
 * console table:
 *
 * - chevrons pointing in the direction of increasing `s`;
 * - a start/finish line at `s = 0`;
 * - a tick across the track at every corner, labelled `T1..T11`, with the
 *   label placed on the *outside* of the turn.
 *
 * That last part is the visual twin of check F. The outside of a corner is
 * `d` of the opposite sign to the curvature, so a flipped `right` vector puts
 * all eleven labels on the inside of their corners — obvious at a glance, and
 * it would survive every check that only looks at the loop's shape.
 */
export function OrientationAids({ track, frame }: Props) {
  const half = track.widthM / 2
  /**
   * drei's `<Html>` appends to `events.connected`, falling back to the canvas's
   * parent. R3F 9 connects events in the Canvas's own layout effect, which runs
   * after its children's, so a label mounted straight away sees the fallback
   * first and re-targets one commit later. drei 10 handles that by unmounting
   * its private React root and creating a new one on the same element, and
   * under React 19 the deferred unmount wipes the new root's content: the
   * label's box is placed but empty (the S/F label vanished this way). Mounting
   * the labels only once events are connected gives them their final target
   * from the first render.
   */
  const connected = useThree((s) => s.events.connected)

  const chevrons = useMemo(() => {
    const pos: number[] = []
    for (let s = 0; s < frame.lengthM; s += CHEVRON_SPACING_M) {
      pushTri(pos, frame, [s + 11, 0], [s - 5, -3.2], [s - 5, 3.2])
    }
    return geometryFrom(pos)
  }, [frame])

  const startFinish = useMemo(() => {
    const pos: number[] = []
    quad(pos, frame, track.startFinishS - 1, track.startFinishS + 1, -half, half)
    return geometryFrom(pos)
  }, [frame, track.startFinishS, half])

  const cornerTicks = useMemo(() => {
    const pos: number[] = []
    for (const c of track.corners) quad(pos, frame, c.s - 0.8, c.s + 0.8, -half, half)
    return geometryFrom(pos)
  }, [frame, track.corners, half])

  const labels = useMemo(
    () =>
      track.corners.map((c) => {
        // Outside of the turn: right-hand corner (curvature > 0) => label left.
        const side = curvatureAt(frame, c.s) > 0 ? -1 : 1
        const p = toWorld(frame, c.s, side * (half + 14), MARKER_H)
        return { corner: c, hand: side < 0 ? 'right' : 'left', position: p }
      }),
    [frame, track.corners, half],
  )

  const sfLabel = useMemo(
    () => toWorld(frame, track.startFinishS, -(half + 14), MARKER_H),
    [frame, track.startFinishS, half],
  )

  return (
    <group>
      <mesh geometry={chevrons}>
        <meshBasicMaterial color="#ffd400" />
      </mesh>
      <mesh geometry={startFinish}>
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <mesh geometry={cornerTicks}>
        <meshBasicMaterial color="#7a7a88" />
      </mesh>

      {connected ? (
        <>
          <Html position={sfLabel} center style={labelStyle('#ffffff')}>
            S/F · s=0
          </Html>
          {labels.map(({ corner, hand, position }) => (
            <Html key={corner.number} position={position} center style={labelStyle('#ffd400')}>
              T{corner.number} {hand === 'right' ? '→' : '←'}
              <span style={{ opacity: 0.65, marginLeft: 6 }}>{corner.name}</span>
            </Html>
          ))}
        </>
      ) : null}
    </group>
  )
}

function labelStyle(color: string): CSSProperties {
  return {
    color,
    font: '500 12px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace',
    background: 'rgba(12,12,18,0.75)',
    padding: '2px 6px',
    borderRadius: 3,
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
    userSelect: 'none',
  }
}
