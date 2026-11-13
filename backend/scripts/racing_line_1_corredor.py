#!/usr/bin/env python3
"""RACING-LINE-1 Task 3 — gates geométricos do candidato C08 (Emenda nº 1).

Report-only, determinístico, zero corrida, zero rede, pista frozen intocada.
Avalia OFFLINE a linha virtual do candidato ratificado na Emenda nº 1 de
PREREG_RACING_LINE_1.md: arco circular R = 18,0 m com limites derivados por
bi-tangência s_a = 2282,417 m e s_b = 2342,863 m.

Pipeline (sem fallback silencioso):
1. carrega a pista frozen e verifica o SHA pinado;
2. re-deriva a raiz bi-tangente da geometria frozen (Newton 2D, mesmo método
   do Task 2) e confere os limites ratificados (tol 0,01 m);
3. constrói a linha virtual: vértices frozen externos a [s_a, s_b] preservados
   byte-idênticos, pontos de tangência interpolados na linha, arco R=18 m
   discretizado com ds ≤ 1,0 m;
4. gates: corredor (|lat| ≤ 6,0 m da linha central frozen), C1 (< 1,0° nas
   duas emendas), fechamento (< 1e-4 m) e zero auto-interseção;
5. escreve JSON exclusivo com todos os números, hashes e a linha virtual;
6. repetição em processo separado deve ser byte-idêntica (cmp=0).

Saída exclusiva: ``experiments/racing-line-1/c3/CORREDOR_C08.json``.
Exit 0 = gates OK; exit 4 = PARE; exit 2 = erro de entrada/proveniência.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND))

from scripts import saidas_verdict as SV  # noqa: E402
from scripts import racing_line_1_geometria as RG  # noqa: E402

VERSION = "racing-line-1/task3-corredor-v1.0"
SAIDAS_VERDICT_SHA256 = (
    "e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c"
)

# Constantes ratificadas na Emenda nº 1 do PREREG_RACING_LINE_1.md
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"
S_A_M = 2282.417
S_B_M = 2342.863
R_ARC_M = 18.0
SIGMA = -1.0                    # Junção = curva à direita (raiz dominante)
KAPPA_THRESH = 0.006
MERGE_GAP_M = 40.0

# Gates pinados no prompt executivo / Emenda nº 1
CORRIDOR_MAX_M = 6.0
C1_TOL_DEG = 1.0
CLOSURE_TOL_M = 1e-4
DS_ARC_MAX_M = 1.0
DERIV_TOL_M = 0.01
CORRIDOR_PROBE_M = 0.05  # sondagem densa do arco p/ o gate medir a curva contínua

OUT_PATH = BACKEND / "experiments" / "racing-line-1" / "c3" / "CORREDOR_C08.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def vertex_geometry(wps: np.ndarray) -> Tuple[np.ndarray, float]:
    """s cumulativo por vértice e comprimento total do laço."""
    closed = np.vstack([wps, wps[:1]])
    diff = np.diff(closed, axis=0)
    seg = np.hypot(diff[:, 0], diff[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    return cum, float(np.sum(seg))


def interp_on_line(wps: np.ndarray, cum: np.ndarray, s: float
                   ) -> Tuple[np.ndarray, int, np.ndarray]:
    """Posição interpolada na polilinha frozen em s, índice do segmento e
    direção unitária do segmento (sentido de percurso)."""
    j = int(np.searchsorted(cum, s, side="right") - 1)
    j = min(max(j, 0), len(wps) - 1)
    k = (j + 1) % len(wps)
    span = (cum[k] - cum[j]) if cum[k] > cum[j] else (
        cum[-1] + float(np.linalg.norm(wps[0] - wps[-1])) - cum[j])
    t = min(max((s - cum[j]) / max(span, 1e-12), 0.0), 1.0)
    p = wps[j] * (1.0 - t) + wps[k] * t
    d = wps[k] - wps[j]
    d = d / max(float(np.linalg.norm(d)), 1e-12)
    return p, j, d


def c1_deviation_deg(t_line: np.ndarray, t_arc: np.ndarray) -> float:
    """Ângulo entre duas tangentes unitárias, em graus [0, 180]."""
    cosang = float(np.clip(np.dot(t_line, t_arc), -1.0, 1.0))
    return math.degrees(math.acos(cosang))


def max_dist_to_polyline(pts: np.ndarray, poly: np.ndarray
                         ) -> Tuple[float, int]:
    """Máxima distância dos pontos à polilinha fechada e o índice do ponto."""
    a = poly
    b = np.roll(poly, -1, axis=0)
    ab = b - a
    L2 = np.maximum((ab * ab).sum(axis=1), 1e-18)
    dmin = np.empty(len(pts))
    for i in range(len(pts)):
        p = pts[i]
        ap = p - a
        t = np.clip((ap * ab).sum(axis=1) / L2, 0.0, 1.0)
        proj = a + t[:, None] * ab
        dmin[i] = np.hypot(*(p - proj).T).min()
    k = int(np.argmax(dmin))
    return float(dmin[k]), k


def segments_self_intersect(poly: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """Auto-interseção própria estrita na polilinha fechada (vetorizada)."""
    n = len(poly)
    if n < 4:
        return False, None
    a = poly
    b = np.roll(poly, -1, axis=0)
    d = b - a

    def cross_mat(px: np.ndarray, py: np.ndarray) -> np.ndarray:
        # cross(d_j, p_i) para todos os pares (i, j): matrizes (n, n)
        ddx = d[:, 0][None, :]
        ddy = d[:, 1][None, :]
        return ddx * (py[:, None] - b[:, 1][None, :]) - ddy * (
            px[:, None] - b[:, 0][None, :])

    ax_, ay_ = a[:, 0], a[:, 1]
    bx_, by_ = b[:, 0], b[:, 1]
    d1 = cross_mat(ax_, ay_)   # linha j × ponto a_i
    d2 = cross_mat(bx_, by_)   # linha j × ponto b_i
    d3 = cross_mat(ax_, ay_).T  # linha i × ponto a_j
    d4 = cross_mat(bx_, by_).T  # linha i × ponto b_j
    strict = ((d1 > 0) != (d2 > 0)) & ((d3 > 0) != (d4 > 0))
    idx = np.arange(n)
    adj = (np.abs(idx[:, None] - idx[None, :]) == 1) | (
        (idx[:, None] == 0) & (idx[None, :] == n - 1)) | (
        (idx[:, None] == n - 1) & (idx[None, :] == 0))
    strict &= ~np.eye(n, dtype=bool) & ~adj
    strict &= np.triu(np.ones((n, n), dtype=bool), k=1)
    if strict.any():
        i, j = np.unravel_index(int(np.argmax(strict)), strict.shape)
        return True, (int(i), int(j))
    return False, None


def build_virtual_line(wps: np.ndarray, cum: np.ndarray, s_a: float, s_b: float,
                       R: float, ds_max: float
                       ) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Linha virtual: externos byte-idênticos + tangência interpolada + arco.

    Centro: solução de |O−P_a| = |O−P_b| = R escolhida pela menor divergência
    angular C1 contra a tangente da linha em s_a (a candidata errada diverge
    ~180°). Sweep no sentido horário (curva à direita)."""
    p_a, _, d_a = interp_on_line(wps, cum, s_a)
    p_b, _, d_b = interp_on_line(wps, cum, s_b)
    chord = p_b - p_a
    half = float(np.linalg.norm(chord)) / 2.0
    if half >= R:
        raise ValueError(f"corda {2*half:.3f} m >= R {R} m: sem círculo")
    mid = (p_a + p_b) / 2.0
    u = chord / np.linalg.norm(chord)
    perp = np.array([u[1], -u[0]])  # normal à direita do sentido a->b
    h = math.sqrt(R * R - half * half)
    candidates = [mid + h * perp, mid - h * perp]

    best = None
    for O in candidates:
        # tangente no início do arco horário em P_a: rotaciona (P_a - O) em -90°
        v = p_a - O
        t_arc = np.array([v[1], -v[0]]) / R
        dev = c1_deviation_deg(d_a, t_arc)
        if best is None or dev < best[0]:
            best = (dev, O)
    dev_a_cand, O = best
    if dev_a_cand > C1_TOL_DEG:
        raise ValueError(f"nenhum centro compatível com C1 em s_a: {dev_a_cand:.4f}°")

    theta_a = math.atan2(p_a[1] - O[1], p_a[0] - O[0])
    theta_b = math.atan2(p_b[1] - O[1], p_b[0] - O[0])
    sweep = (theta_a - theta_b) % (2.0 * math.pi)  # horário positivo
    if not (0.0 < sweep < 2.0 * math.pi):
        raise ValueError(f"sweep inválido: {sweep}")
    L_arc = R * sweep
    n_arc = int(math.ceil(L_arc / ds_max))
    ds_arc = L_arc / n_arc

    interior = []
    for j in range(1, n_arc):
        th = theta_a - sweep * j / n_arc
        interior.append([O[0] + R * math.cos(th), O[1] + R * math.sin(th)])

    keep_lo = [i for i in range(len(wps)) if cum[i] <= s_a]
    keep_hi = [i for i in range(len(wps)) if cum[i] > s_b]
    virt = np.vstack([
        wps[keep_lo],
        p_a[None, :],
        np.array(interior),
        p_b[None, :],
        wps[keep_hi],
    ])

    t_arc_start = np.array([math.sin(theta_a), -math.cos(theta_a)])
    t_arc_end = np.array([math.sin(theta_b), -math.cos(theta_b)])
    info = {
        "p_a": p_a, "p_b": p_b, "O": O, "R_m": float(R),
        "theta_a": theta_a, "theta_b": theta_b,
        "sweep_rad": sweep, "sweep_deg": math.degrees(sweep),
        "L_arc_m": L_arc, "n_arc": n_arc, "ds_arc_m": ds_arc,
        "keep_lo": keep_lo, "keep_hi": keep_hi,
        "t_arc_start": t_arc_start, "t_arc_end": t_arc_end,
    }
    return virt, info


