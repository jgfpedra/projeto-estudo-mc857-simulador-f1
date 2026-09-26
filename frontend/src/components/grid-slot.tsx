import { useMemo, useState } from "react"
import { ArrowLeftRight, ChevronDown, Search, X } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"

import { NULL_DRIVER_ID, type Driver, flag } from "@/data/pilots"

export type GridSlotValue = {
  position: number
  driverId: string
}

type GridSlotProps = {
  slot: GridSlotValue
  drivers: Driver[]
  selectedDriverIds: Set<string>
  disabled?: boolean
  onSelect: (position: number, driverId: string) => void
}

export function GridSlot({
  slot,
  drivers,
  selectedDriverIds,
  disabled = false,
  onSelect,
}: GridSlotProps) {
  const [search, setSearch] = useState("")

  const driver = drivers.find((pilot) => pilot.id === slot.driverId)
  const isEmpty = slot.driverId === NULL_DRIVER_ID
  const normalizedSearch = search.trim().toLocaleLowerCase()

  const availableDrivers = useMemo(() => {
    return drivers
      .filter((pilot) => {
        const isCurrentDriver = pilot.id === slot.driverId
        if (isCurrentDriver) return false

        return (
          !normalizedSearch ||
          pilot.name.toLocaleLowerCase().includes(normalizedSearch) ||
          pilot.shortName.toLocaleLowerCase().includes(normalizedSearch) ||
          pilot.teamName.toLocaleLowerCase().includes(normalizedSearch) ||
          pilot.nationality.toLocaleLowerCase().includes(normalizedSearch)
        )
      })
      .sort((a, b) => {
        const aSelected = selectedDriverIds.has(a.id)
        const bSelected = selectedDriverIds.has(b.id)

        if (aSelected !== bSelected) return aSelected ? 1 : -1
        return a.name.localeCompare(b.name, "pt-BR")
      })
  }, [drivers, normalizedSearch, selectedDriverIds, slot.driverId])

  const handleOpenChange = (open: boolean) => {
    if (!open) setSearch("")
  }

  return (
    <DropdownMenu onOpenChange={handleOpenChange}>
      <div className="relative h-full w-full">
        <DropdownMenuTrigger asChild disabled={disabled}>
          <button
            type="button"
            className={[
              "group relative flex min-h-[112px] w-full min-w-0 items-center bg-card p-3 text-left uppercase transition-colors",
              "hover:bg-accent/70 focus:outline-none focus:ring-1 focus:ring-inset focus:ring-primary",
              isEmpty ? "border border-dashed border-border" : "border border-transparent",
              disabled ? "cursor-default opacity-100" : "cursor-pointer",
            ].join(" ")}
          >
            <div className="flex w-full min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center bg-background text-xs font-black italic">
                {String(slot.position).padStart(2, "0")}
              </div>

              {isEmpty ? (
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                    P{slot.position}
                  </div>
                  <div className="mt-1 text-sm font-black uppercase text-muted-foreground">
                    Selecionar piloto
                  </div>
                  <div className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground/70">
                    Vaga vazia
                  </div>
                </div>
              ) : (
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                      P{slot.position}
                    </span>
                    <span className="text-lg leading-none">
                      {flag(driver?.countryCode ?? "")}
                    </span>
                  </div>
                  <div className="mt-1 truncate text-sm font-black uppercase">
                    {driver?.name}
                  </div>
                  <div className="mt-1 truncate text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {driver?.teamName}
                  </div>
                </div>
              )}

              {!isEmpty && driver && (
                <span className="shrink-0 text-2xl font-black italic text-muted-foreground/40">
                  {driver.number}
                </span>
              )}

              {!disabled && (
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
              )}

            </div>
          </button>
        </DropdownMenuTrigger>
      </div>

      {!disabled && (
        <DropdownMenuContent
          align="start"
          sideOffset={6}
          className="z-[100] w-[var(--radix-dropdown-menu-trigger-width)] min-w-0 rounded-none border-border bg-popover p-1"
        >
          <div className="p-1">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => event.stopPropagation()}
                placeholder="Buscar piloto..."
                className="h-10 rounded-none border-border bg-background pl-9 text-xs font-bold uppercase placeholder:text-muted-foreground/60"
                autoFocus
              />
            </div>
          </div>

          {!isEmpty && driver && (
            <>
              <div className="flex items-center gap-3 px-3 py-2.5">
                <span className="text-lg leading-none">{flag(driver.countryCode)}</span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-black uppercase">{driver.name}</div>
                  <div className="mt-0.5 truncate text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    {driver.teamName} · {driver.nationality}
                  </div>
                </div>
                <span className="flex shrink-0 items-center gap-2 text-xs font-black italic text-muted-foreground">
                  {driver.number}
                  <button
                    type="button"
                    aria-label={`Remover ${driver.name} da posição ${slot.position}`}
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      onSelect(slot.position, NULL_DRIVER_ID)
                    }}
                    className="flex h-6 w-6 items-center justify-center border border-border text-muted-foreground transition-colors hover:border-destructive hover:bg-destructive hover:text-destructive-foreground"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </span>
              </div>
              <DropdownMenuSeparator className="bg-border" />
            </>
          )}

          <div className="max-h-[216px] overflow-y-auto pr-1">
            {availableDrivers.length > 0 ? (
              availableDrivers.map((pilot) => (
                <DropdownMenuItem
                  key={pilot.id}
                  onSelect={() => onSelect(slot.position, pilot.id)}
                  className={[
                    "cursor-pointer rounded-none py-3",
                    selectedDriverIds.has(pilot.id)
                      ? "bg-muted/70 hover:bg-muted"
                      : "",
                  ].join(" ")}
                >
                  <div className="flex min-w-0 w-full items-center gap-3">
                    <span className="text-lg leading-none">{flag(pilot.countryCode)}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <div className="truncate text-xs font-black uppercase">{pilot.name}</div>
                        {selectedDriverIds.has(pilot.id) && (
                          <span className="shrink-0 text-[9px] font-black uppercase tracking-wider text-primary">
                            Trocar
                          </span>
                        )}
                      </div>
                      <div className="mt-0.5 truncate text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        {pilot.teamName} · {pilot.nationality}
                      </div>
                    </div>
                    <span className="ml-auto flex shrink-0 items-center gap-2 text-right text-xs font-black italic text-muted-foreground">
                      {pilot.number}
                      {selectedDriverIds.has(pilot.id) && (
                        <ArrowLeftRight className="h-3.5 w-3.5 text-primary" />
                      )}
                    </span>
                  </div>
                </DropdownMenuItem>
              ))
            ) : (
              <div className="px-3 py-5 text-center text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Nenhum piloto encontrado
              </div>
            )}
          </div>
        </DropdownMenuContent>
      )}
    </DropdownMenu>
  )
}
