import { useEffect, useMemo, useRef } from 'react'
import type { Mesh } from 'three'
import { buildRibbonGeometry } from './ribbon'
import type { TrackFrame } from './frame'

interface Props {
  frame: TrackFrame
  widthM: number
}

/**
 * The track surface. No kerbs, no run-off, no texture yet (M2): a flat colour
 * is what makes an orientation mistake obvious instead of decorated.
 */
export function TrackRibbon({ frame, widthM }: Props) {
  const mesh = useRef<Mesh>(null)
  const geometry = useMemo(() => buildRibbonGeometry(frame, widthM), [frame, widthM])
  useEffect(() => () => geometry.dispose(), [geometry])

  // Check G: the scene graph itself is not mirroring the geometry.
  // Every check in verify.ts runs on the data; this one runs on what actually
  // reaches the GPU. A negative scale anywhere up the parent chain reflects the
  // track after all the data checks have passed, and nothing else would catch it.
  useEffect(() => {
    const m = mesh.current
    if (!m) return
    m.updateWorldMatrix(true, false)
    const det = m.matrixWorld.determinant()
    console.log(
      `${det > 0 ? 'PASS' : 'FAIL'}  [I] Scene graph applies no mirroring — ` +
        `world matrix determinant ${det.toFixed(3)} (expect > 0)`,
    )
  }, [geometry])

  return (
    <mesh ref={mesh} geometry={geometry}>
      <meshStandardMaterial color="#3a3a42" roughness={0.9} metalness={0} />
    </mesh>
  )
}
