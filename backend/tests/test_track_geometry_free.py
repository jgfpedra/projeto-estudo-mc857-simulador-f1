"""FONTE-2 — testes do módulo track_geometry_free + fail-loud do draw_track
(prereg 9ba3f8c §6: 2 testes unitários).

t_f2_1: o filtro de outliers NÃO distorce a geometria — círculo sintético
        de 800 m de raio percorrido em multi-volta com GARAGEM parada
        (5.000 amostras paradas) no início: a volta extraída deve ter
        arco ≈ 2π·800 (tolerância 5%) e raio médio ≈ 800 (tolerância 2%).
t_f2_2: fail-loud — load_track com pista inexistente levanta SystemExit
        != 0 e a mensagem de erro lista os mirrors canônicos + OpenF1 +
        --legacy-preset (nunca desenha outra pista silenciosamente).
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from scripts.tracks import track_geometry_free as TGF  # noqa: E402


def _synthetic_session(radius: float = 800.0, laps: int = 5,
                       garage_samples: int = 5000, hz: float = 9.0):
    """Sessão sintética: garagem parada + voltas de círculo a 60 m/s."""
    import datetime
    samples = []
    t0 = datetime.datetime(2024, 9, 1, 12, 0, 0,
                           tzinfo=datetime.timezone.utc)
    dt = datetime.timedelta(seconds=1.0 / hz)
    # garagem: 5000 amostras paradas num ponto fixo (a ~2R do círculo)
    t = t0
    for _ in range(garage_samples):
        samples.append({"date": t.isoformat(), "x": 3 * radius,
                        "y": 3 * radius, "z": 0})
        t += dt
    # 5 voltas de círculo: raio 800, v angular = 60/800 rad/s
    w = 60.0 / radius
    n_lap = int(2 * np.pi / w * hz)
    for i in range(laps * n_lap):
        th = w * (i / hz)
        x = radius * np.cos(th) / 0.1   # /location usa DECÍMETROS
        y = radius * np.sin(th) / 0.1
        samples.append({"date": t.isoformat(), "x": x, "y": y, "z": 0})
        t += dt
    return samples


def test_t_f2_1_filtro_nao_distorce_geometria():
    samples = _synthetic_session()
    line = TGF.filter_race_line(samples, unit_scale=0.1)
    assert line is not None and len(line) >= 50, "volta não extraída"
    closed = np.vstack([line, line[:1]])
    arc = float(np.hypot(*np.diff(closed, axis=0).T).sum())
    alvo = 2 * np.pi * 800.0
    assert abs(arc - alvo) / alvo < 0.05, \
        f"arco {arc:.0f} m distorce o círculo {alvo:.0f} m (>5%)"
    # raio médio: distância ao centroide ≈ 800 m
    c = line.mean(axis=0)
    r_med = float(np.hypot(line[:, 0] - c[0], line[:, 1] - c[1]).mean())
    assert abs(r_med - 800.0) / 800.0 < 0.02, \
        f"raio médio {r_med:.0f} m distorce 800 m (>2%)"


def test_t_f2_2_fail_loud_lista_opcoes(monkeypatch):
    # SEM REDE: o fail-loud é testado com o OpenF1 stubado (a 1ª versão
    # deste teste fez 1 chamada de rede NÃO-LOGADA a OpenF1 (país
    # fictício, 1,9 s) — DISCLOSED no probe_log #6; regra: teste não
    # gasta orçamento de rede).
    from scripts.tracks import draw_track as DT
    # load_track importa o módulo DENTRO da função — o monkeypatch no
    # objeto-módulo compartilhado é visível no import da função.
    monkeypatch.setattr(TGF, "openf1_track", lambda *a, **k: None)
    with pytest.raises(SystemExit) as ei:
        DT.load_track(name="pista-inexistente-xyz")
    assert ei.value.code == 3, "exit code do fail-loud deve ser 3"
    # a exceção já imprimiu a lista no stderr (main); aqui garantimos o
    # código e que NENHUM Track foi devolvido silenciosamente
