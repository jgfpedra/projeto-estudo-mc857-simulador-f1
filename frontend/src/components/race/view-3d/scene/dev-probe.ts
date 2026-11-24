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
import type { Camera, InstancedMesh, WebGLRenderer } from "three"

import { interpolateCars } from "@/helpers/race-live"
import type { Frame } from "@/types/race"
import type { CameraMode } from "./camera-math"
import { frameAlpha } from "./live-pose"

type StoreView = { frame: Frame | null; prevFrame: Frame | null; frameAt: number; tickIntervalMs: number }

type Drawn = {
  now: number
  frame: Frame | null
  prevFrame: Frame | null
  frameAt: number
  tickIntervalMs: number
  cars: { driverId: string; x: number; y: number; pinTop: [number, number, number] | null }[]
}

export type ProbeSink = {
  record: (now: number, s: StoreView, body: InstancedMesh | null, pins: InstancedMesh, ids: string[]) => void
}

type Context = {
  /** `useThree((s) => s.get)`: estado atual do Canvas. */
  three: () => { gl: WebGLRenderer; camera: Camera }
  mode: CameraMode
  followed: string | null
  colors: Map<string, string>
}

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
        last = { now, frame: s.frame, prevFrame: s.prevFrame, frameAt: s.frameAt, tickIntervalMs: s.tickIntervalMs, cars: [] }
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
        cars.push({ driverId, x, y, pinTop: k > 0 ? [v.x, v.y + 2.4 * k * 0.8, v.z] : null })
      })
      last = { now, frame: s.frame, prevFrame: s.prevFrame, frameAt: s.frameAt, tickIntervalMs: s.tickIntervalMs, cars }
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
      }))
    },
    state() {
      const gl = ctx.three().gl
      return {
        mode: ctx.mode,
        followed: ctx.followed,
        memory: { ...gl.info.memory },
        programs: gl.info.programs?.length ?? 0,
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
