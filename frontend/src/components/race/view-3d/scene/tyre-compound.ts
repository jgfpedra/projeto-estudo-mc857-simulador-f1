/**
 * Cor da faixa de composto no flanco de cada pneu.
 *
 * O parser guarda `tyre_compound` como veio (`CarFrame.tyre`, "UNKNOWN" sem o
 * campo); o backend manda SOFT, MEDIUM, HARD, INTERMEDIATE ou WET. Qualquer
 * caixa é aceita. Desconhecido ou ausente: sem faixa.
 */
export type Compound = "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET"

export const COMPOUND_COLOR: Record<Compound, string> = {
  SOFT: "#E10600",
  MEDIUM: "#FFD12E",
  HARD: "#F0F0F0",
  INTERMEDIATE: "#43B02A",
  WET: "#0067AD",
}

/** Cor da faixa, ou `null` (sem faixa) para composto desconhecido ou ausente. */
export function compoundColor(raw: string | null | undefined): string | null {
  if (typeof raw !== "string") return null
  const key = raw.trim().toUpperCase()
  return Object.prototype.hasOwnProperty.call(COMPOUND_COLOR, key) ? COMPOUND_COLOR[key as Compound] : null
}
