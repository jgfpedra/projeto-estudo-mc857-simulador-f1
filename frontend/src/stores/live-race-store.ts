import { create } from "zustand"

import { detectOvertakes, TRACK_STATUS_LABEL, weatherLabel } from "@/helpers/race-live"
import { api, raceSocketUrl } from "@/services/api"
import { parseLiveMessage } from "@/services/race-parser"
import { openRaceSocket } from "@/services/race-socket"
import type {
  AiCommand,
  AiSuggestion,
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
const RACE_CANCELLED_MESSAGE = "Corrida encerrada por falta de espectadores."
/** Tempo de simulação em que a mesma ultrapassagem não é contada de novo. */
const PASS_DEDUP_S = 5

export type PitTyre = "soft" | "medium" | "hard" | "intermediate" | "wet"

/** syncing: socket reconectado, aguardando a simulação voltar a andar. */
export type LiveStatus = "idle" | "loading" | "live" | "reconnecting" | "syncing" | "finished" | "error"

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
  followedDriverId: string | null
  viewMode: ViewMode
  pitBusy: boolean
  pitError: string | null
  /** true logo após a corrida ser retomada, por alguns segundos. */
  justResumed: boolean
  /** Histórico de sugestões do engenheiro de IA (máx 50). */
  aiSuggestions: AiSuggestion[]
  /** Comando ativo do engenheiro de IA por driverId. */
  aiCommands: Map<string, AiCommand>
  // Estado do ciclo de vida do AiEngineer
  aiEngineerStatus: "idle" | "started" | "monitoring" | "stopped" | "error"
  aiEngineerStats: Record<string, unknown> | null
  aiEngineerError: string | null
  requestPit: (driverId: string, tyre: PitTyre) => Promise<void>
  cancelPit: (driverId: string) => Promise<void>
  load: (raceId: string) => Promise<void>
  disconnect: () => void
  selectDriver: (driverId: string | null) => void
  followDriver: (driverId: string) => void
  unfollowDriver: () => void
  setViewMode: (mode: ViewMode) => void
}

const TRACK_TONE: Record<TrackStatus, Tone> = {
  GREEN: "success",
  YELLOW: "warn",
  SAFETY_CAR: "warn",
  VSC: "warn",
  RED_FLAG: "danger",
}

const MAX_AI_SUGGESTIONS = 50

