import { KIND_LABEL, TONE_TEXT } from "@/helpers/race-live"
import type { FeedItem, FeedKind } from "@/types/race"

/** Só eventos que merecem destaque sobre a pista. */
const BANNER_KINDS: FeedKind[] = ["overtake", "pit_stop", "race_control", "collision", "finish"]
const BANNER_S = 6

/**
 * Aviso discreto na mesma linha dos controles (à direita do toggle).
 * Sem caixa pesada: fundo translúcido e uma linha de texto, para não cobrir a pista no mobile.
 */
export function RaceBanner({ items, simTs }: { items: FeedItem[]; simTs: number }) {
  const recent = items.filter(
    (item) =>
      BANNER_KINDS.includes(item.kind) && item.simTs <= simTs && simTs - item.simTs < BANNER_S,
  )
  const latest = recent[recent.length - 1]

  if (!latest) return null

  return (
    <div
      role="status"
      className="pointer-events-none absolute left-32 right-4 top-4 z-20 flex min-w-0 items-center gap-2 bg-background/40 px-2 py-1 backdrop-blur-sm"
    >
      <span className={`h-2 w-2 shrink-0 rounded-full bg-current ${TONE_TEXT[latest.tone]}`} />
      <span className={`shrink-0 text-[10px] font-black uppercase tracking-wider ${TONE_TEXT[latest.tone]}`}>
        {KIND_LABEL[latest.kind]}
      </span>
      <span className="min-w-0 truncate text-xs font-semibold">{latest.message}</span>
    </div>
  )
}
