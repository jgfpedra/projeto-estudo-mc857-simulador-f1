/**
 * O cenário da corrida: céu com sol, neblina, luz com sombras suaves, chão
 * (grama, asfalto, linhas, zebras, brita, via dos boxes) e os modelos do
 * Kenney Racing Kit, tudo derivado dos waypoints servidos (`layout.ts`).
 */
import { Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { useFrame, useThree } from "@react-three/fiber"
import { useGLTF } from "@react-three/drei"
import {
  BufferAttribute,
  BufferGeometry,
  Color,
  InstancedMesh,
  LineSegments,
  MathUtils,
  Matrix4,
  Mesh,
  SRGBColorSpace,
  ShaderMaterial,
  Vector3,
} from "three"
import type { DirectionalLight, Fog, HemisphereLight, MeshStandardMaterial, Object3D, Texture } from "three"
import { Sky } from "three/examples/jsm/objects/Sky.js"

import type { FollowState } from "../camera-math"
import { lastLive } from "../live-clock"
import type { ScenePitLane } from "../race-track"
import type { TrackFrame } from "../track-frame"
import { Band, PROP_KINDS, propMatrix } from "./layout"
import type { Layout, PropKind } from "./layout"
import { QUALITY } from "./quality"
import type { Quality } from "./quality"
import { LAYERS, bandGeometry, groundGeometry, openBandGeometry, openLaterals } from "./surfaces"
import { PALETTE, kerbTexture, noiseTexture } from "./textures"
import {
  DRY_LOOK,
  WEATHER,
  WeatherBlend,
  effectiveWeather,
  fogRange,
  rainStreakCount,
  rainVisibility,
  setWeatherDebug,
  weatherLook,
  weatherParams,
} from "./weather"
import type { RGB, WeatherLook, WeatherParams } from "./weather"

/** Sol a 32° de elevação (58° do zênite), azimute 210°, como no protótipo. */
const SUN_DIR = new Vector3().setFromSphericalCoords(1, MathUtils.degToRad(58), MathUtils.degToRad(210))
const FOG_COLOR = "#b9cfe0"
const EXPOSURE = 0.8
/** Cor base da via dos boxes (multiplica a textura do asfalto). */
const PIT_COLOR = "#d8d8d8"

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

/**
 * Clima compartilhado entre o céu (que mistura e aplica), o chão (materiais
 * do asfalto) e a chuva. Um por montagem do cenário.
 */
type WeatherState = {
  blend: WeatherBlend
  look: WeatherLook
  target: WeatherLook
  /** Andamento da mistura em curso (1 = terminada). */
  progress: number
  params: WeatherParams
  fog: { near: number; far: number }
  /** Distância da câmera ao alvo (carro seguido ou alvo da órbita), m. */
  cameraDistance: number
  /** Riscos de chuva desenhados no último quadro. */
  streaks: number
  materials: { asphalt: MeshStandardMaterial | null; pit: MeshStandardMaterial | null }
}

function newWeatherState(overviewDistance: number): WeatherState {
  return {
    blend: new WeatherBlend(),
    look: { ...DRY_LOOK },
    target: { ...DRY_LOOK },
    progress: 1,
    params: weatherParams(DRY_LOOK),
    fog: fogRange(DRY_LOOK, overviewDistance, overviewDistance),
    cameraDistance: overviewDistance,
    streaks: 0,
    materials: { asphalt: null, pit: null },
  }
}

function snapshot(w: WeatherState) {
  const r = (v: number) => Math.round(v * 1000) / 1000
  const look = (l: WeatherLook) => ({ cloud: r(l.cloud), wet: r(l.wet), rain: r(l.rain) })
  return {
    look: look(w.look),
    target: look(w.target),
    progress: r(w.progress),
    streaks: w.streaks,
    fog: { near: Math.round(w.fog.near), far: Math.round(w.fog.far) },
    cameraDistance: Math.round(w.cameraDistance),
    params: {
      sunIntensity: r(w.params.sunIntensity),
      hemiIntensity: r(w.params.hemiIntensity),
      overcast: r(w.params.overcast),
      turbidity: r(w.params.turbidity),
      fogColor: w.params.fogColor.map(r),
      asphaltShade: r(w.params.asphaltShade),
      asphaltRoughness: r(w.params.asphaltRoughness),
      asphaltSheen: r(w.params.asphaltSheen),
    },
  }
}

export function Environment(props: Props) {
  const q = QUALITY[props.quality]
  // Um estado por montagem: a mistura não recomeça a cada re-render.
  const [weatherRef] = useState(() => ({ current: newWeatherState(props.overviewDistance) }))
  // Para o gancho de desenvolvimento (`__race3d.weather()`).
  useEffect(() => setWeatherDebug(() => snapshot(weatherRef.current)), [weatherRef])
  return (
    <>
      <SkyAndLight
        shadows={q.shadows}
        mapSize={q.shadowMapSize}
        radius={props.radius}
        overviewDistance={props.overviewDistance}
        followRef={props.followRef}
        weatherRef={weatherRef}
      />
      <Surfaces {...props} weatherRef={weatherRef} />
      {WEATHER.streaks[props.quality] > 0 && (
        <RainStreaks key={props.quality} quality={props.quality} overviewDistance={props.overviewDistance} followRef={props.followRef} weatherRef={weatherRef} />
      )}
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
  weatherRef: { current: WeatherState }
}

/** Base ortonormal da luz, para alinhar o centro da sombra à grade de texels. */
const LIGHT_U = new Vector3().crossVectors(new Vector3(0, 1, 0), SUN_DIR).normalize()
const LIGHT_V = new Vector3().crossVectors(SUN_DIR, LIGHT_U).normalize()

const setRGB = (c: Color, v: RGB) => c.setRGB(v[0], v[1], v[2], SRGBColorSpace)

/**
 * O shader do `Sky` com um céu encoberto por cima: `overcast` = 0 devolve o
 * céu de antes (mix com peso 0); 1 o troca por um cinza um pouco mais claro
 * no horizonte. O mesmo programa em qualquer clima, nada a recompilar.
 */
function addOvercast(material: ShaderMaterial): void {
  const uniformsAt = "uniform vec3 up;"
  const outputAt = "gl_FragColor = vec4( retColor, 1.0 );"
  if (!material.fragmentShader.includes(uniformsAt) || !material.fragmentShader.includes(outputAt))
    throw new Error("Sky shader changed: overcast patch points not found")
  material.uniforms.overcast = { value: 0 }
  material.uniforms.overcastColor = { value: new Vector3(0.5, 0.5, 0.5) }
  material.fragmentShader = material.fragmentShader
    .replace(uniformsAt, `${uniformsAt}\n\t\tuniform float overcast;\n\t\tuniform vec3 overcastColor;`)
    .replace(
      outputAt,
      "float horizonGlow = 1.0 - clamp( direction.y, 0.0, 1.0 );\n\t\t\t" +
        "retColor = mix( retColor, overcastColor * ( 0.8 + 0.35 * horizonGlow ), overcast );\n\t\t\t" +
        outputAt,
    )
}

function SkyAndLight({ shadows, mapSize, radius, overviewDistance, followRef, weatherRef }: SkyProps) {
  const getThree = useThree((s) => s.get)
  const skyRef = useRef<Sky>(null)
  const lightRef = useRef<DirectionalLight>(null)
  const hemiRef = useRef<HemisphereLight>(null)
  const pitBase = useMemo(() => new Color(PIT_COLOR), [])
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
    addOvercast(s.material as ShaderMaterial)
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

    // Clima: o do frame que os carros desenharam (lido um quadro depois, nada numa mistura de
    // 5 s). Até o primeiro frame fica o seco de antes; o primeiro clima entra sem mistura.
    const ws = weatherRef.current
    ws.cameraDistance = dist
    const live = lastLive()
    if (live?.view.cur) {
      ws.look = ws.blend.update(weatherLook(effectiveWeather(live.view.cur.weather)), live.now)
      ws.target = ws.blend.target
      ws.progress = ws.blend.progress(live.now)
    }
    const p = weatherParams(ws.look)
    ws.params = p
    const su = (skyMesh.material as ShaderMaterial).uniforms
    su.turbidity.value = p.turbidity
    su.rayleigh.value = p.rayleigh
    su.mieCoefficient.value = p.mie
    su.overcast.value = p.overcast
    ;(su.overcastColor.value as Vector3).set(p.overcastColor[0], p.overcastColor[1], p.overcastColor[2])
    light.intensity = p.sunIntensity
    setRGB(light.color, p.sunColor)
    const hemi = hemiRef.current
    if (hemi) {
      hemi.intensity = p.hemiIntensity
      setRGB(hemi.color, p.hemiSky)
      setRGB(hemi.groundColor, p.hemiGround)
    }
    ws.fog = fogRange(ws.look, overviewDistance, dist)
    const fog = state.scene.fog as Fog | null
    if (fog) {
      setRGB(fog.color, p.fogColor)
      fog.near = ws.fog.near
      fog.far = ws.fog.far
    }
    const { asphalt, pit } = ws.materials
    if (asphalt) {
      asphalt.color.setScalar(p.asphaltShade)
      asphalt.emissive.setRGB(p.fogColor[0], p.fogColor[1], p.fogColor[2], SRGBColorSpace).multiplyScalar(p.asphaltSheen)
      asphalt.roughness = p.asphaltRoughness
    }
    if (pit) {
      pit.color.copy(pitBase).multiplyScalar(p.asphaltShade)
      pit.emissive.copy(asphalt?.emissive ?? pit.emissive)
      pit.roughness = MathUtils.lerp(0.9, p.asphaltRoughness, ws.look.wet)
    }
  })

  return (
    <>
      <primitive ref={skyRef} object={sky} />
      <fog attach="fog" args={[FOG_COLOR, overviewDistance, overviewDistance * 3]} />
      <hemisphereLight ref={hemiRef} args={["#cfe3ff", "#4d6b3d", 0.9]} />
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

function Surfaces({
  layout,
  frame,
  widthM,
  pitLane,
  center,
  radius,
  overviewDistance,
  weatherRef,
}: Props & { weatherRef: { current: WeatherState } }) {
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
        <meshStandardMaterial
          ref={(m: MeshStandardMaterial | null) => {
            weatherRef.current.materials.asphalt = m
          }}
          map={t.asphalt}
          roughness={0.92}
          {...layer("asphalt")}
        />
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
          <meshStandardMaterial
            ref={(m: MeshStandardMaterial | null) => {
              weatherRef.current.materials.pit = m
            }}
            map={t.asphalt}
            color={PIT_COLOR}
            roughness={0.9}
            {...layer("pit")}
          />
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

/** Caixa da chuva em volta da câmera (m) e queda (m/s), na escala 1 (perto do carro). */
const RAIN_BOX_M = 40
const RAIN_FALL_MPS = 12
const RAIN_STREAK_M = 0.9

const RAIN_VERTEX = /* glsl */ `
uniform float uTime;
uniform float uScale;
uniform vec3 uCam;
attribute float aEnd;
varying float vAlpha;
void main() {
  float box = ${RAIN_BOX_M.toFixed(1)} * uScale;
  // Queda com um pouco de vento; cada risco com velocidade própria (+-15%).
  vec3 dir = normalize(vec3(0.12, -1.0, 0.05));
  float speed = ${RAIN_FALL_MPS.toFixed(1)} * uScale * (0.85 + 0.3 * fract(position.x * 97.0 + position.z * 31.0));
  vec3 p = position * box + dir * (uTime * speed);
  // Dentro de uma caixa que acompanha a câmera (o risco fica no mundo; a caixa dá a volta).
  vec3 rel = mod(p - uCam + 0.5 * box, box) - 0.5 * box;
  vec3 world = uCam + rel + dir * (aEnd * ${RAIN_STREAK_M.toFixed(2)} * uScale);
  float edge = max(max(abs(rel.x), abs(rel.y)), abs(rel.z)) / (0.5 * box);
  vAlpha = (1.0 - 0.7 * aEnd) * (1.0 - smoothstep(0.7, 1.0, edge));
  gl_Position = projectionMatrix * viewMatrix * vec4(world, 1.0);
}
`
const RAIN_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
uniform float uOpacity;
varying float vAlpha;
void main() {
  gl_FragColor = vec4(uColor, uOpacity * vAlpha);
}
`

/** Gerador com semente (mulberry32): a mesma chuva a cada montagem. */
function seeded(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * Riscos de chuva em volta da câmera: um `LineSegments` com todos os riscos
 * da qualidade, animado no vertex shader (nada por quadro na CPU além de três
 * uniforms); a intensidade só muda o `drawRange`. Sem chuva, invisível (nada
 * desenhado). A caixa cresce com a distância da câmera ao alvo, para a chuva
 * aparecer também na visão geral.
 */
type RainProps = { quality: Quality; overviewDistance: number; followRef: { current: FollowState }; weatherRef: { current: WeatherState } }

/** Quantos riscos desenhar (0 esconde). */
function showStreaks(lines: LineSegments, n: number): void {
  lines.visible = n > 0
  if (n > 0) lines.geometry.setDrawRange(0, n * 2)
}

function rainUniforms(lines: LineSegments, timeS: number, camera: Vector3, scale: number, opacity: number): void {
  const u = (lines.material as ShaderMaterial).uniforms
  u.uTime.value = timeS
  ;(u.uCam.value as Vector3).copy(camera)
  u.uScale.value = scale
  u.uOpacity.value = opacity
}

function RainStreaks({ quality, overviewDistance, followRef, weatherRef }: RainProps) {
  const max = WEATHER.streaks[quality]
  const lines = useMemo(() => {
    const rnd = seeded(0x5eed + max)
    const pos = new Float32Array(max * 2 * 3)
    const end = new Float32Array(max * 2)
    for (let i = 0; i < max; i++) {
      const x = rnd()
      const y = rnd()
      const z = rnd()
      pos.set([x, y, z, x, y, z], i * 6)
      end[i * 2 + 1] = 1
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute("position", new BufferAttribute(pos, 3))
    geometry.setAttribute("aEnd", new BufferAttribute(end, 1))
    geometry.setDrawRange(0, 0)
    const material = new ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uScale: { value: 1 },
        uCam: { value: new Vector3() },
        uColor: { value: new Vector3(0.78, 0.82, 0.88) },
        uOpacity: { value: 0.4 },
      },
      vertexShader: RAIN_VERTEX,
      fragmentShader: RAIN_FRAGMENT,
      transparent: true,
      depthWrite: false,
    })
    const l = new LineSegments(geometry, material)
    l.frustumCulled = false
    l.renderOrder = 20
    l.visible = false
    l.name = "rain"
    return l
  }, [max])

  useEffect(
    () => () => {
      lines.geometry.dispose()
      ;(lines.material as ShaderMaterial).dispose()
    },
    [lines],
  )

  useFrame((state) => {
    const ws = weatherRef.current
    const rain = ws.look.rain
    // Some com a distância da câmera (como os marcadores aparecem): nenhum risco na visão geral.
    const visibility = rainVisibility(ws.cameraDistance, overviewDistance)
    const n = visibility > 0.01 ? rainStreakCount(quality, rain) : 0
    ws.streaks = n
    showStreaks(lines, n)
    if (!n) return
    // Tempo do quadro desenhado (congelado junto com os carros); limitado para a precisão do float.
    const timeS = ((lastLive()?.now ?? 0) / 1000) % 10_000
    // Perto do carro (perseguição, a bordo) escala 1; de mais longe a caixa cresce, enquanto some.
    const scale = followRef.current.carIndex >= 0 ? 1 : MathUtils.clamp(ws.cameraDistance / 15, 1, 25)
    const opacity = (0.25 + 0.3 * rain) * visibility
    rainUniforms(lines, timeS, state.camera.position, scale, opacity)
  })

  return <primitive object={lines} />
}

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
