/** Fila única de síntese de voz para todos os painéis do engenheiro. */

export type SpeechUrgency = 'baixa' | 'media' | 'alta'

export type VoiceConfig = {
  lang: string
  voiceURI?: string
  rate: number
  pitch: number
  volume: number
}

type QueueItem = {
  text: string
  priority: number
  timestamp: number
}

type UtteranceFactory = (text: string) => SpeechSynthesisUtterance

const DEFAULT_CONFIG: VoiceConfig = {
  lang: 'pt-BR',
  rate: 1,
  pitch: 1,
  volume: 1,
}

const URGENCY_CONFIG: Record<SpeechUrgency, Pick<VoiceConfig, 'rate' | 'pitch' | 'volume'>> = {
  alta: { rate: 1.1, pitch: 1.05, volume: 1 },
  media: { rate: 1, pitch: 1, volume: 0.95 },
  baixa: { rate: 0.95, pitch: 0.98, volume: 0.9 },
}

const normalizeLang = (lang: string) => lang.replace('_', '-').toLowerCase()

export class SpeechSynthesisManager {
  private queue: QueueItem[] = []
  private current: QueueItem | null = null
  private speaking = false
  private enabled = true
  private config: VoiceConfig = { ...DEFAULT_CONFIG }
  private listeners = new Set<() => void>()
  private activeId = 0

  constructor(
    private synth: SpeechSynthesis | null = typeof window !== 'undefined' && 'speechSynthesis' in window
      ? window.speechSynthesis
      : null,
    private createUtterance: UtteranceFactory = (text) => new SpeechSynthesisUtterance(text),
  ) {
    this.synth?.addEventListener('voiceschanged', () => this.emit())
  }

  private emit(): void {
    for (const listener of this.listeners) listener()
  }

  /** Assina mudanças de fala, fila, configuração e carregamento assíncrono de vozes. */
  subscribe(listener: () => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  getVoices(): SpeechSynthesisVoice[] {
    return this.synth?.getVoices() ?? []
  }

  getConfig(): VoiceConfig {
    return { ...this.config }
  }

  getState(): { speaking: boolean; queueLength: number; enabled: boolean; supported: boolean } {
    return {
      speaking: this.speaking,
      queueLength: this.queue.length,
      enabled: this.enabled,
      supported: this.synth !== null,
    }
  }

  setEnabled(enabled: boolean): void {
    this.enabled = enabled
    if (enabled) this.emit()
    else this.stop()
  }

  setConfig(config: Partial<VoiceConfig>): void {
    this.config = { ...this.config, ...config }
    this.emit()
  }

  /** Seleciona uma voz instalada; null restaura a escolha automática pt-BR. */
  setVoice(voiceURI: string | null): void {
    if (voiceURI === null) {
      this.config = { ...this.config, lang: DEFAULT_CONFIG.lang, voiceURI: undefined }
    } else {
      const voice = this.getVoices().find((candidate) => candidate.voiceURI === voiceURI)
      if (!voice) return
      this.config = { ...this.config, lang: voice.lang, voiceURI: voice.voiceURI }
    }
    this.emit()
  }

  private selectVoice(): SpeechSynthesisVoice | null {
    const voices = this.getVoices()
    if (voices.length === 0) return null

    if (this.config.voiceURI) {
      const selected = voices.find((voice) => voice.voiceURI === this.config.voiceURI)
      if (selected) return selected
    }

    // Português do Brasil, fallback explícito para Portugal e então inglês.
    for (const lang of [this.config.lang, 'pt-BR', 'pt-PT', 'en-US']) {
      const selected = voices.find((voice) => normalizeLang(voice.lang) === normalizeLang(lang))
      if (selected) return selected
    }
    for (const prefix of ['pt', 'en']) {
      const selected = voices.find((voice) => normalizeLang(voice.lang).startsWith(prefix))
      if (selected) return selected
    }
    return voices[0]
  }

  speak(text: string, urgency: SpeechUrgency = 'media'): void {
    const trimmed = text.trim()
    if (!this.enabled || !this.synth || !trimmed) return

    const priority = urgency === 'alta' ? 3 : urgency === 'media' ? 2 : 1
    // AiPanel e AiEngineer observam a mesma mensagem; não a enfileirar duas vezes.
    const duplicate = this.current?.text === trimmed && this.current.priority === priority
      || this.queue.some((item) => item.text === trimmed && item.priority === priority)
    if (duplicate) return

    this.queue.push({ text: trimmed, priority, timestamp: Date.now() })
    this.queue.sort((a, b) => b.priority - a.priority || a.timestamp - b.timestamp)
    this.emit()
    this.processQueue()
  }

  stop(): void {
    this.activeId += 1
    this.queue = []
    this.current = null
    this.speaking = false
    this.synth?.cancel()
    this.emit()
  }

  pause(): void {
    if (this.speaking) this.synth?.pause()
  }

  resume(): void {
    if (this.speaking) this.synth?.resume()
  }

  clearQueue(): void {
    this.queue = []
    this.emit()
  }

  private processQueue(): void {
    if (!this.synth || this.speaking || this.queue.length === 0 || !this.enabled) return
    const item = this.queue.shift()!
    this.current = item
    this.speaking = true
    const id = ++this.activeId
    this.emit()

    const utterance = this.createUtterance(item.text)
    const voice = this.selectVoice()
    if (voice) utterance.voice = voice
    utterance.lang = voice?.lang ?? this.config.lang

    const urgency: SpeechUrgency = item.priority === 3 ? 'alta' : item.priority === 2 ? 'media' : 'baixa'
    const adjustment = URGENCY_CONFIG[urgency]
    utterance.rate = this.config.rate * adjustment.rate
    utterance.pitch = this.config.pitch * adjustment.pitch
    utterance.volume = Math.min(1, this.config.volume * adjustment.volume)

    const finish = () => {
      // cancel() pode disparar onend/onerror depois de outra fala ter começado.
      if (id !== this.activeId) return
      this.current = null
      this.speaking = false
      this.emit()
      setTimeout(() => this.processQueue(), 0)
    }
    utterance.onstart = () => {
      if (id !== this.activeId) return
      this.speaking = true
      this.emit()
    }
    utterance.onend = finish
    utterance.onerror = (event) => {
      if (id === this.activeId) console.warn('[TTS] Speech error:', event.error)
      finish()
    }

    try {
      this.synth.speak(utterance)
    } catch (error) {
      console.warn('[TTS] Unable to start speech:', error)
      finish()
    }
  }
}

export const speechSynthesis = new SpeechSynthesisManager()

/** API estável para componentes que não precisam assinar o estado. */
export function useSpeechSynthesis() {
  return {
    speak: (text: string, urgency?: SpeechUrgency) => speechSynthesis.speak(text, urgency),
    stop: () => speechSynthesis.stop(),
    pause: () => speechSynthesis.pause(),
    resume: () => speechSynthesis.resume(),
    setEnabled: (enabled: boolean) => speechSynthesis.setEnabled(enabled),
    setConfig: (config: Partial<VoiceConfig>) => speechSynthesis.setConfig(config),
    setVoice: (voiceURI: string | null) => speechSynthesis.setVoice(voiceURI),
    getVoices: () => speechSynthesis.getVoices(),
    getState: () => speechSynthesis.getState(),
    getConfig: () => speechSynthesis.getConfig(),
    clearQueue: () => speechSynthesis.clearQueue(),
    subscribe: (listener: () => void) => speechSynthesis.subscribe(listener),
  }
}
