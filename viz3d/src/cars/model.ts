import { useMemo } from 'react'
import { useGLTF } from '@react-three/drei'
import { Box3, Matrix4, Vector3 } from 'three'
import type { BufferGeometry, Material, Mesh, Object3D } from 'three'

function fail(msg: string): never {
  throw new Error(`car model: ${msg}`)
}

/**
 * Everything that is true of one particular glTF file and of nothing else.
 *
 * This is the one place to edit when the model changes. The corrections
 * themselves are *derived* from the file's measured bounding box rather than
 * written down, so a new model needs its axis convention and a target length
 * here and nothing anywhere else — centring and the ground datum fall out.
 */
export interface CarModelSpec {
  url: string
  /** Direction the nose points, in the model's own space. */
  forward: Vector3
  /** Which way is up, in the model's own space. */
  up: Vector3
  /**
   * The dimension used for uniform scaling when no live collision bounds are
   * supplied. A stylized model cannot match both dimensions without distortion.
   */
  fit: { axis: 'width' | 'length'; metres: number }
  /** Optional live collision bounds from the physics engine, in metres. */
  dimensions?: { widthM: number; lengthM: number; heightM: number }
  /**
   * Name of the material carrying the car's paint — the one primitive that
   * takes a per-car colour. Everything else (trim, glass, rims, tyres) stays
   * uniform across the field. Naming it here rather than guessing keeps the
   * next model's answer next to its axes.
   */
  paintMaterial: string
  /** Prefix identifying the wheel nodes, which spin and so cannot be baked. */
  wheelPrefix: string
}

/**
 * Kenney Racing Kit, CC0 (see `ASSETS.md`). A placeholder with road-car
 * proportions — a proper open-wheel model replaces it.
 *
 * Measured raw, straight out of the file: 1.345937 m long, 0.728833 m wide,
 * 0.397014 m tall, bbox centre (-0.350, +0.165, -0.663), tyre contact plane at
 * y = -0.033520. Roughly quarter scale, and centred on nothing in particular:
 * the root node carries a translation that pushes the model off its own origin
 * rather than onto it. `model.test.ts` holds those numbers as a guard against
 * the file being swapped underneath us; nothing in the correction path reads
 * them.
 *
 * It faces **+Z**, which three things agree on: the `wheelFront*` nodes sit at
 * higher z than the `wheelBack*` ones; the +Z end narrows to a nose while the
 * -Z end keeps full width and rises into a spoiler; and with forward = +Z the
 * kit's own left/right wheel names land on the correct sides. The convention in
 * `place.ts` is forward = -Z, so the correction is a 180 degree yaw about Y.
 *
 * Anchored on **width**, at the 2.0 m an F1 car is actually limited to. This
 * body is 1.85:1 where an open-wheel car is nearer 2.8:1, so one uniform scale
 * cannot satisfy both dimensions and the length falls out at 3.693 m — stubby,
 * and obviously a placeholder.
 *
 * Width is the one to protect because `d` is measured in metres across a 13 m
 * ribbon, so car width is the reference anyone reads lateral spacing against
 * when fitting a grid. Anchoring on length instead gave a 2.708 m car, 35% over
 * the real maximum, which would have made the field look like it fits when it
 * does not. A short car is visibly a placeholder; an over-wide one is a
 * plausible-looking lie.
 */
export const RACE_CAR_RED: CarModelSpec = {
  url: '/models/raceCarRed.glb',
  forward: new Vector3(0, 0, 1),
  up: new Vector3(0, 1, 0),
  fit: { axis: 'width', metres: 2.0 },
  paintMaterial: 'red',
  wheelPrefix: 'wheel',
}

/**
 * The correction, as one matrix: model space in, car-local space out.
 *
 * Pure, and split from the loading for the same reason `parseTrack` is split
 * from `loadTrack` — so the transform can be driven from a test without R3F,
 * and so it is the *same* code path the viewer runs rather than a parallel one.
 *
 * Car-local space is the one `carBasis` expects: -Z forward, +X right, +Y up,
 * plan-view centre on the origin, tyres on y = 0. That last part is why
 * `Car.tsx` passes `h = 0` where the box needed half its own height.
 */
