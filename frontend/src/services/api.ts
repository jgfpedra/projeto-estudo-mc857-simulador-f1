import { circuits } from "@/data/circuits"
import { driversBySeason } from "@/data/drivers"
import type { Circuit } from "@/types/circuit"
import type { Driver } from "@/types/driver"
import { env } from "@/config/env"

const API_BASE_URL = env.apiUrl ?? "/api"
const USE_MOCKS = "true"

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) throw new Error(`Erro ao consultar API (${response.status})`)
  return response.json() as Promise<T>
}

export const api = {
  async getCircuits(): Promise<Circuit[]> {
    if (USE_MOCKS) return circuits
    return getJson<Circuit[]>("/circuits")
  },

  async getDriversBySeason(season: number): Promise<Driver[]> {
    if (USE_MOCKS) return driversBySeason[season] ?? []
    return getJson<Driver[]>(`/seasons/${season}/drivers`)
  },
}