let session = 0
let feedSeq = 0
/** Tentativas de reconexão desde a última conexão bem-sucedida. */
let attempts = 0
let socketClose: (() => void) | null = null
let reconnectTimer: number | null = null
let syncTimer: number | null = null
let resumedTimer: number | null = null
/** true enquanto uma reconexão está em curso (até a simulação confirmar que voltou). */
let recovering = false
/** sim_ts do primeiro tick recebido após reconectar; a confirmação exige um tick com tempo maior. */
let syncBaseSimTs: number | null = null
const SYNC_TIMEOUT_MS = 20_000
const RESUMED_BANNER_MS = 4000
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
    aiSuggestions: [] as AiSuggestion[],
    aiCommands: new Map<string, AiCommand>(),
    // Estado do ciclo de vida do AiEngineer
    aiEngineerStatus: "idle" as "idle" | "started" | "monitoring" | "stopped" | "error",
    aiEngineerStats: null as Record<string, unknown> | null,
    aiEngineerError: null as string | null,
    justResumed: false,
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
        recovering = false
        clearSyncTimer()
        set({ status: "finished", classification: snap.classification })
      } else if (snap.status === "cancelled") {
        recovering = false
        clearSyncTimer()
        set({ status: "error", error: RACE_CANCELLED_MESSAGE })
      }
    } catch {
      // Se falhar, a próxima reconexão ressincroniza de novo.
    }
  }

  const clearSyncTimer = () => {
    if (syncTimer !== null) {
      window.clearTimeout(syncTimer)
      syncTimer = null
    }
  }

  /** Marca a corrida como ao vivo. `resumed` indica que ela voltou depois de uma falha. */
  const confirmLive = (resumed: boolean) => {
    recovering = false
    attempts = 0
    syncBaseSimTs = null
    clearSyncTimer()
    if (resumedTimer !== null) window.clearTimeout(resumedTimer)
    resumedTimer = null
    set({ status: "live", error: null, justResumed: resumed })
    if (resumed) {
      resumedTimer = window.setTimeout(() => {
        resumedTimer = null
        set({ justResumed: false })
      }, RESUMED_BANNER_MS)
    }
  }

  const scheduleReconnect = (raceId: string, current: number) => {
    if (current !== session) return
    if (attempts >= MAX_RECONNECTS) {
      recovering = false
      set({ status: "error", error: "Conexão com o simulador perdida. Tente novamente." })
      return
    }
    attempts += 1
    recovering = true
    syncBaseSimTs = null
    set({ status: "reconnecting" })
    reconnectTimer = window.setTimeout(() => openFeed(raceId, current), 1000 * 2 ** (attempts - 1))
  }

  /** Se a simulação não voltar a andar a tempo, a tentativa conta como falha e reconecta. */
  const armSyncTimer = (raceId: string, current: number) => {
    clearSyncTimer()
    syncTimer = window.setTimeout(() => {
      syncTimer = null
      if (current !== session || get().status !== "syncing") return
      socketClose?.()
      socketClose = null
      scheduleReconnect(raceId, current)
    }, SYNC_TIMEOUT_MS)
  }

  const apply = (msg: LiveMessage) => {
    // Validar raceId para eventos que o carregam (previne eventos órfãos/stale)
    const currentRaceId = get().raceId
    if (currentRaceId && 'raceId' in msg && msg.raceId !== currentRaceId) {
      console.warn('[live-store] Evento de race_id diferente ignorado:', msg.raceId, 'esperado:', currentRaceId, 'kind:', msg.kind)
      return
    }

    switch (msg.kind) {
      case "tick": {
        const now = performance.now()
        const { frame: prev, frameAt, tickIntervalMs } = get()
        const measured = frameAt > 0 ? now - frameAt : 0
        const interval =
          measured > 0 && measured < 1000 ? 0.8 * tickIntervalMs + 0.2 * measured : tickIntervalMs

        const status = get().status
        if (status === "loading") {
          confirmLive(false)
        } else if (status === "syncing") {
          if (syncBaseSimTs === null) syncBaseSimTs = msg.frame.simTs
          else if (msg.frame.simTs > syncBaseSimTs) confirmLive(true)
        }

        const rewound = prev !== null && msg.frame.simTs < prev.simTs
        if (rewound) lastPass.clear()
        for (const o of detectOvertakes(rewound ? null : prev, msg.frame)) {
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

        set({ prevFrame: rewound ? null : prev, frame: msg.frame, frameAt: now, tickIntervalMs: interval })
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

      case "pit_requested":
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "pit_request",
          tone: "info",
          driverIds: [msg.driverId],
          message: `${nameOf(msg.driverId)} pede ${msg.tyreCompound.toLowerCase()} na próxima entrada dos boxes`,
        })
        return

      case "pit_cancelled":
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "pit_request",
          tone: "info",
          driverIds: [msg.driverId],
          message: `${nameOf(msg.driverId)} cancelou o pedido de box`,
        })
        return

      case "pit_cancel_rejected":
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "pit_request",
          tone: "warn",
          driverIds: [msg.driverId],
          message: `${nameOf(msg.driverId)}: cancelamento recusado, o carro já está na via dos boxes`,
        })
        return

      case "ai_suggestion": {
        set((s) => ({
          aiSuggestions: [...s.aiSuggestions, {
            simTs: msg.simTs,
            lap: msg.lap,
            driverId: msg.driverId,
            message: msg.message,
            urgency: msg.urgency,
            command: msg.command,
          }].slice(-MAX_AI_SUGGESTIONS),
        }))
        // Push to event feed as well
        const urgencyLabel = msg.urgency === "alta" ? "🔴" : msg.urgency === "media" ? "🟡" : "🟢"
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "pit_request", // reuse kind for feed display
          tone: msg.urgency === "alta" ? "danger" : msg.urgency === "media" ? "warn" : "info",
          driverIds: [msg.driverId],
          message: `${urgencyLabel} Engenheiro (${nameOf(msg.driverId)}): ${msg.message}`,
        })
        return
      }

      case "ai_command": {
        set((s) => {
          const newCommands = new Map(s.aiCommands)
          newCommands.set(msg.driverId, {
            simTs: msg.simTs,
            lap: msg.lap,
            driverId: msg.driverId,
            command: msg.command,
            value: msg.value,
            reason: msg.reason,
            issuedBy: msg.issuedBy,
          })
          return { aiCommands: newCommands }
        })
        pushFeed({
          simTs: msg.simTs,
          lap: msg.lap,
          kind: "pit_request",
          tone: "info",
          driverIds: [msg.driverId],
          message: `⚡ Comando IA (${nameOf(msg.driverId)}): ${msg.command.toUpperCase()} — ${msg.reason}`,
        })
        return
      }

      case "race_recovered":
        if (get().status === "finished") return
        // Outra réplica restaurou a corrida a partir do checkpoint: o tempo pode voltar para trás.
        lastPass.clear()
        set({ prevFrame: null })
        confirmLive(true)
        pushFeed({
          simTs: msg.simTs,
          lap: get().frame?.lap ?? 0,
          kind: "race_control",
          tone: "success",
          driverIds: [],
          message: "Corrida retomada após falha no servidor",
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

      case "race_recovered":
        // Corrida foi recuperada no backend (HA). O snapshot já será buscado via resync() no onOpen.
        // Apenas garantimos que o status volte para "live" para a UI sair do estado "reconnecting".
        set({ status: "live" })
        return

      case "ai_started": {
        set({
          aiEngineerStatus: "started",
          aiEngineerStats: {
            totalLaps: msg.totalLaps,
            userDriverId: msg.userDriverId,
            numDrivers: msg.numDrivers,
            decisionIntervalS: msg.decisionIntervalS,
          },
          aiEngineerError: null,
        })
        pushFeed({
          simTs: msg.simTs,
          lap: 0,
          kind: "pit_request",
          tone: "info",
          driverIds: [],
          message: `🤖 Engenheiro de IA iniciado — monitorando ${msg.numDrivers} pilotos`,
        })
        return
      }

      case "ai_monitoring": {
        set({
          aiEngineerStatus: "monitoring",
          aiEngineerStats: msg.stats,
        })
        // Não adiciona ao feed - é apenas heartbeat interno
        return
      }

      case "ai_stopped": {
        set({
          aiEngineerStatus: "stopped",
          aiEngineerStats: msg.stats,
        })
        pushFeed({
          simTs: msg.simTs,
          lap: get().frame?.lap ?? 0,
          kind: "pit_request",
          tone: msg.reason === "error" ? "danger" : "info",
          driverIds: [],
          message: `🤖 Engenheiro de IA finalizado (${msg.reason})`,
        })
        return
      }

      case "ai_error": {
        set({
          aiEngineerStatus: "error",
          aiEngineerError: `${msg.errorType}: ${msg.error}`,
        })
        pushFeed({
          simTs: msg.simTs,
          lap: msg.cycle,
          kind: "pit_request",
          tone: "warn",
          driverIds: msg.driverId ? [msg.driverId] : [],
          message: `⚠️ Erro no Engenheiro IA: ${msg.error}`,
        })
        return
      }
    }
  }

  const openFeed = (raceId: string, current: number) => {
    socketClose = openRaceSocket(raceSocketUrl(`/ws/races/${raceId}`), {
      onOpen: () => {
        if (current !== session) return
        // Conexão inicial: vira "ao vivo" no primeiro tick.
        if (!recovering) return
        // Reconexão: só confirma depois que a simulação voltar a andar.
        set({ status: "syncing", error: null })
        syncBaseSimTs = null
        armSyncTimer(raceId, current)
        void resync(raceId, current)
      },

      onMessage: (raw) => {
        if (current !== session) return
        const msg = parseLiveMessage(raw)
        if (msg) apply(msg)
      },

      onClose: (code) => {
        if (current !== session || get().status === "finished") return
        clearSyncTimer()

        if (code === 4404) {
          set({ status: "error", error: "Corrida não encontrada no simulador." })
          return
        }
        if (code === 4410) {
          set({ status: "error", error: RACE_CANCELLED_MESSAGE })
          return
        }

        scheduleReconnect(raceId, current)
      },
    })
  }

  return {
    status: "idle",
    ...freshRaceState(),
    raceId: null,
    selectedDriverId: null,
    followedDriverId: null,
    viewMode: "2d",
    pitBusy: false,
    pitError: null,
    aiEngineerStatus: "idle",
    aiEngineerStats: null,
    aiEngineerError: null,

    load: async (raceId) => {
      get().disconnect()
      const current = session
      attempts = 0
      recovering = false
      syncBaseSimTs = null
      clearSyncTimer()
      feedSeq = 0
      lastPass.clear()

      const fresh = freshRaceState()
      set({ ...fresh, status: "loading", raceId, selectedDriverId: null })

      try {
        const [race, snap] = await Promise.all([api.getRace(raceId), api.getSnapshot(raceId)])
        if (current !== session) return

        set({
          race,
          frame: snap.lastFrame,
          frameAt: performance.now(),
          classification: snap.classification,
          status: snap.status === "finished" ? "finished" : snap.status === "cancelled" ? "error" : "loading",
          error: snap.status === "cancelled" ? RACE_CANCELLED_MESSAGE : null,
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
      clearSyncTimer()
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      socketClose?.()
      socketClose = null
    },

    selectDriver: (driverId) => set({ selectedDriverId: driverId }),

    followDriver: (driverId: string) => set({ followedDriverId: driverId }),

    unfollowDriver: () => set({ followedDriverId: null }),

    setViewMode: (mode) => set({ viewMode: mode }),

    requestPit: async (driverId, tyre) => {
      const raceId = get().raceId
      if (!raceId || get().pitBusy) return
      set({ pitBusy: true, pitError: null })
      try {
        await api.requestPitStop(raceId, driverId, tyre)
      } catch (error) {
        set({ pitError: error instanceof Error ? error.message : "Não foi possível pedir o box." })
      } finally {
        set({ pitBusy: false })
      }
    },

    cancelPit: async (driverId) => {
      const raceId = get().raceId
      if (!raceId || get().pitBusy) return
      set({ pitBusy: true, pitError: null })
      try {
        await api.cancelPitStop(raceId, driverId)
      } catch (error) {
        set({ pitError: error instanceof Error ? error.message : "Não foi possível cancelar o pedido." })
      } finally {
        set({ pitBusy: false })
      }
    },
  }
})
