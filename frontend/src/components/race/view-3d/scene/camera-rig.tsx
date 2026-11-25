import { useLayoutEffect, useRef } from "react"
import type { ComponentRef } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { OrbitControls } from "@react-three/drei"
import { PerspectiveCamera } from "three"
import type { Camera } from "three"

import { CHASE, ONBOARD, chasePose, newPose, newRigState, onboardPose, stepRig } from "./camera-math"
import type { CameraMode, FollowState } from "./camera-math"
import type { Overview } from "./race-track"
import type { TrackFrame } from "./track-frame"

const ORBIT_FOV_DEG = 45
/** near nas câmeras que seguem um carro; na visão geral cresce com a distância (precisão de profundidade). */
const FOLLOW_NEAR_M = 0.3

function setLens(camera: Camera, fovDeg: number, near: number, far: number): void {
  if (!(camera instanceof PerspectiveCamera)) return
  camera.fov = fovDeg
  camera.near = near
  camera.far = far
  camera.updateProjectionMatrix()
}

type Props = {
  frame: TrackFrame
  mode: CameraMode
  /** Escrito a cada quadro por `Cars`, lido aqui; nunca renderizado. */
  followRef: { current: FollowState }
  overview: Overview
}

/**
 * Dono da câmera. Portado de `viz3d/src/cameras/CameraRig.tsx`: órbita para a
 * visão geral, perseguição e T-cam para seguir um carro.
 *
 * Montado depois de `Cars`, dentro do mesmo `Suspense`, para que o `useFrame`
 * daqui rode em seguida e leia a pose deste quadro. Tudo com prioridade 0.
 *
 * Diferença do viz3d: entrar na órbita sempre volta à visão geral ajustada à
 * pista (não ao último ponto de vista salvo), porque `selectedDriverId = null`
 * significa "visão geral" na página.
 */
export function CameraRig({ frame, mode, followRef, overview }: Props) {
  const camera = useThree((s) => s.camera)
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null)
  const rig = useRef(newRigState())
  const pose = useRef(newPose())

  useLayoutEffect(() => {
    const far = overview.distance * 6
    if (mode === "orbit") {
      setLens(camera, ORBIT_FOV_DEG, Math.max(1, overview.distance / 200), far)
      camera.position.copy(overview.position)
      camera.up.set(0, 1, 0)
      const c = controls.current
      if (c) {
        c.target.copy(overview.target)
        c.update()
      } else {
        camera.lookAt(overview.target)
      }
    } else {
      setLens(camera, mode === "chase" ? CHASE.fovDeg : ONBOARD.fovDeg, FOLLOW_NEAR_M, far)
      // Ao entrar num modo de seguir, corta para o carro em vez de amortecer de onde estava.
      rig.current.carIndex = -1
    }
  }, [mode, overview, camera])

  useFrame((_, delta) => {
    if (mode === "orbit") return
    const f = followRef.current
    stepRig(rig.current, frame, f, delta)
    // Sem semente (carro sem pose ainda): deixa a câmera onde está.
    if (rig.current.carIndex < 0) return
    const p =
      mode === "chase"
        ? chasePose(frame, rig.current, f, CHASE, pose.current)
        : onboardPose(frame, rig.current, f, ONBOARD, pose.current)
    camera.position.copy(p.position)
    camera.up.copy(p.up)
    camera.lookAt(p.target)
  })

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      // Desligado ao seguir: os eventos retornam cedo e o drei não chama update(),
      // então o rig controla a câmera sem disputa.
      enabled={mode === "orbit"}
      target={overview.target.toArray()}
      maxDistance={overview.distance * 2}
      minDistance={Math.max(5, overview.distance / 100)}
      maxPolarAngle={Math.PI / 2 - 0.05}
    />
  )
}
