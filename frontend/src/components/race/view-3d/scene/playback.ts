/**
 * Reprodução com buffer para o 3D.
 *
 * O 2D desenha na borda ao vivo: `prevFrame -> frame`, com `alpha` medido
 * desde a chegada do último tick. Como os ticks chegam com 87-112 ms de
 * intervalo mesmo no localhost, o carro para quando um tick atrasa (`alpha`
 * preso em 1) e salta quando um tick adianta; na perseguição isso vira
 * tremedeira nas curvas.
 *
 * Aqui os frames ficam num buffer (os últimos ~3 s, por `simTs`) e o 3D
 * desenha um instante de simulação `t` que fica ~150 ms atrás do frame mais
 * novo. `t` avança pelo tempo de parede, vezes a taxa da simulação (tempo de
 * simulação por tempo de parede, estimada pelos próprios frames), com um
 * ajuste de no máximo +-5% para manter o atraso. Sem extrapolação: se `t`
 * alcança o frame mais novo, ele para ali até chegar outro. Ressincroniza na
 * hora (sem ajuste suave) depois de um snapshot ou reconexão, de um salto no
 * tempo de simulação, ou se ficar mais de 1 s atrás.
 *
 * Puro (sem React, sem three, sem store) para ser testado com `node --test`.
 */
import type { Frame } from "@/types/race"

export const PLAYBACK = {
  /** Atraso médio alvo atrás do frame mais novo, ms de parede. */
  delayMs: 150,
  /** Janela de frames guardada, s de simulação. */
  bufferS: 3,
  /** Ajuste máximo da taxa para manter o atraso. */
  maxNudge: 0.05,
  /** Ganho do ajuste: erro relativo do atraso -> fração da taxa. */
  gain: 0.15,
  /** Constante de tempo da média do atraso, s. */
  lagTauS: 0.5,
  /** Atrás disso (ms de parede) ressincroniza em vez de ajustar. */
  resyncLagMs: 1000,
  /** Salto entre frames consecutivos (s de simulação) tratado como ressincronização. */
  maxGapS: 1,
  /** Peso de cada nova estimativa da taxa da simulação. */
  rateBlend: 0.3,
  /** Janela da estimativa da taxa, s de simulação. */
  rateWindowS: 20,
  /** Abaixo disso de janela (s de simulação), a taxa fica como estava (1 no início). */
  rateMinSpanS: 2,
  /** Uma pausa maior que esta entre chegadas (ms) recomeça a janela da taxa. */
  ratePauseMs: 500,
  /** Chegadas a menos disto da anterior (ms) são um lote e não entram na taxa. */
  rateBunchMs: 30,
} as const

export type PlaybackSample = {
  /** Frame anterior a `t` (nulo se só há um frame). */
  prev: Frame | null
  /** Frame seguinte a `t` (ou o mais novo, parado). */
  cur: Frame
  /** Fração de `prev` a `cur`, 0..1. */
  alpha: number
  /** Instante de simulação desenhado, s. */
  simTs: number
  /** `t` alcançou o frame mais novo e está parado nele. */
  held: boolean
  /** Conta as ressincronizações; muda quando o 3D deve cortar a câmera. */
  resyncs: number
  /** Atraso atrás do frame mais novo, ms de parede. */
  lagMs: number
  /** Taxa usada neste quadro (tempo de simulação por tempo de parede, já com o ajuste). */
  rate: number
}

type Entry = { frame: Frame; at: number }
type Pacing = { ts: number; at: number }

export class PlaybackClock {
  private entries: Entry[] = []
  /** (simTs, chegada) dos últimos ~20 s, para a taxa da simulação. */
  private pacing: Pacing[] = []
  private lastArrival: number | null = null
  /** Instante de simulação desenhado, s. */
  private t: number | null = null
  private lastWall: number | null = null
  /** Tempo de simulação por tempo de parede (1 em tempo real). */
  private simRate = 1
  /** Atraso médio atrás do frame mais novo, s de parede. */
  private lagAvg: number = PLAYBACK.delayMs / 1000
  private resyncCount = 0
  private held = false

  /** Esquece tudo (outra corrida, ou a store sem frame). */
  clear(): void {
    this.entries = []
    this.pacing = []
    this.lastArrival = null
    this.t = null
    this.lastWall = null
  }

  /**
   * Frame novo, chegado em `wallMs` (`performance.now()`). Mesmo `simTs` do
   * frame mais novo o substitui (ex.: mudança de clima, ou um snapshot do
   * mesmo instante). `resync` vem de um snapshot (a store zera `prevFrame`):
   * descarta o buffer.
   */
  push(frame: Frame, wallMs: number, resync = false): void {
    const newest = this.entries.at(-1)
    if (newest && frame.simTs === newest.frame.simTs) {
      newest.frame = frame
      return
    }
    const backwards = newest !== undefined && frame.simTs < newest.frame.simTs
    const gap = newest !== undefined && frame.simTs - newest.frame.simTs > PLAYBACK.maxGapS
    if (resync || backwards || gap || this.t === null) {
      this.entries = [{ frame, at: wallMs }]
      this.pacing = []
      this.trackPacing(frame.simTs, wallMs)
      this.restart()
      return
    }
    this.entries.push({ frame, at: wallMs })
    const keepFrom = frame.simTs - PLAYBACK.bufferS
    while (this.entries.length > 2 && this.entries[1].frame.simTs <= keepFrom) this.entries.shift()
    this.trackPacing(frame.simTs, wallMs)
    this.estimateRate()
  }

