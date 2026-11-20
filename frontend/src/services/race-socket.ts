export type SocketHandlers = {
  onOpen: () => void
  onMessage: (raw: unknown) => void
  onClose: (code: number) => void
}

/** Uma tentativa de conexão. A reconexão fica com o store, que ressincroniza pelo snapshot. */
export function openRaceSocket(url: string, handlers: SocketHandlers): () => void {
  const ws = new WebSocket(url)
  let closedByClient = false

  ws.onopen = () => handlers.onOpen()

  ws.onmessage = (event: MessageEvent<string>) => {
    try {
      handlers.onMessage(JSON.parse(event.data))
    } catch {
      // Mensagem que não é JSON: ignorada.
    }
  }

  ws.onclose = (event) => {
    if (!closedByClient) handlers.onClose(event.code)
  }

  return () => {
    closedByClient = true
    ws.close(1000)
  }
}
