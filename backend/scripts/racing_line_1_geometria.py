#!/usr/bin/env python3
"""RACING-LINE-1 Task 2 — construção geométrica offline do candidato C08.

Report-only, determinístico, zero corrida, zero rede, zero alteração da pista
frozen. Implementa EXATAMENTE o §3 de PREREG_RACING_LINE_1.md:

1. carrega a pista frozen local e verifica o SHA pinado;
2. obtém a janela C08 pela definição canônica de curva
   (``build_corner_definitions`` de ``saidas_verdict.py``, parâmetros canônicos);
3. tenta um arco circular de R=18,0 m tangente às direções da linha nos
   limites da janela (posição + tangente congeladas nos dois vértices de
   fronteira — construção superdeterminada: o resíduo mede a coincidência);
4. se houver solução, substitui somente os pontos internos à janela, preserva
   os externos byte-idênticos e avalia os gates: C1 nos emendas, corredor
   (meia-largura da pista frozen), fechamento, auto-interseção e erro de
   projeção;
5. se NÃO houver solução, o veredito é PARE (§7 do prereg: sem ajuste post
   hoc). Como evidência para o dono, o JSON registra também a varredura
   report-only de raízes bi-tangentes com limites LIVRES dentro da janela
   (evidência para uma eventual nova preregistração — NÃO é candidato);
6. escreve todos os limites, parâmetros, hashes e métricas no JSON;
7. a repetição em processo separado deve produzir JSON byte-idêntico (cmp=0).

Saída exclusiva: ``experiments/racing-line-1/c2/GEOMETRIA_C08.json``.
Exit 0 = candidato construído e aprovado nos gates; exit 4 = PARE (JSON
gravado com as evidências); exit 2 = erro de entrada.
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
from model_train.velocity_profile import compute_kappa_profile  # noqa: E402

VERSION = "racing-line-1/task2-geometria-v1.0"
SAIDAS_VERDICT_SHA256 = (
    "e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c"
)

# Constantes congeladas no §2 do PREREG_RACING_LINE_1.md
TRACK_FILE = BACKEND / "model_train" / "tracks_frozen" / "interlagos_v2.json"
TRACK_SHA_PIN = "164876196eb12174"
R_ARC_M = 18.0
KAPPA_THRESH = 0.006          # canônico de build_corner_definitions
MERGE_GAP_M = 40.0            # canônico
SMOOTH_WINDOW_M = 30.0        # canônico (perfil de curvatura da definição)
DS_TARGET = 4.0               # canônico
CORNER_ID = "C08"
CORNER_NAME_SUBSTR = "Junção"
RESIDUAL_TOL_M = 1e-3         # resíduo máximo para declarar solução exata
TANGENT_TOL_RAD = 1e-4        # casamento de tangente na emenda
CORRIDOR_SLACK_M = 0.0        # corredor: exatamente a faixa da pista frozen

OUT_PATH = BACKEND / "experiments" / "racing-line-1" / "c2" / "GEOMETRIA_C08.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def vertex_geometry(wps: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """s cumulativo, tangente centrada unitária e normal esquerda por vértice."""
    closed = np.vstack([wps, wps[:1]])
    diff = np.diff(closed, axis=0)
    seg = np.hypot(diff[:, 0], diff[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    total = float(np.sum(seg))
    T = np.roll(wps, -1, axis=0) - np.roll(wps, 1, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = np.stack([-T[:, 1], T[:, 0]], axis=1)  # normal esquerda (+90°)
    return cum, T, N, total


def heading_signed(wps: np.ndarray) -> np.ndarray:
    """Heading centrado por vértice (mesma convenção de compute_kappa_profile)."""
    T = np.roll(wps, -1, axis=0) - np.roll(wps, 1, axis=0)
    return np.arctan2(T[:, 1], T[:, 0])


def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def seg_point_dist(px: float, py: float, ax: float, ay: float,
                   bx: float, by: float) -> float:
    """Distância do ponto (px,py) ao segmento AB."""
    abx, aby = bx - ax, by - ay
    L2 = abx * abx + aby * aby
    if L2 <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * abx + (py - ay) * aby) / L2
    t = min(1.0, max(0.0, t))
    return math.hypot(px - (ax + t * abx), py - (ay + t * aby))


def max_dist_to_polyline(pts: np.ndarray, poly: np.ndarray) -> float:
    """Máxima distância dos pontos aoCamino polilinha fechado (vetorizado)."""
    a = poly
    b = np.roll(poly, -1, axis=0)
    ab = b - a
    L2 = np.maximum((ab * ab).sum(axis=1), 1e-18)
    out = np.empty(len(pts))
    for i in range(len(pts)):
        p = pts[i]
        ap = p - a
        t = np.clip((ap * ab).sum(axis=1) / L2, 0.0, 1.0)
        proj = a + t[:, None] * ab
        out[i] = np.hypot(*(p - proj).T).min()
    return float(out.max())


def segments_self_intersect(poly: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int]]]:
    """Verifica auto-interseção própria na polilinha fechada (pares não adjacentes)."""
    n = len(poly)
    a = poly
    b = np.roll(poly, -1, axis=0)

    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    def strict_cross(i: int, j: int) -> bool:
        p1, p2 = a[i], b[i]
        p3, p4 = a[j], b[j]
        d1 = cross(p3, p4, p1)
        d2 = cross(p3, p4, p2)
        d3 = cross(p1, p2, p3)
        d4 = cross(p1, p2, p4)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    for i in range(n):
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue  # adjacentes compartilham vértice
            if strict_cross(i, j):
                return True, (int(i), int(j))
    return False, None


def offset_roots_within_window(wps: np.ndarray, idx_w: np.ndarray, sigma: float,
                               R: float) -> List[Dict[str, float]]:
    """Varredura report-only: raízes exatas de O(s)=P(s)+σR·N(s) consigo mesma
    dentro da janela (limites livres). Newton 2D com sementes da grade,
    determinístico. Evidência para eventual nova preregistração."""
    cum, T, N, _ = vertex_geometry(wps)
    heads = heading_signed(wps)

    def O_at(i: int) -> np.ndarray:
        return wps[i] + sigma * R * N[i]

    roots: List[Dict[str, float]] = []
    O_w = np.array([O_at(i) for i in idx_w])
    m = len(idx_w)
    for a_i in range(m):
        for b_i in range(a_i + 1, m):
            d = float(np.linalg.norm(O_w[a_i] - O_w[b_i]))
            if d > 2.0:
                continue
            # Newton 2D em (s_a, s_b) contínuos com interpolação linear de P,N
            sa, sb = float(cum[idx_w[a_i]]), float(cum[idx_w[b_i]])

            def interp(arr: np.ndarray, s: float) -> np.ndarray:
                s_mod = s % float(cum[-1] + np.linalg.norm(wps[0] - wps[-1]))
                j = int(np.searchsorted(cum, s_mod, side="right") - 1) % len(wps)
                k = (j + 1) % len(wps)
                span = (cum[k] - cum[j]) if cum[k] > cum[j] else (cum[-1] + np.linalg.norm(wps[0] - wps[-1]) - cum[j])
                t = min(max((s_mod - cum[j]) / max(span, 1e-12), 0.0), 1.0)
                return arr[j] * (1.0 - t) + arr[k] * t

            def G(sa: float, sb: float) -> np.ndarray:
                return (interp(wps, sa) + sigma * R * interp(N, sa)
                        - interp(wps, sb) - sigma * R * interp(N, sb))

            g = G(sa, sb)
            for _ in range(60):
                if float(np.linalg.norm(g)) < 1e-9:
                    break
                eps = 1e-5
                J = np.column_stack([
                    (G(sa + eps, sb) - G(sa - eps, sb)) / (2 * eps),
                    (G(sa, sb + eps) - G(sa, sb - eps)) / (2 * eps),
                ])
                det = float(np.linalg.det(J))
                if abs(det) < 1e-12:
                    break
                step = np.linalg.solve(J, -g)
                sa += float(step[0])
                sb += float(step[1])
                g = G(sa, sb)
            if float(np.linalg.norm(g)) < 1e-6:
                L = float(np.sum(np.linalg.norm(
                    np.diff(np.vstack([wps, wps[:1]]), axis=0), axis=1)))
                sa_m, sb_m = sa % L, sb % L
                if sb_m < sa_m:
                    sa_m, sb_m = sb_m, sa_m
                if any(abs(sa_m - r["s_a_m"]) < 1.0 and abs(sb_m - r["s_b_m"]) < 1.0
                       for r in roots):
                    continue
                psi_a, psi_b = float(interp(heads, sa)), float(interp(heads, sb))
                roots.append({
                    "s_a_m": round(sa_m, 3),
                    "s_b_m": round(sb_m, 3),
                    "net_turn_deg": round(math.degrees(wrap_angle(psi_b - psi_a)), 2),
                    "residual_m": float(np.linalg.norm(g)),
                })
    roots.sort(key=lambda r: (r["s_a_m"], r["s_b_m"]))
    return roots


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
    n_wp = int(track.get("n_wp", len(wps)))
    if len(wps) != n_wp:
        print("ERRO: n_wp divergente dos waypoints", file=sys.stderr)
        return 2
    half_width = float(track["width_m"]) / 2.0 + CORRIDOR_SLACK_M

    sv_sha = sha256_file(Path(SV.__file__).resolve())
    if sv_sha != SAIDAS_VERDICT_SHA256:
        print(f"ERRO: saidas_verdict.py alterado: {sv_sha}", file=sys.stderr)
        return 2

    # 2. Janela C08 canônica
    corners = SV.build_corner_definitions(
        wps, kappa_thresh=KAPPA_THRESH, merge_gap_m=MERGE_GAP_M,
        generic_names=False,
    )
    c08 = [c for c in corners if c["id"] == CORNER_ID]
    if not c08 or CORNER_NAME_SUBSTR not in c08[0]["name"]:
        print("ERRO: C08/Junção não encontrada na definição canônica", file=sys.stderr)
        return 2
    c08 = c08[0]
    s0_can, s1_can = float(c08["s0"]), float(c08["s1"])

    cum, T, N, total_len = vertex_geometry(wps)
    heads = heading_signed(wps)
    idx_w = np.where((cum >= s0_can) & (cum <= s1_can))[0]
    if len(idx_w) < 3:
        print("ERRO: janela C08 com vértices insuficientes", file=sys.stderr)
        return 2
    i_a, i_b = int(idx_w[0]), int(idx_w[-1])
    s_eff_a, s_eff_b = float(cum[i_a]), float(cum[i_b])

    # sentido da curva pelo perfil canônico
    s_arr, kap = compute_kappa_profile(
        wps, ds_target=DS_TARGET, smooth_window_m=SMOOTH_WINDOW_M)
    mw = (s_arr >= s0_can) & (s_arr <= s1_can)
    sigma = 1.0 if float(kap[mw].mean()) > 0 else -1.0

    # 3. Modo literal: arco tangente nos limites congelados da janela
    O_a = wps[i_a] + sigma * R_ARC_M * N[i_a]
    O_b = wps[i_b] + sigma * R_ARC_M * N[i_b]
    residual_in = float(np.linalg.norm(O_a - O_b))
    # combinações opostas (diagnóstico; não são candidato de quina)
    res_others = {}
    for sig in (1.0, -1.0):
        Oa = wps[i_a] + sig * R_ARC_M * N[i_a]
        Ob = wps[i_b] + sig * R_ARC_M * N[i_b]
        res_others[f"sigma_{int(sig)}_ambos"] = round(float(np.linalg.norm(Oa - Ob)), 6)

    chord = float(np.linalg.norm(wps[i_b] - wps[i_a]))
    sweep_from_chord_deg = math.degrees(
        2.0 * math.asin(min(chord / (2.0 * R_ARC_M), 1.0)))
    net_turn_deg = math.degrees(wrap_angle(float(heads[i_b]) - float(heads[i_a])))

    verdict = "OK" if residual_in <= RESIDUAL_TOL_M else "PARE"
    virtual_line: Optional[List[List[float]]] = None
    gates: Dict[str, Any] = {}

    if verdict == "OK":
        # 4. construção do arco e emenda
        psi_a, psi_b = float(heads[i_a]), float(heads[i_b])
        dpsi = wrap_angle(psi_b - psi_a)  # <0 = direita
        sweep = -dpsi if sigma < 0 else dpsi
        if sweep <= 0 or sweep >= 2 * math.pi:
            verdict = "PARE"
            gates["sweep_invalido"] = {"sweep_rad": sweep}
        else:
            theta_a = math.atan2(wps[i_a][1] - O_a[1], wps[i_a][0] - O_a[0])
            n_int = i_b - i_a - 1
            arc_pts = []
            for k in range(1, n_int + 1):
                th = theta_a + (dpsi * k / (n_int + 1))
                arc_pts.append([O_a[0] + R_ARC_M * math.cos(th),
                                O_a[1] + R_ARC_M * math.sin(th)])
            virt = wps.copy()
            virt[i_a + 1:i_b, :] = np.array(arc_pts)

            # gates
            head_v = heading_signed(virt)
            step = np.abs(np.roll(head_v, -1) - head_v)
            step = np.minimum(step, 2 * math.pi - step)
            splice_steps = [float(step[i_a]), float(step[i_b - 1])]
            step_ref = np.abs(np.roll(heads, -1) - heads)
            step_ref = np.minimum(step_ref, 2 * math.pi - step_ref)
            gates["c1_emenda"] = {
                "passo_heading_emendas_rad": [round(v, 6) for v in splice_steps],
                "passo_max_fora_janela_rad": round(float(step_ref[:i_a].max()) if i_a > 0 else 0.0, 6),
                "passo_max_arco_rad": round(float(step[i_a:i_b].max()), 6),
                "ok": bool(max(splice_steps) <= float(step[i_a:i_b].max()) * 1.05 + TANGENT_TOL_RAD),
            }
            dev = max_dist_to_polyline(virt, wps)
            gates["corredor"] = {
                "meia_largura_m": half_width,
                "desvio_max_m": round(dev, 4),
                "ok": bool(dev <= half_width),
            }
            closing = float(np.linalg.norm(virt[0] - virt[-1]))
            gates["fechamento"] = {
                "segmento_fechamento_m": round(closing, 4),
                "spacing_medio_m": round(total_len / len(wps), 4),
                "ok": bool(closing <= 2.0 * total_len / len(wps)),
            }
            inter, pair = segments_self_intersect(virt)
            gates["auto_intersecao"] = {"ok": not inter, "par": pair}
            gates["externos_intactos"] = {
                "ok": bool(np.array_equal(virt[:i_a + 1], wps[:i_a + 1])
                           and np.array_equal(virt[i_b:], wps[i_b:])),
            }
            ok_all = (gates["c1_emenda"]["ok"] and gates["corredor"]["ok"]
                      and gates["fechamento"]["ok"] and not inter
                      and gates["externos_intactos"]["ok"])
            verdict = "OK" if ok_all else "PARE"
            virtual_line = [[round(float(x), 6) for x in p] for p in virt]
            gates["linha_virtual_sha256"] = hashlib.sha256(
                json.dumps(virtual_line, sort_keys=True).encode()).hexdigest()
    else:
        roots = offset_roots_within_window(wps, idx_w, sigma, R_ARC_M)
        gates["raizes_bi_tangentes_limites_livres"] = roots
        gates["nota_evidencia"] = (
            "varredura report-only com limites livres dentro da janela C08; "
            "NÃO é candidato — o prereg exige tangência nos limites congelados")

    payload = {
        "schema_version": VERSION,
        "prereg": "experiments/racing-line-1/PREREG_RACING_LINE_1.md",
        "track_file": str(TRACK_FILE.relative_to(BACKEND)),
        "track_sha256_pin": TRACK_SHA_PIN,
        "n_waypoints": n_wp,
        "width_m": float(track["width_m"]),
        "half_width_m": half_width,
        "constantes": {
            "R_arco_m": R_ARC_M,
            "kappa_thresh": KAPPA_THRESH,
            "merge_gap_m": MERGE_GAP_M,
            "smooth_window_m": SMOOTH_WINDOW_M,
            "ds_target": DS_TARGET,
            "residual_tol_m": RESIDUAL_TOL_M,
        },
        "saidas_verdict_sha256": sv_sha,
        "janela_canonica": {
            "id": CORNER_ID, "name": c08["name"],
            "s0_m": round(s0_can, 3), "s1_m": round(s1_can, 3),
            "kmax": round(float(c08["kmax"]), 6),
        },
        "janela_efetiva_vertices": {
            "i_a": i_a, "i_b": i_b,
            "s_a_m": round(s_eff_a, 3), "s_b_m": round(s_eff_b, 3),
            "n_vertices_internos": int(i_b - i_a - 1),
        },
        "sentido_curva": "direita" if sigma < 0 else "esquerda",
        "sigma": sigma,
        "modo_literal_limites_congelados": {
            "residuo_centros_m": round(residual_in, 6),
            "residuos_outras_combinacoes_m": res_others,
            "corda_m": round(chord, 3),
            "sweep_pela_corda_deg": round(sweep_from_chord_deg, 2),
            "giro_liquido_linha_deg": round(net_turn_deg, 2),
            "solucao_exata": bool(residual_in <= RESIDUAL_TOL_M),
        },
        "gates": gates,
        "verdict": verdict,
        "vertices_virtual": virtual_line,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        print(f"ERRO: saída já existe (escrita exclusiva): {OUT_PATH}", file=sys.stderr)
        return 3
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"janela C08 canônica: s {s0_can:.1f} -> {s1_can:.1f} m "
          f"({c08['name']}; sentido {'direita' if sigma < 0 else 'esquerda'})")
    print(f"limites efetivos (vértices): s {s_eff_a:.3f} / {s_eff_b:.3f} m "
          f"({i_b - i_a - 1} vértices internos)")
    print(f"modo literal (limites congelados): resíduo dos centros = "
          f"{residual_in:.6f} m (tol {RESIDUAL_TOL_M} m) | corda {chord:.2f} m | "
          f"sweep pela corda {sweep_from_chord_deg:.1f}° | giro da linha {net_turn_deg:.1f}°")
    if verdict == "OK":
        print(f"gates: {json.dumps({k: v for k, v in gates.items() if k != 'linha_virtual_sha256'}, ensure_ascii=False)}")
    else:
        roots = gates.get("raizes_bi_tangentes_limites_livres", [])
        print(f"PARE: sem arco exato nos limites congelados; "
              f"raízes bi-tangentes com limites livres na janela: {len(roots)}")
        for r in roots:
            print(f"   s {r['s_a_m']} -> {r['s_b_m']} m | giro {r['net_turn_deg']}°")
    print(f"VEREDITO: {verdict} -> {OUT_PATH}")
    return 0 if verdict == "OK" else 4


if __name__ == "__main__":
    raise SystemExit(main())
