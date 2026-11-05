import { BufferAttribute, BufferGeometry } from 'three'
import type { TrackFrame } from './frame'

/**
 * Build the track surface as a closed triangle strip, two vertices per
 * centreline sample.
 *
 * Deliberately not `ExtrudeGeometry` (docs/3d-design.md section 7): per-vertex
 * control is what makes variable width, banking and the wider run-off /
 * narrower kerb ribbons a parameter change rather than a rewrite.
 *
 * Vertex layout, for sample `i` at arc length `s[i]`:
 *
 *     2i     = centre - right * halfWidth     (left edge,  uv.y = 0)
 *     2i + 1 = centre + right * halfWidth     (right edge, uv.y = 1)
 *
 * and the strip wraps, so the last sample indexes back into sample 0 and the
 * seam at start/finish is a real shared edge rather than a visible join.
 *
 * `uv.x` is `s / lengthM`, i.e. lap fraction, so a kerb texture only needs
 * `repeat.x` set to the stripe count to get stripes of constant length in
 * metres. `uv.y` runs 0 (left) to 1 (right).
 *
 * @param widthM   full ribbon width in metres
 * @param heightM  vertical offset along the surface normal, for stacking the
 *                 run-off and kerb ribbons later without z-fighting
 */
export function buildRibbonGeometry(
  frame: TrackFrame,
  widthM: number,
  heightM = 0,
): BufferGeometry {
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
      const sign = side === 0 ? -1 : 1 // 0 = left edge, 1 = right edge
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

  // Two triangles per segment. Winding is counter-clockwise seen from above,
  // which is front-facing for an upward normal: get this backwards and the
  // track vanishes under a default (back-face culling) material.
  const index = new Uint32Array(n * 6)
  for (let i = 0; i < n; i++) {
    const a = i * 2 // left,  this sample
    const b = i * 2 + 1 // right, this sample
    const c = ((i + 1) % n) * 2 // left,  next sample
    const d = (((i + 1) % n) * 2) + 1 // right, next sample
    const o = i * 6
    index[o + 0] = a
    index[o + 1] = b
    index[o + 2] = c
    index[o + 3] = b
    index[o + 4] = d
    index[o + 5] = c
  }

  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new BufferAttribute(positions, 3))
  geometry.setAttribute('normal', new BufferAttribute(normals, 3))
  geometry.setAttribute('uv', new BufferAttribute(uvs, 2))
  geometry.setIndex(new BufferAttribute(index, 1))
  geometry.computeBoundingSphere()
  return geometry
}
