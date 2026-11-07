export type CircuitLayout = {
  id: string
  periods: string[]          // ex.: ["1990-2019", "2021-2026"]
  firstYear: number | null
  lastYear: number | null
  lengthKm: number | null
  turns: number | null
  svgUrl: string | null
  isCurrent: boolean
  simulable: boolean
}

export type Circuit = {
  id: string
  name: string               // ex.: "José Carlos Pace"
  fullName: string           // ex.: "Autódromo José Carlos Pace"
  city: string | null
  country: string | null
  countryCode: string | null
  simulable: boolean
  layouts: CircuitLayout[]
}