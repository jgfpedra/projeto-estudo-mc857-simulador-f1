import { create } from "zustand"

import { detectOvertakes, TRACK_STATUS_LABEL, weatherLabel } from "@/helpers/race-live"
import { api, raceSocketUrl } from "@/services/api"
import { parseLiveMessage } from "@/services/race-parser"
import { openRaceSocket } from "@/services/race-socket"
import type {
  FeedItem,
  FinalEntry,
  Frame,
  LiveMessage,
  RaceInfo,
  Tone,
  TrackStatus,
  ViewMode,
} from "@/types/race"

const FEED_LIMIT = 200
const MAX_RECONNECTS = 5
/** Tempo de simulação em que a mesma ultrapassagem não é contada de novo. */
const PASS_DEDUP_S = 5

export type LiveStatus = "idle" | "loading" | "live" | "reconnecting" | "finished" | "error"

type LiveRaceState = {
  status: LiveStatus
  error: string | null
  raceId: string | null
  race: RaceInfo | null
  frame: Frame | null
  prevFrame: Frame | null
  /** performance.now() de quando o frame atual chegou. */
  frameAt: number
  /** Intervalo medido entre ticks, em ms. */
  tickIntervalMs: number
  trackStatus: TrackStatus
  feed: FeedItem[]
  classification: FinalEntry[] | null
  selectedDriverId: string | null
  viewMode: ViewMode
  load: (raceId: string) => Promise<void>
  disconnect: () => void
  selectDriver: (driverId: string | null) => void
  setViewMode: (mode: ViewMode) => void
}

const TRACK_TONE: Record<TrackStatus, Tone> = {
  GREEN: "success",
  YELLOW: "warn",
  SAFETY_CAR: "warn",
  VSC: "warn",
  RED_FLAG: "danger",
}

let session = 0
let feedSeq = 0
/** Tentativas de reconexão desde a última conexão bem-sucedida. */
let attempts = 0
let socketClose: (() => void) | null = null
let reconnectTimer: number | null = null
const lastPass = new Map<string, number>()

/** Estado da corrida. Não inclui a seleção nem o modo de visualização, que são escolhas do usuário. */
function freshRaceState() {
  return {
    error: null as string | null,
    race: null as RaceInfo | null,
    frame: null as Frame | null,
    prevFrame: null as Frame | null,
    frameAt: 0,
    tickIntervalMs: 100,
    trackStatus: "GREEN" as TrackStatus,
    feed: [] as FeedItem[],
    classification: null as FinalEntry[] | null,
  }
}

