/**
 * Cena 3D da corrida ao vivo. Carregada sob demanda por `race-view-3d.tsx`
 * (`React.lazy`), então three, R3F e drei ficam fora do bundle do 2D.
 *
 * Portada da página ao vivo do viz3d (`viz3d/src/live/LiveRace.tsx`), sem a
 * conexão própria: a corrida, os ticks e a seleção vêm do frontend.
 */
import { Suspense, memo, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { Canvas, useThree } from "@react-three/fiber"
import { Sphere } from "three"

import type { RaceInfo } from "@/types/race"
import { CameraRig } from "./scene/camera-rig"
import { newFollowState } from "./scene/camera-math"
import type { CameraMode, FollowState } from "./scene/camera-math"
import { carColors } from "./scene/car-colors"
import { Cars } from "./scene/cars"
import { createProbe } from "./scene/dev-probe"
import { overviewPose, pitLaneFromRace, trackFromRace } from "./scene/race-track"
import { buildFrame } from "./scene/track-frame"
import type { TrackFrame } from "./scene/track-frame"
import { PitLaneRibbon, StartFinishLine, TrackRibbon } from "./scene/track-meshes"

type FollowMode = Exclude<CameraMode, "orbit">

export type RaceSceneProps = {
  race: RaceInfo
  selectedDriverId: string | null
  onSelectDriver: (driverId: string | null) => void
}

const FOLLOW_LABEL: Record<FollowMode, string> = { chase: "Perseguição", onboard: "A bordo" }
/** Arrastar mais que isto (px) com um carro seguido volta à visão geral. */
const DRAG_EXIT_PX = 6

/**
 * Sair do seguimento pelo canvas: arrastar, rolar ou Esc chamam
 * `onSelectDriver(null)`, como o botão "Visão geral" da página.
 */
function FollowExit({ following, onExit }: { following: boolean; onExit: () => void }) {
  const gl = useThree((s) => s.gl)
  const latest = useRef({ following, onExit })
  useLayoutEffect(() => {
    latest.current = { following, onExit }
  })

  useEffect(() => {
    const el = gl.domElement
    let start: { x: number; y: number } | null = null
    const exit = () => {
      if (latest.current.following) latest.current.onExit()
    }
    const down = (e: PointerEvent) => {
      start = { x: e.clientX, y: e.clientY }
    }
    const move = (e: PointerEvent) => {
      if (!start || e.buttons === 0) return
      if (Math.hypot(e.clientX - start.x, e.clientY - start.y) > DRAG_EXIT_PX) {
        start = null
        exit()
      }
    }
    const up = () => {
      start = null
    }
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") exit()
    }
    el.addEventListener("pointerdown", down)
    el.addEventListener("pointermove", move)
    el.addEventListener("pointerup", up)
    el.addEventListener("wheel", exit, { passive: true })
    window.addEventListener("keydown", key)
    return () => {
      el.removeEventListener("pointerdown", down)
      el.removeEventListener("pointermove", move)
      el.removeEventListener("pointerup", up)
      el.removeEventListener("wheel", exit)
      window.removeEventListener("keydown", key)
    }
  }, [gl])

  return null
}

type ContentProps = {
  race: RaceInfo
  frame: TrackFrame
  center: Sphere
  drivers: RaceInfo["drivers"]
  colors: Map<string, string>
  mode: CameraMode
  selectedDriverId: string | null
  onSelectDriver: (driverId: string | null) => void
}

/** Carros, câmera e gancho de desenvolvimento: precisam do estado do Canvas. */
function Content({ race, frame, center, drivers, colors, mode, selectedDriverId, onSelectDriver }: ContentProps) {
  const size = useThree((s) => s.size)
  const getThree = useThree((s) => s.get)
  const followRef = useRef<FollowState>(newFollowState())
  const overview = useMemo(
    () => overviewPose(center.center, center.radius, 45, size.width / Math.max(1, size.height)),
    [center, size.width, size.height],
  )

  const probe = useMemo(
    () =>
      import.meta.env.DEV
        ? createProbe({ three: getThree, mode, followed: selectedDriverId, colors })
        : null,
    [getThree, mode, selectedDriverId, colors],
  )
  useEffect(() => probe?.install(), [probe])

  const selectedIndex = selectedDriverId ? drivers.findIndex((d) => d.driverId === selectedDriverId) : -1

  return (
    <>
      <Cars
        drivers={drivers}
        colors={colors}
        frame={frame}
        carBox={race.carGeometry}
        selectedIndex={selectedIndex}
        showPins={mode === "orbit"}
        followRef={followRef}
        onPick={(id) => onSelectDriver(id)}
        probe={probe?.sink ?? null}
      />
      <CameraRig frame={frame} mode={selectedIndex >= 0 ? mode : "orbit"} followRef={followRef} overview={overview} />
    </>
  )
}

function RaceScene({ race, selectedDriverId, onSelectDriver }: RaceSceneProps) {
  const [followMode, setFollowMode] = useState<FollowMode>("chase")
  const mode: CameraMode = selectedDriverId ? followMode : "orbit"

  const scene = useMemo(() => {
    const track = trackFromRace(race.track)
    if (track.points.length < 3) return null
    const frame = buildFrame(track.points)
    const pitLane = pitLaneFromRace(race.track.pitLane)
    const center = new Sphere().setFromPoints([...track.points, ...(pitLane?.points ?? [])])
    const drivers = [...race.drivers].sort((a, b) => a.gridPosition - b.gridPosition)
    return { track, frame, pitLane, center, drivers, colors: carColors(drivers) }
  }, [race])

  if (!scene) {
    return (
      <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
        Traçado indisponível: o backend não enviou os waypoints da pista.
      </div>
    )
  }

  const start = overviewPose(scene.center.center, scene.center.radius, 45, 16 / 9)

  return (
    <div className="relative h-full w-full" data-testid="race-view-3d">
      <Canvas
        key={race.raceId}
        dpr={[1, 2]}
        camera={{ fov: 45, near: 1, far: start.distance * 6, position: start.position.toArray() }}
        aria-label="Visualização 3D da corrida"
      >
        <color attach="background" args={["#111116"]} />
        <hemisphereLight args={["#ffffff", "#30303c", 1.1]} />
        <directionalLight position={[600, 1200, 400]} intensity={1.2} />
        <TrackRibbon frame={scene.frame} widthM={scene.track.widthM} />
        {scene.pitLane && <PitLaneRibbon lane={scene.pitLane} />}
        <StartFinishLine track={scene.track} />
        <Suspense fallback={null}>
          <Content
            race={race}
            frame={scene.frame}
            center={scene.center}
            drivers={scene.drivers}
            colors={scene.colors}
            mode={mode}
            selectedDriverId={selectedDriverId}
            onSelectDriver={onSelectDriver}
          />
        </Suspense>
        <FollowExit following={selectedDriverId !== null} onExit={() => onSelectDriver(null)} />
      </Canvas>

      {selectedDriverId && (
        <div className="absolute right-2 top-2 z-10 flex border border-border bg-background/80 text-[10px] font-bold uppercase tracking-wider">
          {(Object.keys(FOLLOW_LABEL) as FollowMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setFollowMode(m)}
              aria-pressed={followMode === m}
              className={`px-2.5 py-1.5 ${followMode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
            >
              {FOLLOW_LABEL[m]}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default memo(RaceScene)
