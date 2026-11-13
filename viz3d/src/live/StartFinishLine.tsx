import { useEffect, useMemo } from 'react'
import { BufferGeometry, DoubleSide, Float32BufferAttribute, Vector3 } from 'three'
import type { Track } from '../track/types'
import { startLineEndpoints } from './track'

export function StartFinishLine({ track }: { track: Track }) {
  const geometry = useMemo(() => {
    const [left, right] = startLineEndpoints(track)
    const tangent = track.points[1].clone().sub(track.points[track.points.length - 1]).normalize().multiplyScalar(0.5)
    const height = new Vector3(0, 0.08, 0)
    const a = left.clone().sub(tangent).add(height)
    const b = right.clone().sub(tangent).add(height)
    const c = right.clone().add(tangent).add(height)
    const d = left.clone().add(tangent).add(height)
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new Float32BufferAttribute([...a.toArray(), ...b.toArray(), ...c.toArray(), ...a.toArray(), ...c.toArray(), ...d.toArray()], 3))
    geometry.computeVertexNormals()
    return geometry
  }, [track])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <mesh geometry={geometry}><meshBasicMaterial color="white" side={DoubleSide} /></mesh>
}
