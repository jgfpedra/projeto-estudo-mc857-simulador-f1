import { useEffect, useMemo, useState } from "react"
import { ArrowLeft, ChevronDown, MapPin, Search } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

import { CURRENT_LAYOUT_ID } from "@/types/circuit"
import { useCircuitStore } from "@/stores/circuit-store"

function getFlagEmoji(countryCode: string) {
  return countryCode
    .toUpperCase()
    .replace(/./g, (char) =>
      String.fromCodePoint(127397 + char.charCodeAt(0)),
    )
}

export function CircuitSelection() {
  const navigate = useNavigate()
  const [search, setSearch] = useState("")

  const circuits = useCircuitStore((state) => state.circuits)
  const selectedCircuitId = useCircuitStore((state) => state.selectedCircuitId)
  const selectedLayoutId = useCircuitStore((state) => state.selectedLayoutId)
  const isLoading = useCircuitStore((state) => state.isLoading)
  const error = useCircuitStore((state) => state.error)
  const fetchCircuits = useCircuitStore((state) => state.fetchCircuits)
  const selectCircuit = useCircuitStore((state) => state.selectCircuit)
  const selectLayout = useCircuitStore((state) => state.selectLayout)

  useEffect(() => {
    void fetchCircuits()
  }, [fetchCircuits])

  const filteredCircuits = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase()
    if (!normalizedSearch) return circuits

    return circuits.filter((circuit) =>
      circuit.name.toLocaleLowerCase().includes(normalizedSearch) ||
      circuit.country.toLocaleLowerCase().includes(normalizedSearch) ||
      circuit.city.toLocaleLowerCase().includes(normalizedSearch),
    )
  }, [circuits, search])

  const selectedCircuit =
    circuits.find((circuit) => circuit.id === selectedCircuitId) ?? circuits[0]

  const selectedLayout = selectedCircuit?.layouts.find(
    (layout) => layout.id === selectedLayoutId,
  ) ?? selectedCircuit?.layouts.find(
    (layout) => layout.id === CURRENT_LAYOUT_ID,
  ) ?? selectedCircuit?.layouts[0]

  function handleConfirm() {
    if (!selectedCircuit || !selectedLayout) return
    navigate("/driver-team-selection")
  }

  return (
    <main className="relative min-h-svh bg-background text-foreground lg:h-svh lg:overflow-hidden">
      {/* Background */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_45%,rgba(220,38,38,0.12),transparent_40%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,rgba(0,0,0,0.25)_100%)]" />
      </div>

      {/* Racing line */}
      <div className="absolute left-0 top-0 h-1 w-full bg-primary" />

      <div className="relative z-10 flex min-h-svh flex-col lg:h-full lg:min-h-0">
        <div className="relative z-10 flex min-h-svh flex-col">
          {/* Header */}
          <header className="border-b border-border">
            <div className="container mx-auto px-6 py-6 lg:px-12 lg:py-8">
              <div className="flex items-center gap-6">
                <Button
                  variant="outline"
                  onClick={() => navigate("/")}
                  aria-label="Voltar ao menu principal"
                  className="h-11 w-11 shrink-0 rounded-none border-border bg-transparent p-0 hover:bg-accent sm:w-auto sm:px-4"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>

                <div>
                  <div className="mb-3 flex items-center gap-3">
                    <div className="h-1 w-10 bg-primary" />
                    <span className="text-xs font-bold uppercase tracking-[0.3em] text-primary">
                      F1 SIMULATOR
                    </span>
                  </div>

                  <h1 className="text-4xl font-black uppercase italic tracking-tighter sm:text-5xl">
                    Selecionar Circuito
                  </h1>
                  <p className="mt-3 text-sm text-muted-foreground">
                    Escolha o circuito para a sua corrida.
                  </p>
                </div>
              </div>
            </div>
          </header>

          {/* Main */}
          <div className="container mx-auto min-h-0 flex-1 px-6 py-6 lg:flex lg:px-12 lg:py-8">
            <div className="grid min-h-0 w-full grid-cols-1 gap-6 lg:h-full lg:flex-1 lg:grid-cols-[minmax(280px,360px)_1fr]">
              {/* Circuit list */}
              <section className="flex h-[280px] min-h-0 flex-col border border-border bg-card/40 lg:h-full">
                <div className="border-b border-border p-4">
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Buscar circuito ou país..."
                      className="h-11 rounded-none border-border bg-background pl-10"
                    />
                  </div>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
                  {isLoading ? (
                    <div className="flex h-40 items-center justify-center px-6 text-center text-sm text-muted-foreground">
                      Carregando circuitos...
                    </div>
                  ) : error ? (
                    <div className="flex h-40 flex-col items-center justify-center gap-3 px-6 text-center text-sm text-muted-foreground">
                      <span>{error}</span>
                      <Button variant="outline" size="sm" onClick={() => void fetchCircuits()}>
                        Tentar novamente
                      </Button>
                    </div>
                  ) : filteredCircuits.length > 0 ? (
                    <div>
                      {filteredCircuits.map((circuit) => {
                        const isSelected = circuit.id === selectedCircuit?.id

                        return (
                          <button
                            key={circuit.id}
                            type="button"
                            onClick={() => selectCircuit(circuit.id)}
                            className={[
                              "group relative flex w-full items-center gap-4 border-b border-border px-5 py-4 text-left transition-colors",
                              isSelected
                                ? "bg-primary text-primary-foreground"
                                : "bg-transparent hover:bg-accent",
                            ].join(" ")}
                          >
                            <div
                              className={[
                                "absolute left-0 top-0 h-full w-1 transition-opacity",
                                isSelected
                                  ? "bg-primary-foreground opacity-100"
                                  : "bg-primary opacity-0 group-hover:opacity-100",
                              ].join(" ")}
                            />

                            <span className="text-2xl leading-none">
                              {getFlagEmoji(circuit.countryCode)}
                            </span>

                            <div className="min-w-0 flex-1">
                              <div
                                className={[
                                  "truncate text-sm font-black uppercase tracking-wide",
                                  isSelected ? "text-primary-foreground" : "text-foreground",
                                ].join(" ")}
                              >
                                {circuit.name}
                              </div>
                              <div
                                className={[
                                  "mt-1 text-xs",
                                  isSelected ? "text-primary-foreground/70" : "text-muted-foreground",
                                ].join(" ")}
                              >
                                {circuit.country}
                              </div>
                            </div>

                            <ChevronDown
                              className={[
                                "h-4 w-4 -rotate-90 transition-transform",
                                isSelected ? "text-primary-foreground" : "text-muted-foreground",
                              ].join(" ")}
                            />
                          </button>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="flex h-40 items-center justify-center px-6 text-center text-sm text-muted-foreground">
                      Nenhum circuito encontrado.
                    </div>
                  )}
                </div>

                <div className="border-t border-border px-5 py-3">
                  <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
                    {filteredCircuits.length}{" "}
                    {filteredCircuits.length === 1 ? "circuito" : "circuitos"}
                  </span>
                </div>
              </section>

              {/* Circuit preview */}
              <section className="flex min-h-0 flex-col border border-border bg-card/40">
                {selectedCircuit && selectedLayout ? (
                  <>
                    {/* Circuit information */}
                    <div className="border-b border-border p-6 lg:p-8">
                      <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-start">
                        <div>
                          <div className="mb-3 flex items-center gap-3">
                            <span className="text-3xl">
                              {getFlagEmoji(selectedCircuit.countryCode)}
                            </span>
                            <span className="text-xs font-bold uppercase tracking-[0.25em] text-muted-foreground">
                              {selectedCircuit.country}
                            </span>
                          </div>

                          <h2 className="text-3xl font-black uppercase italic tracking-tight lg:text-4xl">
                            {selectedCircuit.name}
                          </h2>

                          <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
                            <MapPin className="h-4 w-4" />
                            <span>{selectedCircuit.city}</span>
                            <span>·</span>
                            <span>{selectedCircuit.country}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Track */}
                    <div className="relative min-h-0 flex-1 overflow-hidden bg-background/50 p-6 lg:p-8">
                      <div className="pointer-events-none absolute inset-0 opacity-30">
                        <div className="absolute left-1/2 top-1/2 h-px w-full -translate-x-1/2 bg-border" />
                        <div className="absolute left-1/2 top-1/2 h-full w-px -translate-y-1/2 bg-border" />
                      </div>

                      <div className="relative z-10 flex h-full w-full items-center justify-center p-8">
                        <img
                          className="h-full max-h-[360px] max-w-[720px]"
                          src={selectedLayout.svg}
                          alt={`Traçado ${selectedLayout.name} — ${selectedCircuit.name}`}
                        />
                      </div>
                    </div>

                    {/* Configuration */}
                    <div className="shrink-0 border-t border-border p-5 lg:p-6">
                      <div className="grid gap-5 sm:grid-cols-[1fr_auto] sm:items-center">
                        <div>
                          <label className="mb-2 block text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
                            Variação do circuito
                          </label>

                          <Select value={selectedLayout.id} onValueChange={selectLayout}>
                            <SelectTrigger className="h-12 w-full rounded-none border-border bg-background uppercase">
                              <SelectValue placeholder="Selecione o layout" />
                            </SelectTrigger>
                            <SelectContent>
                              {selectedCircuit.layouts.map((layout) => {
                                const label = layout.id === CURRENT_LAYOUT_ID
                                  ? `Atual — ${layout.name}`
                                  : `${layout.yearFrom ?? "Histórico"}${layout.yearTo ? `–${layout.yearTo}` : ""} — ${layout.name}`

                                return (
                                  <SelectItem key={layout.id} value={layout.id}>
                                    {label}
                                  </SelectItem>
                                )
                              })}
                            </SelectContent>
                          </Select>

                          <p className="mt-2 text-xs text-muted-foreground">
                            Selecione uma versão histórica para utilizar o traçado correspondente.
                          </p>
                        </div>

                        <div className="flex items-center justify-center sm:h-full">
                          <Button
                            onClick={handleConfirm}
                            disabled={isLoading || Boolean(error) || !selectedCircuit || !selectedLayout}
                            size="lg"
                            className="h-12 w-full rounded-none px-8 font-black uppercase tracking-wider sm:w-auto"
                          >
                            Confirmar
                            <span className="ml-3 text-lg">→</span>
                          </Button>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex min-h-[280px] flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
                    {isLoading ? "Carregando circuitos..." : "Nenhum circuito disponível."}
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
