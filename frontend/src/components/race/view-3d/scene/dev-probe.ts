/**
 * Gancho só de desenvolvimento para a verificação headless (Playwright).
 *
 * Expõe `window.__race3d` enquanto o 3D está montado. `sample()` devolve as
 * posições que o 3D *desenhou* (lidas da matriz de instância que vai para a
 * GPU, não recalculadas) e as posições da interpolação do 2D
 * (`interpolateCars`) avaliada no mesmo instante de simulação que o 3D
 * desenhou (o da reprodução com buffer, ~150 ms atrás do frame mais novo).
 * `smoothness()` mede o passo do carro seguido quadro a quadro
 * (`smoothness.ts`) e `playback("live")` volta ao caminho antigo, na borda ao
 * vivo, para comparar. `cameraJitter()` mede o tremor da direção da câmera
 * que segue o carro e da posição dele na tela (`camera-jitter.ts`), e
 * `chaseRig("track")` volta à perseguição antiga, pela pista, para comparar.
 * `shadowOffset()` mede onde a sombra do carro seguido caiu no mapa de sombra
 * do último quadro, no referencial do carro. `tyreBands()` lê a cor e a
 * visibilidade das faixas de composto (do buffer de instâncias),
 * `tyreView(id)` põe a câmera ao lado de um carro e `weather()` devolve o
 * clima misturado e os parâmetros da cena. Em produção
 * `import.meta.env.DEV` é falso e nada disso é instalado.
 */
import { Color, Matrix4, Vector3 } from "three"
import type { Camera, DirectionalLight, InstancedMesh, MeshBasicMaterial, Scene, WebGLRenderer } from "three"

import { interpolateCars } from "@/helpers/race-live"
import { useLiveRaceStore } from "@/stores/live-race-store"
import type { Frame } from "@/types/race"
import { chaseRigMode, setChaseRigMode } from "./camera-math"
import type { CameraMode, CameraPose, ChaseRig } from "./camera-math"
import { angleJitter, bearing } from "./camera-jitter"
import type { AngleSample } from "./camera-jitter"
import { weatherSnapshot } from "./environment/weather"
import { softwareProbeReleased, softwareRendering } from "./environment/quality"
import type { Quality } from "./environment/quality"
import type { ViewPose } from "./environment/views"
import { freezeLive, liveFrozen, playbackMode, setPlaybackMode, unfreezeLive } from "./live-clock"
import type { LiveView, PlaybackMode } from "./live-clock"
import { smoothness } from "./smoothness"
import type { TraceSample } from "./smoothness"

type Drawn = {
  now: number
  view: LiveView
  cars: {
    driverId: string
    x: number
    y: number
    /** Frente do carro no three (unitária, no plano). */
    fx: number
    fz: number
    pinTop: [number, number, number] | null
    pinScale: number
  }[]
  /** Opacidade dos marcadores neste quadro (0 = escondidos). */
  pinOpacity: number
  bands: TyreBands | null
  /** Pilotos na ordem das instâncias. */
  ids: string[]
}

/** Faixas de composto: o InstancedMesh (carro k, roda w -> k * perCar + w) e a cor aplicada a cada carro. */
export type TyreBands = { mesh: InstancedMesh; perCar: number; hex: (string | null | undefined)[] }

export type ProbeSink = {
  record: (now: number, view: LiveView, body: InstancedMesh | null, pins: InstancedMesh, ids: string[], bands: TyreBands | null) => void
  /** Chamado pelo rig depois de pôr a câmera, no mesmo quadro de `record`. */
  camera: (pose: CameraPose, cut: number) => void
}

/** Câmera no quadro: direção (rad), carro em relação ao eixo (rad), corte do rig. */
type CameraTrace = { yawRad: number; carOffRad: number; cut: number; rig: ChaseRig; camera: CameraMode }

/** Quadro do carro seguido, para `smoothness()` e `cameraJitter()`. */
type Traced = TraceSample & { sM: number | null; held: boolean; lagMs: number; mode: PlaybackMode; cam: CameraTrace | null }

/** ~10 min a 60 Hz. */
const TRACE_LIMIT = 36_000
/** Frames da store guardados pelo gancho, s de simulação (cobre um congelamento de vários segundos). */
const HISTORY_S = 15

type Context = {
  /** `useThree((s) => s.get)`: estado atual do Canvas. */
  three: () => { gl: WebGLRenderer; camera: Camera; scene: Scene; controls: unknown }
  mode: CameraMode
  followed: string | null
  colors: Map<string, string>
  quality: Quality
  /** Pontos de vista fixos para capturas (só com o cenário ligado). */
  views: Record<string, ViewPose> | null
}

