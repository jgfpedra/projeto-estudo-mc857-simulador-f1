import type { Circuit, CircuitLayout } from "@/types/circuit"

/**
 * Layout efetivo da seleção: o escolhido, se for simulável;
 * senão o atual; senão o primeiro simulável. Undefined se nenhum for simulável.
 */
export function resolveLayout(
  circuit: Circuit | undefined,
  layoutId: string | null,
): CircuitLayout | undefined {
  if (!circuit) return undefined
  const simulable = circuit.layouts.filter((layout) => layout.simulable)

  return (
    simulable.find((layout) => layout.id === layoutId) ??
    simulable.find((layout) => layout.isCurrent) ??
    simulable[0]
  )
}

export function layoutLabel(layout: CircuitLayout): string {
  const base = `${layout.isCurrent ? "Atual" : "Histórico"} · ${layout.periods.join(", ")}`
  return layout.simulable ? base : `${base} (não simulável)`
}