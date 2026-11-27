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

const normalizeLang = (lang: string) => lang.replace('_', '-').toLowerCase()

function preferredVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  return voices.find((voice) => NATURAL_VOICE.test(voice.name))
    ?? voices.find((voice) => voice.default)
    ?? voices[0]
}

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
    if (!this.#enabled || !this.getState().supported || !trimmed) return

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
    this.#paused = false
    this.#lastSpokenAt = -Infinity
    this.#recentNotices.clear()
    this.#clearWatchdog()
    this.#releaseAudio()
    this.#synth?.cancel()
    this.#emit()
  }

  pause(): void {
    if (!this.#speaking || (this.#audioRequest && !this.#audio)) return
    this.#paused = true
    clearTimeout(this.#watchdogTimer)
    if (this.#audio) this.#audio.pause()
    else this.#synth?.pause()
  }

  resume(): void {
    if (!this.#paused) return
    this.#paused = false
    this.#restartWatchdog?.()
    if (this.#audio) void this.#audio.play().catch((error) => console.warn('[Rádio] Erro ao continuar:', error))
    else this.#synth?.resume()
  }

  clearQueue(): void {
    this.#resetPending()
    this.#emit()
  }

  #resetPending(): void {
    clearTimeout(this.#pendingTimer)
    this.#pendingTimer = undefined
    this.#pending.clear()
  }

  #processQueue(): void {
    clearTimeout(this.#pendingTimer)
    this.#pendingTimer = undefined
    if (!this.#enabled || this.#speaking || this.#pending.size === 0) return

    const now = Date.now()
    for (const urgency of RADIO_PRIORITIES) {
      const item = this.#pending.get(urgency)
      if (!item) continue

      const lastNoticeAt = this.#recentNotices.get(item.noticeKey) ?? -Infinity
      const playAt = Math.max(now, this.#lastSpokenAt + RADIO_INTERVAL_MS[urgency],
        lastNoticeAt + REPEAT_INTERVAL_MS[urgency])
      if (playAt > item.expiresAt) {
        this.#pending.delete(urgency)
        continue
      }
      if (playAt > now) {
        this.#pendingTimer = setTimeout(() => this.#processQueue(), playAt - now)
        this.#emit()
        return
      }
      this.#resetPending()
      this.#startSpeech(item, now)
      return
    }
    this.#emit()
  }

  #startSpeech(item: QueueItem, now: number): void {
    this.#lastSpokenAt = now
    this.#recentNotices.set(item.noticeKey, now)
    this.#speaking = true
    const id = ++this.#activeId
    this.#emit()

    if (typeof window !== 'undefined' && !this.#config.voiceURI) {
      void this.#playNeural(item, id)
    } else {
      this.#playBrowser(item, id)
    }
  }

  #watch(timeoutMs: number, expire: () => void): void {
    this.#restartWatchdog = () => {
      clearTimeout(this.#watchdogTimer)
      if (!this.#paused) this.#watchdogTimer = setTimeout(expire, timeoutMs)
    }
    this.#restartWatchdog()
  }

  #clearWatchdog(): void {
    clearTimeout(this.#watchdogTimer)
    this.#watchdogTimer = undefined
    this.#restartWatchdog = null
  }

  #releaseAudio(): void {
    this.#audioRequest?.abort()
    this.#audioRequest = null
    const audio = this.#audio
    this.#audio = null
    if (!audio) return
    audio.onended = null
    audio.onerror = null
    audio.ontimeupdate = null
    audio.pause()
    URL.revokeObjectURL(audio.src)
  }

  #finish(id: number, cancelBrowserSpeech = false): void {
    if (id !== this.#activeId) return
    // Eventos atrasados de uma fala não podem encerrar a próxima.
    this.#activeId += 1
    this.#speaking = false
    this.#paused = false
    this.#clearWatchdog()
    this.#releaseAudio()
    if (cancelBrowserSpeech) this.#synth?.cancel()
    this.#emit()
    this.#processQueue()
  }

  async #playNeural(item: QueueItem, id: number): Promise<void> {
    const controller = new AbortController()
    this.#audioRequest = controller
    const isCurrent = () => id === this.#activeId && this.#audioRequest === controller
    const fallback = (error: unknown) => {
      if (!isCurrent()) return
      this.#clearWatchdog()
      this.#releaseAudio()
      console.warn('[Rádio] Voz neural indisponível, usando a voz do navegador:', error)
      this.#playBrowser(item, id)
    }

    this.#watch(RADIO_START_TIMEOUT_MS, () => fallback('Tempo de geração excedido'))
    try {
      const response = await fetch(RADIO_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: item.text.slice(0, 480) }),
        signal: controller.signal,
      })
      if (!response.ok) throw new Error('Voz neural indisponível')
      const blob = await response.blob()
      if (!isCurrent()) return

      const audio = new Audio()
      this.#audio = audio
      audio.src = URL.createObjectURL(blob)
      let lastPosition = 0
      audio.onended = () => {
        if (isCurrent()) this.#finish(id)
      }
      audio.onerror = () => fallback(audio.error)
      audio.ontimeupdate = () => {
        if (!isCurrent() || audio.currentTime <= lastPosition) return
        lastPosition = audio.currentTime
        this.#restartWatchdog?.()
      }
      this.#watch(AUDIO_STALL_TIMEOUT_MS, () => {
        if (lastPosition === 0) {
          fallback('A reprodução não iniciou')
        } else {
          console.warn('[Rádio] Reprodução interrompida')
          this.#finish(id)
        }
      })
      await audio.play()
    } catch (error) {
      fallback(error)
    }
  }

  #playBrowser(item: QueueItem, id: number): void {
    if (!this.#synth) {
      this.#finish(id)
      return
    }

    try {
      const utterance = this.#createUtterance(item.text)
      const voice = this.#selectVoice()
      if (voice) utterance.voice = voice
      utterance.lang = voice?.lang ?? this.#config.lang
      utterance.rate = this.#config.rate
      utterance.pitch = this.#config.pitch
      utterance.volume = this.#config.volume

      const expire = () => {
        console.warn('[Rádio] A voz do navegador parou de responder')
        this.#finish(id, true)
      }
      this.#watch(RADIO_START_TIMEOUT_MS, expire)
      utterance.onstart = () => {
        if (id !== this.#activeId) return
        const durationMs = 5_000 + (item.text.length * 100) / utterance.rate
        this.#watch(Math.max(12_000, durationMs), expire)
      }
      utterance.onend = () => this.#finish(id)
      utterance.onerror = (event) => {
        if (id !== this.#activeId) return
        console.warn('[Rádio] Erro na voz do navegador:', event.error)
        this.#finish(id)
      }
      this.#synth.speak(utterance)
    } catch (error) {
      console.warn('[Rádio] Erro ao iniciar a voz do navegador:', error)
      this.#finish(id)
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