export function carModelMatrix(raw: Box3, spec: CarModelSpec): Matrix4 {
  const forward = spec.forward.clone().normalize()
  const up = spec.up.clone().normalize()
  const right = new Vector3().crossVectors(forward, up)
  if (right.lengthSq() < 1e-12) fail(`${spec.url}: forward and up are parallel`)
  right.normalize()

  /*
   * `makeBasis(right, up, -forward)` is the matrix taking car-local axes *to*
   * model axes — the same three columns `carBasis` assembles from the track
   * frame, one level down. We want the other direction, and for an orthonormal
   * basis the inverse is the transpose. Going through the basis rather than
   * writing "rotate 180 about Y" is what keeps this general: the next model's
   * axis convention is a spec change, not a code change.
   */
  const rot = new Matrix4().makeBasis(right, up, forward.clone().negate()).transpose()

  /*
   * Measure *after* rotating, so the anchored dimension is a known axis of
   * car-local space — z for length, x for width — rather than whichever raw
   * axis this particular file happened to use for it.
   */
  const rotated = raw.clone().applyMatrix4(rot)
  const size = rotated.getSize(new Vector3())
  const measured = spec.fit.axis === 'width' ? size.x : size.z
  if (!(measured > 0)) fail(`${spec.url}: zero ${spec.fit.axis}`)
  const k = spec.fit.metres / measured

  // Live races supply chassis bounds. The stylized placeholder is stretched
  // to match those bounds; its detailed shape still differs from the box.
  const sx = spec.dimensions ? spec.dimensions.widthM / size.x : k
  const sy = spec.dimensions ? spec.dimensions.heightM / size.y : k
  const sz = spec.dimensions ? spec.dimensions.lengthM / size.z : k
  if (![sx, sy, sz].every((scale) => Number.isFinite(scale) && scale > 0)) fail(`${spec.url}: invalid dimensions`)
  const pre = new Matrix4().makeScale(sx, sy, sz).multiply(rot)

  /*
   * Datum. Plan-view centre to the origin so `(s, d)` positions the middle of
   * the car, and the lowest point — the tyres — to y = 0 so `h` means ride
   * height and nothing else.
   */
  const box = raw.clone().applyMatrix4(pre)
  return new Matrix4()
    .makeTranslation(-(box.min.x + box.max.x) / 2, -box.min.y, -(box.min.z + box.max.z) / 2)
    .multiply(pre)
}

/**
 * Measure a loaded glTF scene and bake the correction into a copy of it.
 *
 * The copy is not optional. `useGLTF` caches by URL and hands every caller the
 * same object, so correcting it in place would corrupt the cache for everyone
 * after the first — which is precisely what M4's twenty cars will be.
 * `clone(true)` shares geometries and materials, which is what we want anyway.
 */
export function adaptCarModel(scene: Object3D, spec: CarModelSpec = RACE_CAR_RED): Object3D {
  const model = scene.clone(true)
  const raw = new Box3().setFromObject(model)
  if (raw.isEmpty()) fail(`${spec.url}: no geometry to measure`)
  // The configured axes are orthogonal, so Three can decompose this transform.
  model.applyMatrix4(carModelMatrix(raw, spec))
  model.updateMatrixWorld(true)
  return model
}

/** The adapted model, corrected once per load rather than once per frame. */
export function useCarModel(spec: CarModelSpec = RACE_CAR_RED): Object3D {
  const { scene } = useGLTF(spec.url)
  return useMemo(() => adaptCarModel(scene, spec), [scene, spec])
}

useGLTF.preload(RACE_CAR_RED.url)

/** One drawable primitive, in car-local space with the adapter already baked. */
export interface CarPart {
  name: string
  geometry: BufferGeometry
  material: Material
  /** True for the primitive that takes a per-car colour. */
  paint: boolean
}

