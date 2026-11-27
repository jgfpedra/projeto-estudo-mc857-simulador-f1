/**
 * Síntese de voz (TTS) para o rádio do engenheiro.
 * Usa a Web Speech API nativa do navegador.
 */

type QueueItem = {
  text: string;
  priority: number; // maior = mais urgente
  timestamp: number;
};

type VoiceConfig = {
  lang: string;
  rate: number;
  pitch: number;
  volume: number;
};

const DEFAULT_CONFIG: VoiceConfig = {
  lang: "pt-BR",
  rate: 1.0,
  pitch: 1.0,
  volume: 1.0,
};

const URGENCY_CONFIG: Record<string, Partial<VoiceConfig>> = {
  alta: { rate: 1.1, pitch: 1.05, volume: 1.0 },
  media: { rate: 1.0, pitch: 1.0, volume: 0.95 },
  baixa: { rate: 0.95, pitch: 0.98, volume: 0.9 },
};

class SpeechSynthesisManager {
  private synth: SpeechSynthesis | null = null;
  private queue: QueueItem[] = [];
  private isSpeaking = false;
  private config: VoiceConfig = { ...DEFAULT_CONFIG };
  private enabled = true;
  private onStateChange?: (speaking: boolean) => void;

  constructor() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this.synth = window.speechSynthesis;
      this.loadVoices();
      // Voices podem carregar assincronamente
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  private loadVoices(): void {
    if (!this.synth) return;
    const voices = this.synth.getVoices();
    // Log para debug
    console.log("[TTS] Voices loaded:", voices.map(v => `${v.name} (${v.lang})`));
  }

  private selectVoice(lang: string): SpeechSynthesisVoice | null {
    if (!this.synth) return null;
    const voices = this.synth.getVoices();
    // Prioriza voz exata, depois por prefixo de idioma
    return (
      voices.find(v => v.lang === lang) ??
      voices.find(v => v.lang.startsWith(lang.split("-")[0])) ??
      voices.find(v => v.lang.startsWith("pt")) ??
      voices[0] ??
      null
    );
  }

  /** Habilita/desabilita TTS */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (!enabled) {
      this.stop();
      this.queue = [];
    }
  }

  /** Callback quando estado de fala muda */
  setOnStateChange(callback: (speaking: boolean) => void): void {
    this.onStateChange = callback;
  }

  /** Configurações globais */
  setConfig(config: Partial<VoiceConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /** Adiciona texto à fila de fala */
  speak(text: string, urgency: "baixa" | "media" | "alta" = "media"): void {
    if (!this.enabled || !this.synth || !text.trim()) return;

    const priority = urgency === "alta" ? 3 : urgency === "media" ? 2 : 1;

    // Evita duplicatas exatas consecutivas
    const last = this.queue[this.queue.length - 1];
    if (last && last.text === text && last.priority === priority) {
      return;
    }

    this.queue.push({
      text: text.trim(),
      priority,
      timestamp: Date.now(),
    });

    // Ordena por prioridade (maior primeiro), depois por timestamp (mais antigo primeiro)
    this.queue.sort((a, b) => b.priority - a.priority || a.timestamp - b.timestamp);

    this.processQueue();
  }

  /** Interrompe fala atual e limpa fila */
  stop(): void {
    if (this.synth) {
      this.synth.cancel();
    }
    this.isSpeaking = false;
    this.queue = [];
    this.onStateChange?.(false);
  }

  /** Pausa fala atual */
  pause(): void {
    if (this.synth && this.isSpeaking) {
      this.synth.pause();
    }
  }

  /** Retoma fala pausada */
  resume(): void {
    if (this.synth && this.isSpeaking) {
      this.synth.resume();
    }
  }

  private processQueue(): void {
    if (!this.synth || this.isSpeaking || this.queue.length === 0 || !this.enabled) {
      return;
    }

    const item = this.queue.shift()!;
    this.speakItem(item);
  }

  private speakItem(item: QueueItem): void {
    if (!this.synth || !this.enabled) {
      this.isSpeaking = false;
      this.processQueue();
      return;
    }

    this.isSpeaking = true;
    this.onStateChange?.(true);

    const utterance = new SpeechSynthesisUtterance(item.text);

    // Configura voz
    const voice = this.selectVoice(this.config.lang);
    if (voice) {
      utterance.voice = voice;
    }

    // Configura parâmetros
    utterance.lang = this.config.lang;
    utterance.rate = this.config.rate * (URGENCY_CONFIG[item.priority === 3 ? "alta" : item.priority === 2 ? "media" : "baixa"]?.rate ?? 1);
    utterance.pitch = this.config.pitch * (URGENCY_CONFIG[item.priority === 3 ? "alta" : item.priority === 2 ? "media" : "baixa"]?.pitch ?? 1);
    utterance.volume = this.config.volume * (URGENCY_CONFIG[item.priority === 3 ? "alta" : item.priority === 2 ? "media" : "baixa"]?.volume ?? 1);

    // Callbacks
    utterance.onstart = () => {
      this.isSpeaking = true;
      this.onStateChange?.(true);
    };

    utterance.onend = () => {
      this.isSpeaking = false;
      this.onStateChange?.(false);
      // Processa próximo na fila
      setTimeout(() => this.processQueue(), 50);
    };

    utterance.onerror = (event) => {
      console.warn("[TTS] Speech error:", event.error);
      this.isSpeaking = false;
      this.onStateChange?.(false);
      // Continua com próximo mesmo em erro
      setTimeout(() => this.processQueue(), 50);
    };

    this.synth.speak(utterance);
  }

  /** Retorna estado atual */
  getState(): { speaking: boolean; queueLength: number; enabled: boolean } {
    return {
      speaking: this.isSpeaking,
      queueLength: this.queue.length,
      enabled: this.enabled,
    };
  }

  /** Limpa fila mantendo fala atual */
  clearQueue(): void {
    this.queue = [];
  }
}

// Singleton
export const speechSynthesis = new SpeechSynthesisManager();

/** Hook React para usar TTS */
export function useSpeechSynthesis() {
  return {
    speak: (text: string, urgency?: "baixa" | "media" | "alta") => speechSynthesis.speak(text, urgency),
    stop: () => speechSynthesis.stop(),
    pause: () => speechSynthesis.pause(),
    resume: () => speechSynthesis.resume(),
    setEnabled: (enabled: boolean) => speechSynthesis.setEnabled(enabled),
    setConfig: (config: Partial<VoiceConfig>) => speechSynthesis.setConfig(config),
    setOnStateChange: (callback: (speaking: boolean) => void) => speechSynthesis.setOnStateChange(callback),
    getState: () => speechSynthesis.getState(),
    clearQueue: () => speechSynthesis.clearQueue(),
  };
}

export type { VoiceConfig };