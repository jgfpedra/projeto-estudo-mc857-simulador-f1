type SectionProps = {
  step: string
  title: string
  description: string
  action?: React.ReactNode
  children: React.ReactNode
}

export function Section({ step, title, description, action, children }: SectionProps) {
  return (
    <section className="border border-border bg-card/40">
      <div className="flex items-start justify-between gap-4 border-b border-border p-5">
        <div className="flex items-start gap-4">
          <span className="text-2xl font-black italic text-muted-foreground/40">{step}</span>
          <div>
            <h2 className="text-lg font-black uppercase tracking-wide">{title}</h2>
            <p className="mt-1 text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </section>
  )
}