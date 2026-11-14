import type {
  Bounds,
  CarFrame,
  FeedKind,
  Frame,
  RaceDriver,
  Tone,
  TrackStatus,
} from "@/types/race"

/** Largura da pista em metros. */
export const TRACK_WIDTH_M = 12

const PALETTE = [
  "#E8002D", "#27F4D2", "#FF8000", "#3671C6", "#229971",
  "#FF87BC", "#64C4FF", "#52E252", "#B6BABD", "#6692FF",
  "#FFD12E", "#FF5F5F", "#9B8CFF", "#00D2BE", "#F5A623",
  "#C0FF4D", "#4DC3FF", "#FF6EC7", "#A3A3A3", "#FFFFFF",
]

/** Cor da equipe. Sem cor no backend, usa a paleta pela posição no grid. */
export function driverColor(driver: RaceDriver | undefined, index: number): string {
  return driver?.teamColor ?? PALETTE[index % PALETTE.length]
}

const WEATHER_LABEL: Record<string, string> = {
  DRY: "Seco",
  CLOUDY: "Nublado",
  DAMP: "Úmido",
  WET: "Chuva",
}

/** Nome exibido para o clima do motor (DRY/CLOUDY/DAMP/WET). Desconhecido volta como veio. */
export function weatherLabel(kind: string): string {
  return WEATHER_LABEL[kind] ?? kind
}

export const TRACK_STATUS_LABEL: Record<TrackStatus, string> = {
  GREEN: "Verde",
  YELLOW: "Amarela",
  SAFETY_CAR: "Safety car",
  VSC: "VSC",
  RED_FLAG: "Bandeira vermelha",
}

export const KIND_LABEL: Record<FeedKind, string> = {
  overtake: "Ultrapassagem",
  pit_stop: "Pit stop",
  tyre_worn: "Pneu",
  weather: "Clima",
  collision: "Contato",
  race_control: "Controle de corrida",
  finish: "Chegada",
}

export const TONE_TEXT: Record<Tone, string> = {
  info: "text-sky-400",
  success: "text-emerald-400",
  warn: "text-amber-400",
  danger: "text-red-500",
}

export const TONE_BORDER: Record<Tone, string> = {
  info: "border-sky-400",
  success: "border-emerald-400",
  warn: "border-amber-400",
  danger: "border-red-500",
}

export const COMPOUND_BADGE: Record<string, { letter: string; className: string }> = {
  SOFT: { letter: "S", className: "bg-red-600 text-white" },
  MEDIUM: { letter: "M", className: "bg-yellow-400 text-black" },
  HARD: { letter: "H", className: "bg-zinc-100 text-black" },
  INTERMEDIATE: { letter: "I", className: "bg-green-600 text-white" },
  WET: { letter: "W", className: "bg-blue-600 text-white" },
}

/** mm:ss.d para tempo de corrida. */
export function formatClock(seconds: number): string {
  const total = Math.max(0, seconds)
  const m = Math.floor(total / 60)
  return `${String(m).padStart(2, "0")}:${(total % 60).toFixed(1).padStart(4, "0")}`
}

export function gapLabel(car: CarFrame): string {
  if (car.position === 1) return "LÍDER"
  if (car.lapsBehind > 0) return `+${car.lapsBehind} V`
  if (car.gapToLeaderS === null) return "—"
  return `+${car.gapToLeaderS.toFixed(1)}`
}

export function boundsOf(points: [number, number][]): Bounds {
  if (points.length === 0) return { minX: 0, maxX: 1, minY: 0, maxY: 1 }
  const xs = points.map((p) => p[0])
  const ys = points.map((p) => p[1])
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  }
}

/**
 * Ultrapassagens entre dois frames: um carro que subiu de posição passou os carros
 * que estavam entre a nova posição e a antiga.
 */
export function detectOvertakes(
  prev: Frame | null,
  cur: Frame,
): { passerId: string; passedId: string; position: number }[] {
  if (!prev) return []
  const before = new Map(prev.cars.map((c) => [c.driverId, c.position]))
  const out: { passerId: string; passedId: string; position: number }[] = []

  for (const car of cur.cars) {
    const old = before.get(car.driverId)
    if (old === undefined || car.position >= old) continue

    for (const other of cur.cars) {
      if (other.driverId === car.driverId) continue
      const otherOld = before.get(other.driverId)
      if (otherOld !== undefined && otherOld >= car.position && otherOld < old) {
        out.push({ passerId: car.driverId, passedId: other.driverId, position: car.position })
      }
    }
  }

  return out
}

/** Posição interpolada entre o frame anterior e o atual. alpha vai de 0 a 1. */
export function interpolateCars(
  prev: Frame | null,
  cur: Frame,
  alpha: number,
): Map<string, { x: number; y: number }> {
  const prevById = new Map((prev?.cars ?? []).map((c) => [c.driverId, c]))
  const out = new Map<string, { x: number; y: number }>()

  for (const c of cur.cars) {
    const p = prevById.get(c.driverId) ?? c
    out.set(c.driverId, {
      x: p.x + (c.x - p.x) * alpha,
      y: p.y + (c.y - p.y) * alpha,
    })
  }

  return out
}

/** Ids de pilotos citados em eventos recentes, para destacar no mapa. */
export function recentDriverIds(
  items: { simTs: number; driverIds: string[] }[],
  simTs: number,
  windowS: number,
): Set<string> {
  const ids = new Set<string>()
  for (const item of items) {
    if (item.simTs <= simTs && simTs - item.simTs < windowS) {
      item.driverIds.forEach((id) => ids.add(id))
    }
  }
  return ids
}
