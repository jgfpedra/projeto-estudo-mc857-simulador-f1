/**
 * Modelo do carro: correção de eixos/escala e geometria para instâncias.
 *
 * Portado de `viz3d/src/cars/model.ts` (`carModelMatrix`, `adaptCarModel`,
 * `carGeometry`) e de `viz3d/src/cars/instance.ts` (`poseMatrix`,
 * `wheelMatrix`, `wheelAngle`). Removidos: o posicionamento por `(s, d)` e o
 * `useGLTF.preload` (o carregamento fica no chunk preguiçoso do 3D).
 *
 * Modelo: Kenney Racing Kit `raceCarRed` (CC0, ver `viz3d/ASSETS.md`).
 * Espaço local do carro: -Z para frente, +X à direita, +Y para cima, centro no
 * plano na origem e pneus em y = 0.
 */
import { Box3, Matrix4, Quaternion, Vector3 } from "three"
import type { BufferGeometry, Material, Mesh, Object3D } from "three"

function fail(msg: string): never {
  throw new Error(`car model: ${msg}`)
}

export interface CarModelSpec {
  url: string
  /** Para onde o bico aponta no espaço do próprio modelo. */
  forward: Vector3
  up: Vector3
  /** Escala uniforme quando não há dimensões do chassi. */
  fit: { axis: "width" | "length"; metres: number }
  /** Caixa de colisão do backend; o modelo estilizado é ajustado a ela. */
  dimensions?: { widthM: number; lengthM: number; heightM: number }
  /** Material da pintura, o único que recebe cor por carro. */
  paintMaterial: string
  /** Prefixo dos nós das rodas, que giram e por isso não podem ser fundidos ao corpo. */
  wheelPrefix: string
}

/** Kenney `raceCarRed`: aponta para +Z, ancorado em 2,0 m de largura sem dimensões do chassi. */
export function raceCarSpec(url: string, dimensions?: CarModelSpec["dimensions"]): CarModelSpec {
  return {
    url,
    forward: new Vector3(0, 0, 1),
    up: new Vector3(0, 1, 0),
    fit: { axis: "width", metres: 2.0 },
    dimensions,
    paintMaterial: "red",
    wheelPrefix: "wheel",
  }
}

/** Matriz do espaço do modelo para o espaço local do carro (rotação, escala, datum). */
export function carModelMatrix(raw: Box3, spec: CarModelSpec): Matrix4 {
  const forward = spec.forward.clone().normalize()
  const up = spec.up.clone().normalize()
  const right = new Vector3().crossVectors(forward, up)
  if (right.lengthSq() < 1e-12) fail(`${spec.url}: forward and up are parallel`)
  right.normalize()

  // makeBasis(right, up, -forward) leva eixos do carro para eixos do modelo; a inversa é a transposta.
  const rot = new Matrix4().makeBasis(right, up, forward.clone().negate()).transpose()

  const rotated = raw.clone().applyMatrix4(rot)
  const size = rotated.getSize(new Vector3())
  const measured = spec.fit.axis === "width" ? size.x : size.z
  if (!(measured > 0)) fail(`${spec.url}: zero ${spec.fit.axis}`)
  const k = spec.fit.metres / measured

  // Com as dimensões do chassi, o modelo é esticado até a mesma caixa externa.
  const sx = spec.dimensions ? spec.dimensions.widthM / size.x : k
  const sy = spec.dimensions ? spec.dimensions.heightM / size.y : k
  const sz = spec.dimensions ? spec.dimensions.lengthM / size.z : k
  if (![sx, sy, sz].every((scale) => Number.isFinite(scale) && scale > 0)) fail(`${spec.url}: invalid dimensions`)
  const pre = new Matrix4().makeScale(sx, sy, sz).multiply(rot)

  const box = raw.clone().applyMatrix4(pre)
  return new Matrix4()
    .makeTranslation(-(box.min.x + box.max.x) / 2, -box.min.y, -(box.min.z + box.max.z) / 2)
    .multiply(pre)
}

/** Cópia corrigida da cena: o `useGLTF` guarda em cache e compartilha o original. */
export function adaptCarModel(scene: Object3D, spec: CarModelSpec): Object3D {
  const model = scene.clone(true)
  const raw = new Box3().setFromObject(model)
  if (raw.isEmpty()) fail(`${spec.url}: no geometry to measure`)
  model.applyMatrix4(carModelMatrix(raw, spec))
  model.updateMatrixWorld(true)
  return model
}

export interface CarPart {
  name: string
  geometry: BufferGeometry
  material: Material
  paint: boolean
}

export interface CarWheel {
  name: string
  centre: Vector3
  radiusM: number
  axle: Vector3
  parts: CarPart[]
}

export interface CarGeometry {
  body: CarPart[]
  wheels: CarWheel[]
}

/**
 * Achata o modelo corrigido em geometrias para `InstancedMesh`. O corpo é
 * fundido no espaço do carro; cada roda fica relativa ao próprio centro para
 * poder girar. Geometrias e materiais são clonados (o cache do glTF é
 * compartilhado), então quem chama deve descartá-los.
 */
