import { afterEach, describe, expect, it, vi } from 'vitest'
import { SpeechSynthesisManager } from './SpeechSynthesis'

type FakeUtterance = {
  text: string
  voice: SpeechSynthesisVoice | null
  lang: string
  rate: number
  pitch: number
  volume: number
  onstart: (() => void) | null
  onend: (() => void) | null
  onerror: ((event: SpeechSynthesisErrorEvent) => void) | null
}

function voice(lang: string): SpeechSynthesisVoice {
  return { lang, name: `Voz ${lang}`, voiceURI: lang } as SpeechSynthesisVoice
}

function setup(voices: SpeechSynthesisVoice[] = [voice('pt-BR')]) {
  const spoken: FakeUtterance[] = []
  const cancel = vi.fn()
  const synth = {
    getVoices: () => voices,
    addEventListener: () => undefined,
    speak: (utterance: SpeechSynthesisUtterance) => spoken.push(utterance as unknown as FakeUtterance),
    cancel,
    pause: () => undefined,
    resume: () => undefined,
  } as unknown as SpeechSynthesis
  const manager = new SpeechSynthesisManager(synth, (text) => ({
    text,
    voice: null,
    lang: '',
    rate: 1,
    pitch: 1,
    volume: 1,
    onstart: null,
    onend: null,
    onerror: null,
  }) as unknown as SpeechSynthesisUtterance)
  return { manager, spoken, cancel }
}

afterEach(() => {
  vi.useRealTimers()
})

describe('SpeechSynthesisManager', () => {
  it('usa pt-BR e tem fallbacks explícitos para pt-PT e en-US', () => {
    const br = setup([voice('pt-PT'), voice('pt-BR')])
    br.manager.speak('teste')
    expect(br.spoken[0].voice?.lang).toBe('pt-BR')

    const pt = setup([voice('en-US'), voice('pt-PT')])
    pt.manager.speak('teste')
    expect(pt.spoken[0].voice?.lang).toBe('pt-PT')
    expect(pt.spoken[0].lang).toBe('pt-PT')

    const en = setup([voice('en-US'), voice('fr-FR')])
    en.manager.speak('teste')
    expect(en.spoken[0].voice?.lang).toBe('en-US')
  })

  it('respeita a voz escolhida pelo usuário', () => {
    const { manager, spoken } = setup([voice('pt-BR'), voice('en-US')])
    manager.setVoice('en-US')
    manager.speak('warning', 'alta')

    expect(spoken[0].voice?.voiceURI).toBe('en-US')
    expect(spoken[0].lang).toBe('en-US')
    expect(spoken[0].rate).toBeCloseTo(1.1)
  })

  it('serializa a fila, prioriza urgência e remove duplicatas entre painéis', () => {
    vi.useFakeTimers()
    const { manager, spoken } = setup()
    manager.speak('baixa', 'baixa')
    manager.speak('média', 'media')
    manager.speak('alta', 'alta')
    manager.speak('alta', 'alta')

    expect(spoken.map((item) => item.text)).toEqual(['baixa'])
    expect(manager.getState().queueLength).toBe(2)

    spoken[0].onend?.()
    vi.runAllTimers()
    expect(spoken.map((item) => item.text)).toEqual(['baixa', 'alta'])

    spoken[1].onend?.()
    vi.runAllTimers()
    expect(spoken.map((item) => item.text)).toEqual(['baixa', 'alta', 'média'])
  })

  it('interrompe a fala e ignora o callback antigo após cancelamento', () => {
    vi.useFakeTimers()
    const { manager, spoken, cancel } = setup()
    manager.speak('atual')
    manager.speak('na fila')
    const cancelled = spoken[0]

    manager.stop()
    cancelled.onend?.()
    vi.runAllTimers()

    expect(cancel).toHaveBeenCalledOnce()
    expect(spoken).toHaveLength(1)
    expect(manager.getState()).toMatchObject({ speaking: false, queueLength: 0 })
  })
})
