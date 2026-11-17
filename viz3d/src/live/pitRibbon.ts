import { BufferGeometry, Float32BufferAttribute, Uint32BufferAttribute, Vector3 } from 'three'

/** Superfície aberta dos boxes, sem fechar a última amostra na primeira. */
export function buildPitRibbon(points: Vector3[], widthM: number): BufferGeometry {
  const positions: number[] = []
  const indices: number[] = []
  const up = new Vector3(0, 1, 0)
  const halfWidth = widthM / 2
  for (let i = 0; i < points.length; i++) {
    const before = points[Math.max(0, i - 1)]
    const after = points[Math.min(points.length - 1, i + 1)]
    const tangent = after.clone().sub(before)
    // Uma inversão exata pode anular a diferença central; usa o segmento seguinte.
    if (tangent.lengthSq() < 1e-12) tangent.subVectors(after, points[i])
    if (tangent.lengthSq() < 1e-12) tangent.subVectors(points[i], before)
    const right = tangent.normalize().cross(up).normalize()
    for (const side of [-1, 1]) {
      positions.push(points[i].x + right.x * side * halfWidth,
                     points[i].y + 0.03,
                     points[i].z + right.z * side * halfWidth)
    }
    if (i < points.length - 1) {
      const a = i * 2
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2)
    }
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
  geometry.setIndex(new Uint32BufferAttribute(indices, 1))
  geometry.computeVertexNormals()
  geometry.computeBoundingSphere()
  return geometry
}

/** Contornos de destaque, ainda seguindo exatamente as bordas da via aberta. */
export function buildPitEdges(surface: BufferGeometry): BufferGeometry {
  const surfacePositions = surface.getAttribute('position')
  const samples = surfacePositions.count / 2
  const positions: number[] = []
  for (let i = 0; i < samples - 1; i++) {
    for (const side of [0, 1]) {
      for (const vertex of [i * 2 + side, (i + 1) * 2 + side]) {
        positions.push(surfacePositions.getX(vertex), surfacePositions.getY(vertex) + 0.02, surfacePositions.getZ(vertex))
      }
    }
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
  geometry.computeBoundingSphere()
  return geometry
}
