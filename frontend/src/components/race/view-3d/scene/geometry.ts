/**
 * Geometria da pista, da via dos boxes e da linha de chegada.
 *
 * `buildRibbonGeometry` vem de `viz3d/src/track/ribbon.ts`; `buildPitRibbon` e
 * `buildPitEdges` de `viz3d/src/live/pitRibbon.ts`; `buildStartLine` do corpo
 * de `viz3d/src/live/StartFinishLine.tsx`. Mesma matemática, mesmos vértices.
 */
import { BufferAttribute, BufferGeometry, Float32BufferAttribute, Uint32BufferAttribute, Vector3 } from "three"

import type { TrackFrame } from "./track-frame.ts"
import { startLineEndpoints } from "./race-track.ts"
import type { SceneTrack } from "./race-track.ts"

/**
 * Superfície da pista como faixa fechada, dois vértices por ponto da linha:
 * `2i` à esquerda e `2i + 1` à direita. O último ponto liga de volta ao
 * primeiro, então a linha de chegada é uma aresta compartilhada.
 */
export function buildRibbonGeometry(frame: TrackFrame, widthM: number, heightM = 0): BufferGeometry {
  const n = frame.points.length
  const half = widthM / 2

  const positions = new Float32Array(n * 2 * 3)
  const normals = new Float32Array(n * 2 * 3)
  const uvs = new Float32Array(n * 2 * 2)

  for (let i = 0; i < n; i++) {
    const c = frame.points[i]
    const r = frame.right[i]
    const up = frame.up[i]
    const u = frame.s[i] / frame.lengthM

    for (let side = 0; side < 2; side++) {
      const sign = side === 0 ? -1 : 1
      const v = (i * 2 + side) * 3
      positions[v + 0] = c.x + r.x * sign * half + up.x * heightM
      positions[v + 1] = c.y + r.y * sign * half + up.y * heightM
      positions[v + 2] = c.z + r.z * sign * half + up.z * heightM
      normals[v + 0] = up.x
      normals[v + 1] = up.y
      normals[v + 2] = up.z
      const t = (i * 2 + side) * 2
      uvs[t + 0] = u
      uvs[t + 1] = side
    }
  }

  // Anti-horário visto de cima: frontal para a normal para cima.
  const index = new Uint32Array(n * 6)
  for (let i = 0; i < n; i++) {
    const a = i * 2
    const b = i * 2 + 1
    const c = ((i + 1) % n) * 2
    const d = ((i + 1) % n) * 2 + 1
    const o = i * 6
    index[o + 0] = a
    index[o + 1] = b
    index[o + 2] = c
    index[o + 3] = b
    index[o + 4] = d
    index[o + 5] = c
  }

  const geometry = new BufferGeometry()
  geometry.setAttribute("position", new BufferAttribute(positions, 3))
  geometry.setAttribute("normal", new BufferAttribute(normals, 3))
  geometry.setAttribute("uv", new BufferAttribute(uvs, 2))
  geometry.setIndex(new BufferAttribute(index, 1))
  geometry.computeBoundingSphere()
  return geometry
}

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
      positions.push(
        points[i].x + right.x * side * halfWidth,
        points[i].y + 0.03,
        points[i].z + right.z * side * halfWidth,
      )
    }
    if (i < points.length - 1) {
      const a = i * 2
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2)
    }
  }
  const geometry = new BufferGeometry()
  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3))
  geometry.setIndex(new Uint32BufferAttribute(indices, 1))
  geometry.computeVertexNormals()
  geometry.computeBoundingSphere()
  return geometry
}

/** Contornos da via aberta, seguindo exatamente as bordas da superfície. */
export function buildPitEdges(surface: BufferGeometry): BufferGeometry {
  const surfacePositions = surface.getAttribute("position")
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
  geometry.setAttribute("position", new Float32BufferAttribute(positions, 3))
  geometry.computeBoundingSphere()
  return geometry
}

/** Faixa branca de 1 m na linha de chegada, de borda a borda da pista. */
export function buildStartLine(track: SceneTrack): BufferGeometry {
  const pts = track.points
  const [left, right] = startLineEndpoints(track)
  const tangent = pts[1].clone().sub(pts[pts.length - 1]).normalize().multiplyScalar(0.5)
  const height = new Vector3(0, 0.08, 0)
  const a = left.clone().sub(tangent).add(height)
  const b = right.clone().sub(tangent).add(height)
  const c = right.clone().add(tangent).add(height)
  const d = left.clone().add(tangent).add(height)
  const geometry = new BufferGeometry()
  geometry.setAttribute(
    "position",
    new Float32BufferAttribute([...a.toArray(), ...b.toArray(), ...c.toArray(), ...a.toArray(), ...c.toArray(), ...d.toArray()], 3),
  )
  geometry.computeVertexNormals()
  geometry.computeBoundingSphere()
  return geometry
}