export function carGeometry(scene: Object3D, spec: CarModelSpec): CarGeometry {
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
    // A cor por instância multiplica a do material: a pintura fica branca para a cor sair exata.
    if (paint && "color" in material) (material as unknown as { color: { set(v: string): void } }).color.set("#ffffff")
    return { name: mesh.name, geometry: mesh.geometry.clone().applyMatrix4(m), material, paint }
  }

  const body: CarPart[] = []
  const wheels = new Map<string, CarWheel>()
  const wheelCorrections = new Map<string, Matrix4>()
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
      // O eixo da roda é a dimensão mais fina; as outras duas são diâmetros.
      const dims: [number, Vector3][] = [
        [size.x, new Vector3(1, 0, 0)],
        [size.y, new Vector3(0, 1, 0)],
        [size.z, new Vector3(0, 0, 1)],
      ]
      dims.sort((a, b) => a[0] - b[0])
      // O chassi ao vivo é esticado em cada eixo; desfaz a elipse no plano de giro
      // para o pneu continuar circular e não "quicar" ao girar.
      let radius = (dims[1][0] + dims[2][0]) / 4
      if (spec.dimensions) {
        const diameter = Math.min(dims[1][0], dims[2][0])
        radius = diameter / 2
        const scale = new Vector3(1, 1, 1)
        for (const [s, axis] of dims.slice(1)) {
          if (axis.x) scale.x = diameter / s
          if (axis.y) scale.y = diameter / s
          if (axis.z) scale.z = diameter / s
        }
        wheelCorrections.set(node.name, new Matrix4().makeScale(scale.x, scale.y, scale.z))
      }
      wheel = { name: node.name, centre: box.getCenter(new Vector3()), radiusM: radius, axle: dims[0][1], parts: [] }
      wheels.set(node.name, wheel)
    }
    scratch.makeTranslation(-wheel.centre.x, -wheel.centre.y, -wheel.centre.z).multiply(mesh.matrixWorld)
    const correction = wheelCorrections.get(node.name)
    if (correction) scratch.premultiply(correction)
    wheel.parts.push(part(mesh, scratch))
  })

  return { body, wheels: [...wheels.values()] }
}

const pos = new Vector3()
const quat = new Quaternion()
const ONE = new Vector3(1, 1, 1)
const spin = new Quaternion()
const wheelPos = new Vector3()
const Y_AXIS = new Vector3(0, 1, 0)

/** Matriz de um carro pela pose: giro em +y e translação, escala unitária (determinante +1). */
export function poseMatrix(x: number, z: number, yawRad: number, h: number, out: Matrix4): Matrix4 {
  pos.set(x, h, z)
  quat.setFromAxisAngle(Y_AXIS, yawRad)
  return out.compose(pos, quat, ONE)
}

/** Matriz de uma roda: a do carro, até o centro da roda, e o giro no próprio eixo. */
export function wheelMatrix(car: Matrix4, wheel: CarWheel, angleRad: number, out: Matrix4): Matrix4 {
  spin.setFromAxisAngle(wheel.axle, angleRad)
  wheelPos.copy(wheel.centre)
  out.compose(wheelPos, spin, ONE)
  return out.premultiply(car)
}

/** Faixa do composto: raio do anel e do tubo, em frações do raio da roda. */
export const TYRE_BAND = { ring: 0.86, tube: 0.14 }

const Z_AXIS = new Vector3(0, 0, 1)

/**
 * Matriz, no espaço da roda (centro na origem, como as partes dela), que leva
 * um toro de raio 1 no plano XY (eixo +Z) ao flanco externo do pneu: eixo do
 * toro no eixo da roda, apontando para fora do carro, encostado na face
 * externa (centro do tubo na face: metade para fora). Anel até o raio da
 * roda (0,86 + 0,14), no ombro do pneu: de trás e de cima ele aparece como
 * uma faixa na borda externa do pneu. O anel é simétrico no giro, então
 * ele acompanha a roda pela mesma `wheelMatrix`.
 */
export function tyreBandLocal(wheel: CarWheel, out: Matrix4): Matrix4 {
  const box = new Box3()
  for (const p of wheel.parts) {
    p.geometry.computeBoundingBox()
    if (p.geometry.boundingBox) box.union(p.geometry.boundingBox)
  }
  // Fora do carro: o lado do eixo em que a roda está (o carro é centrado em x = 0).
  const side = Math.sign(wheel.centre.dot(wheel.axle)) || 1
  const outward = wheel.axle.clone().multiplyScalar(side)
  const face = box.isEmpty() ? 0 : side > 0 ? box.max.dot(wheel.axle) : -box.min.dot(wheel.axle)
  const scale = wheel.radiusM * TYRE_BAND.ring
  const position = outward.clone().multiplyScalar(face)
  return out.compose(position, new Quaternion().setFromUnitVectors(Z_AXIS, outward), new Vector3(scale, scale, scale))
}

/** Ângulo da roda após percorrer `distanceM`, rolando sem deslizar. Negativo porque a frente é -Z. */
export function wheelAngle(distanceM: number, radiusM: number): number {
  return -distanceM / radiusM
}