/** A wheel: its parts are relative to its own centre, so it can spin in place. */
export interface CarWheel {
  name: string
  /** Centre of the wheel in car-local space. */
  centre: Vector3
  radiusM: number
  /** Unit axle direction in car-local space. */
  axle: Vector3
  parts: CarPart[]
}

export interface CarGeometry {
  body: CarPart[]
  wheels: CarWheel[]
}

/**
 * Flatten the adapted model into geometry an `InstancedMesh` can draw.
 *
 * The adapter's matrix is baked into the *vertices* here, once, so an instance
 * matrix is pure placement and nothing per-frame has to remember that this
 * model needed correcting. Bodywork is baked all the way into car-local space;
 * wheel parts are baked relative to their own centre instead, because they have
 * to keep turning.
 *
 * Geometries are cloned before they are transformed — `useGLTF` caches them and
 * `applyMatrix4` writes through the position attribute in place, so skipping
 * the clone would corrupt the cache permanently and silently.
 */
export function carGeometry(scene: Object3D, spec: CarModelSpec = RACE_CAR_RED): CarGeometry {
  const model = adaptCarModel(scene, spec)
  model.updateMatrixWorld(true)

  const wheelNodes = new Map<string, Object3D>()
  model.traverse((o) => {
    if (o.name.startsWith(spec.wheelPrefix) && !wheelNodes.has(o.name)) wheelNodes.set(o.name, o)
  })
  if (wheelNodes.size === 0) fail(`${spec.url}: no nodes named ${spec.wheelPrefix}*`)

  const owner = (o: Object3D): Object3D | null => {
    for (let n: Object3D | null = o; n; n = n.parent) if (wheelNodes.has(n.name)) return n
    return null
  }

  const part = (mesh: Mesh, m: Matrix4): CarPart => {
    const material = (mesh.material as Material).clone()
    const paint = material.name === spec.paintMaterial
    // Per-instance colour multiplies the material colour, so the paint material
    // goes white and the palette entry lands exactly instead of tinting pink.
    if (paint && 'color' in material) (material as unknown as { color: { set(v: string): void } }).color.set('#ffffff')
    return { name: mesh.name, geometry: mesh.geometry.clone().applyMatrix4(m), material, paint }
  }

  const body: CarPart[] = []
  const wheels = new Map<string, CarWheel>()
  const scratch = new Matrix4()

  model.traverse((o) => {
    const mesh = o as Mesh
    if (!mesh.isMesh) return
    const node = owner(o)
    if (!node) {
      body.push(part(mesh, mesh.matrixWorld))
      return
    }
    let wheel = wheels.get(node.name)
    if (!wheel) {
      const box = new Box3().setFromObject(node)
      const size = box.getSize(new Vector3())
      /*
       * The axle is the axis the wheel is thinnest along; the other two are
       * diameters and agree to within roundoff on any wheel worth the name.
       * Derived rather than written down, so a model with its wheels on a
       * different axis needs no edit here.
       */
      const dims: [number, Vector3][] = [
        [size.x, new Vector3(1, 0, 0)],
        [size.y, new Vector3(0, 1, 0)],
        [size.z, new Vector3(0, 0, 1)],
      ]
      dims.sort((a, b) => a[0] - b[0])
      wheel = {
        name: node.name,
        centre: box.getCenter(new Vector3()),
        radiusM: (dims[1][0] + dims[2][0]) / 4,
        axle: dims[0][1],
        parts: [],
      }
      wheels.set(node.name, wheel)
    }
    // Relative to the wheel centre, so the instance matrix can rotate about it.
    scratch
      .makeTranslation(-wheel.centre.x, -wheel.centre.y, -wheel.centre.z)
      .multiply(mesh.matrixWorld)
    wheel.parts.push(part(mesh, scratch))
  })

  return { body, wheels: [...wheels.values()] }
}
