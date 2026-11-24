/**
 * Pontos de vista fixos para as capturas de tela (só o gancho de
 * desenvolvimento usa): visão geral, grid de largada e uma curva.
 */
import { Vector3 } from "three"

import { toWorld } from "../track-frame.ts"
import type { TrackFrame } from "../track-frame.ts"
import { kappaAt } from "./curvature.ts"
import type { Layout } from "./layout.ts"

export type ViewPose = { position: Vector3; target: Vector3 }

export function showcaseViews(frame: TrackFrame, layout: Layout, overview: ViewPose): Record<"overview" | "grid" | "corner", ViewPose> {
  // Grid: atrás da largada, um pouco à direita, olhando para o pórtico.
  const grid = {
    position: toWorld(frame, -110, 3, 7),
    target: toWorld(frame, 12, 0, 1.5),
  }
  // Curva: primeiro ápice depois da largada, câmera por dentro olhando para fora (arquibancada ao fundo).
  const apex = layout.peaks.find((s) => s > 40) ?? layout.peaks[0] ?? frame.lengthM / 3
  const out = kappaAt(frame, layout.kappa, apex) > 0 ? -1 : 1
  const corner = {
    position: toWorld(frame, apex, -out * 38, 6),
    target: toWorld(frame, apex, out * 20, 4),
  }
  return {
    overview: { position: overview.position.clone(), target: overview.target.clone() },
    grid: { position: grid.position.clone(), target: grid.target.clone() },
    corner: { position: corner.position.clone(), target: corner.target.clone() },
  }
}
