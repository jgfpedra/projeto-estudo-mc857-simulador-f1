"""FONTE-2 — módulo de geometria GRATUITA (prereg 9ba3f8c §2/§4).

Duas fontes read-only, ZERO login, ZERO paywall:
  (a) MIRROR canônico — lê os JSONs congelados (interlagos_v2/Monaco_v2/
      Spa_v2) via load_track_frozen (import read-only; loader INTOCADO) e
      devolve waypoints/width/metadata. Zero rede.
  (b) OPENF1 location — /sessions?country_name=&year=&session_name=Race →
      session_key; /location?session_key=&driver_number= → x/y/z de 1
      carro; filtro de outliers GROSSEIROS simples e documentado
      (paradas/pit por densidade + velocidade; método: janela móvel de
      densidade — remove pontos onde o espaçamento local ao vizinho
      anterior é <1 m OU onde o passo temporal acumulado para de avançar
      — reinícios de volta são detectados por salto negativo >300 m na
      progressão monotônica do índice de tempo e a volta MAIS LONGA é
      mantida). Devolve centro-estrada amostrado + metadata.

  Chamadas de rede: contadas/logadas pelo caller (probe_log APPEND).
"""
from __future__ import annotations

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)


import json
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

OPENF1 = "https://api.openf1.org/v1"

# Mirrors canônicos (ADOÇÃO-H-2; loader prioriza {key}_v2 — nomes EXATOS
# que load_track_frozen resolve; PROIBIDO renomear aqui)
CANONICAL_MIRRORS = {
    "interlagos": "interlagos",
    "monaco": "Monaco",
    "spa": "Spa",
}


# ----------------------------------------------------------------------------
# Fonte (a): MIRROR congelado — zero rede
# ----------------------------------------------------------------------------
def load_mirror(name: str):
    """Lê o mirror canônico (read-only) e devolve um dict com
    waypoints/width/metadata — SEM tocar o loader (leitura JSON direta
    pelo load_track_frozen importado, que é read-only)."""
    from backend.model_train.f1_env import load_track_frozen
    key = CANONICAL_MIRRORS.get(str(name).strip().lower())
    if key is None:
        return None
    track = load_track_frozen(key)
    wps = np.asarray(track.waypoints, dtype=np.float64)
    closed = np.vstack([wps, wps[:1]])
    length = float(np.hypot(*(np.diff(closed, axis=0).T)).sum())
    return {
        "source": "mirror",
        "name": getattr(track, "name", key),
        "waypoints": wps,
        "width_m": float(getattr(track, "width_m", 12.0)),
        "sf_idx": int(getattr(track, "start_finish_waypoint", 0)),
        "length_m": length,
        "n_wp": len(wps),
    }


def mirror_options() -> List[str]:
    return sorted(CANONICAL_MIRRORS.keys())


# ----------------------------------------------------------------------------
# Fonte (b): OpenF1 /location — telemetria ESPACIAL de 1 carro, sem login
# ----------------------------------------------------------------------------
def _get(url: str, timeout: float = 60.0):
    """GET read-only; devolve (status, latência_ms, bytes, payload)."""
    import time
    import urllib.error
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
            return r.status, round((time.time() - t0) * 1000), len(body), body
    except urllib.error.HTTPError as e:
        return e.code, round((time.time() - t0) * 1000), 0, e.read() or b""
    except Exception as e:
        return f"ERR:{type(e).__name__}", round((time.time() - t0) * 1000), 0, str(e).encode()


def openf1_session_key(country_name: str, year: int,
                        session_name: str = "Race", log=None):
    """Busca session_key de uma corrida por país/ano. Retorna
    (session_key, meta_list) — log é um callable(probe, endpoint, status,
    lat_ms, size, payload) para o probe_log APPEND (teto do caller)."""
    url = (f"{OPENF1}/sessions?country_name={urllib.request.quote(country_name)}"
           f"&year={year}&session_name={urllib.request.quote(session_name)}")
    st, ms, size, body = _get(url)
    if log:
        log("A", url, st, ms, size, body, nota=f"country={country_name} year={year}")
    if st != 200:
        return None, (st, ms, size)
    import datetime
    meta = json.loads(body)
    # uma corrida por país/ano em geral; se houver múltiplas, a mais recente
    meta = sorted(meta, key=lambda m: m.get("date_start", "")) if meta else meta
    return (meta[-1] if meta else None), (st, ms, size, meta)


def openf1_location(session_key: int, driver_number: int = 44, log=None):
    """Baixa /location de 1 driver; devolve (samples, http_meta)."""
    url = (f"{OPENF1}/location?session_key={session_key}"
           f"&driver_number={driver_number}")
    st, ms, size, body = _get(url, timeout=120.0)
    if log:
        log("A", url, st, ms, size, body,
            nota=f"session={session_key} driver={driver_number}")
    if st != 200:
        return None, (st, ms, size)
    samples = json.loads(body)
    return samples, (st, ms, size)


