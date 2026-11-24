import { useEffect, useMemo, useRef } from "react"
import { useFrame } from "@react-three/fiber"
import type { ThreeEvent } from "@react-three/fiber"
import { useGLTF } from "@react-three/drei"
import { Color, ConeGeometry, DynamicDrawUsage, InstancedMesh, Matrix4, MeshBasicMaterial, Vector3 } from "three"

import { useLiveRaceStore } from "@/stores/live-race-store"
import type { CarGeometry as ChassisBox, RaceDriver } from "@/types/race"
import { carGeometry, poseMatrix, raceCarSpec, wheelAngle, wheelMatrix } from "./car-model"
import type { CarPart } from "./car-model"
import type { FollowState } from "./camera-math"
import { LapUnwrapper, WheelOdometer, engineYaw, frameAlpha, interpolatePoses, toThreeX, toThreeZ } from "./live-pose"
import type { CarPose } from "./live-pose"
import { nearestS, wrapS } from "./track-frame"
import type { TrackFrame } from "./track-frame"
import type { ProbeSink } from "./dev-probe"

/** Folga entre os pneus e a pista, metros (mesma do viz3d). */
const RIDE_HEIGHT_M = 0.01
/** Marcador acima de cada carro na visão geral: escala por metro de distância da câmera. */
const PIN_SCALE_PER_M = 0.012
const PIN_HEIGHT = 2.4

export const MODEL_URL = `${import.meta.env.BASE_URL}models/raceCarRed.glb`

type Props = {
  drivers: RaceDriver[]
  colors: Map<string, string>
  frame: TrackFrame
  carBox: ChassisBox | null
  /** Índice em `drivers` do carro seguido; -1 na visão geral. */
  selectedIndex: number
  showPins: boolean
  followRef: { current: FollowState }
  onPick: (driverId: string) => void
  probe: ProbeSink | null
}

function instanced(part: CarPart, count: number): InstancedMesh {
  const mesh = new InstancedMesh(part.geometry, part.material, count)
  mesh.instanceMatrix.setUsage(DynamicDrawUsage)
  // Sombra no chão do cenário (a luz só projeta sombra na qualidade alta).
  mesh.castShadow = true
  mesh.receiveShadow = true
  // As instâncias se espalham pela volta inteira: um volume único só pode estar errado.
  mesh.frustumCulled = false
  return mesh
}

/**
 * Envia as matrizes do quadro para a GPU. Para malhas clicáveis, recalcula a
 * esfera envolvente: o raycast do `InstancedMesh` a guarda e os carros andam.
 */
function publish(meshes: InstancedMesh[], pickable: boolean): void {
  for (const m of meshes) {
    m.instanceMatrix.needsUpdate = true
    if (pickable) m.computeBoundingSphere()
  }
}

function pinGeometry(): ConeGeometry {
  // Ponta para baixo, na origem; a base fica PIN_HEIGHT acima.
  const g = new ConeGeometry(0.9, PIN_HEIGHT, 16)
  g.rotateX(Math.PI)
  g.translate(0, PIN_HEIGHT / 2, 0)
  return g
}

/**
 * Os carros na pista. Portado de `viz3d/src/cars/Grid.tsx`: um `InstancedMesh`
 * por primitiva do modelo, rodas giradas pelo hodômetro. A diferença é a
 * fonte: em vez do `LiveBuffer` do viz3d, a pose vem da store do frontend,
 * lida com `getState()` dentro do `useFrame` (sem re-render por tick), e é
 * interpolada exatamente como em `track-2d.tsx`.
 */
