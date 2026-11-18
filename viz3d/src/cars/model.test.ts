import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { Box3, Matrix4, Vector3 } from 'three'
import { wheelMatrix } from './instance'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { Object3D } from 'three'
import { RACE_CAR_RED, adaptCarModel, carGeometry, carModelMatrix } from './model'
import type { CarModelSpec } from './model'

/**
 * Float slop on a chain of a rotation, a uniform scale and a translation. Not a
 * fudge factor: the largest coordinate here is 2.5 m and a double carries far
 * more than that, so anything above this is a real error and not roundoff.
 */
const EPS = 1e-9

/**
 * Same artifact and the same loader the viewer runs, read off disk the way
 * `frame.test.ts` reads `monza.json`. `GLTFLoader.parse` needs no DOM for a GLB
 * with embedded buffers and no textures, which this one is.
 */
function loadRaceCarRed(): Promise<Object3D> {
  const url = new URL('../../public/models/raceCarRed.glb', import.meta.url)
  const buf = readFileSync(fileURLToPath(url))
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
  // `parse` calls back on a microtask, not inline, so this has to be awaited.
  return new Promise((resolve, reject) => {
    new GLTFLoader().parse(ab as ArrayBuffer, '', (gltf) => resolve(gltf.scene), reject)
  })
}

describe('carModelMatrix', () => {
  it('does not mirror the car', () => {
    // A negative determinant is the failure `carBasis` guards against one level
    // up, and it would show here as a car whose single-sided faces are inside
    // out. Uniform scale k, so the determinant is exactly k cubed.
    const raw = new Box3(new Vector3(-1, -1, -2), new Vector3(1, 1, 2))
    const m = carModelMatrix(raw, { ...RACE_CAR_RED, fit: { axis: 'length', metres: 8 } })
    expect(m.determinant()).toBeCloseTo(2 ** 3, 9)
    expect(m.determinant()).toBeGreaterThan(0)
  })

  it('turns the model nose onto -Z and keeps up on +Y', () => {
    const raw = new Box3(new Vector3(-1, -1, -2), new Vector3(1, 1, 2))
    const m = carModelMatrix(raw, RACE_CAR_RED)
    const nose = RACE_CAR_RED.forward.clone().transformDirection(m)
    const up = RACE_CAR_RED.up.clone().transformDirection(m)
    expect(nose.distanceTo(new Vector3(0, 0, -1))).toBeLessThan(EPS)
    expect(up.distanceTo(new Vector3(0, 1, 0))).toBeLessThan(EPS)
  })

  it('centres the plan view on the origin and puts the lowest point on y = 0', () => {
    // Deliberately off-origin and lopsided, like the real file.
    const raw = new Box3(new Vector3(-3, 2, -10), new Vector3(-1, 3, -4))
    const box = raw.clone().applyMatrix4(carModelMatrix(raw, RACE_CAR_RED))
    expect(box.getCenter(new Vector3()).x).toBeCloseTo(0, 9)
    expect(box.getCenter(new Vector3()).z).toBeCloseTo(0, 9)
    expect(box.min.y).toBeCloseTo(0, 9)
    expect(box.getSize(new Vector3()).x).toBeCloseTo(RACE_CAR_RED.fit.metres, 9)
  })

  it('normalises a model whose long axis is x just as well', () => {
    // The property that makes this reusable: the next model's axis convention
    // is a spec change, not a code change.
    const spec: CarModelSpec = {
      ...RACE_CAR_RED,
      forward: new Vector3(1, 0, 0),
      fit: { axis: 'length', metres: 5 },
    }
    const raw = new Box3(new Vector3(10, 5, -3), new Vector3(12, 6, 1))
    const box = raw.clone().applyMatrix4(carModelMatrix(raw, spec))
    const size = box.getSize(new Vector3())
    expect(size.z).toBeCloseTo(5, 9) // the 2 m x extent, scaled by 2.5
    expect(size.x).toBeCloseTo(10, 9) // the 4 m z extent becomes the width
    expect(size.y).toBeCloseTo(2.5, 9)
    expect(box.min.y).toBeCloseTo(0, 9)
    expect(box.getCenter(new Vector3()).x).toBeCloseTo(0, 9)
  })

  it('anchors on whichever dimension the spec names', () => {
    // Same box, same axes, one field different: the anchor is a spec decision
    // and must not need the correction path to be edited.
    const raw = new Box3(new Vector3(10, 5, -3), new Vector3(12, 6, 1))
    const base = { ...RACE_CAR_RED, forward: new Vector3(1, 0, 0) }
    const byLength = raw
      .clone()
      .applyMatrix4(carModelMatrix(raw, { ...base, fit: { axis: 'length', metres: 5 } }))
      .getSize(new Vector3())
    const byWidth = raw
      .clone()
      .applyMatrix4(carModelMatrix(raw, { ...base, fit: { axis: 'width', metres: 2 } }))
      .getSize(new Vector3())
    expect(byLength.z).toBeCloseTo(5, 9)
    expect(byWidth.x).toBeCloseTo(2, 9)
    // Uniform scale either way, so the aspect ratio is untouched.
    expect(byLength.x / byLength.z).toBeCloseTo(byWidth.x / byWidth.z, 9)
  })
})

