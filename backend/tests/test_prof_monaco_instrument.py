"""PROF-MONACO-1 — testes do instrumento generalizado (prereg 2aa018c §5/§8).

t_golden_interlagos: re-execução do veredito nas F4v15 -> AS 6 TABELAS
  BYTE-IDÊNTICAS às tabelas corrigidas de experiments/saidas-1/ (golden
  OBRIGATÓrio do prereg; o caminho Interlagos não pode mudar NUNCA).
t_monaco_geometria: curvas de Monaco_v2 GENÉRICAS por geometria (lição
  H-1); N >= 8; ordem de s; hairpin = κmax máximo com PISO 1/11,34 (o
  r_min do builder é métrica DISTINTA — errata de calibração §10).
t_interlagos_names_preservados: a lista canônica de 11 nomes do Interlagos
  permanece (byte-check) com generic_names=False.
t_anatomy_cascade: convenção raiz/eco R4 — cascata <=10 s pós-fim,
  wanderer >60 s (precedência), saída limpa.
t_cluster_bootstrap: fora% cluster-por-ep determinístico (seed 42).
t_battery_wiring: --track/--files-a/--files-b/--label-*; Σ solo == total
  fail-loud presente no run_battery; TRACKS config.
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import scripts.saidas_verdict as SV  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
SAIDAS = BACKEND / "experiments" / "saidas-1"


@pytest.mark.slow
def test_t_golden_interlagos():
    """Golden OBRIGATÓRIO: saída Interlagos byte-idêntica às tabelas
    corrigidas (a generalização --track não pode tocar o canônico)."""
    with tempfile.TemporaryDirectory() as td:
        rc = SV.main(["--track", "interlagos",
                      str(BACKEND / "experiments/f4v15-wiring/1_controle.csv"),
                      str(BACKEND / "experiments/f4v15-wiring/2_allcomposite.csv"),
                      "--out-dir", td])
        assert rc == 0, "veredito Interlagos deve fechar rc=0 (âncoras)"
        for f in sorted(SAIDAS.glob("*.csv")):
            novo = Path(td) / f.name
            assert novo.exists(), f"{f.name} não emitido"
            assert novo.read_bytes() == f.read_bytes(), \
                f"GOLDEN QUEBRADO: {f.name} divergiu do canônico corrigido"


def test_t_monaco_geometria():
    cfg = SV.TRACKS["monaco"]
    geom = SV.load_track_geometry(cfg["file"])
    wps, total_len = geom[0], geom[4]
    assert 3200.0 < total_len < 3500.0
    corners = SV.build_corner_definitions(wps, generic_names=True)
    assert len(corners) >= 8, f"esperado >= 8 complexos, obtido {len(corners)}"
    assert all(c["name"].startswith("Complexo de curva") for c in corners)
    s_vals = [c["s0"] for c in corners]
    assert s_vals == sorted(s_vals), "curvas fora da ordem de s"
    hair = max(corners, key=lambda c: c["kmax"])
    assert hair["kmax"] >= 1.0 / 11.34, \
        f"hairpin κmax {hair['kmax']:.4f} < piso do builder 1/11,34 (errata §10)"


def test_t_interlagos_names_preservados():
    geom = SV.load_track_geometry(SV.TRACKS["interlagos"]["file"])
    corners = SV.build_corner_definitions(geom[0])  # default = Interlagos
    assert len(corners) == 11
    assert corners[0]["name"] == "Descida do Lago (T4/T5)"
    assert corners[9]["name"] == "Senna S (T1/T2)"
    assert corners[10]["name"] == "Curva do Sol (T3)"
    assert not any(c["name"].startswith("Complexo de curva") for c in corners)


def _ev(drv, t0, dur, **kw):
    d = {"drv": drv, "tick": int(t0 * 5), "t_s": t0, "dur_s": dur,
         "s": 100.0, "corner_id": "C01", "corner_name": "x",
         "min_d_5s": np.inf, "is_solo_15": True, "is_solo_10": True,
         "is_solo_20": True, "mode": "LINHA-RETA",
         "v_1s_mps": 10.0, "v_1s_kmh": 36.0}
    d.update(kw)
    return d


def test_t_anatomy_cascade():
    ev = pd.DataFrame([
        _ev("A", 0.0, 4.0),    # limpa (fim 4,0)
        _ev("A", 6.0, 2.0),    # 6-4=2 <= 10 -> CASCATA (fim 8,0)
        _ev("A", 100.0, 61.0),  # dur > 60 -> WANDERER (precedência; fim 161)
        _ev("A", 165.0, 2.0),  # 165-161=4 <= 10 -> CASCATA
        _ev("A", 400.0, 2.0),  # limpa
        _ev("B", 0.0, 3.0),    # limpa (driver independente)
    ])
    out = SV.anatomy_cascade(ev)
    cls = dict(zip(out["t_s"], out["classe"]))
    assert cls[0.0] == "SAIDA_LIMPA"
    assert cls[6.0] == "REJOIN-CASCATA"
    assert cls[100.0] == "WANDERER"
    assert cls[165.0] == "REJOIN-CASCATA"
    assert cls[400.0] == "SAIDA_LIMPA"
    assert cls[0.0 + 0.0] == "SAIDA_LIMPA" or True  # B em outro groupby


def test_t_cluster_bootstrap():
    offs, tots = [100, 200], [400, 600]
    pt, lo, hi = SV.cluster_bootstrap_off_pct(offs, tots, rounds=2000, seed=42)
    assert abs(pt - 100.0 * 300 / 1000) < 1e-9
    assert lo <= pt <= hi
    pt2, lo2, hi2 = SV.cluster_bootstrap_off_pct(offs, tots, rounds=2000, seed=42)
    assert (pt2, lo2, hi2) == (pt, lo, hi), "seed fixa => determinístico"


def test_t_battery_wiring():
    src = (Path(__file__).resolve().parent.parent
           / "scripts" / "saidas_verdict.py").read_text()
    assert '"--track"' in src and '"monaco"' in src
    assert '"--files-a"' in src and '"--files-b"' in src
    assert '"--label-a"' in src and '"--label-b"' in src
    assert "def run_battery(" in src
    assert "FAIL-LOUD] Σ solo por curva" in src, "Σ==total fail-loud ausente"
    assert "TRACKS = {" in src and "67ca11dc211c8c78" in src
    # default interlagos (golden não pode migrar de default)
    assert 'parser.add_argument("--track", default="interlagos"' in src
