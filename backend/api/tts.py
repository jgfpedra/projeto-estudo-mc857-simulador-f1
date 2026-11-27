"""Síntese de voz local (espeak-ng) para o engenheiro de IA.

O Firefox/Zen no Linux só fala via speech-dispatcher; sem ele, o
`speechSynthesis` do navegador não tem vozes. Este módulo gera o áudio no
servidor para que o painel funcione em qualquer navegador.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from collections import OrderedDict

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 800
_CACHE_LIMIT = 256
_ESPEAK = shutil.which('espeak-ng') or shutil.which('espeak')

# espeak-ng: nomes de voz pt-br/pt/en. A ordem é o fallback quando o idioma
# pedido não existe na instalação.
_VOICE_FALLBACKS = ('pt-br', 'pt', 'en')

_cache: "OrderedDict[str, bytes]" = OrderedDict()


def available() -> bool:
    """True quando o binário de síntese existe na imagem."""
    return _ESPEAK is not None


def _voice_candidates(lang: str) -> list[str]:
    normalized = (lang or 'pt-br').replace('_', '-').lower()
    candidates = [normalized]
    if normalized.startswith('pt'):
        candidates.extend(['pt-br', 'pt'])
    elif normalized.startswith('en'):
        candidates.append('en')
    candidates.extend(_VOICE_FALLBACKS)
    return list(dict.fromkeys(candidates))


def _run(voice: str, text: str) -> bytes | None:
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as handle:
            path = handle.name
        # Grava em arquivo: o WAV de stdout do espeak sai com tamanho inválido.
        proc = subprocess.run(
            [_ESPEAK, '-v', voice, '-s', '165', '-p', '45', '-w', path, text],
            capture_output=True, timeout=20,
        )
        if proc.returncode != 0:
            return None
        with open(path, 'rb') as handle:
            data = handle.read()
        return data or None
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning('síntese de voz falhou (%s): %s', voice, exc)
        return None
    finally:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass


def synthesize(text: str, lang: str = 'pt-br') -> bytes | None:
    """Devolve o WAV da fala ou None quando não há como sintetizar."""
    clean = ' '.join((text or '').split()).strip()[:MAX_TEXT_LENGTH]
    if not clean or _ESPEAK is None:
        return None

    for voice in _voice_candidates(lang):
        key = f'{voice}|{clean}'
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            return cached
        data = _run(voice, clean)
        if data is not None:
            _cache[key] = data
            while len(_cache) > _CACHE_LIMIT:
                _cache.popitem(last=False)
            return data
    return None