type Controls = { target: Vector3; enabled: boolean; update: () => void }

declare global {
  interface Window {
    __race3d?: unknown
  }
}

/*
 * Cópia própria dos frames da store, por `simTs`, para avaliar o 2D em
 * qualquer instante recente. No módulo (não no gancho) porque o gancho é
 * recriado a cada troca de seleção ou de câmera.
 */
let history: Frame[] = []
let historyUsers = 0
let historyStop: (() => void) | null = null

function keep(f: Frame): void {
  const newest = history.at(-1)
  if (newest && f.simTs < newest.simTs) history = []
  if (newest && f.simTs === newest.simTs) history[history.length - 1] = f
  else history.push(f)
  while (history.length > 2 && history[0].simTs < f.simTs - HISTORY_S) history.shift()
}

function watchHistory(): () => void {
  if (historyUsers++ === 0) {
    const s = useLiveRaceStore.getState()
    if (s.prevFrame) keep(s.prevFrame)
    if (s.frame) keep(s.frame)
    historyStop = useLiveRaceStore.subscribe((st, prev) => {
      if (st.frame && st.frame !== prev.frame) keep(st.frame)
    })
  }
  return () => {
    if (--historyUsers > 0) return
    historyStop?.()
    historyStop = null
  }
}

function twoDAt(simTs: number): { prev: Frame | null; cur: Frame; alpha: number } | null {
  if (history.length === 0) return null
  // Mais antigo que a cópia (o gancho começou a copiar depois do relógio do 3D): sem como avaliar.
  if (simTs < history[0].simTs) return null
  if (simTs === history[0].simTs) return { prev: null, cur: history[0], alpha: 1 }
  for (let i = history.length - 1; i > 0; i--) {
    const a = history[i - 1]
    if (simTs >= a.simTs) {
      const b = history[i]
      return { prev: a, cur: b, alpha: Math.min(1, (simTs - a.simTs) / (b.simTs - a.simTs)) }
    }
  }
  return null
}