export function Cars({ drivers, colors, frame, carBox, selectedIndex, showPins, followRef, onPick, probe }: Props) {
  const spec = useMemo(
    () =>
      raceCarSpec(
        MODEL_URL,
        carBox ? { lengthM: carBox.lengthM, widthM: carBox.widthM, heightM: carBox.heightM } : undefined,
      ),
    [carBox],
  )
  const { scene } = useGLTF(spec.url)
  const parts = useMemo(() => carGeometry(scene, spec), [scene, spec])
  const count = drivers.length

  const meshes = useMemo(() => {
    const body = parts.body.map((p) => instanced(p, count))
    const wheels = parts.wheels.map((w) => ({ wheel: w, meshes: w.parts.map((p) => instanced(p, count)) }))
    const pins = new InstancedMesh(pinGeometry(), new MeshBasicMaterial({ color: "#ffffff", toneMapped: false, fog: false }), count)
    pins.instanceMatrix.setUsage(DynamicDrawUsage)
    pins.frustumCulled = false
    pins.name = "car-pins"

    const colour = new Color()
    drivers.forEach((d, k) => {
      colour.set(colors.get(d.driverId) ?? "#ffffff")
      pins.setColorAt(k, colour)
      body.forEach((mesh, i) => {
        if (parts.body[i].paint) mesh.setColorAt(k, colour)
      })
    })
    for (const m of [...body, pins]) if (m.instanceColor) m.instanceColor.needsUpdate = true
    return { body, wheels, pins }
  }, [parts, drivers, colors, count])

  useEffect(
    () => () => {
      for (const m of meshes.body) m.dispose()
      for (const w of meshes.wheels) for (const m of w.meshes) m.dispose()
      meshes.pins.dispose()
      meshes.pins.geometry.dispose()
      ;(meshes.pins.material as MeshBasicMaterial).dispose()
    },
    [meshes],
  )
  useEffect(
    () => () => {
      for (const p of parts.body) {
        p.geometry.dispose()
        p.material.dispose()
      }
      for (const w of parts.wheels)
        for (const p of w.parts) {
          p.geometry.dispose()
          p.material.dispose()
        }
    },
    [parts],
  )

  const scratchRef = useRef({
      car: new Matrix4(),
      wheel: new Matrix4(),
      pin: new Matrix4(),
      hidden: new Matrix4().makeScale(0, 0, 0),
      world: new Vector3(),
      lastHeading: new Map<string, number>(),
      odometer: new WheelOdometer(),
      unwrap: new LapUnwrapper(),
      lastFrame: null as unknown,
      lastSelected: -2,
  })
  // Altura do teto do carro, para o marcador, medida na própria geometria.
  const carTopM = useMemo(() => {
    let top = 0
    for (const p of parts.body) {
      p.geometry.computeBoundingBox()
      top = Math.max(top, p.geometry.boundingBox?.max.y ?? 0)
    }
    return top + RIDE_HEIGHT_M
  }, [parts])

  const ids = useMemo(() => drivers.map((d) => d.driverId), [drivers])

  useFrame((state) => {
    const s = useLiveRaceStore.getState()
    const now = performance.now()
    const scratch = scratchRef.current
    const f = followRef.current

    if (!s.frame) {
      for (let i = 0; i < count; i++) {
        for (const m of meshes.body) m.setMatrixAt(i, scratch.hidden)
        for (const w of meshes.wheels) for (const m of w.meshes) m.setMatrixAt(i, scratch.hidden)
        meshes.pins.setMatrixAt(i, scratch.hidden)
      }
      f.carIndex = -1
    } else {
      const alpha = frameAlpha(now, s.frameAt, s.tickIntervalMs)
      const poses = interpolatePoses(s.prevFrame, s.frame, alpha, scratch.lastHeading)
      scratch.odometer.update(s.prevFrame, s.frame)
      // Ressincronização: o carro seguido pode ter saltado; a câmera corta.
      const jumped = s.frame !== scratch.lastFrame && s.prevFrame === null && scratch.lastFrame !== null
      scratch.lastFrame = s.frame
      if (jumped || selectedIndex !== scratch.lastSelected) {
        scratch.unwrap.reset()
        f.cut++
        scratch.lastSelected = selectedIndex
      }
      const cam = state.camera.position

      for (let i = 0; i < count; i++) {
        const pose: CarPose | undefined = poses.get(ids[i])
        if (!pose) {
          for (const m of meshes.body) m.setMatrixAt(i, scratch.hidden)
          for (const w of meshes.wheels) for (const m of w.meshes) m.setMatrixAt(i, scratch.hidden)
          meshes.pins.setMatrixAt(i, scratch.hidden)
          if (i === selectedIndex) f.carIndex = -1
          continue
        }
        const x = toThreeX(pose.x)
        const z = toThreeZ(pose.y)
        const yaw = engineYaw(pose.headingRad)
        poseMatrix(x, z, yaw, RIDE_HEIGHT_M, scratch.car)
        for (const m of meshes.body) m.setMatrixAt(i, scratch.car)

        const travelled = scratch.odometer.sample(ids[i], alpha)
        for (const w of meshes.wheels) {
          wheelMatrix(scratch.car, w.wheel, wheelAngle(travelled, w.wheel.radiusM), scratch.wheel)
          for (const m of w.meshes) m.setMatrixAt(i, scratch.wheel)
        }

        if (showPins) {
          scratch.world.set(x, carTopM, z)
          const k = Math.min(80, Math.max(1, cam.distanceTo(scratch.world) * PIN_SCALE_PER_M))
          scratch.pin.makeScale(k, k, k).setPosition(x, carTopM + 0.6 * k, z)
          meshes.pins.setMatrixAt(i, scratch.pin)
        } else {
          meshes.pins.setMatrixAt(i, scratch.hidden)
        }

        if (i === selectedIndex) {
          // progress_m para a câmera; sem ele, s_m desembrulhado; sem ambos, projeção na pista.
          const sWrapped = pose.sM ?? nearestS(frame, x, z)
          f.sUnwrapped = pose.progressM ?? scratch.unwrap.next(wrapS(frame, sWrapped), frame.lengthM)
          f.d = 0
          f.speedMps = pose.speedMps
          f.carIndex = i
          f.posed = true
          f.x = x
          f.z = z
          f.yawRad = yaw
        }
      }
      if (selectedIndex < 0) f.carIndex = -1
    }

    publish(meshes.body, true)
    for (const w of meshes.wheels) publish(w.meshes, false)
    publish([meshes.pins], true)

    probe?.record(now, s, meshes.body[0] ?? null, meshes.pins, ids)
  })

  const pick = (e: ThreeEvent<MouseEvent>) => {
    if (e.instanceId === undefined) return
    const id = ids[e.instanceId]
    if (!id) return
    e.stopPropagation()
    onPick(id)
  }
  const over = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation()
    document.body.style.cursor = "pointer"
  }
  const out = () => {
    document.body.style.cursor = ""
  }
  useEffect(() => out, [])

  return (
    <>
      {meshes.body.map((m, i) => (
        <primitive key={`body${i}`} object={m} onClick={pick} onPointerOver={over} onPointerOut={out} />
      ))}
      {meshes.wheels.map((w, i) => w.meshes.map((m, k) => <primitive key={`wheel${i}-${k}`} object={m} />))}
      <primitive object={meshes.pins} visible={showPins} onClick={pick} onPointerOver={over} onPointerOut={out} />
    </>
  )
}
