/** Esmaecimento dos marcadores acima dos carros (`cars.tsx`). */

/**
 * Marcadores só com a câmera longe dos carros: aparecem entre 25% e 40% da
 * distância da visão geral (até o carro mais próximo). Na visão geral o carro
 * mais próximo fica a pelo menos ~63% dessa distância, então lá estão sempre
 * opacos; no grid, numa curva ou com zoom de perto, somem.
 */
export const PIN_FADE = { from: 0.25, to: 0.4 } as const

export function pinOpacity(nearestCarM: number, overviewDistanceM: number): number {
  const a = PIN_FADE.from * overviewDistanceM
  const b = PIN_FADE.to * overviewDistanceM
  const t = Math.min(1, Math.max(0, (nearestCarM - a) / Math.max(b - a, 1e-6)))
  return t * t * (3 - 2 * t)
}