  /** Avança `t` até `wallMs` e devolve o par de frames e o `alpha` a desenhar. */
  sample(wallMs: number): PlaybackSample | null {
    const newest = this.entries.at(-1)
    if (!newest || this.t === null) return null
    const newestTs = newest.frame.simTs
    // Primeiro quadro desde que o relógio começou: parte do atraso alvo atrás do mais novo. Os
    // frames chegam desde a montagem, mas a cena pode levar quase 1 s para carregar (modelos,
    // shaders); sem isso o 3D começava esse tempo atrás e voltava a +5%, devagar.
    const first = this.lastWall === null
    let dt = this.lastWall === null ? 0 : Math.max(0, (wallMs - this.lastWall) / 1000)
    this.lastWall = wallMs

    const target = PLAYBACK.delayMs / 1000
    if (first || ((newestTs - this.t) / this.simRate) * 1000 > PLAYBACK.resyncLagMs) {
      this.restart()
      dt = 0
    }
    const nudge = Math.min(
      PLAYBACK.maxNudge,
      Math.max(-PLAYBACK.maxNudge, (PLAYBACK.gain * (this.lagAvg - target)) / target),
    )
    const rate = this.simRate * (1 + nudge)
    let t = (this.t as number) + dt * rate
    this.held = t >= newestTs
    if (this.held) t = newestTs
    this.t = t
    const lag = (newestTs - t) / this.simRate
    this.lagAvg += (lag - this.lagAvg) * (1 - Math.exp(-dt / PLAYBACK.lagTauS))

    return { ...this.bracket(t), simTs: t, held: this.held, resyncs: this.resyncCount, lagMs: lag * 1000, rate }
  }

  /** Taxa da simulação estimada (tempo de simulação por tempo de parede). */
  get rate(): number {
    return this.simRate
  }

  private restart(): void {
    const newest = this.entries.at(-1)
    if (!newest) return
    // Atrás do mais novo pelo atraso alvo; até chegarem frames anteriores, `bracket` segura no mais antigo.
    this.t = newest.frame.simTs - (PLAYBACK.delayMs / 1000) * this.simRate
    this.lagAvg = PLAYBACK.delayMs / 1000
    this.resyncCount++
  }

  private bracket(t: number): { prev: Frame | null; cur: Frame; alpha: number } {
    const e = this.entries
    if (e.length === 1 || t <= e[0].frame.simTs) return { prev: null, cur: e[0].frame, alpha: 1 }
    for (let i = e.length - 1; i > 0; i--) {
      const a = e[i - 1].frame
      if (t >= a.simTs) {
        const b = e[i].frame
        const span = b.simTs - a.simTs
        return { prev: a, cur: b, alpha: span > 0 ? Math.min(1, (t - a.simTs) / span) : 1 }
      }
    }
    return { prev: null, cur: e[0].frame, alpha: 1 }
  }

  /**
   * Taxa da simulação pelo contorno inferior das chegadas. Atrasos (rede,
   * página ocupada) só empurram uma chegada para depois, nunca para antes;
   * então, em cada ponta da janela, a chegada mais adiantada em relação ao
   * seu `simTs` dá o ritmo real. Um mínimos-quadrados sobre todas as chegadas
   * lia o lote de ticks entregue depois de uma parada da página (ao montar o
   * 3D, por exemplo) como simulação acelerada, e o 3D alcançava o frame mais
   * novo e ficava parado nele por segundos. A janela recomeça numa pausa de
   * mais de 0,5 s entre chegadas (pode ser a engine parada, que muda a
   * relação entre `simTs` e chegada); a primeira chegada depois da pausa e as
   * que vêm a menos de 30 ms da anterior (um lote) não entram: a hora delas é
   * a de quando a página ficou livre, não a do tick.
   */
  private estimateRate(): void {
    const p = this.pacing
    const span = p.length > 1 ? p[p.length - 1].ts - p[0].ts : 0
    if (span < PLAYBACK.rateMinSpanS) return
    const quarter = span / 4
    const early = (x: Pacing) => x.at / 1000 - x.ts
    let a = p[0]
    let b = p[p.length - 1]
    for (const x of p) {
      if (x.ts <= p[0].ts + quarter && early(x) < early(a)) a = x
      if (x.ts >= p[p.length - 1].ts - quarter && early(x) < early(b)) b = x
    }
    const wall = (b.at - a.at) / 1000
    if (!(wall > 0) || b.ts - a.ts < quarter) return
    const est = Math.min(4, Math.max(0.25, (b.ts - a.ts) / wall))
    this.simRate += (est - this.simRate) * PLAYBACK.rateBlend
  }

  private trackPacing(ts: number, at: number): void {
    const last = this.lastArrival
    this.lastArrival = at
    if (last !== null && at - last > PLAYBACK.ratePauseMs) {
      this.pacing = []
      return
    }
    if (last !== null && at - last < PLAYBACK.rateBunchMs) return
    this.pacing.push({ ts, at })
    while (this.pacing.length > 2 && this.pacing[0].ts < ts - PLAYBACK.rateWindowS) this.pacing.shift()
  }
}