export const useLiveRaceStore = create<LiveRaceState>()((set, get) => {
  const nameOf = (driverId: string): string => {
    const driver = get().race?.drivers.find((d) => d.driverId === driverId)
    return driver?.abbreviation ?? driverId
  }

  const pushFeed = (item: Omit<FeedItem, "id">) => {
    set((s) => ({
      feed: [...s.feed, { ...item, id: ++feedSeq }].slice(-FEED_LIMIT),
    }))
  }

  const resync = async (raceId: string, current: number) => {
    try {
      const snap = await api.getSnapshot(raceId)
      if (current !== session) return
      if (snap.lastFrame) set({ frame: snap.lastFrame, prevFrame: null, frameAt: performance.now() })
      if (snap.status === "finished") {
        set({ status: "finished", classification: snap.classification })
      }
    } catch {
      // Se falhar, a próxima reconexão ressincroniza de novo.
    }
  }

  const apply = (msg: LiveMessage) => {
    switch (msg.kind) {
      case "tick": {
        const now = performance.now()
        const { frame: prev, frameAt, tickIntervalMs } = get()
        const measured = frameAt > 0 ? now - frameAt : 0
        const interval =
          measured > 0 && measured < 1000 ? 0.8 * tickIntervalMs + 0.2 * measured : tickIntervalMs

        for (const o of detectOvertakes(prev, msg.frame)) {
          const key = `${o.passerId}>${o.passedId}`
          const last = lastPass.get(key)
          if (last !== undefined && msg.frame.simTs - last < PASS_DEDUP_S) continue
          lastPass.set(key, msg.frame.simTs)
          pushFeed({
            simTs: msg.frame.simTs,
            lap: msg.frame.lap,
            kind: "overtake",
            tone: "info",
            driverIds: [o.passerId, o.passedId],
            message: `${nameOf(o.passerId)} ultrapassa ${nameOf(o.passedId)} por P${o.position}`,
          })
        }

        set({ prevFrame: prev, frame: msg.frame, frameAt: now, tickIntervalMs: interval })
        return
      }

      case "race_control":
        set({ trackStatus: msg.status })
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "race_control",
          tone: TRACK_TONE[msg.status],
          driverIds: [],
          message: msg.message || TRACK_STATUS_LABEL[msg.status],
        })
        return

      case "pit_stop":
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "pit_stop",
          tone: "warn",
          driverIds: [msg.driverId],
          message: `${nameOf(msg.driverId)} entra nos boxes e monta ${msg.newCompound.toLowerCase()}`,
        })
        return

      case "tyre_worn":
        pushFeed({
          simTs: msg.simTs,
          lap: get().frame?.lap ?? 0,
          kind: "tyre_worn",
          tone: "warn",
          driverIds: [msg.driverId],
          message: `${nameOf(msg.driverId)}: pneu ${msg.compound.toLowerCase()} com ${Math.round(msg.tyreLifePct)}% de vida`,
        })
        return

      case "weather_changed":
        set((s) => ({ frame: s.frame ? { ...s.frame, weather: msg.weather } : s.frame }))
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "weather",
          tone: "info",
          driverIds: [],
          message: `Clima mudou: ${weatherLabel(msg.weather.kind)}`,
        })
        return

      case "collision":
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "collision",
          tone: "danger",
          driverIds: [msg.driverAId, msg.driverBId],
          message: `Contato entre ${nameOf(msg.driverAId)} e ${nameOf(msg.driverBId)}`,
        })
        return

      case "race_end":
        set({ status: "finished", classification: msg.classification })
        pushFeed({
          simTs: msg.simTs,
          lap: get().frame?.lap ?? 0,
          kind: "finish",
          tone: "success",
          driverIds: [],
          message: "Corrida finalizada",
        })
        return
    }
  }

  const openFeed = (raceId: string, current: number) => {
    socketClose = openRaceSocket(raceSocketUrl(`/ws/races/${raceId}`), {
      onOpen: () => {
        if (current !== session) return
        const recovering = attempts > 0
        attempts = 0
        set({ status: "live", error: null })
        // Depois de reconectar, o servidor só manda ticks novos: busca o estado atual pelo snapshot.
        if (recovering) void resync(raceId, current)
      },

      onMessage: (raw) => {
        if (current !== session) return
        const msg = parseLiveMessage(raw)
        if (msg) apply(msg)
      },

      onClose: (code) => {
        if (current !== session || get().status === "finished") return

        if (code === 4404) {
          set({ status: "error", error: "Corrida não encontrada no simulador." })
          return
        }

        if (attempts >= MAX_RECONNECTS) {
          set({ status: "error", error: "Conexão com o simulador perdida." })
          return
        }

        attempts += 1
        set({ status: "reconnecting" })
        reconnectTimer = window.setTimeout(
          () => openFeed(raceId, current),
          1000 * 2 ** (attempts - 1),
        )
      },
    })
  }

  return {
    status: "idle",
    ...freshRaceState(),
    raceId: null,
    selectedDriverId: null,
    viewMode: "2d",

    load: async (raceId) => {
      get().disconnect()
      const current = session
      attempts = 0
      feedSeq = 0
      lastPass.clear()

      set({ ...freshRaceState(), status: "loading", raceId, selectedDriverId: null })

      try {
        const [race, snap] = await Promise.all([api.getRace(raceId), api.getSnapshot(raceId)])
        if (current !== session) return

        set({
          race,
          frame: snap.lastFrame,
          frameAt: performance.now(),
          classification: snap.classification,
          status: snap.status === "finished" ? "finished" : "loading",
        })

        if (snap.status === "running") openFeed(raceId, current)
      } catch (error) {
        if (current === session) {
          set({
            status: "error",
            error: error instanceof Error ? error.message : "Não foi possível carregar a corrida.",
          })
        }
      }
    },

    disconnect: () => {
      session++
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      socketClose?.()
      socketClose = null
    },

    selectDriver: (driverId) => set({ selectedDriverId: driverId }),

    setViewMode: (mode) => set({ viewMode: mode }),
  }
})
