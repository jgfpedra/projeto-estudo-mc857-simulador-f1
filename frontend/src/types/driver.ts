/** Dados de um piloto em uma temporada específica, retornados pela API. */
export type Driver = {
  id: string
  name: string
  shortName: string
  number: number
  country: string
  countryCode: string
  teamId: string
  teamName: string
  teamShortName: string
}

/** O grid guarda somente a posição e o ID do piloto; null representa vaga vazia. */
export type GridSlot = {
  position: number
  driverId: string | null
}

export type DriverMode = "custom" | "random"
export const NULL_DRIVER_ID = "__null__"
