import { KIND_LABEL, TONE_TEXT, formatClock } from "@/helpers/race-live"
import type { FeedItem } from "@/types/race"

export function EventFeed({ items }: { items: FeedItem[] }) {
  if (items.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-xs uppercase tracking-wider text-muted-foreground">
        Nenhum evento ainda
      </div>
    )
  }

  return (
    <ul className="min-h-0 flex-1 overflow-y-auto">
      {[...items].reverse().map((item) => (
        <li key={item.id} className="border-b border-border px-4 py-2.5">
          <div
            className={`text-[10px] font-bold uppercase tracking-wider tabular-nums ${TONE_TEXT[item.tone]}`}
          >
            {formatClock(item.simTs)} · V{item.lap} · {KIND_LABEL[item.kind]}
          </div>
          <div className="text-xs font-semibold">{item.message}</div>
        </li>
      ))}
    </ul>
  )
}
