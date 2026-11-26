/**
 * Cena 3D da corrida ao vivo. Carregada sob demanda por `race-view-3d.tsx`
 * (`React.lazy`), então three, R3F e drei ficam fora do bundle do 2D.
 *
 * Portada da página ao vivo do viz3d (`viz3d/src/live/LiveRace.tsx`), sem a
 * conexão própria: a corrida, os ticks e a seleção vêm do frontend.
 */
import { Suspense, memo, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { Canvas, useThree } from "@react-three/fiber"
import { Sphere, Vector3 } from "three"

import type { RaceInfo, AiSuggestion, AiCommand } from "@/types/race"
import { CameraRig } from "./scene/camera-rig"
import { newFollowState } from "./scene/camera-math"
import type { CameraMode, FollowState } from "./scene/camera-math"
import { carColors } from "./scene/car-colors"
import { Cars } from "./scene/cars"
import { createProbe } from "./scene/dev-probe"
import { acquirePlayback } from "./scene/live-clock"
import { Environment } from "./scene/environment/environment"
import { buildLayout } from "./scene/environment/layout"
import type { Layout } from "./scene/environment/layout"
import { QUALITIES, QUALITY, QUALITY_LABEL, loadQuality, saveQuality } from "./scene/environment/quality"
import type { Quality } from "./scene/environment/quality"
import { showcaseViews } from "./scene/environment/views"
import { overviewPose, pitLaneFromRace, trackFromRace } from "./scene/race-track"
import type { ScenePitLane, SceneTrack } from "./scene/race-track"
import { buildFrame } from "./scene/track-frame"
import type { TrackFrame } from "./scene/track-frame"
import { PitLaneRibbon, StartFinishLine, TrackRibbon } from "./scene/track-meshes"
import { View3DToolbarSlot } from "./toolbar-slot"
import { AiEngineer } from "@/components/race/ai/ai-engineer"
import { useLiveRaceStore } from "@/stores/live-race-store"

type FollowMode = Exclude<CameraMode, "orbit">

export type RaceSceneProps = {
  race: RaceInfo
  selectedDriverId: string | null
  onSelectDriver: (driverId: string | null) => void
  /** Sugestões do engenheiro de IA (do live-race-store). */
  aiSuggestions?: AiSuggestion[]
  /** Comandos ativos do engenheiro de IA. */
  aiCommands?: Map<string, AiCommand>
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

type SceneData = {
  track: SceneTrack
  frame: TrackFrame
  pitLane: ScenePitLane | null
  center: Sphere
  drivers: RaceInfo["drivers"]
  colors: Map<string, string>
}

type ContentProps = {
  race: RaceInfo
  scene: SceneData
  layout: Layout | null
  quality: Quality
  followRef: { current: FollowState }
  mode: CameraMode
  selectedDriverId: string | null
  onSelectDriver: (driverId: string | null) => void
  aiSuggestions: AiSuggestion[]
  aiCommands: Map<string, AiCommand>
  aiEngineerStatus: "idle" | "started" | "monitoring" | "stopped" | "error"
}

/** Carros, câmera e gancho de desenvolvimento: precisam do estado do Canvas. */
function Content({ race, scene, layout, quality, followRef, mode, selectedDriverId, onSelectDriver, aiSuggestions, aiCommands, aiEngineerStatus }: ContentProps) {
  const { frame, center, drivers, colors } = scene
  const size = useThree((s) => s.size)
  const getThree = useThree((s) => s.get)
  const overview = useMemo(
    () => overviewPose(center.center, center.radius, 45, size.width / Math.max(1, size.height)),
    [center, size.width, size.height],
  )

  const probe = useMemo(
    () =>
      import.meta.env.DEV
        ? createProbe({
            three: getThree,
            mode,
            followed: selectedDriverId,
            colors,
            quality,
            views: layout ? showcaseViews(frame, layout, overview) : null,
          })
        : null,
    [getThree, mode, selectedDriverId, colors, quality, layout, frame, overview],
  )
  useEffect(() => probe?.install(), [probe])

  const selectedIndex = selectedDriverId ? drivers.findIndex((d) => d.driverId === selectedDriverId) : -1

  // Posição do engenheiro: acima da linha de chegada (s=0)
  const engineerPosition = useMemo(() => {
    const pos = new Vector3()
    // frame não tem toWorld exposto aqui, mas center.center é o centro do circuito
    // A linha de chegada está aproximadamente em center.center
    pos.copy(center.center)
    pos.y = 8 // altura do engenheiro
    return pos
  }, [center])

  return (
    <>
      <Cars
        drivers={drivers}
        colors={colors}
        frame={frame}
        carBox={race.carGeometry}
        selectedIndex={selectedIndex}
        showPins={mode === "orbit"}
        overviewDistance={overview.distance}
        followRef={followRef}
        onPick={(id) => onSelectDriver(id)}
        probe={probe?.sink ?? null}
      />
      <CameraRig
        frame={frame}
        mode={selectedIndex >= 0 ? mode : "orbit"}
        followRef={followRef}
        overview={overview}
        probeCamera={probe?.sink.camera ?? null}
      />
      {/* Engenheiro de IA 3D */}
      <AiEngineer
        suggestions={aiSuggestions}
        commands={aiCommands}
        followedDriverId={selectedDriverId}
        position={engineerPosition}
        engineerStatus={aiEngineerStatus}
      />
    </>
  )
}

/**
 * Tudo dentro do `<Canvas>`: o cenário (ou o visual antigo, sem cenário) e o
 * conteúdo. O `followRef` nasce aqui para que a sombra siga o mesmo alvo da câmera.
 */
function Stage(props: Omit<ContentProps, "followRef"> & { overviewDistance: number }) {
  const followRef = useRef<FollowState>(newFollowState())
  const { scene, layout, quality, overviewDistance, aiSuggestions, aiCommands, aiEngineerStatus } = props
  const env = QUALITY[quality].environment ? layout : null
  return (
    <>
      {env ? (
        <Environment
          layout={env}
          frame={scene.frame}
          widthM={scene.track.widthM}
          pitLane={scene.pitLane}
          center={scene.center.center}
          radius={scene.center.radius}
          overviewDistance={overviewDistance}
          quality={quality}
          followRef={followRef}
        />
      ) : (
        <>
          <color attach="background" args={["#111116"]} />
          <hemisphereLight args={["#ffffff", "#30303c", 1.1]} />
          <directionalLight position={[600, 1200, 400]} intensity={1.2} />
          <TrackRibbon frame={scene.frame} widthM={scene.track.widthM} />
          {scene.pitLane && <PitLaneRibbon lane={scene.pitLane} />}
        </>
      )}
      <StartFinishLine track={scene.track} />
      <Suspense fallback={null}>
        <Content {...props} followRef={followRef} aiSuggestions={aiSuggestions} aiCommands={aiCommands} aiEngineerStatus={aiEngineerStatus} />
      </Suspense>
    </>
  )
}

function RaceScene({ race, selectedDriverId, onSelectDriver }: RaceSceneProps) {
  const [followMode, setFollowMode] = useState<FollowMode>("chase")
  const mode: CameraMode = selectedDriverId ? followMode : "orbit"
  const [quality, setQuality] = useState<Quality>(loadQuality)
  const toolbarSlot = useContext(View3DToolbarSlot)
  // Buffer de frames enquanto o 3D está montado; ao sair, ele (e um congelamento do gancho) se vai.
  useEffect(() => acquirePlayback(), [])
  const chooseQuality = (q: Quality) => {
    setQuality(q)
    saveQuality(q)
  }

  // AI state from store (fallback to props for compatibility)
  const aiSuggestions = useLiveRaceStore((s) => s.aiSuggestions)
  const aiCommands = useLiveRaceStore((s) => s.aiCommands)
  const aiEngineerStatus = useLiveRaceStore((s) => s.aiEngineerStatus)

  const scene = useMemo(() => {
    const track = trackFromRace(race.track)
    if (track.points.length < 3) return null
    const frame = buildFrame(track.points)
    const pitLane = pitLaneFromRace(race.track.pitLane)
    const center = new Sphere().setFromPoints([...track.points, ...(pitLane?.points ?? [])])
    const drivers = [...race.drivers].sort((a, b) => a.gridPosition - b.gridPosition)
    return { track, frame, pitLane, center, drivers, colors: carColors(drivers) }
  }, [race])

  // Só com o cenário ligado (~0,1 s numa pista de 4 m).
  const envOn = QUALITY[quality].environment
  const layout = useMemo(
    () => (scene && envOn ? buildLayout(scene.frame, scene.track.widthM, scene.pitLane) : null),
    [scene, envOn],
  )

  if (!scene) {
    return (
      <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
        Traçado indisponível: o backend não enviou os waypoints da pista.
      </div>
    )
  }

  const start = overviewPose(scene.center.center, scene.center.radius, 45, 16 / 9)

  // Seletor de cenário: na barra de cima, ao lado da chave 2D/3D (pelo portal da página; a faixa
  // de eventos vem depois dele). Embaixo do canvas o cartão do piloto selecionado o cobria. Fica
  // fora do canvas (ver abaixo), e um <select> nativo abre a lista fora do documento.
  const qualityControl = (
    <label className="flex h-[38px] items-center border border-border bg-background/90 text-[10px] font-bold uppercase tracking-wider">
      <span className="pl-2.5 text-muted-foreground">Cenário</span>
      <select
        value={quality}
        onChange={(e) => chooseQuality(e.target.value as Quality)}
        aria-label="Qualidade do cenário 3D"
        className="h-full cursor-pointer bg-transparent pl-1.5 pr-1 text-xs font-black uppercase text-foreground outline-none"
      >
        {QUALITIES.map((q) => (
          <option key={q} value={q} className="bg-background text-foreground">
            {QUALITY_LABEL[q]}
          </option>
        ))}
      </select>
    </label>
  )

  return (
    <div className="relative flex h-full w-full flex-col" data-testid="race-view-3d">
      {toolbarSlot ? createPortal(qualityControl, toolbarSlot) : <div className="absolute -top-12 right-[-8px] z-30">{qualityControl}</div>}

      {/* O canvas fica sozinho na sua área: um elemento HTML sempre por cima dele mudava a
          composição do Chrome e, com WebGL por software, às vezes gerava um aviso
          "Blit feedback loop" ao montar/desmontar o 3D. */}
      <div className="relative min-h-0 flex-1">
        <Canvas
          key={race.raceId}
          dpr={[1, 2]}
          // Sem cenário, o renderizador fica como era antes dele (sem mapa de sombras).
          shadows={envOn ? "soft" : false}
          camera={{ fov: 45, near: 1, far: start.distance * 6, position: start.position.toArray() }}
          aria-label="Visualização 3D da corrida"
        >
          <Stage
            race={race}
            scene={scene}
            layout={layout}
            quality={quality}
            overviewDistance={start.distance}
            mode={mode}
            selectedDriverId={selectedDriverId}
            onSelectDriver={onSelectDriver}
            aiSuggestions={aiSuggestions}
            aiCommands={aiCommands}
            aiEngineerStatus={aiEngineerStatus}
          />
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
    </div>
  )
}

export default memo(RaceScene)
