"""FASE H-0 — H1/H2: builder de pista FROZEN a partir do mirror F1DB (SVG).

Prereg: PREREG_FASE_H.md (commit 21ac676, ANTES deste código). ZERO runs.
Pipeline pinado: download do SVG da era (URL do circuit_layouts_evolution.json
commitado) -> parse do path `d` (comandos M/c/s/z APENAS; outro = PARE) ->
amostragem das Béziers (24 pts/curva) -> gate de fechamento (<=1% L) ->
escala = oficial/L_svg -> reamostragem em arco a 4,0 m -> GEOM GATE
(G1 clearance>=8m não-adjacentes | G2 zero crossover | G3 R_min>=8m |
G4 turns = metadata±3 | G5 comprimento <=0,1%) -> freeze em tracks_frozen/
com sha256 hex[:16] (convenção do load_track_frozen) + chaves aditivas de
proveniência. Gate FAIL -> NÃO congela (PARE documentado no stdout).

Nome do artefato: {Name}_mirror*_v1.json — NUNCA {Name}_v2.json (o loader dá
prioridade a _v2 e mudaria a pista canônica sem decisão do dono).

    .venv/bin/python scripts/tracks/track_mirror_build.py monaco
    .venv/bin/python scripts/tracks/track_mirror_build.py spa
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


import hashlib
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND))
FROZEN_DIR = BACKEND / "model_train" / "tracks_frozen"
EVOLUTION = BACKEND / "data" / "circuit_layouts_evolution.json"

DS_M = 4.0            # espaçamento de reamostragem (convenção das frozen)
SAMPLES_PER_CURVE = 24
MIN_ARC_GAP_M = 40.0  # segmentos "não adjacentes" (definição do audit)
GATE = dict(clearance_min_m=8.0, r_min_m=8.0, turns_tol=3, len_tol_pct=0.1)

# alvo por circuito: (nome F1DB, layout-id, oficial_m, nome do arquivo, era, nome da pista)
TARGETS = {
    "monaco": dict(circuit="Monaco", layout_id="monaco-6", official_m=3337.0,
                   out="Monaco_mirror2021_v1.json",
                   era="2003-2019, 2021-2026", track_name="Monaco Grand Prix (mirror 2021)"),
    "spa": dict(circuit="Spa-Francorchamps", layout_id="spa-francorchamps-4",
                official_m=7004.0, out="Spa_mirror_v1.json",
                era="2007-2026", track_name="Spa-Francorchamps (mirror 2007-2026)"),
}


# ----------------------------------------------------------------------------
# Parser do path SVG (M/c/s/z — o que as fontes F1DB usam)
# ----------------------------------------------------------------------------
def parse_svg_path(d: str, samples: int = SAMPLES_PER_CURVE):
    """`d` -> polilinha densa (np array Nx2) + ponto inicial. PARE em comando
    fora de M/c/s/z (prereg §2.1)."""
    if not re.fullmatch(r'[Mcsz0-9eE,.\s\-]+', d):
        bad = sorted(set(re.findall(r'[A-Za-z]', d)) - set('Mcsz'))
        raise ValueError(f"comando(s) fora do prereg (M/c/s/z apenas): {bad}")
    parts = re.findall(r'([Mcsz])([^Mcsz]*)', d)
    pts, prev, p0, last_ctrl, last_cmd = [], None, None, None, None
    for cmd, argstr in parts:
        nums = [float(x) for x in re.findall(r'-?\d*\.?\d+(?:e-?\d+)?', argstr)]
        if cmd == 'M':
            prev = p0 = np.array(nums[:2])
            pts.append(prev.copy())
            last_ctrl, last_cmd = None, 'M'
        elif cmd in 'cs':
            step = 6 if cmd == 'c' else 4
            for k in range(0, len(nums), step):
                if cmd == 'c':
                    c1 = prev + np.array(nums[k:k + 2])
                    c2 = prev + np.array(nums[k + 2:k + 4])
                    end = prev + np.array(nums[k + 4:k + 6])
                else:  # 's': c1 = reflexão do último controle
                    c1 = prev + (prev - last_ctrl) if (last_cmd in 'cs' and last_ctrl is not None) else prev
                    c2 = prev + np.array(nums[k:k + 2])
                    end = prev + np.array(nums[k + 2:k + 4])
                t = np.linspace(0.0, 1.0, samples)[1:]
                tt = t[:, None]
                mt = (1.0 - t)[:, None]
                pts.extend(mt ** 3 * prev + 3 * mt ** 2 * tt * c1 + 3 * mt * tt ** 2 * c2 + tt ** 3 * end)
                prev, last_ctrl, last_cmd = end, c2, cmd
        elif cmd == 'z':
            break  # fecha no ponto inicial
    return np.array(pts), p0, prev


def resample_closed(pts: np.ndarray, ds: float = DS_M):
    """Reamostra o LOOP FECHADO em arco a `ds`. Retorna waypoints Nx2."""
    closed = np.vstack([pts, pts[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    n = max(int(round(total / ds)), 8)
    s_targets = np.arange(n) * (total / n)
    wps = np.empty((n, 2))
    idx = np.searchsorted(cum, s_targets) - 1
    idx = np.clip(idx, 0, len(seg) - 1)
    t = (s_targets - cum[idx]) / np.maximum(seg[idx], 1e-12)
    wps = closed[idx] + t[:, None] * (closed[idx + 1] - closed[idx])
    return wps


# ----------------------------------------------------------------------------
# Geometria (gate + detector compartilham)
# ----------------------------------------------------------------------------
def seg_seg_min_dist(wps: np.ndarray):
    """Distância mínima entre CADA par de segmentos não-adjacentes.
    Retorna (i, j, dist) só para pares com gap de arco > MIN_ARC_GAP_M e
    dist < 25 m (janela de report). Vetorial em blocos."""
    A = wps
    B = np.roll(wps, -1, axis=0)
    n = len(wps)
    min_gap_wp = int(MIN_ARC_GAP_M / DS_M) + 1
    out = []
    for i in range(n):
        j0 = (i + min_gap_wp) % n
        jcount = n - 2 * min_gap_wp
        if jcount <= 0:
            break
        js = (j0 + np.arange(jcount)) % n
        # distância ponto-segmento dos 4 endpoints ao segmento oposto
        def p2seg(P, S0, S1):
            v = S1 - S0
            L2 = np.maximum((v ** 2).sum(-1), 1e-12)
            tt = np.clip(((P - S0) * v).sum(-1) / L2, 0.0, 1.0)
            proj = S0 + tt[..., None] * v
            return np.hypot(*(P - proj).T)

        d = np.minimum(p2seg(A[i], A[js], B[js]), p2seg(A[js], A[i], B[i]))
        d = np.minimum(d, np.minimum(p2seg(B[i], A[js], B[js]), p2seg(B[js], A[i], B[i])))
        for k in np.where(d < 25.0)[0]:
            out.append((i, int(js[k]), float(d[k])))
    return out


def count_crossovers(wps: np.ndarray):
    """Interseções entre segmentos não-adjacentes (G2)."""
    A = wps
    B = np.roll(wps, -1, axis=0)
    n = len(wps)
    min_gap_wp = int(MIN_ARC_GAP_M / DS_M) + 1
    n_cross = 0
    for i in range(n):
        j0 = (i + min_gap_wp) % n
        jcount = n - 2 * min_gap_wp
        if jcount <= 0:
            break
        js = (j0 + np.arange(jcount)) % n
        s_dir = B[i] - A[i]                 # direção do segmento i
        v_dir = B[js] - A[js]               # direção do segmento j
        r = A[js] - A[i]                    # q - p
        denom = s_dir[0] * v_dir[:, 1] - s_dir[1] * v_dir[:, 0]   # cross(s, v)
        safe = np.abs(denom) > 1e-12
        # t*cross(s,v) = cross(r,v);  u*cross(s,v) = cross(r,s)
        t = np.where(safe, (r[:, 0] * v_dir[:, 1] - r[:, 1] * v_dir[:, 0])
                     / np.where(safe, denom, 1.0), -1.0)
        u = np.where(safe, (r[:, 0] * s_dir[1] - r[:, 1] * s_dir[0])
                     / np.where(safe, denom, 1.0), -1.0)
        hit = safe & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
        n_cross += int(hit.sum())
    return n_cross  # cada cruzamento conta 2 (i,j)+(j,i)


def radii_and_turns(wps: np.ndarray, kappa_thresh=0.02, min_sep_m=30.0):
    """R por tripleta consecutiva + turns = picos de κ (limiar, separação mín.)."""
    p0, p1, p2 = wps, np.roll(wps, -1, axis=0), np.roll(wps, -2, axis=0)
    a = np.hypot(*(p1 - p0).T)
    b = np.hypot(*(p2 - p1).T)
    c = np.hypot(*(p2 - p0).T)
    area2 = np.abs((p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) -
                   (p1[:, 1] - p0[:, 1]) * (p2[:, 0] - p0[:, 0]))
    with np.errstate(divide='ignore', invalid='ignore'):
        R = np.where(area2 > 1e-9, (a * b * c) / np.maximum(area2, 1e-9), np.inf)
    R = np.where(np.isfinite(R), R, np.inf)
    r_min = float(R.min())
    kappa = 1.0 / np.where(R > 0, R, np.inf)
    # picos locais de κ acima do limiar com separação
    peaks, last_s = [], -1e9
    for i in np.where(kappa > kappa_thresh)[0]:
        if kappa[i] >= kappa[i - 1] and kappa[i] >= kappa[(i + 1) % len(wps)]:
            if i - last_s >= min_sep_m / DS_M:
                peaks.append(i)
                last_s = i
    return r_min, len(peaks), R


# ----------------------------------------------------------------------------
# Build + gate + freeze
# ----------------------------------------------------------------------------
def fetch_svg_url(circuit: str, layout_id: str) -> str:
    data = json.loads(EVOLUTION.read_text())
    for c in data["circuits"]:
        if c["name"] == circuit:
            for lay in c["layouts"]:
                if lay["id"] == layout_id:
                    return lay["svg"]["black-outline"], lay["turns"], lay["year_ranges"]
    raise KeyError(f"layout {layout_id} não achado para {circuit}")


def build(key: str, write: bool = True, g4_kappa: float = 0.02,
          official_turns: int = None, g4_gate: bool = True):
    """H-0: g4_kappa=0,02 + turns da metadata F1DB. FASE-H-1: a calibração
    chama com κ* (controles) e oficiais do PREREG_FASE_H1 §2; g4_gate=False
    (ramo B) -> G4 vira report-only (fingerprint), sem bloquear."""
    tgt = TARGETS[key]
    url, turns_meta, years = fetch_svg_url(tgt["circuit"], tgt["layout_id"])
    if official_turns is None:
        official_turns = turns_meta
    print(f"[H] {tgt['circuit']} | layout {tgt['layout_id']} | anos {years} | "
          f"turns metadata {turns_meta} | oficiais do prereg {official_turns} | g4_kappa={g4_kappa}")
    svg = urllib.request.urlopen(url, timeout=30).read().decode()
    d = re.search(r'<path[^>]*d="([^"]+)"', svg).group(1)
    pts, p0, pend = parse_svg_path(d)
    # fechamento (z fecha no inicial; o gap medido deve ser ~0)
    closed = np.vstack([pts, p0[None, :]])
    L_svg = float(np.hypot(*np.diff(closed, axis=0).T).sum())
    gap = float(np.hypot(*(pend - p0)))
    print(f"[H] parse: {len(pts)} pts | L_svg={L_svg:.1f}u | gap fechamento={gap:.3f}u ({100 * gap / L_svg:.3f}%L)")
    if gap > 0.01 * L_svg:
        print(f"[H] GATE fechamento FAIL (gap {gap:.2f}u > 1% L) -> NÃO congela; PARE documentado")
        return 1
    scale = tgt["official_m"] / L_svg
    wps = resample_closed(pts * scale, DS_M)
    L = float(np.hypot(*np.diff(np.vstack([wps, wps[:1]]), axis=0).T).sum())
    print(f"[H] escala={scale:.4f} m/u | n_wp={len(wps)} | L={L:.1f}m (oficial {tgt['official_m']:.0f}m)")

    # GEOM GATE
    pairs = seg_seg_min_dist(wps)
    clearance = min((d for _, _, d in pairs), default=99.0)
    n_cross = count_crossovers(wps)
    r_min, n_turns, R = radii_and_turns(wps, kappa_thresh=g4_kappa)
    len_err_pct = 100 * abs(L - tgt["official_m"]) / tgt["official_m"]
    # hairpins/esses DOCUMENTADOS: as 8 curvas mais apertadas (wp, R_m)
    tight = [(int(i), round(float(R[i]), 1)) for i in np.argsort(R)[:8]]
    print(f"[H] G1 clearance={clearance:.2f}m (>= {GATE['clearance_min_m']})")
    print(f"[H] G2 crossovers={n_cross // 2} (esperado 0; contagem//2 p/ pares duplicados)")
    print(f"[H] G3 R_min={r_min:.2f}m (>= {GATE['r_min_m']}) | 8 mais apertadas (wp, R_m): {tight}")
    print(f"[H] G4 turns detectados={n_turns} @κ={g4_kappa} (oficiais {official_turns}±{GATE['turns_tol']}"
          f"{'' if g4_gate else ' — RAMO B: REPORT-ONLY'})")
    print(f"[H] G5 |L-oficial|={len_err_pct:.4f}% (<= {GATE['len_tol_pct']}%)")
    checks = {
        "G1 clearance >= 8,0m": clearance >= GATE["clearance_min_m"],
        "G2 zero crossover": n_cross == 0,
        "G3 R_min >= 8,0m": r_min >= GATE["r_min_m"],
        "G5 comprimento <= 0,1%": len_err_pct <= GATE["len_tol_pct"],
    }
    if g4_gate:
        checks["G4 turns = oficiais±3"] = abs(n_turns - official_turns) <= GATE["turns_tol"]
    allp = all(checks.values())
    for k, v in checks.items():
        print(f"    {k}: {'PASS' if v else 'FAIL'}")
    if not allp:
        print("[H] GEOM GATE FAIL -> NÃO congela; PARE documentado (prereg §3)")
        return 1
    if not write:
        return 0
    data = {
        "name": tgt["track_name"],
        "waypoints": [[round(float(x), 4), round(float(y), 4)] for x, y in wps],
        "width_m": 12.0,
        "sf_idx": 0,
        "n_wp": len(wps),
        # proveniência aditiva (o loader lê só as chaves canônicas)
        "source_svg": url,
        "era": tgt["era"],
        "official_length_m": tgt["official_m"],
        "scale_m_per_unit": round(scale, 6),
        "gate_clearance_min_m": round(clearance, 3),
        "gate_crossovers": n_cross // 2,
        "r_min_m": round(r_min, 2),
        "turns_detected": n_turns,
        "g4_kappa_used": g4_kappa,
        "sf_note": "sf_idx=0: fonte SVG não marca SF nem direção; âncoras de corrida = era de adoção (dono)",
    }
    if not g4_gate:
        data["g4_note"] = (
            "G4 MORTO como gate (FASE-H-1 ramo B): calibração em controles deu 0/5 in-band "
            "em TODA a grade κ 0,004-0,020 (detector κ-picos infla em frozen de telemetria "
            "21-28 vs oficiais 14-18 e deflaciona em mirrors Bézier; não reproduz a convenção "
            "oficial de turns em nenhuma classe de fonte) — turns = FINGERPRINT REPORT-ONLY; "
            "completude = G5 (comprimento) + G1/G2/G3"
        )
    raw = json.dumps({k: v for k, v in data.items()}, sort_keys=True).encode()
    data["sha256"] = hashlib.sha256(raw).hexdigest()[:16]
    out = FROZEN_DIR / tgt["out"]
    out.write_text(json.dumps(data, indent=1))
    print(f"[H] CONGELADO: {out} | sha256={data['sha256']} | n_wp={data['n_wp']}")
    return 0


def main(argv):
    if len(argv) != 1 or argv[0] not in TARGETS:
        print(__doc__)
        return 2
    return build(argv[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
