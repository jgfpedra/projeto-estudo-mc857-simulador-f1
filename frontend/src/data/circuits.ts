import type { Circuit } from "@/types/circuit"

export const circuits: Circuit[] = [
  {
    id: "interlagos",
    name: "Autódromo José Carlos Pace",
    country: "Brasil",
    countryCode: "BR",
    city: "São Paulo",
    layouts: [
      { id: "__current__", name: "Traçado Atual", svg: "./interlagos-2.svg", yearFrom: 2025 },
      { id: "interlagos-older", name: "Traçado histórico", svg: "./interlagos-2.svg", yearFrom: 1979, yearTo: 1989 },
    ],
  },
  {
    id: "monza",
    name: "Autodromo Nazionale di Monza",
    country: "Itália",
    countryCode: "IT",
    city: "Monza",
    layouts: [
      { id: "__current__", name: "Traçado Atual", svg: "./interlagos-2.svg", yearFrom: 2025 },
      { id: "monza-older", name: "Traçado histórico", svg: "./interlagos-2.svg", yearFrom: 1950, yearTo: 1999 },
    ],
  },
]