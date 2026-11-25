/**
 * O cenário da corrida: céu com sol, neblina, luz com sombras suaves, chão
 * (grama, asfalto, linhas, zebras, brita, via dos boxes) e os modelos do
 * Kenney Racing Kit, tudo derivado dos waypoints servidos (`layout.ts`).
 */
import { Suspense, useEffect, useLayoutEffect, useMemo, useRef } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { useGLTF } from "@react-three/drei"
import { InstancedMesh, MathUtils, Matrix4, Mesh, Vector3 } from "three"
import type { BufferGeometry, DirectionalLight, Object3D, ShaderMaterial, Texture } from "three"
import { Sky } from "three/examples/jsm/objects/Sky.js"

import type { FollowState } from "../camera-math"
import type { ScenePitLane } from "../race-track"
import type { TrackFrame } from "../track-frame"
import { Band, PROP_KINDS, propMatrix } from "./layout"
import type { Layout, PropKind } from "./layout"
import { QUALITY } from "./quality"
import type { Quality } from "./quality"
import { LAYERS, bandGeometry, groundGeometry, openBandGeometry, openLaterals } from "./surfaces"
import { PALETTE, kerbTexture, noiseTexture } from "./textures"

/** Sol a 32° de elevação (58° do zênite), azimute 210°, como no protótipo. */
const SUN_DIR = new Vector3().setFromSphericalCoords(1, MathUtils.degToRad(58), MathUtils.degToRad(210))
const FOG_COLOR = "#b9cfe0"
const EXPOSURE = 0.8

const PROP_URL =(kind: PropKind) => `${import.meta.env.BASE_URL}models/${kind}.glb`

type Props = {
  layout: Layout
  frame: TrackFrame
  widthM: number
  pitLane: ScenePitLane | null
  center: Vector3
  radius: number
  /** Distância da câmera da visão geral: escala da neblina e do chão. */
  overviewDistance: number
  quality: Quality
  followRef: { current: FollowState }
}

export function Environment(props: Props) {
  const q = QUALITY[props.quality]
  return (
    <>
      <SkyAndLight
        shadows={q.shadows}
        mapSize={q.shadowMapSize}
        radius={props.radius}
        overviewDistance={props.overviewDistance}
        followRef={props.followRef}
      />
      <Surfaces {...props} />
      <Suspense fallback={null}>
        <KitProps layout={props.layout} treeFraction={q.treeFraction} />
      </Suspense>
    </>
  )
}

// ---------------------------------------------------------------------------

type SkyProps = {
  shadows: boolean
  mapSize: number
  radius: number
  overviewDistance: number
  followRef: { current: FollowState }
}

/** Base ortonormal da luz, para alinhar o centro da sombra à grade de texels. */
const LIGHT_U = new Vector3().crossVectors(new Vector3(0, 1, 0), SUN_DIR).normalize()
const LIGHT_V = new Vector3().crossVectors(SUN_DIR, LIGHT_U).normalize()

