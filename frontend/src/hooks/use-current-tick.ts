import { useEffect, useState } from "react"

import { tickPlayer } from "@/services/tick-player"
import type { Tick } from "@/types/race"

/** Tick atual. Re-renderiza só quando o índice muda, não a cada frame. */
export function useCurrentTick(): Tick | null {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    const sync = () => {
      const i = Math.max(
        0,
        Math.min(tickPlayer.ticks.length - 1, Math.floor(tickPlayer.time * tickPlayer.hz)),
      )
      setIndex((prev) => (prev === i ? prev : i))
    }

    sync()
    const offFrame = tickPlayer.subscribeFrame(sync)
    const offState = tickPlayer.subscribeState(sync)
    return () => {
      offFrame()
      offState()
    }
  }, [])

  return tickPlayer.ticks[index] ?? null
}

export function usePlayerState() {
  const [state, setState] = useState({ playing: false, speed: 1 })

  useEffect(() => {
    const sync = () => setState({ playing: tickPlayer.playing, speed: tickPlayer.speed })
    sync()
    return tickPlayer.subscribeState(sync)
  }, [])

  return state
}