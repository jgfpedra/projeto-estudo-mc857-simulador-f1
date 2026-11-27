import { useEffect, useState } from "react"
import { Volume2, VolumeX } from "lucide-react"
import { speechSynthesis } from "@/services/speech-synthesis"

/** Controles globais: todos os painéis compartilham a mesma fila e voz. */
export function SpeechControls() {
  const [, setRevision] = useState(0)
  useEffect(() => speechSynthesis.subscribe(() => setRevision((value) => value + 1)), [])

  const { enabled, supported } = speechSynthesis.getState()
  const config = speechSynthesis.getConfig()
  const voices = speechSynthesis.getVoices()
    .filter((voice) => /^(pt|en)[-_]/i.test(voice.lang))
    .sort((a, b) => a.lang.localeCompare(b.lang) || a.name.localeCompare(b.name))

  return (
    <div className="pointer-events-auto flex items-center gap-1">
      {supported && voices.length > 0 && (
        <select
          value={config.voiceURI ?? ""}
          onChange={(event) => speechSynthesis.setVoice(event.target.value || null)}
          className="h-6 max-w-28 rounded border border-border/50 bg-background px-1 text-[9px] text-muted-foreground"
          aria-label="Voz do engenheiro"
          title="Voz do engenheiro"
        >
          <option value="">Automática (pt-BR)</option>
          {voices.map((voice) => (
            <option key={voice.voiceURI} value={voice.voiceURI}>{voice.name} ({voice.lang})</option>
          ))}
        </select>
      )}
      <button
        type="button"
        disabled={!supported}
        onClick={() => speechSynthesis.setEnabled(!enabled)}
        className={`p-1 rounded transition-colors ${enabled ? "text-green-400 hover:text-green-300" : "text-muted-foreground hover:text-red-400"}`}
        aria-label={enabled ? "Desativar síntese de voz" : "Ativar síntese de voz"}
        title={supported ? (enabled ? "TTS ativo" : "TTS desativado") : "Síntese de voz não suportada neste navegador"}
      >
        {enabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
      </button>
    </div>
  )
}
