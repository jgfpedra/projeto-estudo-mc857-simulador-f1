import { env } from "@/config/env"
import type { ApiCircuit, ApiDriver, ApiLayout, ApiRaceRequest, ApiRaceResponse } from "@/types/api"
import type { Circuit, CircuitLayout } from "@/types/circuit"
import type { Driver } from "@/types/driver"
import { parseRaceInfo, parseSnapshot } from "@/services/race-parser"
import type { RaceInfo, RaceSnapshot } from "@/types/race"

export type RaceStartResponse = {
  raceId: string
  wsPath: string
  grid: string[]
  initialWeather: string
  warnings: string[]
}

const API_BASE_URL = (env.apiUrl ?? "").replace(/\/$/, "")

function defaultWsBase(): string {
  if (API_BASE_URL) return API_BASE_URL.replace(/^http/, "ws")
  const scheme = window.location.protocol === "https:" ? "wss" : "ws"
  return `${scheme}://${window.location.host}`
}

/** URL completa do websocket de uma corrida, a partir do ws_path devolvido pelo POST. */
export function raceSocketUrl(wsPath: string): string {
  const base = (env.wsUrl ?? defaultWsBase()).replace(/\/$/, "")
  return `${base}${wsPath}`
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail)) {
      // Erros de validação do FastAPI (422) vêm como lista de { msg, loc, ... }.
      return body.detail
        .map((item: { msg?: unknown }) => (typeof item.msg === "string" ? item.msg : ""))
        .filter(Boolean)
        .join("; ")
    }
  } catch {
    // Corpo que não é JSON: usa a mensagem padrão abaixo.
  }
  return `Erro ao consultar API (${response.status})`
}

async function request<T>(
  path: string,
  init: { method?: "GET" | "POST"; body?: unknown } = {},
): Promise<T> {
  const { method = "GET", body } = init

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      Accept: "application/json",
      ...(body !== undefined && { "Content-Type": "application/json" }),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) throw new Error(await readErrorMessage(response))
  return (await response.json()) as T
}

const pickSvg = (svg: Record<string, string | null> | null | undefined): string | null =>
  svg?.["white-outline"] ?? svg?.["white"] ?? svg?.["black-outline"] ?? svg?.["black"] ?? null

function mapLayout(l: ApiLayout): CircuitLayout {
  return {
    id: l.id,
    periods: l.years,
    firstYear: l.first_year,
    lastYear: l.last_year,
    lengthKm: l.length_km,
    turns: l.turns,
    svgUrl: pickSvg(l.svg),
    isCurrent: l.is_current,
    simulable: l.simulable,
  }
}

function mapCircuit(c: ApiCircuit): Circuit {
  return {
    id: c.id,
    name: c.name ?? c.full_name ?? c.id,
    fullName: c.full_name ?? c.name ?? c.id,
    city: c.city,
    country: c.country.name,
    countryCode: c.country.code,
    simulable: c.simulable,
    layouts: c.layouts.map(mapLayout),
  }
}

function mapDriver(d: ApiDriver): Driver {
  return {
    id: d.id,
    name: d.name ?? d.id,
    shortName: d.abbreviation ?? d.id,
    number: d.number ?? 0,
    country: d.country.name ?? "",
    countryCode: d.country.code ?? "",
    teamId: d.team_id ?? "",
    teamName: d.team ?? "",
    teamShortName: d.team ?? "",
  }
}

export const api = {
  async getRace(raceId: string): Promise<RaceInfo> {
    const race = parseRaceInfo(await request<unknown>(`/races/${encodeURIComponent(raceId)}`))
    if (!race) throw new Error("Resposta inválida ao carregar a corrida.")
    return race
  },

  async getSnapshot(raceId: string): Promise<RaceSnapshot> {
    const snapshot = parseSnapshot(
      await request<unknown>(`/races/${encodeURIComponent(raceId)}/snapshot`),
    )
    if (!snapshot) throw new Error("Resposta inválida ao carregar o estado da corrida.")
    return snapshot
  },
  async getCircuits(): Promise<Circuit[]> {
    const data = await request<ApiCircuit[]>("/circuits")
    return data.map(mapCircuit)
  },

  getSeasons(): Promise<number[]> {
    return request<number[]>("/seasons")
  },

  async getDrivers(season: number): Promise<Driver[]> {
    const data = await request<ApiDriver[]>(`/seasons/${season}/drivers`)
    return data.map(mapDriver)
  },

  async startRace(body: ApiRaceRequest): Promise<RaceStartResponse> {
    const data = await request<ApiRaceResponse>("/races", { method: "POST", body })
    return {
      raceId: data.race_id,
      wsPath: data.ws_path,
      grid: data.grid,
      initialWeather: data.initial_weather,
      warnings: data.warnings,
    }
  },
}