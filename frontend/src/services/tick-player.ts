import type { Tick } from "@/types/race"

type Listener = () => void

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v))

/**
 * Relógio da reprodução, fora do React.
 * - O D3 se inscreve em `subscribeFrame` (a cada frame).
 * - O React se inscreve em `subscribeState` (play, pause, seek, velocidade).
 * Ao vivo, basta chamar `push` com cada tick recebido pelo websocket.
 */
class TickPlayer {
  ticks: Tick[] = []
  hz = 2
  time = 0
  speed = 1
  playing = false

  private raf: number | null = null
  private last = 0
  private frameListeners = new Set<Listener>()
  private stateListeners = new Set<Listener>()

  get duration(): number {
    return this.ticks.length > 1 ? (this.ticks.length - 1) / this.hz : 0
  }

  load(ticks: Tick[], hz: number) {
    this.pause()
    this.ticks = ticks
    this.hz = hz
    this.time = 0
    this.emitFrame()
    this.emitState()
  }

  push(tick: Tick) {
    this.ticks.push(tick)
    this.emitState()
  }

  play() {
    if (this.playing || this.ticks.length < 2) return
    if (this.time >= this.duration) this.time = 0
    this.playing = true
    this.last = performance.now()
    this.raf = requestAnimationFrame(this.loop)
    this.emitState()
  }

  pause() {
    this.playing = false
    if (this.raf !== null) cancelAnimationFrame(this.raf)
    this.raf = null
    this.emitState()
  }

  toggle() {
    if (this.playing) this.pause()
    else this.play()
  }

  seek(t: number) {
    this.time = clamp(t, 0, this.duration)
    this.last = performance.now()
    this.emitFrame()
  }

  setSpeed(speed: number) {
    this.speed = speed
    this.emitState()
  }

  subscribeFrame(listener: Listener): () => void {
    this.frameListeners.add(listener)
    return () => {
      this.frameListeners.delete(listener)
    }
  }

  subscribeState(listener: Listener): () => void {
    this.stateListeners.add(listener)
    return () => {
      this.stateListeners.delete(listener)
    }
  }

  private loop = (now: number) => {
    const dt = Math.min((now - this.last) / 1000, 0.25)
    this.last = now
    this.time = Math.min(this.duration, this.time + dt * this.speed)
    this.emitFrame()

    if (this.time >= this.duration) this.pause()
    else this.raf = requestAnimationFrame(this.loop)
  }

  private emitFrame() {
    this.frameListeners.forEach((listener) => listener())
  }

  private emitState() {
    this.stateListeners.forEach((listener) => listener())
  }
}

export const tickPlayer = new TickPlayer()