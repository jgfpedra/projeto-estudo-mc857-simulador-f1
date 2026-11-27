/** Fila única de síntese de voz para todos os painéis do engenheiro. */

import { env } from "@/config/env"

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

// WAV silencioso: libera a reprodução de áudio no Firefox/Zen após o clique.
const SILENT_WAV =
  'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA='

const API_BASE_URL = (env.apiUrl ?? '').replace(/\/$/, '')

const normalizeLang = (lang: string) => lang.replace('_', '-').toLowerCase()

const canUseServerVoice = () => typeof window !== 'undefined' && typeof fetch === 'function'

export class SpeechSynthesisManager {
  #queue: QueueItem[] = []
  #current: QueueItem | null = null
  #speaking = false
  #enabled = true
  #config: VoiceConfig = { ...DEFAULT_CONFIG }
  #listeners = new Set<() => void>()
  #activeId = 0
  #synth: SpeechSynthesis | null
  #createUtterance: UtteranceFactory
  #audio: HTMLAudioElement | null = null
  #abort: AbortController | null = null

  constructor(
    synth?: SpeechSynthesis | null,
    createUtterance?: UtteranceFactory,
  ) {
    this.#synth = synth ?? (typeof window !== 'undefined' && 'speechSynthesis' in window
      ? window.speechSynthesis
      : null)
    this.#createUtterance = createUtterance ?? ((text) => new SpeechSynthesisUtterance(text))
    this.#synth?.addEventListener('voiceschanged', () => this.#emit())
  }

  #emit(): void {
    for (const listener of this.#listeners) listener()
  }

  /** Assina mudanças de fala, fila, configuração e carregamento assíncrono de vozes. */
  subscribe(listener: () => void): () => void {
    this.#listeners.add(listener)
    return () => this.#listeners.delete(listener)
  }

  getVoices(): SpeechSynthesisVoice[] {
    return this.#synth?.getVoices() ?? []
  }

  getConfig(): VoiceConfig {
    return { ...this.#config }
  }

  getState(): { speaking: boolean; queueLength: number; enabled: boolean; supported: boolean } {
    return {
      speaking: this.#speaking,
      queueLength: this.#queue.length,
      enabled: this.#enabled,
      supported: this.#synth !== null || canUseServerVoice(),
    }
  }

  /** Desbloqueia a síntese durante um gesto do usuário (Firefox/Zen e políticas de autoplay). */
  unlock(): void {
    if (!this.#enabled) return
    this.#synth?.resume()
    try {
      const audio = new Audio(SILENT_WAV)
      audio.volume = 0
      void audio.play().then(() => audio.pause()).catch(() => {})
    } catch {
      // Sem áudio disponível neste contexto; a voz do servidor ainda pode funcionar.
    }
  }

  setEnabled(enabled: boolean): void {
    this.#enabled = enabled
    if (enabled) {
      this.unlock()
      this.#emit()
    } else this.stop()
  }

  setConfig(config: Partial<VoiceConfig>): void {
    this.#config = { ...this.#config, ...config }
    this.#emit()
  }

  /** Seleciona uma voz instalada; null restaura a escolha automática pt-BR. */
  setVoice(voiceURI: string | null): void {
    if (voiceURI === null) {
      this.#config = { ...this.#config, lang: DEFAULT_CONFIG.lang, voiceURI: undefined }
    } else {
      const voice = this.getVoices().find((candidate) => candidate.voiceURI === voiceURI)
      if (!voice) return
      this.#config = { ...this.#config, lang: voice.lang, voiceURI: voice.voiceURI }
    }
    this.#emit()
  }

  #selectVoice(): SpeechSynthesisVoice | null {
    const voices = this.getVoices()
    if (voices.length === 0) return null

    if (this.#config.voiceURI) {
      const selected = voices.find((voice) => voice.voiceURI === this.#config.voiceURI)
      if (selected) return selected
    }

    // Português do Brasil, fallback explícito para Portugal e então inglês.
    for (const lang of [this.#config.lang, 'pt-BR', 'pt-PT', 'en-US']) {
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
    if (!this.#enabled || !trimmed) return
    if (!this.#synth && !canUseServerVoice()) return

    const priority = urgency === 'alta' ? 3 : urgency === 'media' ? 2 : 1
    // AiPanel e AiEngineer observam a mesma mensagem; não a enfileirar duas vezes.
    const duplicate = this.#current?.text === trimmed && this.#current.priority === priority
      || this.#queue.some((item) => item.text === trimmed && item.priority === priority)
    if (duplicate) return

    this.#queue.push({ text: trimmed, priority, timestamp: Date.now() })
    this.#queue.sort((a, b) => b.priority - a.priority || a.timestamp - b.timestamp)
    this.#emit()
    this.#processQueue()
  }

  stop(): void {
    this.#activeId += 1
    this.#queue = []
    this.#current = null
    this.#speaking = false
    this.#abort?.abort()
    this.#abort = null
    if (this.#audio) {
      this.#audio.onended = null
      this.#audio.onerror = null
      this.#audio.pause()
      this.#audio.src = ''
      this.#audio = null
    }
    this.#synth?.cancel()
    this.#emit()
  }

  pause(): void {
    if (this.#speaking) {
      this.#synth?.pause()
      this.#audio?.pause()
    }
  }

  resume(): void {
    if (this.#speaking) {
      this.#synth?.resume()
      void this.#audio?.play().catch(() => {})
    }
  }

  clearQueue(): void {
    this.#queue = []
    this.#emit()
  }

  #complete(id: number): void {
    // cancel()/stop() pode disparar onend/onerror depois de outra fala ter começado.
    if (id !== this.#activeId) return
    this.#current = null
    this.#speaking = false
    this.#emit()
    setTimeout(() => this.#processQueue(), 0)
  }

  #processQueue(): void {
    if (this.#speaking || this.#queue.length === 0 || !this.#enabled) return
    if (!this.#synth && !canUseServerVoice()) return

    const item = this.#queue.shift()!
    this.#current = item
    this.#speaking = true
    const id = ++this.#activeId
    this.#emit()

    const voice = this.#synth ? this.#selectVoice() : null
    if (voice) this.#speakWithBrowser(item, voice, id, true)
    else this.#speakWithServer(item, id)
  }

  #urgencyFor(item: QueueItem): SpeechUrgency {
    return item.priority === 3 ? 'alta' : item.priority === 2 ? 'media' : 'baixa'
  }

  #speakWithBrowser(item: QueueItem, voice: SpeechSynthesisVoice, id: number, allowServerFallback: boolean): void {
    const utterance = this.#createUtterance(item.text)
    utterance.voice = voice
    utterance.lang = voice.lang ?? this.#config.lang

    const adjustment = URGENCY_CONFIG[this.#urgencyFor(item)]
    utterance.rate = this.#config.rate * adjustment.rate
    utterance.pitch = this.#config.pitch * adjustment.pitch
    utterance.volume = Math.min(1, this.#config.volume * adjustment.volume)

    let finished = false
    const finish = () => {
      if (finished) return
      finished = true
      this.#complete(id)
    }
    utterance.onstart = () => {
      if (id !== this.#activeId) return
      this.#speaking = true
      this.#emit()
    }
    utterance.onend = finish
    utterance.onerror = (event) => {
      if (finished) return
      finished = true
      const error = (event as SpeechSynthesisErrorEvent).error
      console.warn('[TTS] Speech error:', error)
      // Voz do sistema quebrada (ex.: sem speech-dispatcher): tenta o servidor.
      if (allowServerFallback && canUseServerVoice() && error !== 'interrupted' && error !== 'canceled') {
        this.#speakWithServer(item, id)
        return
      }
      this.#complete(id)
    }

    try {
      this.#synth!.speak(utterance)
    } catch (error) {
      console.warn('[TTS] Unable to start speech:', error)
      if (allowServerFallback && canUseServerVoice()) this.#speakWithServer(item, id)
      else this.#complete(id)
    }
  }

  #speakWithServer(item: QueueItem, id: number): void {
    if (!canUseServerVoice()) {
      this.#complete(id)
      return
    }
    const controller = new AbortController()
    this.#abort = controller
    const url = `${API_BASE_URL}/tts?text=${encodeURIComponent(item.text)}&lang=${encodeURIComponent(this.#config.lang)}`

    let finished = false
    const finish = () => {
      if (finished) return
      finished = true
      if (this.#abort === controller) this.#abort = null
      this.#complete(id)
    }

    void fetch(url, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const blob = await response.blob()
        if (id !== this.#activeId) return

        const objectUrl = URL.createObjectURL(blob)
        const audio = new Audio(objectUrl)
        this.#audio = audio
        const release = () => {
          URL.revokeObjectURL(objectUrl)
          if (this.#audio === audio) this.#audio = null
        }
        audio.onended = () => { release(); finish() }
        audio.onerror = () => { release(); finish() }
        await audio.play()
      })
      .catch((error: unknown) => {
        if ((error as { name?: string } | null)?.name === 'AbortError') return
        console.warn('[TTS] Falha na voz do servidor:', error)
        finish()
      })
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
