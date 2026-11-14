import type { Frame, RaceInfo } from "@/types/race"

/**
 * Contrato da visualização 3D. A implementação real é feita em outro módulo e deve:
 * - aceitar estas props;
 * - quando `selectedDriverId` não for nulo, colocar a câmera em terceira pessoa seguindo esse piloto
 *   (usar `headingDeg` do carro, quando existir, para orientar a câmera);
 * - interpolar entre ticks com `interpolateCars` (helpers/race-live), usando `prevFrame`,
 *   `frame` e `frameAt` do `useLiveRaceStore`;
 * - chamar `onSelectDriver(null)` quando o usuário quiser sair do seguimento.
 */
export type RaceView3DProps = {
  race: RaceInfo
  frame: Frame | null
  selectedDriverId: string | null
  onSelectDriver: (driverId: string | null) => void
}

export function RaceView3D({ race, frame, selectedDriverId }: RaceView3DProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
      <span className="font-black uppercase tracking-wider">Visualização 3D em integração</span>
      <span className="text-xs">
        {race.track.name} · volta {frame?.lap ?? 0}/{race.numLaps}
        {selectedDriverId ? ` · câmera em ${selectedDriverId}` : ""}
      </span>
    </div>
  )
}
