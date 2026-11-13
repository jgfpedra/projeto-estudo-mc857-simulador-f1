type ToggleButtonProps = {
  active: boolean
  onClick: () => void
  labelOn: string
  labelOff: string
}

export function ToggleButton({ active, onClick, labelOn, labelOff }: ToggleButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={[
        "shrink-0 border px-4 py-2 text-[11px] font-black uppercase tracking-wider transition-colors",
        active
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-background text-muted-foreground hover:bg-accent hover:text-foreground",
      ].join(" ")}
    >
      {active ? labelOn : labelOff}
    </button>
  )
}