describe('raceCarRed.glb', () => {
  it('still measures what the spec was written against', async () => {
    /*
     * A guard, not a derivation: nothing in `model.ts` reads these numbers.
     * They are here so that replacing the file fails loudly rather than
     * silently producing a wrong-sized car.
     */
    const raw = new Box3().setFromObject(await loadRaceCarRed())
    const size = raw.getSize(new Vector3())
    expect(size.x).toBeCloseTo(0.728833, 6)
    expect(size.y).toBeCloseTo(0.397014, 6)
    expect(size.z).toBeCloseTo(1.345937, 6)
    expect(raw.min.y).toBeCloseTo(-0.03352, 6)
    // Off its own origin by a long way, which is why the adapter recentres.
    expect(raw.getCenter(new Vector3()).x).toBeCloseTo(-0.35, 6)
  })

  it('comes out 2 m wide, centred, and sitting on y = 0', async () => {
    const box = new Box3().setFromObject(adaptCarModel(await loadRaceCarRed()))
    const size = box.getSize(new Vector3())
    // The anchor: a real F1 car's maximum width, so lateral spacing in metres
    // can be judged against it.
    expect(size.x).toBeCloseTo(2, 9)
    // What falls out of it. Short, because the placeholder is stubby — which
    // is the honest direction for the error to run.
    expect(size.z).toBeCloseTo(3.6934, 3)
    expect(size.y).toBeCloseTo(1.0895, 3)
    // The datum, to float precision. It is not offset by a ride height: that
    // clearance belongs to `Car.tsx`, so nothing here has to subtract it out.
    expect(Math.abs(box.min.y)).toBeLessThan(EPS)
    expect(Math.abs(box.getCenter(new Vector3()).x)).toBeLessThan(EPS)
    expect(Math.abs(box.getCenter(new Vector3()).z)).toBeLessThan(EPS)
  })

  it('fits the live model to the physics chassis bounds', async () => {
    const spec: CarModelSpec = { ...RACE_CAR_RED, dimensions: { lengthM: 5, widthM: 1.8, heightM: 0.7 } }
    const box = new Box3().setFromObject(adaptCarModel(await loadRaceCarRed(), spec))
    const size = box.getSize(new Vector3())
    expect(size.z).toBeCloseTo(5, 7)
    expect(size.x).toBeCloseTo(1.8, 7)
    expect(size.y).toBeCloseTo(0.7, 7)
    expect(box.getCenter(new Vector3()).x).toBeCloseTo(0, 7)
    expect(box.getCenter(new Vector3()).z).toBeCloseTo(0, 7)
    expect(box.min.y).toBeCloseTo(0, 7)
    const rendered = carGeometry(await loadRaceCarRed(), spec)
    const visibleBounds = new Box3()
    for (const part of rendered.body) {
      part.geometry.computeBoundingBox()
      if (part.geometry.boundingBox) visibleBounds.union(part.geometry.boundingBox)
    }
    for (const wheel of rendered.wheels) for (const part of wheel.parts) {
      part.geometry.computeBoundingBox()
      if (part.geometry.boundingBox) visibleBounds.union(part.geometry.boundingBox.clone().translate(wheel.centre))
    }
    const visibleSize = visibleBounds.getSize(new Vector3())
    expect(visibleSize.x).toBeCloseTo(1.8, 5)
    expect(visibleSize.z).toBeCloseTo(5, 5)
    expect(visibleSize.y).toBeCloseTo(0.7, 5)
    const wheels = rendered.wheels
    expect(wheels).toHaveLength(4)
    for (const wheel of wheels) {
      expect(Math.abs(wheel.axle.x)).toBe(1)
      const lowestAt = (angle: number) => {
        const transform = wheelMatrix(new Matrix4(), wheel, angle, new Matrix4())
        const point = new Vector3()
        let lowest = Infinity
        for (const part of wheel.parts) {
          const positions = part.geometry.getAttribute('position')
          for (let i = 0; i < positions.count; i++) {
            point.fromBufferAttribute(positions, i).applyMatrix4(transform)
            lowest = Math.min(lowest, point.y)
          }
        }
        return lowest
      }
      // Resizing the body must not turn the rotating tyre into an ellipse.
      expect(lowestAt(Math.PI / 2)).toBeCloseTo(lowestAt(0), 5)
      expect(lowestAt(Math.PI)).toBeCloseTo(lowestAt(0), 5)
    }
  })

  it('drives nose first, with its front-left wheel on its own left', async () => {
    /*
     * The orientation assertion stated in the kit's own node names rather than
     * in coordinates. Car-local is -Z forward and +X right, so the front wheels
     * must end up at lower z than the rear ones, and the left one at negative x.
     * A mirrored or back-to-front model fails one of these two.
     */
    const model = adaptCarModel(await loadRaceCarRed())
    const at = (name: string) => {
      const node = model.getObjectByName(name)
      if (!node) throw new Error(`${name} missing from the model`)
      return node.getWorldPosition(new Vector3())
    }
    expect(at('wheelFrontLeft').z).toBeLessThan(at('wheelBackLeft').z)
    expect(at('wheelFrontLeft').x).toBeLessThan(0)
    expect(at('wheelFrontRight').x).toBeGreaterThan(0)
  })
})
