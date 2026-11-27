/** Fila única de síntese de voz para todos os painéis do engenheiro. */
import { env } from "@/config/env"

const RADIO_URL = `${(env.apiUrl ?? "").replace(/\/$/, "")}/races/radio/audio`


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
  expiresAt: number
  noticeKey: string
}

type UtteranceFactory = (text: string) => SpeechSynthesisUtterance

const DEFAULT_CONFIG: VoiceConfig = {
  lang: 'pt-BR',
  rate: 0.82,
  pitch: 1,
  volume: 1,
}

const RADIO_PRIORITIES: SpeechUrgency[] = ['alta', 'media', 'baixa']
const RADIO_INTERVAL_MS = { alta: 8_000, media: 20_000, baixa: 30_000 }
const REPEAT_INTERVAL_MS = { alta: 20_000, media: 30_000, baixa: 35_000 }
const PENDING_GRACE_MS = 5_000
const RADIO_START_TIMEOUT_MS = 6_000
const AUDIO_STALL_TIMEOUT_MS = 8_000
const NATURAL_VOICE = /natural|neural|premium|enhanced/i

// WAV silencioso: libera a reprodução de áudio no Firefox/Zen após o clique.
const SILENT_WAV =
  'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA='

const API_BASE_URL = (env.apiUrl ?? '').replace(/\/$/, '')

const normalizeLang = (lang: string) => lang.replace('_', '-').toLowerCase()

const canUseServerVoice = () => typeof window !== 'undefined' && typeof fetch === 'function'

export class SpeechSynthesisManager {
  #pending = new Map<SpeechUrgency, QueueItem>()
  #pendingTimer: ReturnType<typeof setTimeout> | undefined
  #speaking = false
  #enabled = true
  #config: VoiceConfig = { ...DEFAULT_CONFIG }
  #listeners = new Set<() => void>()
  #activeId = 0
  #audio: HTMLAudioElement | null = null
  #audioRequest: AbortController | null = null
  #watchdogTimer: ReturnType<typeof setTimeout> | undefined
  #restartWatchdog: (() => void) | null = null
  #paused = false
  #lastSpokenAt = -Infinity
  #recentNotices = new Map<string, number>()
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
      queueLength: this.#pending.size,
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
    if (!this.#enabled || !trimmed) return
    if (!this.#synth && !canUseServerVoice()) return

    const now = Date.now()
    for (const [key, time] of this.#recentNotices) {
      if (now - time >= REPEAT_INTERVAL_MS.baixa) this.#recentNotices.delete(key)
    }

    // Keep only the latest advice at each urgency while the radio is busy.
    this.#pending.set(urgency, {
      text: trimmed,
      expiresAt: now + RADIO_INTERVAL_MS[urgency] + PENDING_GRACE_MS,
      noticeKey: `${urgency}:${subject ?? trimmed}`,
    })
    this.#emit()
    this.#processQueue()
  }

  stop(): void {
    this.#activeId += 1
    this.#resetPending()
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
    this.#resetPending()
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
  }

  #watch(timeoutMs: number, expire: () => void): void {
    this.#restartWatchdog = () => {
      clearTimeout(this.#watchdogTimer)
      if (!this.#paused) this.#watchdogTimer = setTimeout(expire, timeoutMs)
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

    this.#watch(RADIO_START_TIMEOUT_MS, () => fallback('Tempo de geração excedido'))
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