# ----------------------------------------------------------------------------
# Filtro de outliers — SIMPLES e documentado (prereg §2-P3)
# ----------------------------------------------------------------------------
def filter_race_line(samples: List[Dict], min_step_m: float = 0.5,
                     cell_m: float = 60.0, resample_m: float = 10.0,
                     unit_scale: float = 0.1) -> Optional[np.ndarray]:
    """De amostras /location (lista cronológica de dicts com x/y/z/date)
    devolve o centro-estrada (Nx2, METROS) de UMA volta completa.

    Método v4 (final; v1 salto>300m e v2 origem falharam — v1: cruzar a
    linha não gera salto; v2: 1ª amostra é box/garagem; v3: cadeia NN
    embaraça. Tudo documentado no probe_log/ANEXO):
      0. UNIDADE EMPÍRICA: x/y da /location do session 9590 (Monza 2024)
         são DECÍMETROS — bounding box 12.568×21.684 unidades ≡ footprint
         real de Monza 1.257×2.168 m (razão exata 10×); arco de janela
         57.515 un × 0,1 = 5.751,5 m ≈ 5.793 m oficiais (−0,7%).
         unit_scale=0.1 aplica a correção (DISCLOSED; z não é usado).
      1. ordena por date; remove PARADO (passo < min_step m — garagem/
         grid/pit parado: 6.599 amostras numa célula só no 9590);
      2. células de cell_m; a mais visitada é LINHA DE CORRIDA (revistada
         ~1-3×/volta ao passo que box é raro);
      3. janelas entre visitas CONSECUTIVAS a essa célula = voltas;
         escolhe a de arco mais próximo da MEDIANA (descarta janelas
         parciais do box e da bandeirada);
      4. re-amostra uniformemente a resample_m.
    Sanidade: teste unitário do prereg (círculo sintético multi-volta
    com garagem parada) — não distorce a geometria."""
    if not samples:
        return None
    pts = sorted(samples, key=lambda s: s.get("date", ""))
    xy = np.array([[float(s["x"]), float(s["y"])] for s in pts]) * unit_scale
    if len(xy) < 100:
        return None
    step = np.hypot(*np.diff(xy, axis=0).T)
    moving = np.concatenate([[True], step > min_step_m])
    mv = xy[moving]
    idx_mv = np.where(moving)[0]
    cell = np.floor(mv / cell_m).astype(np.int64)
    uniq, inv, counts = np.unique(cell, axis=0, return_inverse=True,
                                   return_counts=True)
    C = int(np.argmax(counts))
    visits = [int(idx_mv[k]) for k in range(len(mv)) if inv[k] == C]
    arcs, wins = [], []
    for a, b in zip(visits[:-1], visits[1:]):
        lap = xy[a:b]
        if len(lap) < 50:
            continue
        arc = float(np.hypot(*np.diff(lap, axis=0).T).sum())
        arcs.append(arc)
        wins.append((a, b))
    if len(arcs) < 2:
        return None
    arcs = np.array(arcs)
    med = float(np.median(arcs))
    k = int(np.argmin(np.abs(arcs - med)))
    a, b = wins[k]
    line = xy[a:b]
    # limpeza final dentro da volta: remove micro-paradas
    keep = [0]
    for i in range(1, len(line)):
        if np.hypot(*(line[i] - line[keep[-1]])) >= 1.0:
            keep.append(i)
    line = line[keep]
    closed = np.vstack([line, line[:1]])
    dd = np.hypot(*np.diff(closed, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(dd)])
    total = cum[-1]
    if total < 100.0:
        return None
    n_new = max(int(total / resample_m), 32)
    s_new = np.linspace(0.0, total, n_new, endpoint=False)
    return np.column_stack([
        np.interp(s_new, cum, closed[:, 0]),
        np.interp(s_new, cum, closed[:, 1])])


def openf1_track(country_name: str, year: int, driver_number: int = 44,
                 log=None, session_key: Optional[int] = None,
                 cache_path: Optional[Path] = None):
    """Pipeline completo OpenF1 → centro-estrada. Devolve dict no MESMO
    formato de load_mirror (source='openf1') ou None (caller decide
    fallback/erro). session_key conhecido evita 1 chamada; cache_path
    persiste o payload para debug offline."""
    if session_key is None:
        sk_meta, _ = openf1_session_key(country_name, year, log=log)
        if not sk_meta:
            return None
        session_key = int(sk_meta["session_key"])
    if cache_path is not None and Path(cache_path).exists():
        samples = json.loads(Path(cache_path).read_text())
    else:
        samples, _ = openf1_location(session_key, driver_number, log=log)
        if cache_path is not None and samples:
            Path(cache_path).write_text(json.dumps(samples))
    if not samples:
        return None
    line = filter_race_line(samples)
    if line is None or len(line) < 50:
        return None
    closed = np.vstack([line, line[:1]])
    length = float(np.hypot(*(np.diff(closed, axis=0).T)).sum())
    return {
        "source": "openf1",
        "name": f"{country_name} {year} (driver {driver_number})",
        "waypoints": line,
        "width_m": 12.0,
        "sf_idx": 0,
        "length_m": length,
        "n_wp": len(line),
        "session_key": session_key,
    }
