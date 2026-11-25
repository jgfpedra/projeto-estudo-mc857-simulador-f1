"""PISTA-IDENT-1 (prereg 3758661 §2): RESOLUÇÃO DE DADOS de pista,
separada da adaptação Gymnasium do f1_env. Tudo aqui é MOVIDO VERBATIM
de backend/model_train/f1_env.py (G1) + fail-loud/identidade (G2/G3).
f1_env re-exporta resolve_track/load_track_frozen — TODOS os imports
existentes continuam funcionando."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Garante a raiz do projeto E o backend/ no sys.path (o engine importa
# "from domain import ..." — o backend/ precisa estar no caminho; o
# f1_env faz o mesmo para backend.model_train)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.domain.track import Track, build_interlagos_track
from backend.domain.track_loader import FastF1TrackLoader

# FROZEN_TRACKS_DIR (do f1_env: MODEL_DIR/'tracks_frozen' — o MODEL_DIR
# de lá é backend/model_train, onde os JSONs congelados vivem)
FROZEN_TRACKS_DIR = (Path(__file__).resolve().parent.parent
                     / "model_train" / "tracks_frozen")


class TrackResolutionError(RuntimeError):
    """PISTA-IDENT-1 G2: pista pedida não carregou. A lista de opções
    acompanha a mensagem (mirrors canônicos / CSV / OpenF1 / preset via
    flag). NUNCA desenhar/carregar outra pista silenciosamente."""


# chaves case-exatas p/ exibição (a doc busca os arquivos {key}_v2.json)
MIRROR_OPTIONS = ("interlagos", "Monaco", "Spa")


def _lista_opcoes():
    return ("Opções disponíveis:\n"
            "  - Mirrors canônicos (load_track_frozen, instantâneo): "
            + ", ".join(MIRROR_OPTIONS) + "\n"
            "  - CSV de waypoints (reference_csv / caminho .csv)\n"
            "  - Pista F1 2023+ via OpenF1 (draw_track --track <país>)\n"
            "  - Fallback legado (FastF1→preset Interlagos): passando "
            "allow_fallback=True / --allow-track-fallback (use sabendo "
            "que carregará Interlagos)")


def track_identity(track, requested=None, fonte="?"):
    """PISTA-IDENT-1 G3: identidade verificável da pista em uso.

    Devolve dict com nome, nº de waypoints, comprimento (m), hash
    SHA-256 da geometria (waypoints — o mecanismo do sha frozen
    67ca11dc211c8c78 é o modelo), a fonte (csv/mirror/fastf1/
    openf1/preset) e o nome SOLICITADO. Determinístico entre
    chamadas para a mesma geometria."""
    import hashlib as _h
    wps = np.asarray(getattr(track, "waypoints", []), dtype=np.float64)
    h = _h.sha256(wps.tobytes()).hexdigest()[:16]
    closed = np.vstack([wps, wps[:1]]) if len(wps) else wps
    length = float(np.hypot(*np.diff(closed, axis=0).T).sum()) if len(wps) else 0.0
    return {
        "requested": str(requested) if requested is not None else str(getattr(track, "name", "?")),
        "efetiva": str(getattr(track, "name", "?")),
        "fonte": fonte,
        "sha256": h,
        "n_wp": int(len(wps)),
        "length_m": round(length, 1),
    }


# --- Pistas reais via FastF1 (sem waypoints hardcoded) ---------------------
# Padrão: GP de São Paulo (Interlagos) baixado do FastF1, cacheado em disco.
# Se o evento pedido não existir, cai para o GP de São Paulo; se ainda assim
# falhar (ex.: sem internet e sem cache), último recurso é o preset local.
FASTF1_DEFAULT_YEAR = 2024
FASTF1_DEFAULT_EVENT = "São Paulo"
# MODEL_DIR do f1_env era backend/model_train; o cache fastf1 vive la
FASTF1_CACHE_DIR = Path(__file__).resolve().parent.parent / "model_train" / "cache_fastf1"

# aliases amigáveis -> nome do evento no FastF1
_FASTF1_EVENT_ALIASES = {
    "interlagos": FASTF1_DEFAULT_EVENT,
    "sao paulo": FASTF1_DEFAULT_EVENT,
    "são paulo": FASTF1_DEFAULT_EVENT,
    "sao-paulo": FASTF1_DEFAULT_EVENT,
    "são-paulo": FASTF1_DEFAULT_EVENT,
    "brazil": FASTF1_DEFAULT_EVENT,
    "default": FASTF1_DEFAULT_EVENT,
    "none": FASTF1_DEFAULT_EVENT,
}


def _fastf1_event_name(track_str):
    if track_str is None or not str(track_str).strip():
        return FASTF1_DEFAULT_EVENT
    s = str(track_str).strip()
    return _FASTF1_EVENT_ALIASES.get(s.lower(), s)


def resolve_track(track=None, reference_csv=None, year=FASTF1_DEFAULT_YEAR,
                  session="R", cache_dir=None, width_m=12.0,
                  allow_fallback=False):
    """Resolve a pista de treino com esta ordem de prioridade:

    1. ``track`` já sendo um objeto :class:`Track` -> usa direto;
    2. CSV de referência (``reference_csv`` ou caminho .csv) -> pista do arquivo;
    3. FastF1 com o evento pedido (dados reais);
    4. Fallback: FastF1 GP de São Paulo (Interlagos);
    5. Último recurso (offline/sem cache): preset local de Interlagos.
    """
    if isinstance(track, Track):
        return track
    csv_path = None
    if reference_csv is not None:
        csv_path = Path(reference_csv)
    elif track is not None:
        candidate = Path(str(track))
        if str(track).lower().endswith(".csv") or candidate.exists():
            csv_path = candidate
    if csv_path is not None:
        if not csv_path.is_absolute() and not csv_path.exists():
            if (MODEL_DIR / csv_path).exists():
                csv_path = MODEL_DIR / csv_path
            elif (PROJECT_ROOT / csv_path).exists():
                csv_path = PROJECT_ROOT / csv_path
        ref = pd.read_csv(str(csv_path))
        return Track.from_waypoints(
            name=csv_path.stem,
            waypoints=ref[['X', 'Y']].values.astype(float),
            width_m=width_m,
        )

    # PISTA-IDENT-1 G2/G3 (prereg 3758661 §3-§4): MIRROR CANÔNICO PRIMEIRO
    # — o padrão do draw_track pós-FONTE-2, agora no caminho de
    # TREINO/EVAL. As 3 canônicas resolvem instantâneo (zero rede, sha
    # verificado); o FastF1 legado fica para pistas fora do espelho; a
    # substituição silenciosa por Interlagos MORRE no default.
    # keys EXATOS de load_track_frozen (loader CASE-SENSITIVE: 'monaco'
    # != 'Monaco_v2.json' — lição H-1; track_geometry_free.CANONICAL_
    # MIRRORS é a referência). Lookup em minúsculas (o alias 'interlagos'
    # -> 'São Paulo' tem maiúsculas), OUTPUT no case exato do arquivo.
    _mk = str(_fastf1_event_name(track)).strip().lower()
    _mk = {"são paulo": "interlagos", "sao paulo": "interlagos",
           "são-paulo": "interlagos", "sao-paulo": "interlagos",
           "brazil": "interlagos", "default": "interlagos",
           "none": "interlagos", "interlagos": "interlagos",
           "monaco": "Monaco", "spa": "Spa"}.get(_mk)
    if _mk is not None:
        t_m = load_track_frozen(_mk, strict=True)
        if t_m is not None:
            print(f"[track_resolution] MIRROR canônico: '{track}' -> "
                  f"{t_m.name} ({len(t_m.waypoints)} wp, sha "
                  f"{getattr(t_m, 'frozen_sha256', '?')}), ZERO rede")
            return t_m

    cache = Path(cache_dir) if cache_dir is not None else FASTF1_CACHE_DIR
    loader = FastF1TrackLoader(cache_dir=cache)
    event = _fastf1_event_name(track)
    attempts = [event] + ([] if event == FASTF1_DEFAULT_EVENT else [FASTF1_DEFAULT_EVENT])
    for ev in attempts:
        try:
            t = loader.load(year=year, event=ev, session=session,
                            load_session=True,       # circuit_info exige voltas carregadas
                            grid_from_telemetry=False)  # sem telemetria: só o desenho da pista
            print(f"[F1MultiContextEnv] Pista carregada do FastF1: {t.name} "
                  f"({year}, {ev}), {len(t.waypoints)} waypoints")
            return t
        except Exception as e:
            print(f"[F1MultiContextEnv] FastF1 falhou p/ '{ev}' ({year}): {e}")

    # PISTA-IDENT-1 G2 (prereg 3758661 §3): o fallback silencioso MORRE.
    # O comportamento antigo (FastF1→preset Interlagos sem aviso) fica
    # SÓ atrás de allow_fallback=True (flag --allow-track-fallback no
    # eval/race_diagnostic), com WARNING LOUD + registro FALLBACK.
    if allow_fallback:
        print("[track_resolution][AVISO LOUD] FALLBACK ATIVO: FastF1 falhou "
              "para '" + str(track) + f"' ({year}) — carregando o PRESET "
              "LEGADO de Interlagos (comportamento antigo).")
        return build_interlagos_track()
    raise TrackResolutionError(
        f"Pista '{track}' (ano {year}) não carregou (CSV ausente, FastF1 "
        f"falhou, cache ausente/morto).\n" + _lista_opcoes())


def load_track_frozen(name: str, strict: bool = True):
    """Carrega a pista congelada v1 pelo nome. VERIFICA sha256.

    Args:
      name: alias amigável (interlagos, Monza, ...) — resolve o arquivo
            <name>_v1.json em tracks_frozen/.
      strict: se True (runner) — hash errado ou arquivo ausente = ERRO.
              se False — retorna None silenciosamente (para uso opcional).

    NUNCA faz fallback: se não tem frozen, o chamador decide (o runner
    deve abortar; scripts de investigação podem usar resolve_track).
    """
    import hashlib
    import json as _json
    alias = name.strip().lower()
    _alias_map = {
        'interlagos': 'interlagos', 'são paulo': 'interlagos',
        'sao paulo': 'interlagos', 'sao-paulo': 'interlagos',
        'brazil': 'interlagos', 'default': 'interlagos', 'none': 'interlagos',
    }
    key = _alias_map.get(alias, name.strip())
    # v15 R2 S4: v2 (SF corrigido) tem prioridade sobre v1 (SF original)
    path = FROZEN_TRACKS_DIR / f'{key}_v2.json'
    if not path.exists():
        path = FROZEN_TRACKS_DIR / f'{key}_v1.json'
    if not path.exists():
        if strict:
            raise FileNotFoundError(
                f"PISTA FROZEN AUSENTE: {path}. O runner REJEITA corridas em "
                f"pistas não congeladas (incidente 9099235: fallback silencioso "
                f"para preset procedural produziu carros burros). Congele a "
                f"pista primeiro ou use --track com uma frozen existente.")
        return None
    data = _json.loads(path.read_text())
    # verifica sha256 do conteúdo ORIGINAL (sem o campo sha256 em si)
    data_check = {k: v for k, v in data.items() if k != 'sha256'}
    raw = _json.dumps(data_check, sort_keys=True).encode()
    actual = hashlib.sha256(raw).hexdigest()[:16]
    if actual != data['sha256']:
        if strict:
            raise ValueError(
                f"PISTA FROZEN CORROMPIDA: {path.name} sha256 esperado "
                f"{data['sha256']} mas calculado {actual}. ABORTO — pista "
                f"adulterada.")
        return None
    wps = [(float(x), float(y)) for x, y in data['waypoints']]
    from backend.domain import Track
    t = Track.from_waypoints(
        name=data['name'],
        waypoints=wps,
        width_m=float(data.get('width_m', 12.0)),
    )
    # v15 R2 S6: o sf_idx do ARQUIVO FROZEN é AUTORITATIVO. A função pura
    # find_best_start_waypoint foi a FERRAMENTA que gerou o valor de v2
    # (registrado em sf_method no json); no load, o json é a fonte única.
    # O override em runtime (herança do FASE R) fez B3.1-v2 ignorar o
    # sf_idx do arquivo e rodar SEMPRE com a função pura — medido:
    # SF 929 (sweeper) = largada VERMELHA (1352 contatos, 68% fora);
    # toda a base verde (B3.1 223, v14, B3.3c) foi medida com SF 729.
    t.start_finish_waypoint = int(data['sf_idx'])
    # v15 R5a: sha256 do arquivo frozen visível ao runner (FONTE em todo log)
    t.frozen_sha256 = str(data['sha256'])
    return t
