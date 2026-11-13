"""FASE H-0 — testes do pipeline mirror + detector G3 (prereg 21ac676 §5).

t1 parser do path SVG (M/c/s/z; rejeita comandos fora do prereg);
t2 resample em arco (ds≈4 m; loop fechado);
t3 gates sintéticos (clean PASSA; fold <8 m falha G1; cruzamento falha G2;
   R apertado falha G3);
t4 convenção de sha do freeze (a do load_track_frozen — valida contra um
   frozen existente; adaptação declarada: o t4 original "artefatos se
   congelados" ficou N/A — os mirrors NÃO foram congelados, G4 FAIL);
t5 detector G3 sintético (near-touch <2 m = risco; gap 20 m = gap).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.tracks.track_mirror_build import (parse_svg_path, resample_closed,
                                                seg_seg_min_dist, count_crossovers,
                                                radii_and_turns)
from backend.scripts.tracks.track_g3_detector import GAP_M, RISK_M

BACKEND = Path(__file__).resolve().parent.parent


def test_t1_parser_svg_path():
    """M/c/s/z -> pontos Bézier; endpoints exatos; comando fora = PARE."""
    d = "M 0 0 c 10 0 10 10 0 10 s -10 0 0 10 z"
    pts, p0, pend = parse_svg_path(d, samples=8)
    assert p0 is not None and np.allclose(p0, [0, 0])
    # c: end = (0,10); s: c1 refletido, end = (0,20)
    assert np.allclose(pend, [0, 20]), f"end do 's' errado: {pend}"
    assert np.allclose(pts[0], [0, 0])
    # ponto final da primeira Bézier = (0,10) (o primeiro sample da 2ª curva é > 0)
    assert np.allclose(pts[7], [0, 10]), "end da 1ª Bézier (c) errado"
    try:
        parse_svg_path("M 0 0 L 10 10 z")
        raise SystemExit("comando L deveria ser REJEITADO (prereg §2.1)")
    except ValueError as e:
        assert "fora do prereg" in str(e)


def test_t2_resample_fechado_ds4():
    """Círculo denso -> resample a 4 m: n_wp ~ 2πR/4, espaçamento ~4, loop."""
    R = 100.0
    ang = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
    pts = np.stack([R * np.cos(ang), R * np.sin(ang)], axis=1)
    wps = resample_closed(pts, ds=4.0)
    n_expected = int(round(2 * np.pi * R / 4.0))
    assert abs(len(wps) - n_expected) <= 1
    seg = np.hypot(*np.diff(np.vstack([wps, wps[:1]]), axis=0).T)
    assert abs(float(seg.mean()) - 4.0) < 0.05, f"ds medio {seg.mean():.3f} != 4"
    assert float(seg.max()) < 4.15 and float(seg.min()) > 3.85


def test_t3_gates_sinteticos():
    """Clean passa; fold <8 m falha G1; cruzamento falha G2; R apertado falha G3.
    Fixtures DENSOS: a janela de não-adjacência (gap de arco >40 m) exige
    >11 wps entre os segmentos opostos."""
    # clean: círculo R=100 (clearance ~ diâmetro; R_min ~100; sem cruzamento)
    ang = np.linspace(0, 2 * np.pi, 160, endpoint=False)
    circle = np.stack([100 * np.cos(ang), 100 * np.sin(ang)], axis=1)
    pairs = seg_seg_min_dist(circle)
    # pares não-adjacentes do círculo ficam a ~40 m — fora da janela de
    # report (<25 m) -> lista vazia; clearance = default 99 (padrão do gate)
    assert min((d for _, _, d in pairs), default=99.0) >= 8.0
    assert count_crossovers(circle) == 0
    r_min, _, _ = radii_and_turns(circle)
    assert r_min >= 8.0
    # fold: estádio 200x5 denso -> lados opostos a 5 m (arco ~200 m) falham G1
    fold = resample_closed(np.array([[0, 0], [200, 0], [200, 5], [0, 5]], dtype=float), 4.0)
    pairs_f = seg_seg_min_dist(fold)
    assert pairs_f and min(d for _, _, d in pairs_f) < 8.0, "fold de 5m deveria falhar G1"
    # cruzamento: dois círculos sobrepostos (R=60, centros ±50) -> crossover > 0
    t = np.linspace(0, 2 * np.pi, 300)
    eight = np.vstack([
        np.stack([50 + 60 * np.cos(t), 60 * np.sin(t)], axis=1),
        np.stack([-50 + 60 * np.cos(t), 60 * np.sin(t)], axis=1)])
    eight_wps = resample_closed(eight, 4.0)
    assert count_crossovers(eight_wps) > 0, "círculos sobrepostos deveriam ter crossover"
    # R apertado: tripleta em arco apertado (R≈6,15 m) -> R_min < 8
    tri = np.array([[0, 0], [4, 0], [5, 3.0]], dtype=float)
    r_tri, _, _ = radii_and_turns(tri)
    assert r_tri < 8.0, f"arco apertado deveria dar R_min < 8 (veio {r_tri:.2f})"


def test_t4_convencao_sha_do_freeze():
    """A convenção sha do builder = a do load_track_frozen (validada contra
    um frozen REAL). [ADOÇÃO-H-2: Monaco_v1 movido para archive/ — path
    atualizado; disclose no fechamento.]"""
    import hashlib
    data = json.loads((BACKEND / "archive" / "tracks_frozen_v1" / "Monaco_v1.json").read_text())
    data_check = {k: v for k, v in data.items() if k != "sha256"}
    raw = json.dumps(data_check, sort_keys=True).encode()
    assert hashlib.sha256(raw).hexdigest()[:16] == data["sha256"], \
        "convenção sha do builder diverge do loader"


def test_t5_detector_sintetico():
    """Near-touch 1,5 m = risco de hint; espaçamento 20 m = gap. Fixtures
    DENSOS (janela de não-adjacência >40 m de arco)."""
    # pinça: estádio 200x1.5 denso -> lados opostos a 1,5 m (< RISK_M)
    pinch = resample_closed(np.array([[0, 0], [200, 0], [200, 1.5], [0, 1.5]], dtype=float), 4.0)
    pairs = seg_seg_min_dist(pinch)
    risks = [d for _, _, d in pairs if d < RISK_M]
    assert risks, "pinça de 1,5m deveria flaggar risco de hint"
    # gap: loop com um trecho de 20 m entre waypoints adjacentes
    withgap = np.array([[0, 0], [20, 0], [21, 1], [1, 1], [0, 0]], dtype=float)
    seg = np.hypot(*np.diff(np.vstack([withgap, withgap[:1]]), axis=0).T)
    gaps = seg[seg > GAP_M]
    assert len(gaps) >= 1 and float(gaps.max()) > 19.0, "gap de 20m deveria flaggear"
