import { createContext } from "react"

/**
 * Lugar na barra de cima da página, ao lado da chave 2D/3D, onde a cena 3D
 * põe seus controles (o seletor de cenário) por portal. A página fornece o
 * elemento; a faixa de eventos vem depois dele na mesma linha, então nada se
 * sobrepõe. Sem provedor (nulo), a cena desenha o seletor no próprio canto.
 */
export const View3DToolbarSlot = createContext<HTMLElement | null>(null)
