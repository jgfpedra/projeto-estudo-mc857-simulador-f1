export type CircuitVariant = {
  id: string
  year: number
  name: string
  layoutImage?: string
}

export type Circuit = {
  id: string
  name: string
  location: string
  country: string
  countryCode: string
  currentLayout: {
    id: string
    name: string
    layoutImage?: string
  }
  historicalVariants: CircuitVariant[]
}

// Temporário.
// Quando os circuitos vierem da API/banco, este array será substituído
// pelos dados retornados pela aplicação.
export const circuits: Circuit[] = [
  {
    id: "interlagos",
    name: "Interlagos",
    location: "São Paulo",
    country: "Brasil",
    countryCode: "BR",
    currentLayout: {
      id: "interlagos-current",
      name: "Layout atual",
    },
    historicalVariants: [
      {
        id: "interlagos-2014",
        year: 2014,
        name: "Layout 2014",
      },
      {
        id: "interlagos-1990",
        year: 1990,
        name: "Layout 1990",
      },
    ],
  },
  {
    id: "monza",
    name: "Monza",
    location: "Monza",
    country: "Itália",
    countryCode: "IT",
    currentLayout: {
      id: "monza-current",
      name: "Layout atual",
    },
    historicalVariants: [
      {
        id: "monza-1981",
        year: 1981,
        name: "Layout 1981",
      },
      {
        id: "monza-1965",
        year: 1965,
        name: "Layout 1965",
      },
    ],
  },
  {
    id: "silverstone",
    name: "Silverstone",
    location: "Silverstone",
    country: "Reino Unido",
    countryCode: "GB",
    currentLayout: {
      id: "silverstone-current",
      name: "Layout atual",
    },
    historicalVariants: [
      {
        id: "silverstone-2009",
        year: 2009,
        name: "Layout 2009",
      },
      {
        id: "silverstone-1990",
        year: 1990,
        name: "Layout 1990",
      },
    ],
  },
  {
    id: "spa",
    name: "Spa-Francorchamps",
    location: "Stavelot",
    country: "Bélgica",
    countryCode: "BE",
    currentLayout: {
      id: "spa-current",
      name: "Layout atual",
    },
    historicalVariants: [
      {
        id: "spa-2004",
        year: 2004,
        name: "Layout 2004",
      },
      {
        id: "spa-1980",
        year: 1980,
        name: "Layout 1980",
      },
    ],
  },
  {
    id: "suzuka",
    name: "Suzuka",
    location: "Suzuka",
    country: "Japão",
    countryCode: "JP",
    currentLayout: {
      id: "suzuka-current",
      name: "Layout atual",
    },
    historicalVariants: [
      {
        id: "suzuka-2003",
        year: 2003,
        name: "Layout 2003",
      },
    ],
  },
  {
    id: "monaco",
    name: "Monaco",
    location: "Monte Carlo",
    country: "Mônaco",
    countryCode: "MC",
    currentLayout: {
      id: "monaco-current",
      name: "Layout atual",
    },
    historicalVariants: [
      {
        id: "monaco-1997",
        year: 1997,
        name: "Layout 1997",
      },
      {
        id: "monaco-1986",
        year: 1986,
        name: "Layout 1986",
      },
    ],
  },
]