function SkyAndLight({ shadows, mapSize, radius, overviewDistance, followRef }: SkyProps) {
  const getThree = useThree((s) => s.get)
  const skyRef = useRef<Sky>(null)
  const lightRef = useRef<DirectionalLight>(null)
  const targetRef = useRef<Object3D>(null)
  const scratch = useRef({ target: new Vector3(), snapped: new Vector3(), half: 0, frames: 0 })

  const sky = useMemo(() => {
    const s = new Sky()
    const u = (s.material as ShaderMaterial).uniforms
    u.sunPosition.value.copy(SUN_DIR)
    u.turbidity.value = 3
    u.rayleigh.value = 1.2
    u.mieCoefficient.value = 0.004
    u.mieDirectionalG.value = 0.8
    s.frustumCulled = false
    // Por último entre os opacos: o depth test descarta os pixels já cobertos
    // pelo chão (o shader do céu é caro e, centrado na câmera, iria primeiro).
    s.renderOrder = 10
    s.name = "sky"
    return s
  }, [])
  useEffect(
    () => () => {
      sky.geometry.dispose()
      ;(sky.material as ShaderMaterial).dispose()
    },
    [sky],
  )

  useLayoutEffect(() => {
    const light = lightRef.current
    const target = targetRef.current
    if (light && target) light.target = target
    // O three desenha as sombras *antes* de montar as luzes do quadro: no
    // primeiro quadro de um renderizador as luzes ainda estão vazias, e os
    // materiais de profundidade de quem já está na cena (modelos em cache)
    // compilariam uma variante a mais, que fica presa ao material. Pula a
    // sombra nesse quadro (e no quadro em que a sombra é religada); ela liga
    // no seguinte, com as luzes já montadas.
    if (light) light.shadow.autoUpdate = false
    scratch.current.frames = 0
    // Volume da sombra refeito no próximo quadro.
    scratch.current.half = 0
  }, [mapSize, shadows])

  useEffect(() => {
    const gl = getThree().gl
    const prev = gl.toneMappingExposure
    gl.toneMappingExposure = EXPOSURE
    return () => {
      getThree().gl.toneMappingExposure = prev
    }
  }, [getThree])

  useFrame((state) => {
    const cam = state.camera
    const skyMesh = skyRef.current
    const light = lightRef.current
    if (!skyMesh || !light) return
    if (scratch.current.frames++ === 1) light.shadow.autoUpdate = true
    // Céu sempre em volta da câmera e dentro do plano far.
    skyMesh.position.copy(cam.position)
    skyMesh.scale.setScalar(("far" in cam ? (cam.far as number) : 10000) * 0.9)

    // Sombra centrada no alvo da câmera: o carro seguido ou o alvo da órbita.
    const sc = scratch.current
    const f = followRef.current
    const controls = state.controls as unknown as { target?: Vector3 } | null
    if (f.carIndex >= 0 && f.posed) sc.target.set(f.x, 0, f.z)
    else if (controls?.target) sc.target.copy(controls.target)
    // Meia largura do volume da sombra pela distância da câmera, em degraus de ~19%.
    const dist = cam.position.distanceTo(sc.target)
    const wanted = MathUtils.clamp(dist * 1.1, 40, radius * 1.25 + 100)
    const half = 2 ** (Math.round(Math.log2(wanted) * 4) / 4)
    const texel = (2 * half) / mapSize
    // Centro alinhado aos texels no espaço da luz: a sombra não "ferve" ao mover.
    const u = Math.round(sc.target.dot(LIGHT_U) / texel) * texel
    const v = Math.round(sc.target.dot(LIGHT_V) / texel) * texel
    const w = sc.target.dot(SUN_DIR)
    sc.snapped.copy(LIGHT_U).multiplyScalar(u).addScaledVector(LIGHT_V, v).addScaledVector(SUN_DIR, w)
    const lightDist = Math.max(400, half * 2)
    light.target.position.copy(sc.snapped)
    light.position.copy(sc.snapped).addScaledVector(SUN_DIR, lightDist)
    light.target.updateMatrixWorld()
    if (half !== sc.half) {
      const c = light.shadow.camera
      c.left = -half
      c.right = half
      c.top = half
      c.bottom = -half
      c.near = 1
      c.far = lightDist + half * 2
      c.updateProjectionMatrix()
      light.shadow.normalBias = texel * 1.2
      sc.half = half
    }
  })

  return (
    <>
      <primitive ref={skyRef} object={sky} />
      <fog attach="fog" args={[FOG_COLOR, overviewDistance, overviewDistance * 3]} />
      <hemisphereLight args={["#cfe3ff", "#4d6b3d", 0.9]} />
      <directionalLight
        key={mapSize}
        ref={lightRef}
        name="sun"
        color="#fff3e0"
        intensity={2.4}
        castShadow={shadows}
        shadow-mapSize={[mapSize, mapSize]}
        shadow-bias={-0.0004}
      />
      <object3D ref={targetRef} />
    </>
  )
}

