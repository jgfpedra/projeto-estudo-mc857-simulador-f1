import { useEffect, useState } from 'react'
import { speechSynthesis } from './SpeechSynthesis'

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
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      {supported && voices.length > 0 && (
        <select
          value={config.voiceURI ?? ''}
          onChange={(event) => speechSynthesis.setVoice(event.target.value || null)}
          aria-label="Voz do engenheiro"
          style={{ maxWidth: 145, background: '#15151e', color: '#c4c4cd', border: '1px solid #3a3a48', font: '10px sans-serif' }}
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
        aria-label={enabled ? 'Desativar síntese de voz' : 'Ativar síntese de voz'}
        title={supported ? (enabled ? 'TTS ativo' : 'TTS desativado') : 'Síntese de voz não suportada neste navegador'}
        style={{ all: 'unset', cursor: supported ? 'pointer' : 'not-allowed', color: enabled ? '#3ecf5a' : '#9a9aa8' }}
      >
        {enabled ? '🔊' : '🔇'}
      </button>
    </span>
  )
}
