import { useEffect } from 'react'
import { useThree } from '@react-three/fiber'
import type { RootState } from '@react-three/fiber'
import type { ClockState } from './replay/clock'
import { ONBOARD } from './cameras/rig'
import type { FollowState, OnboardConfig } from './cameras/rig'

/**
 * Hook for `scripts/snapshot.mjs`, and nothing else.
 *
 * The editor's preview pane cannot run `requestAnimationFrame`, so it never
 * shows motion and cannot tell a working render loop from a stalled one. The
 * snapshot script drives the built app in headless Chromium instead, and needs
 * a few things the DOM does not carry: how many frames WebGL has actually
 * drawn, the r3f store to point the camera at a wheel, and the replay clock
 * and followed-car readout, to step time exactly and check wheel phase
 * against distance travelled.
 *
 * Only mounted when the URL has `?probe`, so a normal visit exposes nothing.
 */
export const PROBE_ENABLED =
  typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('probe')

export interface ViewerProbe {
  /**
   * `renderer.info.render.frame`: incremented inside `WebGLRenderer.render`,
   * so it counts frames drawn, not `requestAnimationFrame` callbacks.
   */
  frames(): number
  /** The r3f store, for inspection and camera placement. */
  store(): RootState
  /** The live replay clock. Mutable: the wheel check steps `tS` directly. */
  clock: ClockState
  /** The followed car's state as `Grid` last wrote it. */
  readout: FollowState
  /** The T-cam's offsets, so the snapshot can check the camera against the car. */
  onboard: OnboardConfig
}

declare global {
  interface Window {
    __viewer?: ViewerProbe
  }
}

interface Props {
  clock: { current: ClockState }
  readout: { current: FollowState }
}

export function Probe({ clock, readout }: Props) {
  const gl = useThree((s) => s.gl)
  const get = useThree((s) => s.get)
  useEffect(() => {
    window.__viewer = {
      frames: () => gl.info.render.frame,
      store: get,
      get clock() {
        return clock.current
      },
      get readout() {
        return readout.current
      },
      onboard: ONBOARD,
    }
    return () => {
      delete window.__viewer
    }
  }, [gl, get, clock, readout])
  return null
}
