/** Fila única de síntese de voz para todos os painéis do engenheiro. */
import { env } from "@/config/env"

const RADIO_URL = `${(env.apiUrl ?? "").replace(/\/$/, "")}/races/radio/audio`


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
  noticeKey: string
}

type UtteranceFactory = (text: string) => SpeechSynthesisUtterance

const DEFAULT_CONFIG: VoiceConfig = {
  lang: 'pt-BR',
  rate: 0.82,
  pitch: 1,
  volume: 1,
}

const RADIO_INTERVAL_MS = { alta: 8_000, media: 20_000 }
const REPEAT_INTERVAL_MS = 35_000
const MAX_PENDING_AGE_MS = 10_000
const NATURAL_VOICE = /natural|neural|premium|enhanced/i

const normalizeLang = (lang: string) => lang.replace('_', '-').toLowerCase()

function preferredVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  return voices.find((voice) => NATURAL_VOICE.test(voice.name))
    ?? voices.find((voice) => voice.default)
    ?? voices[0]
}

export class SpeechSynthesisManager {
  #queue: QueueItem[] = []
  #speaking = false
  #enabled = true
  #config: VoiceConfig = { ...DEFAULT_CONFIG }
  #listeners = new Set<() => void>()
  #activeId = 0
  #audio: HTMLAudioElement | null = null
  #audioUrl: string | null = null
  #audioRequest: AbortController | null = null
  #lastSpokenAt = -Infinity
  #recentNotices = new Map<string, number>()
  #synth: SpeechSynthesis | null
  #createUtterance: UtteranceFactory

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
      supported: this.#synth !== null || (typeof window !== 'undefined' && typeof Audio !== 'undefined'),
    }
  }

  setEnabled(enabled: boolean): void {
    this.#enabled = enabled
    if (enabled) this.#emit()
    else this.stop()
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
      const selected = preferredVoice(voices.filter((voice) => normalizeLang(voice.lang) === normalizeLang(lang)))
      if (selected) return selected
    }
    for (const prefix of ['pt', 'en']) {
      const selected = preferredVoice(voices.filter((voice) => normalizeLang(voice.lang).startsWith(prefix)))
      if (selected) return selected
    }
    return voices[0]
  }

  speak(text: string, urgency: SpeechUrgency = 'media', subject?: string): void {
    const trimmed = text.trim()
    if (!this.#enabled || !this.getState().supported || !trimmed || urgency === 'baixa') return

    const now = Date.now()
    if (now - this.#lastSpokenAt < RADIO_INTERVAL_MS[urgency]) return

    const priority = urgency === 'alta' ? 3 : 2
    const noticeKey = `${urgency}:${subject ?? trimmed}`
    for (const [key, time] of this.#recentNotices) {
      if (now - time >= REPEAT_INTERVAL_MS) this.#recentNotices.delete(key)
    }
    if (this.#recentNotices.has(noticeKey)) return

    // Keep one pending notice so the radio does not read a backlog of old advice.
    const pending = this.#queue[0]
    if (pending && (pending.noticeKey === noticeKey || pending.priority > priority)) return
    this.#queue = [{ text: trimmed, priority, timestamp: now, noticeKey }]
    this.#emit()
    this.#processQueue()
  }

  stop(): void {
    this.#activeId += 1
    this.#queue = []
    this.#speaking = false
    this.#lastSpokenAt = -Infinity
    this.#recentNotices.clear()
    this.#synth?.cancel()
    this.#audioRequest?.abort()
    this.#audioRequest = null
    this.#audio?.pause()
    this.#audio = null
    if (this.#audioUrl) URL.revokeObjectURL(this.#audioUrl)
    this.#audioUrl = null
    this.#emit()
  }

  pause(): void {
    if (this.#audio) this.#audio.pause()
    else if (this.#speaking) this.#synth?.pause()
  }

  resume(): void {
    if (this.#audio) void this.#audio.play().catch((error) => console.warn('[Rádio] Erro ao continuar:', error))
    else if (this.#speaking) this.#synth?.resume()
  }

  clearQueue(): void {
    this.#queue = []
    this.#emit()
  }

  #processQueue(): void {
    if (!this.getState().supported || this.#speaking || this.#queue.length === 0 || !this.#enabled) return
    const item = this.#queue.shift()!
    const now = Date.now()
    if (now - item.timestamp > MAX_PENDING_AGE_MS) {
      this.#emit()
      return
    }
    this.#lastSpokenAt = now
    this.#recentNotices.set(item.noticeKey, now)
    this.#speaking = true
    const id = ++this.#activeId
    this.#emit()

    if (typeof window !== 'undefined' && !this.#config.voiceURI) {
      void this.#playNeural(item, id)
      return
    }
    this.#playBrowser(item, id)
  }

  async #playNeural(item: QueueItem, id: number): Promise<void> {
    const controller = new AbortController()
    this.#audioRequest = controller
    try {
      const response = await fetch(RADIO_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: item.text.slice(0, 480) }),
        signal: controller.signal,
      })
      if (!response.ok) throw new Error('Voz neural indisponível')
      const blob = await response.blob()
      if (id !== this.#activeId) return
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      this.#audioUrl = url
      this.#audio = audio
      const finish = () => {
        if (id !== this.#activeId) return
        URL.revokeObjectURL(url)
        this.#audioUrl = null
        this.#audio = null
        this.#audioRequest = null
        this.#speaking = false
        this.#emit()
        this.#processQueue()
      }
      audio.onended = finish
      audio.onerror = () => {
        if (id !== this.#activeId || this.#audio !== audio) return
        URL.revokeObjectURL(url)
        this.#audioUrl = null
        this.#audio = null
        this.#audioRequest = null
        this.#playBrowser(item, id)
      }
      await audio.play()
    } catch (error) {
      if (id !== this.#activeId || controller.signal.aborted || this.#audioRequest !== controller) return
      this.#audioRequest = null
      if (this.#audioUrl) URL.revokeObjectURL(this.#audioUrl)
      this.#audioUrl = null
      this.#audio = null
      this.#audioRequest = null
      console.warn('[Rádio] Voz neural indisponível, usando a voz do navegador:', error)
      this.#playBrowser(item, id)
    }
  }

  #playBrowser(item: QueueItem, id: number): void {
    const utterance = this.#createUtterance(item.text)
    const voice = this.#selectVoice()
    if (voice) utterance.voice = voice
    utterance.lang = voice?.lang ?? this.#config.lang

    utterance.rate = this.#config.rate
    utterance.pitch = this.#config.pitch
    utterance.volume = this.#config.volume

    const finish = () => {
      // cancel() pode disparar onend/onerror depois de outra fala ter começado.
      if (id !== this.#activeId) return
      this.#speaking = false
      this.#emit()
      setTimeout(() => this.#processQueue(), 0)
    }
    utterance.onstart = () => {
      if (id !== this.#activeId) return
      this.#speaking = true
      this.#emit()
    }
    utterance.onend = finish
    utterance.onerror = (event) => {
      if (id === this.#activeId) console.warn('[TTS] Speech error:', event.error)
      finish()
    }

    try {
      if (!this.#synth) { finish(); return }
      this.#synth.speak(utterance)
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