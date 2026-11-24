/**
 * Gancho só de desenvolvimento para a verificação headless (Playwright).
 *
 * Expõe `window.__race3d` enquanto o 3D está montado. `sample()` devolve as
 * posições que o 3D *desenhou* (lidas da matriz de instância que vai para a
 * GPU, não recalculadas) e as posições 2D para o mesmo `performance.now()`,
 * calculadas por `interpolateCars` com a fórmula de `alpha` de `track-2d.tsx`.
 * Em produção `import.meta.env.DEV` é falso e nada disso é instalado.
 */
import { Matrix4, Vector3 } from "three"
import type { Camera, InstancedMesh, MeshBasicMaterial, Scene, WebGLRenderer } from "three"

import { interpolateCars } from "@/helpers/race-live"
import type { Frame } from "@/types/race"
import type { CameraMode } from "./camera-math"
import { softwareProbeReleased, softwareRendering } from "./environment/quality"
import type { Quality } from "./environment/quality"
import type { ViewPose } from "./environment/views"
import { freezeLive, liveFrozen, unfreezeLive } from "./live-clock"
import { frameAlpha } from "./live-pose"

type StoreView = { frame: Frame | null; prevFrame: Frame | null; frameAt: number; tickIntervalMs: number }

type Drawn = {
  now: number
  frame: Frame | null
  prevFrame: Frame | null
  frameAt: number
  tickIntervalMs: number
  cars: { driverId: string; x: number; y: number; pinTop: [number, number, number] | null; pinScale: number }[]
  /** Opacidade dos marcadores neste quadro (0 = escondidos). */
  pinOpacity: number
}

export type ProbeSink = {
  record: (now: number, s: StoreView, body: InstancedMesh | null, pins: InstancedMesh, ids: string[]) => void
}

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

export function createProbe(ctx: Context): { sink: ProbeSink; install: () => () => void } {
  let last: Drawn | null = null
  const m = new Matrix4()
  const v = new Vector3()

  const sink: ProbeSink = {
    record(now, s, body, pins, ids) {
      if (!body || !s.frame) {
        last = { now, frame: s.frame, prevFrame: s.prevFrame, frameAt: s.frameAt, tickIntervalMs: s.tickIntervalMs, cars: [], pinOpacity: 0 }
        return
      }
      const present = new Set(s.frame.cars.map((c) => c.driverId))
      const cars: Drawn["cars"] = []
      ids.forEach((driverId, i) => {
        if (!present.has(driverId)) return
        body.getMatrixAt(i, m)
        v.setFromMatrixPosition(m)
        const x = v.x
        const y = -v.z
        pins.getMatrixAt(i, m)
        const k = m.elements[5]
        v.setFromMatrixPosition(m)
        cars.push({ driverId, x, y, pinTop: k > 0 ? [v.x, v.y + 2.4 * k * 0.8, v.z] : null, pinScale: k })
      })
      const pinOpacity = pins.visible ? (pins.material as MeshBasicMaterial).opacity : 0
      last = { now, frame: s.frame, prevFrame: s.prevFrame, frameAt: s.frameAt, tickIntervalMs: s.tickIntervalMs, cars, pinOpacity }
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
    /** 3D desenhado vs 2D no mesmo `performance.now()` do último quadro. */
    sample() {
      if (!last || !last.frame) return null
      const alpha = frameAlpha(last.now, last.frameAt, last.tickIntervalMs)
      const twoD = interpolateCars(last.prevFrame, last.frame, alpha)
      let maxErrorM = 0
      const cars = last.cars.map((c) => {
        const p = twoD.get(c.driverId)
        const err = p ? Math.hypot(p.x - c.x, p.y - c.y) : Infinity
        maxErrorM = Math.max(maxErrorM, err)
        return { driverId: c.driverId, x3d: c.x, y3d: c.y, x2d: p?.x ?? null, y2d: p?.y ?? null, errorM: err }
      })
      return { now: last.now, simTs: last.frame.simTs, alpha, drivers: last.frame.cars.length, cars, maxErrorM }
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
    state() {
      const { gl, scene } = ctx.three()
      const fog = scene.fog as { near?: number; far?: number } | null
      return {
        mode: ctx.mode,
        followed: ctx.followed,
        quality: ctx.quality,
        frozen: liveFrozen(),
        renderer: (() => {
          const g = gl.getContext()
          const info = g.getExtension("WEBGL_debug_renderer_info")
          return info ? String(g.getParameter(info.UNMASKED_RENDERER_WEBGL)) : null
        })(),
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
      return () => {
        if (window.__race3d === api) delete window.__race3d
      }
    },
  }
}
