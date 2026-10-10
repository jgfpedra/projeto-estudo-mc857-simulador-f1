/** Contrato sugerido para o circuito retornado pela API. */
export type CircuitLayout = {
  id: string
  name: string
  svg: string
  yearFrom?: number
  yearTo?: number | null
}

export type Circuit = {
  id: string
  name: string
  country: string
  countryCode: string
  city: string
  /** Traçados históricos; o traçado atual continua no campo svg acima. */
  layouts: CircuitLayout[]
}

export const CURRENT_LAYOUT_ID = "__current__"
