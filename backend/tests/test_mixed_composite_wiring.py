"""Testes do grupo composite no --mixed (prereg d54b5fe §6).

t-mixed-parse: "composite:N,edge:M" parseia; soma=10; chave desconhecida rejeita.
t-composite-controller: o ctrl_comp do grupo composite é um NeuralRaceController
obs 'traffic' com _composite_np (NumpyCompositeActor) apontando para os npz do
PROFILES['race'] — o MESMO caminho do --profile composite.
canonical-smoke: o caminho sem --mixed inicia a corrida com o schema esperado.
O fixture histórico pré-wiring continua arquivado, mas não pode ser comparado
bit a bit depois das mudanças intencionais de vácuo e do solver de contatos.
"""
import pandas as pd
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND / "model_train"))

from backend.model_train.race_diagnostic import parse_mixed, assign_groups


def test_t_mixed_parse():
    """composite:N,edge:M parseia; soma e chaves validadas."""
    g = parse_mixed("composite:2,edge:8", n_total=10)
    assert g == {'composite': 2, 'edge': 8}
    g2 = parse_mixed("composite:4,edge:6", n_total=10)
    assert g2 == {'composite': 4, 'edge': 6}
    with pytest.raises(ValueError):
        parse_mixed("composite:3,edge:6", n_total=10)   # soma 9 != 10
    with pytest.raises(ValueError):
        parse_mixed("bogus:2,edge:8", n_total=10)       # chave desconhecida
    groups = assign_groups(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'], g)
    assert groups['A'] == 'composite' and groups['B'] == 'composite'
    assert groups['C'] == 'edge' and groups['J'] == 'edge'
    assert len(groups) == 10


def test_t_composite_controller_do_mixed():
    """PROFILES['race'] aponta solo v10 + residual r2; o wiring do grupo
    composite usa EXATAMENTE esses artefatos (o mesmo caminho do --profile
    composite). Verificação estática dos caminhos + carga do NumpyCompositeActor."""
    from backend.scripts.simulation.run_race_10_cars import PROFILES, MODEL_DIR
    prof = PROFILES['race']
    assert prof['obs_mode'] == 'traffic'
    solo = Path(prof['keras'])
    resid = Path(prof['residual_npz'])
    assert solo.name == 'dagger_actor_best.keras' and 'v10_dagger' in str(solo)
    assert resid.name == 'residual_best_weights.npz' and 'v15_residual' in str(resid)
    assert solo.exists() and resid.exists()
    from backend.model_train.residual_gated import NumpyCompositeActor
    npz = solo.with_name(solo.stem + '_weights.npz')
    comp = NumpyCompositeActor(str(npz), str(resid))
    # forward de sanidade com a ASSINATURA real do NumPy path do runner
    # (tels 34d, ctxs, t_ids, c_ids, res_in 16d, gates):
    obs = np.zeros((2, 34), dtype=np.float32)
    ctx = np.zeros((2, 2), dtype=np.float32)
    t_ids = np.zeros(2, dtype=np.int32)
    c_ids = np.zeros(2, dtype=np.int32)
    res_in = np.zeros((2, 16), dtype=np.float32)
    gates = np.zeros(2, dtype=np.float32)
    a = comp.predict(obs, ctx, t_ids, c_ids, res_in, gates)
    assert a.shape == (2, 2) and np.all(np.isfinite(a)) and np.all(np.abs(a) <= 1.0)
    # com gate 1 e res_in zero: r(0) fixo → finito (o mesmo caminho do
    # residual_forward_only usado no predict_batch do runner)
    a2 = comp.predict(obs, ctx, t_ids, c_ids, res_in, np.ones(2, dtype=np.float32))
    assert np.all(np.isfinite(a2))


def test_canonical_race_without_mixed_keeps_valid_schema(tmp_path):
    """O caminho canônico sem --mixed inicia a corrida e grava telemetria válida."""
    out = tmp_path / "canonical_race.csv"
    cmd = [sys.executable, "model_train/race_diagnostic.py",
           "--actor", "model_train/v10_dagger/dagger_actor_best.keras",
           "--obs-mode", "edge", "--ticks", "30", "--laps", "99",
           "--track", "interlagos", "--seed", "0", "--gov", "vplan",
           "--variance", "grid,compound", "--out", str(out)]
    r = subprocess.run(cmd, cwd=str(BACKEND), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"corrida falhou: {r.stderr[-300:]}"
    assert out.exists()
    df = pd.read_csv(out, comment="#")
    assert not df.empty
    assert df["drv"].nunique() == 10
    assert "grupo" not in df.columns, "o modo canônico não deve ativar o wiring --mixed"
    assert np.isfinite(df[["s", "speed", "lat"]].to_numpy(dtype=np.float64)).all()