// ---------------------------------------------------------------------------

type SurfaceAssets = {
  geometries: Record<string, BufferGeometry>
  textures: Record<"grass" | "verge" | "asphalt" | "sand" | "kerb", Texture>
}

function Surfaces({ layout, frame, widthM, pitLane, center, radius, overviewDistance }: Props) {
  const assets = useMemo<SurfaceAssets>(() => {
    const h = widthM / 2
    const lap: [number, number][] = [[0, frame.lengthM]]
    const seed = layout.seed
    const g: Record<string, BufferGeometry> = {
      ground: groundGeometry(center.x, center.z, Math.max(radius * 12, overviewDistance * 5), 24),
      verge: bandGeometry(frame, -h - 6, h + 6, lap, { y: LAYERS.verge.y, alongM: 24, acrossM: 24 }),
      asphalt: bandGeometry(frame, -h, h, lap, { y: LAYERS.asphalt.y, alongM: 8, acrossM: 8 }),
      lineL: bandGeometry(frame, -h + 0.25, -h + 0.55, lap, { y: LAYERS.lines.y }),
      lineR: bandGeometry(frame, h - 0.55, h - 0.25, lap, { y: LAYERS.lines.y }),
      kerbL: bandGeometry(frame, -h - 1.3, -h, layout.kerbs, { y: LAYERS.kerb.y, alongM: 4 }),
      kerbR: bandGeometry(frame, h, h + 1.3, layout.kerbs, { y: LAYERS.kerb.y, alongM: 4 }),
      // Brita só por fora: curva à direita (curvatura > 0) tem o lado de fora à esquerda.
      sandL: bandGeometry(frame, -h - 16, -h - 1.3, layout.sandLeft, { y: LAYERS.sand.y, alongM: 12, acrossM: 12 }),
      sandR: bandGeometry(frame, h + 1.3, h + 16, layout.sandRight, { y: LAYERS.sand.y, alongM: 12, acrossM: 12 }),
    }
    if (pitLane) {
      const pw = pitLane.widthM / 2
      g.pit = openBandGeometry(pitLane.points, -pw, pw, { y: LAYERS.pit.y, alongM: 8, acrossM: 8 })
      // Linhas da via só onde já saíram do asfalto (na entrada e na saída a via cruza a pista).
      const track = new Band(frame.points, h, true)
      const lat = openLaterals(pitLane.points)
      const off = (side: number) => (i: number) => {
        const p = lat[i]
        const d = side * (pw - 0.2)
        return track.distance(p.x + p.rx * d, p.z + p.rz * d, h + 0.5) > h + 0.3
      }
      g.pitLineL = openBandGeometry(pitLane.points, -pw, -pw + 0.25, { y: LAYERS.pitLines.y }, off(-1))
      g.pitLineR = openBandGeometry(pitLane.points, pw - 0.25, pw, { y: LAYERS.pitLines.y }, off(1))
    }
    const textures = {
      grass: noiseTexture(PALETTE.grass, 0.18, 9000, seed),
      verge: noiseTexture(PALETTE.verge, 0.14, 7000, seed + 1),
      asphalt: noiseTexture(PALETTE.road, 0.14, 12000, seed + 2),
      sand: noiseTexture(PALETTE.sand, 0.22, 9000, seed + 3),
      kerb: kerbTexture(),
    }
    return { geometries: g, textures }
  }, [layout, frame, widthM, pitLane, center, radius, overviewDistance])

  useEffect(
    () => () => {
      for (const g of Object.values(assets.geometries)) g.dispose()
      for (const t of Object.values(assets.textures)) t.dispose()
    },
    [assets],
  )

  const g = assets.geometries
  const t = assets.textures
  const layer = (k: keyof typeof LAYERS) => ({
    name: `surface:${k}`,
    polygonOffset: LAYERS[k].offset !== 0,
    polygonOffsetFactor: LAYERS[k].offset,
    polygonOffsetUnits: LAYERS[k].offset,
  })

  return (
    <group name="environment-surfaces">
      <mesh geometry={g.ground} receiveShadow name="ground">
        <meshStandardMaterial map={t.grass} roughness={1} {...layer("ground")} />
      </mesh>
      <mesh geometry={g.verge} receiveShadow>
        <meshStandardMaterial map={t.verge} roughness={1} {...layer("verge")} />
      </mesh>
      <mesh geometry={g.sandL} receiveShadow>
        <meshStandardMaterial map={t.sand} roughness={1} {...layer("sand")} />
      </mesh>
      <mesh geometry={g.sandR} receiveShadow>
        <meshStandardMaterial map={t.sand} roughness={1} {...layer("sand")} />
      </mesh>
      <mesh geometry={g.asphalt} receiveShadow name="track">
        <meshStandardMaterial map={t.asphalt} roughness={0.92} {...layer("asphalt")} />
      </mesh>
      {(["lineL", "lineR"] as const).map((k) => (
        <mesh key={k} geometry={g[k]} receiveShadow>
          <meshStandardMaterial color={PALETTE.white} roughness={0.8} {...layer("lines")} />
        </mesh>
      ))}
      {(["kerbL", "kerbR"] as const).map((k) => (
        <mesh key={k} geometry={g[k]} receiveShadow>
          <meshStandardMaterial map={t.kerb} roughness={0.7} {...layer("kerb")} />
        </mesh>
      ))}
      {g.pit && (
        <mesh geometry={g.pit} receiveShadow name="pit-lane">
          <meshStandardMaterial map={t.asphalt} color="#d8d8d8" roughness={0.9} {...layer("pit")} />
        </mesh>
      )}
      {(["pitLineL", "pitLineR"] as const).map(
        (k) =>
          g[k] && (
            <mesh key={k} geometry={g[k]} receiveShadow>
              <meshStandardMaterial color={PALETTE.white} roughness={0.8} {...layer("pitLines")} />
            </mesh>
          ),
      )}
    </group>
  )
}

