import type { RaceDriver } from "@/types/race"
import { driverColor } from "../../../../helpers/race-live.ts"

/** Quantas cores da paleta do 2D existem antes de gerar novas. */
const PALETTE_SIZE = 20

function rgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return null
  const n = parseInt(m[1], 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** Saturação HSL em [0, 1]. Cinzas (como o `#808080` do backend) ficam perto de 0. */
function saturation(hex: string): number {
  const c = rgb(hex)
  if (!c) return 0
  const [r, g, b] = c.map((v) => v / 255)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  if (max === min) return 0
  return l > 0.5 ? (max - min) / (2 - max - min) : (max - min) / (max + min)
}

function hsl(h: number, s: number, l: number): string {
  const a = s * Math.min(l, 1 - l)
  const f = (n: number) => {
    const k = (n + h / 30) % 12
    const v = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))
    return Math.round(v * 255)
      .toString(16)
      .padStart(2, "0")
  }
  return `#${f(0)}${f(8)}${f(4)}`.toUpperCase()
}

/** Paleta do 2D, sem os tons cinza/brancos, e depois cores geradas pelo ângulo áureo. */
function* candidates(): Generator<string> {
  for (let i = 0; i < PALETTE_SIZE; i++) {
    const c = driverColor(undefined, i)
    if (saturation(c) >= 0.25) yield c.toUpperCase()
  }
  for (let i = 0; ; i++) yield hsl((i * 137.508) % 360, 0.75, 0.55)
}

/** A cor da equipe vale, exceto se nula ou se o backend marcou a origem como desconhecida. */
export function hasTeamColor(driver: RaceDriver): boolean {
  return driver.teamColor !== null && rgb(driver.teamColor) !== null && driver.teamColorSource !== "unknown"
}

/**
 * Cor de cada piloto no 3D.
 *
 * Usa `teamColor`, exceto quando ela é nula ou `teamColorSource` é "unknown"
 * (o cinza de emergência do backend). Nesses casos cada piloto recebe uma cor
 * própria da paleta, diferente das cores de equipe em uso e das já atribuídas.
 */
export function carColors(drivers: RaceDriver[]): Map<string, string> {
  const out = new Map<string, string>()
  const used = new Set<string>()
  for (const d of drivers) if (hasTeamColor(d)) used.add(d.teamColor!.toUpperCase())

  const next = candidates()
  for (const d of drivers) {
    if (hasTeamColor(d)) {
      out.set(d.driverId, d.teamColor!)
      continue
    }
    let c = next.next().value as string
    while (used.has(c)) c = next.next().value as string
    used.add(c)
    out.set(d.driverId, c)
  }
  return out
}