def smooth_tangent_at(wps: np.ndarray, cum: np.ndarray, s: float) -> np.ndarray:
    """Tangente unitária interpolada do campo CENTRADO por vértice
    (T_i = normalize(P_{i+1} − P_{i−1}), mesma convenção do campo em que a
    raiz bi-tangente é exata) — a tangente suave da curva de referência."""
    n = len(wps)
    T = np.roll(wps, -1, axis=0) - np.roll(wps, 1, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    j = int(np.searchsorted(cum, s, side="right") - 1)
    j = min(max(j, 0), n - 1)
    k = (j + 1) % n
    span = (cum[k] - cum[j]) if cum[k] > cum[j] else (
        cum[-1] + float(np.linalg.norm(wps[0] - wps[-1])) - cum[j])
    t = min(max((s - cum[j]) / max(span, 1e-12), 0.0), 1.0)
    tv = T[j] * (1.0 - t) + T[k] * t
    return tv / max(float(np.linalg.norm(tv)), 1e-12)


def evaluate_gates(virt: np.ndarray, wps: np.ndarray, cum: np.ndarray,
                   info: Dict[str, Any], s_a: Optional[float] = None,
                   s_b: Optional[float] = None) -> Dict[str, Any]:
    """Gates: corredor, C1 nas duas emendas, fechamento, auto-interseção,
    invariância do trecho externo.

    O gate C1 usa as tangentes ANALÍTICAS do arco (continuidade da curva);
    o desvio angular da MALHA discretizada é registrado como informação
    (carrega meio-passo de discretização, não é descontinuidade da curva).
    ``s_a``/``s_b`` ausentes usam os limites ratificados da Emenda nº 1."""
    s_a = S_A_M if s_a is None else float(s_a)
    s_b = S_B_M if s_b is None else float(s_b)
    p_a, _, d_a = interp_on_line(wps, cum, s_a)
    p_b, _, d_b = interp_on_line(wps, cum, s_b)

    # sondagem densa do arco (a malha ds<=1,0 m pode errar o pico do desvio;
    # o gate mede a CURVA contínua com passo fino + cota de erro)
    n_probe = max(2, int(math.ceil(info["L_arc_m"] / CORRIDOR_PROBE_M)))
    th_probe = info["theta_a"] - info["sweep_rad"] * np.arange(n_probe + 1) / n_probe
    arc_probe = info["O"][None, :] + info["R_m"] * np.stack(
        [np.cos(th_probe), np.sin(th_probe)], axis=1)
    pts_all = np.vstack([virt, arc_probe])
    dmax, kmax = max_dist_to_polyline(pts_all, wps)
    probe_err_bound = float(info["L_arc_m"] / n_probe / 2.0)  # derivada ≤ 1
    corridor = {
        "limite_m": CORRIDOR_MAX_M,
        "desvio_max_m": round(dmax, 6),
        "indice_ponto_max": kmax,
        "pontos_sondados": int(len(pts_all)),
        "passo_sonda_m": round(info["L_arc_m"] / n_probe, 6),
        "cota_erro_m": round(float(probe_err_bound), 6),
        "ok": bool(dmax + float(probe_err_bound) <= CORRIDOR_MAX_M),
    }

    i_pa = int(np.argmin(np.linalg.norm(virt - p_a, axis=1)))
    i_pb = int(np.argmin(np.linalg.norm(virt - p_b, axis=1)))
    n = len(virt)
    dir_out_a = virt[(i_pa + 1) % n] - virt[i_pa]
    dir_out_a = dir_out_a / max(float(np.linalg.norm(dir_out_a)), 1e-12)
    dir_in_b = virt[i_pb] - virt[(i_pb - 1) % n]
    dir_in_b = dir_in_b / max(float(np.linalg.norm(dir_in_b)), 1e-12)
    # gate: tangente analítica do arco vs tangente SUAVE interpolada da linha
    # (campo centrado — o mesmo em que a raiz bi-tangente é exata); a
    # direção do segmento frozen é descontínua por construção e entra só
    # como informação
    st_a = smooth_tangent_at(wps, cum, s_a)
    st_b = smooth_tangent_at(wps, cum, s_b)
    dev_a = c1_deviation_deg(st_a, info["t_arc_start"])
    dev_b = c1_deviation_deg(st_b, info["t_arc_end"])
    # informação: mesma comparação contra a direção do segmento frozen
    seg_a = c1_deviation_deg(d_a, info["t_arc_start"])
    seg_b = c1_deviation_deg(d_b, info["t_arc_end"])
    # informação: quebra angular da malha nos vértices de emenda
    mesh_a = c1_deviation_deg(d_a, dir_out_a)
    mesh_b = c1_deviation_deg(d_b, dir_in_b)
    c1 = {
        "tol_deg": C1_TOL_DEG,
        "emenda_a_deg": round(dev_a, 6),
        "emenda_b_deg": round(dev_b, 6),
        "vs_segmento_a_deg_info": round(seg_a, 4),
        "vs_segmento_b_deg_info": round(seg_b, 4),
        "malha_a_deg_info": round(mesh_a, 4),
        "malha_b_deg_info": round(mesh_b, 4),
        "ok": bool(max(dev_a, dev_b) < C1_TOL_DEG),
    }

    err_pa = float(np.linalg.norm(virt[i_pa] - p_a))
    err_pb = float(np.linalg.norm(virt[i_pb] - p_b))
    closing_virt = float(np.linalg.norm(virt[0] - virt[-1]))
    closing_ref = float(np.linalg.norm(wps[0] - wps[-1]))
    closure = {
        "tol_m": CLOSURE_TOL_M,
        "erro_tangencia_a_m": err_pa,
        "erro_tangencia_b_m": err_pb,
        "segmento_fechamento_m": round(closing_virt, 6),
        "segmento_fechamento_ref_m": round(closing_ref, 6),
        "ok": bool(max(err_pa, err_pb, abs(closing_virt - closing_ref)) < CLOSURE_TOL_M),
    }

    inter, pair = segments_self_intersect(virt)
    topo = {"auto_intersecao": inter, "par": pair, "ok": not inter}

    lo_idx = set(info["keep_lo"])
    hi_idx = set(info["keep_hi"])
    virt_set = {tuple(p) for p in map(tuple, virt)}
    missing = [i for i in sorted(lo_idx | hi_idx)
               if tuple(wps[i]) not in virt_set]
    interior_kept = [i for i in range(len(wps))
                     if s_a < cum[i] < s_b and tuple(wps[i]) in virt_set]
    exterior = {
        "vertices_externos_esperados": len(lo_idx | hi_idx),
        "vertices_externos_ausentes": missing,
        "vertices_internos_remanescentes": interior_kept,
        "ok": not missing and not interior_kept,
    }

    return {
        "corredor": corridor,
        "c1_emendas": c1,
        "fechamento": closure,
        "topologia": topo,
        "externo_invariante": exterior,
        "ok_geral": bool(corridor["ok"] and c1["ok"] and closure["ok"]
                         and topo["ok"] and exterior["ok"]),
    }


def main() -> int:
    if not TRACK_FILE.exists():
        print(f"ERRO: pista frozen ausente: {TRACK_FILE}", file=sys.stderr)
        return 2
    with TRACK_FILE.open("r", encoding="utf-8") as f:
        track = json.load(f)
    if track.get("sha256") != TRACK_SHA_PIN:
        print(f"ERRO: SHA divergente: {track.get('sha256')} != {TRACK_SHA_PIN}",
              file=sys.stderr)
        return 2
    wps = np.array(track["waypoints"], dtype=np.float64)
    if len(wps) != int(track.get("n_wp", len(wps))):
        print("ERRO: n_wp divergente", file=sys.stderr)
        return 2
    sv_sha = sha256_file(Path(SV.__file__).resolve())
    if sv_sha != SAIDAS_VERDICT_SHA256:
        print(f"ERRO: saidas_verdict.py alterado: {sv_sha}", file=sys.stderr)
        return 2
    geom_sha = sha256_file(Path(RG.__file__).resolve())

    cum, total_len = vertex_geometry(wps)

    # 2. re-derivação da raiz (proveniência dos limites ratificados)
    corners = SV.build_corner_definitions(
        wps, kappa_thresh=KAPPA_THRESH, merge_gap_m=MERGE_GAP_M,
        generic_names=False)
    c08 = [c for c in corners if c["id"] == "C08"][0]
    idx_w = np.where((cum >= c08["s0"]) & (cum <= c08["s1"]))[0]
    roots = RG.offset_roots_within_window(wps, idx_w, SIGMA, R_ARC_M)
    deriv = None
    for r in roots:
        d = max(abs(r["s_a_m"] - S_A_M), abs(r["s_b_m"] - S_B_M))
        if deriv is None or d < deriv["delta_m"]:
            deriv = {"s_a_deriv_m": r["s_a_m"], "s_b_deriv_m": r["s_b_m"],
                     "delta_m": round(d, 6), "net_turn_deg": r["net_turn_deg"]}
    if deriv is None or deriv["delta_m"] > DERIV_TOL_M:
        print(f"ERRO: limites ratificados não rederiváveis da geometria frozen: {deriv}",
              file=sys.stderr)
        return 2

    # 3. construção no s ratificado
    virt, info = build_virtual_line(wps, cum, S_A_M, S_B_M, R_ARC_M, DS_ARC_MAX_M)

    # 4. gates
    gates = evaluate_gates(virt, wps, cum, info)
    verdict = "OK" if gates["ok_geral"] else "PARE"

    virt_list = [[round(float(x), 6) for x in p] for p in virt]
    payload = {
        "schema_version": VERSION,
        "emenda": "Emenda nº 1 — Limites Derivados por Bi-Tangência",
        "prereg": "experiments/racing-line-1/PREREG_RACING_LINE_1.md",
        "track_file": str(TRACK_FILE.relative_to(BACKEND)),
        "track_sha256_pin": TRACK_SHA_PIN,
        "n_waypoints": int(len(wps)),
        "half_width_m": float(track["width_m"]) / 2.0,
        "saidas_verdict_sha256": sv_sha,
        "racing_line_1_geometria_sha256": geom_sha,
        "constantes_ratificadas": {
            "s_a_m": S_A_M, "s_b_m": S_B_M, "R_m": R_ARC_M,
            "ds_arco_max_m": DS_ARC_MAX_M,
            "corredor_max_m": CORRIDOR_MAX_M, "c1_tol_deg": C1_TOL_DEG,
            "fechamento_tol_m": CLOSURE_TOL_M, "derivacao_tol_m": DERIV_TOL_M,
        },
        "verificacao_derivacao": deriv,
        "construcao": {
            "centro_O_m": [round(float(v), 6) for v in info["O"]],
            "sweep_deg": round(info["sweep_deg"], 4),
            "L_arco_m": round(info["L_arc_m"], 4),
            "n_amostras_arco": info["n_arc"],
            "ds_arco_m": round(info["ds_arc_m"], 6),
            "p_a_m": [round(float(v), 6) for v in info["p_a"]],
            "p_b_m": [round(float(v), 6) for v in info["p_b"]],
            "n_vertices_virtual": int(len(virt)),
            "vertices_externos": len(info["keep_lo"]) + len(info["keep_hi"]),
        },
        "gates": gates,
        "verdict": verdict,
        "linha_virtual_sha256": hashlib.sha256(
            json.dumps(virt_list, sort_keys=True).encode()).hexdigest(),
        "vertices_virtual": virt_list,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        print(f"ERRO: saída já existe (escrita exclusiva): {OUT_PATH}", file=sys.stderr)
        return 3
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    c = payload["construcao"]
    print(f"re-derivação: s_a {deriv['s_a_deriv_m']} / s_b {deriv['s_b_deriv_m']} "
          f"(Δ vs ratificado {deriv['delta_m']} m; giro {deriv['net_turn_deg']}°)")
    print(f"construção: O {c['centro_O_m']} | sweep {c['sweep_deg']}° | "
          f"L_arco {c['L_arco_m']} m | {c['n_amostras_arco']} amostras "
          f"(ds {c['ds_arco_m']} m ≤ {DS_ARC_MAX_M}) | {c['n_vertices_virtual']} vértices")
    g = gates
    print(f"corredor: máx {g['corredor']['desvio_max_m']} m ≤ {CORRIDOR_MAX_M} "
          f"-> {g['corredor']['ok']}")
    print(f"C1: emenda_a {g['c1_emendas']['emenda_a_deg']}° / "
          f"emenda_b {g['c1_emendas']['emenda_b_deg']}° < {C1_TOL_DEG}° "
          f"-> {g['c1_emendas']['ok']}")
    print(f"fechamento: tang_a {g['fechamento']['erro_tangencia_a_m']:.2e} m / "
          f"tang_b {g['fechamento']['erro_tangencia_b_m']:.2e} m -> "
          f"{g['fechamento']['ok']} | auto-interseção: {g['topologia']['auto_intersecao']} "
          f"-> {g['topologia']['ok']} | externo invariante: {g['externo_invariante']['ok']}")
    print(f"VEREDITO: {verdict} -> {OUT_PATH}")
    return 0 if verdict == "OK" else 4


if __name__ == "__main__":
    raise SystemExit(main())
