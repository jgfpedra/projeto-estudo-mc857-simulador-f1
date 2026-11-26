import { Component, Suspense, lazy } from "react"
import type { ReactNode } from "react"

import type { Frame, RaceInfo } from "@/types/race"

/**
 * Contrato da visualização 3D (definido pelo Luiz; as props não mudam):
 * - quando `selectedDriverId` não for nulo, a câmera segue esse piloto em
 *   terceira pessoa, orientada pelo `headingDeg` do carro;
 * - a posição entre ticks é interpolada com `interpolateCars` (helpers/race-live),
 *   usando `prevFrame`, `frame`, `frameAt` e `tickIntervalMs` do `useLiveRaceStore`,
 *   exatamente como o mapa 2D;
 * - `onSelectDriver(null)` é chamado quando o usuário sai do seguimento.
 *
 * As props não mudaram, mas a cena não desenha mais na borda ao vivo: usa
 * `interpolateCars` sobre os frames da store guardados por `simTs`, num
 * instante ~150 ms atrás do mais novo (`scene/playback.ts`), para os ticks
 * irregulares não fazerem o carro parar e saltar. O 2D segue na borda ao vivo.
 *
 * Este módulo é pequeno e entra no bundle da página; a cena (three, R3F, drei)
 * fica em `race-scene.tsx`, carregada com `React.lazy` só quando o 3D é aberto.
 * `frame` não é repassado: a cena lê a store dentro do `useFrame`, sem
 * re-renderizar o React a cada tick.
 */
export type RaceView3DProps = {
  race: RaceInfo
  frame: Frame | null
  selectedDriverId: string | null
  onSelectDriver: (driverId: string | null) => void
}

const RaceScene = lazy(() => import("./race-scene"))

function Message({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">{children}</div>
  )
}

/** WebGL indisponível ou falha ao carregar o chunk/modelo: mostra o erro sem derrubar a página. */
class View3DBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return <Message>Não foi possível abrir a visualização 3D: {this.state.error.message}</Message>
    }
    return this.props.children
  }
}

export function RaceView3D({ race, selectedDriverId, onSelectDriver }: RaceView3DProps) {
  return (
    <View3DBoundary>
      <Suspense fallback={<Message>Carregando visualização 3D...</Message>}>
        <RaceScene race={race} selectedDriverId={selectedDriverId} onSelectDriver={onSelectDriver} />
      </Suspense>
    </View3DBoundary>
  )
}
