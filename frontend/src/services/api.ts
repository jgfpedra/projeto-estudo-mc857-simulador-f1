import { circuits } from "@/data/circuits"
import { driversBySeason } from "@/data/drivers"
import { env } from "@/config/env"
import type { Circuit } from "@/types/circuit"
import type { Driver } from "@/types/driver"
import type { RaceSetupPayload } from "@/types/race-setup"
import { MAX_RACE_LAPS, MIN_RACE_LAPS } from "@/stores/race-laps-store"

export type RaceStartResponse = {
  raceId: string
}

const API_BASE_URL = env.apiUrl || "/api"
const USE_MOCKS = true
const GRID_SIZE = 20

type RequestOptions = {
  method?: "GET" | "POST"
  body?: unknown
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { message?: unknown }
    if (typeof data.message === "string" && data.message) return data.message
  } catch {
    // Corpo de erro que não é JSON: usa a mensagem padrão abaixo.
  }

  return `Erro ao consultar API (${response.status})`
}

async function request<T>(
  path: string,
  { method = "GET", body }: RequestOptions = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      Accept: "application/json",
      ...(body !== undefined && { "Content-Type": "application/json" }),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) throw new Error(await readErrorMessage(response))

  return response.json() as Promise<T>
}

/** Valida o payload antes do envio, para não depender só da resposta do backend. */

function assertValidRaceSetup(payload: RaceSetupPayload): void {
  if (payload.grid.length !== GRID_SIZE) {
    throw new Error(`O grid precisa ter ${GRID_SIZE} pilotos.`)
  }

  if (new Set(payload.grid).size !== payload.grid.length) {
    throw new Error("O grid contém pilotos repetidos.")
  }

  if (payload.tires.strategy.enabled && payload.tires.strategy.stints.length === 0) {
    throw new Error("A estratégia precisa ter ao menos um stint.")
  }

  if (
    !Number.isInteger(payload.totalLaps) ||
    payload.totalLaps < MIN_RACE_LAPS ||
    payload.totalLaps > MAX_RACE_LAPS
  ) {
    throw new Error(`O número de voltas precisa estar entre ${MIN_RACE_LAPS} e ${MAX_RACE_LAPS}.`)
  }

  if (payload.tires.strategy.enabled) {
    const planned = payload.tires.strategy.stints.reduce((sum, stint) => sum + stint.laps, 0)
    if (planned > payload.totalLaps) {
      throw new Error("A estratégia ultrapassa o total de voltas da corrida.")
    }
  }
}

const mockDelay = () => new Promise((resolve) => setTimeout(resolve, 400))

export const api = {
  async getCircuits(): Promise<Circuit[]> {
    if (USE_MOCKS) return circuits
    return request<Circuit[]>("/circuits")
  },

  async getDriversBySeason(season: number): Promise<Driver[]> {
    if (USE_MOCKS) return driversBySeason[season] ?? []
    return request<Driver[]>(`/seasons/${season}/drivers`)
  },

  async startRace(payload: RaceSetupPayload): Promise<RaceStartResponse> {
    assertValidRaceSetup(payload)

    if (USE_MOCKS) {
      await mockDelay()
      console.info("[mock] startRace", payload)
      return { raceId: crypto.randomUUID() }
    }

    return request<RaceStartResponse>("/races", {
      method: "POST",
      body: payload,
    })
  },
}