export function createProbe(ctx: Context): { sink: ProbeSink; install: () => () => void } {
  let last: Drawn | null = null
  let trace: Traced[] = []
  /** Quadro do carro seguido gravado neste quadro, à espera da câmera. */
  let pending: Traced | null = null
  /** Pose desenhada do carro seguido no último quadro (three), para `shadowOffset()`. */
  let followedPose: { x: number; z: number; fx: number; fz: number } | null = null
  const m = new Matrix4()
  const v = new Vector3()

  const sink: ProbeSink = {
    record(now, view, body, pins, ids, bands) {
      pending = null
      followedPose = null
      if (!body || !view.cur) {
        last = { now, view, cars: [], pinOpacity: 0, bands, ids }
        return
      }
      const followedIndex = ctx.followed ? ids.indexOf(ctx.followed) : -1
      if (followedIndex >= 0) {
        body.getMatrixAt(followedIndex, m)
        const e = m.elements
        const f = Math.hypot(e[8], e[10]) || 1
        followedPose = { x: e[12], z: e[14], fx: -e[8] / f, fz: -e[10] / f }
      }
      if (followedIndex >= 0 && !liveFrozen()) {
        body.getMatrixAt(followedIndex, m)
        const e = m.elements
        const car = view.cur.cars.find((c) => c.driverId === ctx.followed)
        if (trace.length >= TRACE_LIMIT) trace.shift()
        pending = {
          wallMs: now,
          x: e[12],
          y: -e[14],
          // Frente do modelo = -Z local, (-sin yaw, -cos yaw) no three: direção = yaw + 90°.
          headingRad: Math.atan2(e[10], -e[8]),
          resyncs: view.resyncs,
          sM: car?.sM ?? null,
          held: view.held,
          lagMs: view.lagMs,
          mode: view.mode,
          cam: null,
        }
        trace.push(pending)
      }
      const present = new Set(view.cur.cars.map((c) => c.driverId))
      const cars: Drawn["cars"] = []
      ids.forEach((driverId, i) => {
        if (!present.has(driverId)) return
        body.getMatrixAt(i, m)
        v.setFromMatrixPosition(m)
        const x = v.x
        const y = -v.z
        const e = m.elements
        const fl = Math.hypot(e[8], e[10]) || 1
        const fx = -e[8] / fl
        const fz = -e[10] / fl
        pins.getMatrixAt(i, m)
        const k = m.elements[5]
        v.setFromMatrixPosition(m)
        cars.push({ driverId, x, y, fx, fz, pinTop: k > 0 ? [v.x, v.y + 2.4 * k * 0.8, v.z] : null, pinScale: k })
      })
      const pinOpacity = pins.visible ? (pins.material as MeshBasicMaterial).opacity : 0
      last = { now, view, cars, pinOpacity, bands, ids }
    },
    camera(pose, cut) {
      if (!pending) return
      const p = pose.position
      const yaw = bearing(p.x, p.z, pose.target.x, pose.target.z)
      const toCar = bearing(p.x, p.z, pose.anchor.x, pose.anchor.z)
      pending.cam = {
        yawRad: yaw,
        carOffRad: Math.atan2(Math.sin(toCar - yaw), Math.cos(toCar - yaw)),
        cut,
        rig: chaseRigMode(),
        camera: ctx.mode,
      }
      pending = null
    },
  }

  const toScreen = (p: [number, number, number]) => {
    const canvas = ctx.three().gl.domElement
    const q = new Vector3(...p).project(ctx.three().camera)
    const rect = canvas.getBoundingClientRect()
    return {
      x: ((q.x + 1) / 2) * rect.width,
      y: ((1 - q.y) / 2) * rect.height,
      onScreen: q.z > -1 && q.z < 1 && Math.abs(q.x) <= 1 && Math.abs(q.y) <= 1,
    }
  }

  const radiusPx = (p: [number, number, number], r: number) => {
    const cam = ctx.three().camera
    const right = new Vector3().setFromMatrixColumn(cam.matrixWorld, 0).normalize()
    const a = toScreen(p)
    const b = toScreen([p[0] + right.x * r, p[1] + right.y * r, p[2] + right.z * r])
    return Math.hypot(b.x - a.x, b.y - a.y)
  }

  const api = {
    /**
     * 3D desenhado vs a interpolação do 2D (`interpolateCars`) avaliada no
     * instante de simulação que o 3D desenhou no último quadro. O par de
     * frames e o `alpha` saem da cópia própria do gancho (os frames da store,
     * por `simTs`), não do relógio do 3D.
     */
    sample() {
      const view = last?.view
      if (!last || !view?.cur || view.simTs === null) return null
      const at = twoDAt(view.simTs)
      if (!at) return null
      const twoD = interpolateCars(at.prev, at.cur, at.alpha)
      let maxErrorM = 0
      const cars = last.cars.map((c) => {
        const p = twoD.get(c.driverId)
        const err = p ? Math.hypot(p.x - c.x, p.y - c.y) : Infinity
        maxErrorM = Math.max(maxErrorM, err)
        return { driverId: c.driverId, x3d: c.x, y3d: c.y, x2d: p?.x ?? null, y2d: p?.y ?? null, errorM: err }
      })
      return {
        now: last.now,
        simTs: view.simTs,
        newestSimTs: useLiveRaceStore.getState().frame?.simTs ?? null,
        lagMs: view.lagMs,
        playback: view.mode,
        alpha: at.alpha,
        drivers: view.cur.cars.length,
        cars,
        maxErrorM,
      }
    },
    /** Onde cada carro e seu marcador aparecem no canvas (pixels CSS). */
    screen() {
      if (!last) return []
      return last.cars.map((c) => ({
        driverId: c.driverId,
        color: ctx.colors.get(c.driverId) ?? null,
        car: toScreen([c.x, 0.4, -c.y]),
        pin: c.pinTop ? toScreen(c.pinTop) : null,
        // Raio do disco do marcador na tela (base do cone, 0,9 * escala), px CSS.
        pinRadiusPx: c.pinTop ? radiusPx(c.pinTop, 0.9 * c.pinScale) : 0,
        pinOpacity: last?.pinOpacity ?? 0,
      }))
    },
    /**
     * Põe a câmera num ponto de vista fixo ("overview" | "grid" | "corner").
     * Desliga a órbita até a próxima chamada com "overview".
     */
    view(name: string) {
      const pose = ctx.views?.[name]
      const { camera, controls } = ctx.three()
      const c = controls as Controls | null
      if (!pose || !c) return false
      c.enabled = name === "overview"
      camera.position.copy(pose.position)
      c.target.copy(pose.target)
      camera.lookAt(pose.target)
      if (c.enabled) c.update()
      return true
    },
    /**
     * Faixas de composto como foram para a GPU: por carro, o composto do frame
     * desenhado, a cor da instância (hex, sRGB) e se os anéis estão visíveis
     * (escala da matriz > 0).
     */
    tyreBands() {
      const b = last?.bands
      if (!last || !b || !last.view.cur) return []
      const tyre = new Map(last.view.cur.cars.map((c) => [c.driverId, c.tyre]))
      const colour = new Color()
      const ids = last.ids
      return ids.map((driverId, k) => {
        let visible = 0
        for (let w = 0; w < b.perCar; w++) {
          b.mesh.getMatrixAt(k * b.perCar + w, m)
          if (Math.abs(m.determinant()) > 1e-12) visible++
        }
        if (b.mesh.instanceColor) b.mesh.getColorAt(k * b.perCar, colour)
        return { driverId, compound: tyre.get(driverId) ?? null, applied: b.hex[k] ?? null, colour: `#${colour.getHexString()}`, visibleRings: visible, rings: b.perCar }
      })
    },
    /**
     * Câmera parada ao lado de um carro (o seguido, se nenhum for dado), na
     * pose do último quadro, para ver as faixas de perto. Use com `freeze()` e
     * fora do seguimento (precisa da órbita, que fica desligada até
     * `view("overview")`).
     */
    tyreView(driverId?: string, distanceM = 5) {
      const id = driverId ?? ctx.followed
      const car = last?.cars.find((c) => c.driverId === id)
      const { camera, controls } = ctx.three()
      const c = controls as Controls | null
      if (!car || !c) return false
      const cx = car.x
      const cz = -car.y
      // Direita do carro = frente girada -90° no plano (three: x, z).
      const rx = -car.fz
      const rz = car.fx
      c.enabled = false
      // Na órbita o plano near cresce com a pista (distância da visão geral / 200, ~7 m): fica além dele.
      const near = "near" in camera ? (camera.near as number) : 1
      const d = Math.max(distanceM, near * 1.8)
      // De cima (~30°): olhando quase na horizontal, o chão mais perto que o near some.
      camera.position.set(cx + rx * d + car.fx * 1.5, Math.max(1.2, d * 0.55), cz + rz * d + car.fz * 1.5)
      c.target.set(cx, 0.35, cz)
      camera.lookAt(c.target)
      return true
    },
    /** Clima misturado, alvo, andamento da mistura, neblina e riscos de chuva do último quadro (null sem cenário). */
    weather() {
      return weatherSnapshot()
    },
    /**
     * Tempo de quadro, ms: `n` renderizações síncronas, cada uma esperando a
     * GPU (lê 1 pixel). Devolve mediana, p90 e média.
     */
    bench(n = 60) {
      const { gl, scene, camera } = ctx.three()
      const g = gl.getContext()
      const px = new Uint8Array(4)
      const once = () => {
        gl.render(scene, camera)
        g.readPixels(0, 0, 1, 1, g.RGBA, g.UNSIGNED_BYTE, px)
      }
      for (let i = 0; i < 5; i++) once()
      const t: number[] = []
      for (let i = 0; i < n; i++) {
        const t0 = performance.now()
        once()
        t.push(performance.now() - t0)
      }
      t.sort((a, b) => a - b)
      const r = (v: number) => Math.round(v * 100) / 100
      return {
        n,
        medianMs: r(t[Math.floor(n / 2)]),
        p90Ms: r(t[Math.floor(n * 0.9)]),
        meanMs: r(t.reduce((a, b) => a + b, 0) / n),
        calls: gl.info.render.calls,
        triangles: gl.info.render.triangles,
        size: [gl.domElement.width, gl.domElement.height],
      }
    },
    /**
     * Congela o relógio do 3D: os carros param na pose deste instante (o
     * WebSocket e o 2D seguem). Para capturas e leituras de posição
     * consistentes em qualquer velocidade de renderização.
     */
    freeze() {
      freezeLive()
      return true
    },
    unfreeze() {
      unfreezeLive()
      return true
    },
    /**
     * "buffered" (padrão) ou "live" (o caminho antigo, na borda ao vivo, só
     * para comparar). Sem argumento, devolve o modo atual.
     */
    playback(next?: PlaybackMode) {
      if (next === "buffered" || next === "live") setPlaybackMode(next)
      return playbackMode()
    },
    /** Esquece os quadros gravados do carro seguido. */
    traceReset() {
      trace = []
      return true
    },
    /**
     * Suavidade do carro seguido desde `traceReset()` (`smoothness.ts`):
     * `spread`, `stalls`, `jumps`, `backwards`. `sRanges` limita a trechos da
     * volta (`s_m`, metros, ex.: [[0, 600], [3700, 4309]]) e `playback` a um
     * modo; cada passagem por um trecho é medida separada das outras. Também
     * conta os quadros parados no frame mais novo e o atraso médio.
     */
    smoothness(opts: { sRanges?: [number, number][]; playback?: PlaybackMode } = {}) {
      const inRange = (sM: number | null) =>
        !opts.sRanges || (sM !== null && opts.sRanges.some(([a, b]) => sM >= a && sM < b))
      const picked: TraceSample[] = []
      let passes = 0
      let inside = false
      let held = 0
      let lagSum = 0
      for (const t of trace) {
        const keep = inRange(t.sM) && (!opts.playback || t.mode === opts.playback)
        if (keep && !inside) passes++
        inside = keep
        if (!keep) continue
        // Uma passagem não emenda na seguinte: chave própria no lugar do contador de ressincronizações.
        picked.push({ ...t, resyncs: t.resyncs * 100_000 + passes })
        if (t.held) held++
        lagSum += t.lagMs
      }
      return {
        ...smoothness(picked),
        passes,
        recorded: picked.length,
        heldFrames: held,
        meanLagMs: picked.length ? Math.round((lagSum / picked.length) * 10) / 10 : null,
      }
    },
    /**
     * "heading" (padrão: atrás do carro, pela direção dele suavizada) ou
     * "track" (o rig antigo, pela pista, só para comparar). Sem argumento,
     * devolve o atual.
     */
    chaseRig(next?: ChaseRig) {
      if (next === "heading" || next === "track") setChaseRigMode(next)
      return chaseRigMode()
    },
    /**
     * Tremor da câmera de perseguição desde `traceReset()`
     * (`camera-jitter.ts`): `camera` = direção da câmera, `carOnScreen` =
     * ângulo do carro em relação ao eixo da câmera, ambos em graus/s.
     * `carHeading` é a mesma medida na direção desenhada do carro, como
     * referência: a média de ±0,25 s não acompanha toda a rotação real num S
     * rápido, então uma câmera lisa ainda lê ~1-2 graus/s ali (`camera-jitter.ts`).
     * `sRanges` como em `smoothness()`; `chaseRig` e `playback` filtram pelo
     * modo gravado em cada quadro. Também devolve o maior |carro fora do eixo|.
     */
    cameraJitter(opts: { sRanges?: [number, number][]; chaseRig?: ChaseRig; playback?: PlaybackMode } = {}) {
      const inRange = (sM: number | null) =>
        !opts.sRanges || (sM !== null && opts.sRanges.some(([a, b]) => sM >= a && sM < b))
      const yaw: AngleSample[] = []
      const off: AngleSample[] = []
      const heading: AngleSample[] = []
      let passes = 0
      let inside = false
      let maxOffRad = 0
      for (const t of trace) {
        const c = t.cam
        const keep =
          c !== null &&
          c.camera === "chase" &&
          inRange(t.sM) &&
          (!opts.chaseRig || c.rig === opts.chaseRig) &&
          (!opts.playback || t.mode === opts.playback)
        if (keep && !inside) passes++
        inside = keep
        if (!keep || !c) continue
        // Corte do rig, ressincronização ou outra passagem: trecho novo.
        const key = (c.cut * 1000 + t.resyncs) * 100_000 + passes
        yaw.push({ wallMs: t.wallMs, rad: c.yawRad, key })
        off.push({ wallMs: t.wallMs, rad: c.carOffRad, key })
        heading.push({ wallMs: t.wallMs, rad: t.headingRad, key })
        maxOffRad = Math.max(maxOffRad, Math.abs(c.carOffRad))
      }
      const r = (x: number) => Math.round(x * 1000) / 1000
      const pack = (j: ReturnType<typeof angleJitter>) => ({
        frames: j.frames,
        jitterDegS: r(j.jitterDegS),
        maxDegS: r(j.maxDegS),
        rateRmsDegS: r(j.rateRmsDegS),
      })
      return {
        passes,
        recorded: yaw.length,
        camera: pack(angleJitter(yaw)),
        carOnScreen: pack(angleJitter(off)),
        carHeading: pack(angleJitter(heading)),
        maxCarOffAxisDeg: r((maxOffRad * 180) / Math.PI),
      }
    },
    /**
     * Onde a sombra do carro seguido caiu no mapa de sombra do último quadro.
     * Lê o mapa (profundidade empacotada em RGBA) numa janela de ±4 m em
     * volta do carro, desprojeta cada texel com a câmera da sombra desse
     * quadro e fica com os pontos a mais de 0,15 m do chão e a até 4 m do
     * carro (a superfície do carro vista pelo sol). Devolve o centro deles no
     * referencial do carro desenhado no mesmo quadro (`alongM` à frente,
     * `leftM` à esquerda). Parado, é a forma do carro; uma sombra desenhada
     * com as matrizes do quadro anterior ficaria `v * dt` atrás disso.
     */
    shadowOffset() {
      const { gl, scene } = ctx.three()
      const light = scene.getObjectByName("sun") as DirectionalLight | undefined
      const map = light?.shadow.map
      const car = followedPose
      if (!light?.castShadow || !map || !car) return null
      const cam = light.shadow.camera
      const size = map.width
      const texel = (cam.right - cam.left) / size
      const p = new Vector3(car.x, 0.5, car.z).project(cam)
      const half = Math.ceil(4 / texel)
      const w = 2 * half
      const clampPx = (x: number) => Math.max(0, Math.min(size - w, x))
      const x0 = clampPx(Math.round(((p.x + 1) / 2) * size) - half)
      const y0 = clampPx(Math.round(((p.y + 1) / 2) * size) - half)
      const buf = new Uint8Array(w * w * 4)
      gl.readRenderTargetPixels(map, x0, y0, w, w, buf)
      let n = 0
      let along = 0
      let left = 0
      const q = new Vector3()
      for (let j = 0; j < w; j++)
        for (let i = 0; i < w; i++) {
          const k = (j * w + i) * 4
          // unpackRGBAToDepth do three.
          const d =
            (buf[k] / 255) * (255 / 256) +
            (buf[k + 1] / 255) * (255 / 65536) +
            (buf[k + 2] / 255) * (255 / 16777216) +
            buf[k + 3] / 255 / 16777216
          if (d >= 0.999999) continue
          q.set(((x0 + i + 0.5) / size) * 2 - 1, ((y0 + j + 0.5) / size) * 2 - 1, d * 2 - 1).unproject(cam)
          const dx = q.x - car.x
          const dz = q.z - car.z
          if (q.y < 0.15 || dx * dx + dz * dz > 16) continue
          along += dx * car.fx + dz * car.fz
          // Esquerda do carro vista de cima: a frente girada 90° (three: (fz, -fx)).
          left += dx * car.fz - dz * car.fx
          n++
        }
      const [a, b] = trace.slice(-2)
      const dt = a && b ? (b.wallMs - a.wallMs) / 1000 : 0
      const r3 = (x: number) => Math.round(x * 1000) / 1000
      return {
        points: n,
        alongM: n ? r3(along / n) : null,
        leftM: n ? r3(left / n) : null,
        texelM: r3(texel),
        frozen: liveFrozen(),
        speedMps: dt > 0 ? r3(Math.hypot(b.x - a.x, b.y - a.y) / dt) : null,
        frameMs: dt > 0 ? r3(dt * 1000) : null,
      }
    },
    state() {
      const { gl, scene } = ctx.three()
      const fog = scene.fog as { near?: number; far?: number } | null
      return {
        mode: ctx.mode,
        followed: ctx.followed,
        quality: ctx.quality,
        frozen: liveFrozen(),
        playback: playbackMode(),
        chaseRig: chaseRigMode(),
        renderer: (() => {
          const g = gl.getContext()
          const info = g.getExtension("WEBGL_debug_renderer_info")
          return info ? String(g.getParameter(info.UNMASKED_RENDERER_WEBGL)) : null
        })(),
        weather: weatherSnapshot(),
        environment: {
          fog: fog ? { near: Math.round(fog.near ?? 0), far: Math.round(fog.far ?? 0) } : null,
          exposure: gl.toneMappingExposure,
          softwareRendering: softwareRendering(),
          softwareProbeReleased: softwareProbeReleased(),
          shadowCasters: scene.getObjectsByProperty("castShadow", true).filter((o) => "isLight" in o).length,
        },
        memory: { ...gl.info.memory },
        programs: gl.info.programs?.length ?? 0,
        programNames: (gl.info.programs ?? []).map((p) => p.name),
        contextLost: gl.getContext().isContextLost(),
      }
    },
  }

  return {
    sink,
    install: () => {
      window.__race3d = api
      const stop = watchHistory()
      return () => {
        stop()
        if (window.__race3d === api) delete window.__race3d
      }
    },
  }
}