// ---------------------------------------------------------------------------

const TREES = new Set<PropKind>(["treeLarge", "treeSmall"])

/** Um `InstancedMesh` por primitiva de cada modelo; geometria e material vêm do cache do `useGLTF`. */
function KitProps({ layout, treeFraction }: { layout: Layout; treeFraction: number }) {
  const gltfs = useGLTF(PROP_KINDS.map(PROP_URL))

  const meshes = useMemo(() => {
    const out: { kind: PropKind; mesh: InstancedMesh }[] = []
    const m = new Matrix4()
    const w = new Matrix4()
    PROP_KINDS.forEach((kind, i) => {
      const list = layout.props[kind]
      if (!list.length) return
      const root = gltfs[i].scene
      root.updateMatrixWorld(true)
      root.traverse((obj) => {
        if (!(obj instanceof Mesh)) return
        const im = new InstancedMesh(obj.geometry, obj.material, list.length)
        list.forEach((p, k) => {
          propMatrix(kind, p, m)
          im.setMatrixAt(k, w.multiplyMatrices(m, obj.matrixWorld))
        })
        im.instanceMatrix.needsUpdate = true
        im.computeBoundingSphere()
        // Árvores: na qualidade baixa só as primeiras (a lista já vem embaralhada).
        im.count = TREES.has(kind) ? Math.round(list.length * treeFraction) : list.length
        im.castShadow = true
        im.receiveShadow = true
        im.name = `prop:${kind}`
        out.push({ kind, mesh: im })
      })
    })
    return out
  }, [gltfs, layout, treeFraction])

  // Geometria e material são do cache (compartilhados entre montagens): só as instâncias são descartadas.
  useEffect(() => () => meshes.forEach((x) => x.mesh.dispose()), [meshes])

  return (
    <group name="environment-props">
      {meshes.map((x) => (
        <primitive key={x.mesh.uuid} object={x.mesh} />
      ))}
    </group>
  )
}
