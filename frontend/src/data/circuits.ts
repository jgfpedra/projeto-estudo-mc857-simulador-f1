export type TrackWaypoint = [number, number]

export type CircuitLayout = {
  id: string
  name: string
  year: number | null
  isCurrent: boolean
  lengthM: number
  waypoints: TrackWaypoint[]
}

export type Circuit = {
  id: string
  name: string
  country: string
  countryCode: string
  location: string
  currentLayout: CircuitLayout
  historicalVariants: CircuitLayout[]
}

/**
 * Coordenadas esquemáticas baseadas no preset de Interlagos
 * existente no backend.
 *
 * O backend trabalha com coordenadas (x, y) em metros.
 * A pista é fechada: o último ponto conecta novamente ao primeiro.
 */
const interlagosWaypoints: TrackWaypoint[] = [
  [0, 0],
  [300, 0],
  [380, 30],
  [430, 80],
  [470, 130],
  [450, 200],
  [380, 260],
  [300, 280],
  [180, 280],
  [60, 280],
  [-30, 260],
  [-90, 220],
  [-140, 160],
  [-160, 100],
  [-150, 40],
  [-90, 10],
  [-40, -20],
  [-10, -30],
  [40, -30],
  [120, -20],
]

/**
 * Por enquanto usamos o mesmo traçado esquemático para a variante
 * histórica apenas para exercitar o seletor de layouts.
 *
 * Quando o backend estiver conectado, cada variante receberá seus
 * próprios waypoints vindos do Track correspondente.
 */
const interlagosHistoricalWaypoints: TrackWaypoint[] = [
  ...interlagosWaypoints,
]

export const circuits: Circuit[] = [
  {
    id: "interlagos",
    name: "Interlagos",
    country: "Brasil",
    countryCode: "BR",
    location: "São Paulo",
    currentLayout: {
      id: "interlagos-2025",
      name: "José Carlos Pace",
      year: 2025,
      isCurrent: true,
      lengthM: 4309,
      waypoints: interlagosWaypoints,
    },
    historicalVariants: [
      {
        id: "interlagos-2019",
        name: "José Carlos Pace",
        year: 2019,
        isCurrent: false,
        lengthM: 4309,
        waypoints: interlagosHistoricalWaypoints,
      },
    ],
  },
]