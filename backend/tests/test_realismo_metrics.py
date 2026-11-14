"""REALISMO-1 · C0 — testes do instrumento `scripts/analysis/realismo_metrics.py`.

PLANO_REALISMO_BOTS_1 v1.1, Task 2 (TDD: escritos antes do instrumento).

- sintéticos com excursões conhecidas: Z_RETA (t <= 10 s inclusivo),
  Z_T1 (t <= 60 s inclusivo), C08 Junção e o wrap de Monaco (C01 com
  s0 < 0); janelas FORA-PRESO (réplica de race_diagnostic.py:1774-1799);
  cascata (anatomy_cascade importada) e nova saída <= 5 s com fronteira
  inteira em ticks; excursão censurada no fim da corrida;
- colado/deadlock pela lógica D3 importada de sanidade1b_verdict com o
  comprimento da pista parametrizado (wrap de Monaco) e restaurado;
- integridade por corrida (D2 do plano);
- aritmética inteira dos gates (107->118, 210->231, 44->41, 31->29);
- avaliador de gates por ciclo + disclosure por realização (alerta 3x);
- relatório de ruído (média/σ, pares ordenados, aproximação normal);
- determinismo (duas leituras, mesmo metrics_sha256) e criação exclusiva;
- golden N=0 na promocao-1 (exatos do plano = PARE se divergir).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

import scripts.analysis.realismo_metrics as RM

BACKEND = Path(__file__).resolve().parents[1]
PROMO = BACKEND / "experiments" / "composite-1" / "promocao-1"

N_ROWS = 500          # t_s 0,0 .. 99,8 (linhas 5 Hz = ticks pares)
HW = 6.0
SHA_INTERLAGOS = "164876196eb12174"
SHA_MONACO = "67ca11dc211c8c78"


# ---------------------------------------------------------------------------
# fixtures sintéticas
# ---------------------------------------------------------------------------
def _driver_rows(drv, s_start, ds_per_row, track_len, n_rows=N_ROWS):
    rows = []
    for k in range(n_rows):
        rows.append(dict(
            tick=2 * k, t_s=round(0.2 * k, 1), drv=drv, speed=20.0,
            s=(s_start + ds_per_row * k) % track_len, lat=0.0,
            cum_dist=float(k), offtrack=0, car_car=0,
            obs4=0.0, obs5=0.0, obs6=1.0))
    return rows


def _off(rows, start, n, lat=7.0):
    for k in range(start, start + n):
        rows[k].update(lat=float(lat), offtrack=1, obs4=float(lat) / HW)


def _write_main(path, rows, track_sha16):
    df = pd.DataFrame(rows).sort_values(["tick", "drv"], kind="stable")
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(f"# race_diag_v3_4_xyraw | track_frozen_sha256={track_sha16} "
                 "| sub_steps=24 | weather_mode=seeded | weather_seed=0 "
                 "| weather_transitions=[] | variance=off\n")
        df.to_csv(fh, index=False)


def _write_events(path):
    path.write_text("# race_diag_v3_contact_solver_v1 events=raw contact points "
                    "| sub->tick: sub//24\nsub,drv_a,drv_b\n", encoding="utf-8")


def _log_text(track_sha16, name, variedade=0, residual=True, override=False,
              var_line=True, preso=None, pilot=None, off_total=0):
    lines = [
        "[Grid] reta antes da SF: 45 m | grid ocupa 42 m",
        f"[diag] pista FROZEN: {name} | 1131 wp | SF wp 729 | sha256 {track_sha16} "
        "| clima=seeded (rng semeado por seed) | variance=off | rejoin_gap=0.0 "
        "| launch_cap=False | launch_stagger=False | pguard=False | grid=f1 "
        f"| rejoin=bearing | anti_glue=False | variedade={variedade} "
        "| prof_repair=False | pass_decision=False",
    ]
    if variedade and var_line:
        lines.append(f"[diag] VARIEDADE-1: N={variedade} (PRNG proprio "
                     "sha256(seed//variedade//N)) | jitter ±0,5m/±0,3m")
    if residual:
        lines.append("[diag] residual baseline sha256=6210fff65b19ad0e")
    if override:
        lines.append("[diag] RESIDUAL OVERRIDE (candidato): x.npz sha256=deadbeefdeadbeef")
    fora = f"  TOTAL fora: {off_total} ticks (1.0%)"
    if preso is not None:
        fora += f" | FORA-PILOTAGEM: {pilot} (x% do fora) | FORA-PRESO: {preso} (y% do fora)"
    lines += [fora,
              "  CARROS-PRESO na sessão: 0 (nenhum — gate exige 0)",
              "  HESITAÇÕES (v<0,5 m/s por 0,3-3 s, pós-largada): 0 (gate: <=3)"]
    return "\n".join(lines) + "\n"


def _interlagos_rows():
    L = RM.track_geometry("interlagos").length_m
    a = _driver_rows("AAA", 2630.0, 0.1, L)      # reta de largada
    _off(a, 11, 5)      # t=2,2 s, s=2631,1 -> Z_RETA
    _off(a, 60, 3)      # t=12,0 s, s=2636,0 -> intervalo da reta, mas t > 10 s
    b = _driver_rows("BBB", 2750.0, 0.1, L)      # Senna S (C10 = T1)
    _off(b, 20, 5)      # t=4,0 s -> Z_T1 com t <= 60
    _off(b, 400, 5)     # t=80,0 s -> C10, t > 60
    _off(b, 495, 5)     # t=99,0 s até o fim -> censurada
    c = _driver_rows("CCC", 2300.0, 0.01, L)     # Junção (C08)
    _off(c, 100, 5)     # tick 200..208, fim tick 210
    _off(c, 130, 2)     # tick 260: gap 50 ticks = 5,0 s -> nova saída <= 5 s
    _off(c, 158, 2)     # tick 316: gap 52 ticks = 5,2 s -> só cascata
    _off(c, 300, 3)     # t=60,0 s (inclusivo) -> gap 28 s
    d = _driver_rows("DDD", 1000.0, 0.1, L)      # Laranjinha (C03)
    for k in range(300, 450):
        d[k]["cum_dist"] = 300.0                 # janela [60,90): progresso 0
    _off(d, 10, 10, lat=25.0)   # janela [0,30): |lat| > 20 -> PRESO
    _off(d, 160, 10)            # janela [30,60): progresso >= 5 -> PILOTAGEM
    _off(d, 310, 10)            # janela [60,90): progresso < 5 -> PRESO
    return a + b + c + d


def _monaco_rows():
    L = RM.track_geometry("monaco").length_m
    e = _driver_rows("EEE", 3300.0, 0.5, L)
    _off(e, 10, 3)      # t=2,0 s, s=3305,0 -> Z_RETA
    _off(e, 63, 2)      # s=3331,5 -> C01 (início com wrap, sem margem) -> Z_T1
    _off(e, 75, 2)      # s=2,27 (depois do wrap) -> C01 -> Z_T1
    f = _driver_rows("FFF", 3320.0, 0.1, L)
    _off(f, 50, 2)      # tick 100 = t 10,0 s (inclusivo), s=3325,0 -> Z_RETA
    _off(f, 53, 2)      # tick 106 > 100 -> fora do critério temporal
    return e + f


class _Paths:
    def __init__(self, base, stem):
        self.log = base / f"{stem}.log"
        self.main = base / f"{stem}.csv"
        self.events = base / f"{stem}_events.csv"


def _fixture(tmp_path, track, **log_kw):
    if track == "interlagos":
        rows, sha, name = _interlagos_rows(), SHA_INTERLAGOS, "São Paulo Grand Prix"
        log_kw.setdefault("preso", 20)
        log_kw.setdefault("pilot", 45)
        log_kw.setdefault("off_total", 65)
    else:
        rows, sha, name = _monaco_rows(), SHA_MONACO, "Monaco Grand Prix (mirror 2021)"
        log_kw.setdefault("off_total", 11)
    p = _Paths(tmp_path, f"syn_{track}")
    _write_main(p.main, rows, sha)
    _write_events(p.events)
    p.log.write_text(_log_text(sha, name, **log_kw), encoding="utf-8")
    return p


def _n_lines(path):
    with Path(path).open("rb") as fh:
        return sum(1 for _ in fh)


def _analyze(p, track, **kw):
    kw.setdefault("expected_main_lines", _n_lines(p.main))
    return RM.analyze_run(run_id="SYN", log=p.log, main_csv=p.main,
                          events_csv=p.events, track=track, **kw)


# ---------------------------------------------------------------------------
# dependências e geometria
# ---------------------------------------------------------------------------
def test_dependencies_are_pinned_and_verified(tmp_path):
    assert RM.BASE_METRICS_SHA256 == (
        "9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728")
    assert RM.sha256_file(BACKEND / "scripts" / "base_metrics.py") == RM.BASE_METRICS_SHA256
    deps = RM.dependencies()
    assert Path(deps.BM.__file__).resolve() == (BACKEND / "scripts" / "base_metrics.py").resolve()
    assert Path(deps.SV.__file__).resolve() == (BACKEND / "scripts" / "saidas_verdict.py").resolve()
    fake = tmp_path / "fake.py"
    fake.write_text("X = 1\n", encoding="utf-8")
    with pytest.raises(RM.InstrumentError):
        RM.load_verified_module("fake_mod", fake, "0" * 64)


def test_track_name_normalization():
    assert RM.normalize_track("interlagos") == "interlagos"
    assert RM.normalize_track("Monaco") == "monaco"
    assert RM.normalize_track("monaco") == "monaco"
    with pytest.raises(RM.InstrumentError):
        RM.normalize_track("interlagos_v3")


def test_zones_match_plan_d3_and_match_corner():
    g = RM.track_geometry("interlagos")
    assert g.t1_corner_id == "C10" and g.junction_corner_id == "C08"
    assert abs(g.z_reta[0] - 2608.2) <= 0.1 and abs(g.z_reta[1] - 2718.3) <= 0.1
    assert abs(g.z_t1[0] - 2718.3) <= 0.1 and abs(g.z_t1[1] - 2882.3) <= 0.1
    sv = RM.dependencies().SV
    assert sv.match_corner(g.z_reta[1] - 1e-6, g.corners, g.length_m)[0] == "Reta"
    assert sv.match_corner(g.z_reta[1] + 1e-6, g.corners, g.length_m)[0] == "C10"
    m = RM.track_geometry("monaco")
    assert m.t1_corner_id == "C01" and m.junction_corner_id is None
    assert abs(m.z_reta[0] - 3288.3) <= 0.1 and abs(m.z_reta[1] - 3331.2) <= 0.1
    assert sv.match_corner(m.z_reta[1] + 1e-6, m.corners, m.length_m)[0] == "C01"
    assert sv.match_corner(2.0, m.corners, m.length_m)[0] == "C01"      # wrap
    for geo in (g, m):                      # Z_RETA inteira é reta no match_corner
        a, b = geo.z_reta
        span = (b - a) % geo.length_m
        for k in range(int(span / 0.5)):
            s = (a + 0.5 * k) % geo.length_m
            assert sv.match_corner(s, geo.corners, geo.length_m)[0] == "Reta"


def test_in_interval_mod_wraps():
    assert RM.in_interval_mod(3330.0, 3288.3, 3331.2, 3335.2)
    assert not RM.in_interval_mod(3331.2, 3288.3, 3331.2, 3335.2)    # semiaberto
    assert RM.in_interval_mod(1.0, 3330.0, 5.0, 3335.2)              # atravessa s=0
    assert not RM.in_interval_mod(6.0, 3330.0, 5.0, 3335.2)


# ---------------------------------------------------------------------------
# métricas novas em sintético
# ---------------------------------------------------------------------------
def test_synthetic_interlagos_metrics(tmp_path):
    p = _fixture(tmp_path, "interlagos")
    out = _analyze(p, "interlagos")
    m = out["metrics"]
    assert m["sample_rows"] == 4 * N_ROWS
    assert m["offtrack_rows"] == 65
    assert m["fora_preso_rows"] == 20 and m["fora_pilotagem_rows"] == 45
    assert m["excursions_total"] == 12
    assert m["excursions_t_le_60s"] == 9          # inclui t=60,0 s
    assert m["z_reta_exits"] == 1                 # t=12 s na reta não conta
    assert [e["drv"] for e in out["events"]["z_reta"]] == ["AAA"]
    assert m["z_t1_exits_t_le_60s"] == 1
    assert m["junction_exits"] == 4
    assert m["corner_exits"] == {"C03": 3, "C08": 4, "C10": 3, "Reta": 2}
    assert m["cascade_events"] == 3 and m["cascade_events_int"] == 3
    assert m["wanderer_events"] == 0
    assert m["cascade_offtime_rows"] == 7
    assert m["censored_excursions"] == 1 and m["reentries"] == 11
    assert m["new_exit_le_5s"] == 1               # gap 50 ticks conta; 52 não
    assert m["new_exit_le_5s_per_reentry"] == pytest.approx(1 / 11)
    assert m["new_exit_le_5s_per_excursion"] == pytest.approx(1 / 12)
    assert m["contacts_5hz_total"] == 0 and m["hesitations"] == 0
    assert out["cross_checks"]["fora_preso_vs_log"]["match"] is True
    assert out["integrity"]["ok"] is True


def test_synthetic_monaco_wrap_zones(tmp_path):
    p = _fixture(tmp_path, "monaco")
    out = _analyze(p, "monaco")
    m = out["metrics"]
    assert m["excursions_total"] == 5
    assert m["z_reta_exits"] == 2                 # EEE t=2,0 e FFF t=10,0
    assert sorted(e["drv"] for e in out["events"]["z_reta"]) == ["EEE", "FFF"]
    assert m["z_t1_exits_t_le_60s"] == 2          # s=3331,5 e s=2,27 (wrap)
    assert m["junction_exits"] is None
    assert out["cross_checks"]["fora_preso_vs_log"]["match"] is None


def test_fora_preso_windows_replica():
    rows = _driver_rows("DDD", 1000.0, 0.1, 4160.4)
    for k in range(300, 450):
        rows[k]["cum_dist"] = 300.0
    _off(rows, 10, 10, lat=25.0)
    _off(rows, 160, 10)
    _off(rows, 310, 10)
    preso, pilot = RM.fora_preso_split(pd.DataFrame(rows))
    assert (preso, pilot) == (20, 10)


def test_glue_deadlock_uses_track_length_and_restores(tmp_path):
    g = _driver_rows("GGG", 500.0, 0.0, 3335.2)
    h = _driver_rows("HHH", 2000.0, 0.0, 3335.2)
    for k in range(100, 115):             # 3,0 s colados atravessando s=0
        g[k]["s"], h[k]["s"] = 3333.0, 1.0
    for k in range(300, 355):             # 11,0 s colados -> deadlock
        g[k]["s"], h[k]["s"] = 1000.0, 1002.0
    path = tmp_path / "glue.csv"
    _write_main(path, g + h, SHA_MONACO)
    s1b = RM.dependencies().S1B
    before = s1b.L_TRACK
    assert RM.glue_deadlock(path, 3335.2) == (70, 1)
    assert RM.glue_deadlock(path, 4160.4) == (55, 1)   # comprimento errado perde o wrap
    assert s1b.L_TRACK == before


# ---------------------------------------------------------------------------
# integridade (D2)
# ---------------------------------------------------------------------------
def _subdir(tmp_path, name):
    d = tmp_path / name
    d.mkdir()
    return d


def test_integrity_checks_variants(tmp_path):
    p = _fixture(tmp_path, "interlagos")
    ok = _analyze(p, "interlagos")["integrity"]
    assert ok["ok"] is True and ok["variedade"] == 0

    p2 = _fixture(_subdir(tmp_path, "override"), "interlagos", override=True)
    bad = _analyze(p2, "interlagos")["integrity"]
    assert bad["ok"] is False and bad["checks"]["no_residual_override"]["pass"] is False

    p3 = _fixture(_subdir(tmp_path, "var2"), "interlagos", variedade=2)
    v2 = _analyze(p3, "interlagos", expect_variedade=2)["integrity"]
    assert v2["ok"] is True and v2["variedade"] == 2
    assert _analyze(p3, "interlagos", expect_variedade=3)["integrity"]["ok"] is False

    p4 = _fixture(_subdir(tmp_path, "var2_sem_linha"), "interlagos", variedade=2,
                  var_line=False)
    checks4 = _analyze(p4, "interlagos")["integrity"]["checks"]
    assert checks4["variedade_line"]["pass"] is False

    p5 = _fixture(_subdir(tmp_path, "cego"), "interlagos", residual=False)
    assert _analyze(p5, "interlagos")["integrity"]["ok"] is False
    assert _analyze(p5, "interlagos", arm="blind")["integrity"]["ok"] is True

    # pista errada no metadado do CSV e na linha FROZEN
    bad_track = _analyze(p, "monaco")["integrity"]["checks"]
    assert bad_track["csv_track_sha"]["pass"] is False
    assert bad_track["log_track_sha"]["pass"] is False


# ---------------------------------------------------------------------------
# aritmética e gates (D3)
# ---------------------------------------------------------------------------
def test_gate_integer_arithmetic():
    assert RM.band_110(107) == 118
    assert RM.band_110(210) == 231
    assert math.ceil(1.1 * 210) == 232          # armadilha do ponto flutuante
    assert RM.floor_95(44) == 41
    assert RM.floor_95(31) == 29
    assert RM.band_110(0) == 0 and RM.band_110(1) == 2 and RM.band_110(10) == 11


def _m(**kw):
    base = dict(sample_rows=30000, contacts_5hz_total=100, contacts_5hz_t_le_60s=80,
                laps_total=44, offtrack_rows=7905, z_reta_exits=12,
                excursions_t_le_60s=35, z_t1_exits_t_le_60s=10,
                junction_exits=40, glued_rows=100, deadlocks=0,
                excursions_total=219)
    base.update(kw)
    return base


def _gate(res, gid):
    return next(g for g in res["gates"] if g["id"] == gid)


def test_gates_for_cycles():
    ids = lambda c, t="interlagos": [g.id for g in RM.gates_for(c, t)]  # noqa: E731
    assert ids("C1") == ["B1", "S1", "R1", "R2", "C1P1", "C1P2", "R2T1"]
    assert ids("C2") == ["B1", "R1", "C23P"]
    assert ids("C3") == ["B1", "R1", "C23P"]
    assert ids("C5") == ["B1", "R1", "R2", "C5P"]
    assert ids("C6") == ["B1", "R1", "R2", "C6G", "C6D"]
    assert ids("C6", "monaco") == ["B1", "R1", "R2", "C6G", "C6D"]
    with pytest.raises(RM.InstrumentError):      # C5 só tem braço ON em Interlagos
        RM.gates_for("C5", "monaco")
    with pytest.raises(RM.InstrumentError):
        RM.gates_for("C9", "interlagos")


def test_evaluate_gates_boundaries():
    off = {0: _m(contacts_5hz_total=107)}
    on_ok = {0: _m(contacts_5hz_total=118, z_reta_exits=0, excursions_t_le_60s=34,
                   offtrack_rows=8205)}
    res = RM.evaluate_gates("C1", "interlagos", off, on_ok)
    assert _gate(res, "B1")["pass"] is True and _gate(res, "B1")["threshold"] == 118
    assert _gate(res, "R2")["pass"] is True        # 100·8205 == 100·7905 + 30000
    assert _gate(res, "C1P1")["pass"] is True
    assert _gate(res, "C1P2")["pass"] is True
    assert res["all_pass"] is True
    on_bad = {0: _m(contacts_5hz_total=119, offtrack_rows=8206, z_reta_exits=1)}
    bad = RM.evaluate_gates("C1", "interlagos", off, on_bad)
    assert _gate(bad, "B1")["pass"] is False
    assert _gate(bad, "R2")["pass"] is False
    assert _gate(bad, "C1P1")["pass"] is False
    assert _gate(bad, "C1P2")["pass"] is False      # 35 < 35 é falso
    assert bad["all_pass"] is False


def test_evaluate_gates_per_realization_and_sums():
    off = {0: _m(z_t1_exits_t_le_60s=5, laps_total=44),
           1: _m(z_t1_exits_t_le_60s=3, laps_total=44)}
    on = {0: _m(z_t1_exits_t_le_60s=0, laps_total=42, z_reta_exits=0),
          1: _m(z_t1_exits_t_le_60s=4, laps_total=42, z_reta_exits=0)}
    res = RM.evaluate_gates("C1", "interlagos", off, on)
    r2t1 = _gate(res, "R2T1")
    assert r2t1["pass"] is False and r2t1["failing_realizations"] == [1]
    r1 = _gate(res, "R1")
    assert r1["off_sum"] == 88 and r1["threshold"] == 83 and r1["pass"] is True
    with pytest.raises(RM.InstrumentError):     # mesmas realizações nos dois braços
        RM.evaluate_gates("C1", "interlagos", off, {0: on[0]})
    with pytest.raises(RM.InstrumentError):     # R-2 exige linhas iguais
        RM.evaluate_gates("C1", "interlagos", {0: _m()}, {0: _m(sample_rows=29990)})


def test_disclosure_alerts_three_x():
    off = {0: _m(contacts_5hz_total=100, glued_rows=0)}
    on = {0: _m(contacts_5hz_total=300, glued_rows=1)}
    d = RM.disclosure(off, on)
    keys = {(a["realization"], a["metric"]) for a in d["alerts"]}
    assert (0, "contacts_5hz_total") in keys and (0, "glued_rows") in keys
    on2 = {0: _m(contacts_5hz_total=299, glued_rows=0)}
    assert RM.disclosure(off, on2)["alerts"] == []
    assert d["rows"][0]["realization"] == 0


# ---------------------------------------------------------------------------
# relatório de ruído (D4/C0)
# ---------------------------------------------------------------------------
def test_noise_report_stats_pairs_and_normal():
    vals = [100, 110, 90, 105, 95]
    z = [3, 1, 2, 0, 5]
    off = {n: _m(contacts_5hz_total=v, z_t1_exits_t_le_60s=zz)
           for n, (v, zz) in enumerate(zip(vals, z))}
    rep = RM.noise_report("interlagos", off)
    st = rep["metrics"]["contacts_5hz_total"]
    assert st["mean"] == pytest.approx(100.0)
    assert st["sd"] == pytest.approx(math.sqrt(62.5))
    b1 = rep["gates"]["B1"]
    assert b1["threshold"] == 550
    expected = 1.0 - 0.5 * (1.0 + math.erf(((550.5 - 500.0) / (math.sqrt(5) * math.sqrt(62.5)))
                                            / math.sqrt(2.0)))
    assert b1["p_fail_normal"] == pytest.approx(expected)
    r2t1 = rep["gates"]["R2T1"]
    assert r2t1["n_pairs"] == 20 and r2t1["pair_fail_frac"] == pytest.approx(0.5)
    flat = {n: _m(contacts_5hz_total=7) for n in range(5)}
    assert RM.noise_report("interlagos", flat)["gates"]["B1"]["p_fail_normal"] == 0.0
    assert rep["gates"]["C1P2"]["kind"] == "primary"
    assert "p_pass_normal" in rep["gates"]["C1P2"]


# ---------------------------------------------------------------------------
# determinismo, criação exclusiva e CLI
# ---------------------------------------------------------------------------
def test_two_reads_same_hash_and_exclusive_cli(tmp_path, capsys):
    p = _fixture(tmp_path, "interlagos")
    a = _analyze(p, "interlagos")
    b = _analyze(p, "interlagos")
    assert a["metrics_sha256"] == b["metrics_sha256"] and RM.verify_metrics_sha(a)
    out = tmp_path / "syn.json"
    argv = ["--run-id", "SYN", "--log", str(p.log), "--main-csv", str(p.main),
            "--events-csv", str(p.events), "--track", "interlagos", "--out", str(out)]
    rc = RM.main(argv)
    assert rc == 3          # 30.002 linhas não se aplicam ao sintético
    written = json.loads(out.read_text(encoding="utf-8"))
    checks = written["integrity"]["checks"]
    assert checks["main_physical_lines"]["pass"] is False
    assert all(v["pass"] for k, v in checks.items() if k != "main_physical_lines")
    assert RM.verify_metrics_sha(written)
    with pytest.raises(FileExistsError):
        RM.main(argv)
    capsys.readouterr()
    assert RM.main(argv[:-2]) == 3
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["metrics_sha256"] == written["metrics_sha256"]


def test_cli_noise_and_gates_from_run_jsons(tmp_path, capsys):
    runs = {}
    for n in (0, 1):
        d = tmp_path / f"n{n}"
        d.mkdir()
        p = _fixture(d, "interlagos", variedade=n)
        payload = _analyze(p, "interlagos", expect_variedade=n)
        path = d / "run.json"
        RM.write_exclusive(path, payload)
        runs[n] = path
    assert RM.main(["noise", "--track", "interlagos",
                    "--off", f"0={runs[0]}", f"1={runs[1]}"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["realizations"] == [0, 1] and RM.verify_metrics_sha(rep)
    # ON == OFF: guardas passam; o primário (melhora estrita) reprova -> exit 1
    assert RM.main(["gates", "--cycle", "C2", "--track", "interlagos",
                    "--off", f"0={runs[0]}", f"1={runs[1]}",
                    "--on", f"0={runs[0]}", f"1={runs[1]}"]) == 1
    res = json.loads(capsys.readouterr().out)
    assert [g["id"] for g in res["gates"]] == ["B1", "R1", "C23P"]
    assert [g["pass"] for g in res["gates"]] == [True, True, False]
    assert res["all_pass"] is False and RM.verify_metrics_sha(res)
    with pytest.raises(RM.InstrumentError):       # N declarado != variedade do log
        RM.main(["noise", "--track", "interlagos", "--off", f"1={runs[0]}"])


# ---------------------------------------------------------------------------
# golden N=0 (promocao-1) — exatos do plano: divergência = PARE
# ---------------------------------------------------------------------------
GOLDEN = [
    ("1_R1_INTERLAGOS_RACE", "interlagos",
     dict(contacts_5hz_total=107, contacts_5hz_t_le_60s=95, laps_total=44,
          offtrack_pct=26.4, hesitations=3, offtrack_rows=7905,
          fora_preso_rows=6281, fora_pilotagem_rows=1624)),
    ("3_R3_MONACO_RACE", "monaco",
     dict(contacts_5hz_total=210, contacts_5hz_t_le_60s=96, laps_total=31,
          offtrack_pct=49.9, hesitations=5, offtrack_rows=14963,
          fora_preso_rows=11294, fora_pilotagem_rows=3669)),
]


@pytest.mark.slow
@pytest.mark.skipif(not (PROMO / "1_R1_INTERLAGOS_RACE.csv").exists(),
                    reason="artefatos da promocao-1 ausentes")
@pytest.mark.parametrize("stem,track,exact", GOLDEN)
def test_golden_promocao_1_n0(stem, track, exact):
    out = RM.analyze_run(run_id=stem, log=PROMO / f"{stem}.log",
                         main_csv=PROMO / f"{stem}.csv",
                         events_csv=PROMO / f"{stem}_events.csv", track=track)
    assert out["integrity"]["ok"] is True and out["integrity"]["variedade"] == 0
    m = out["metrics"]
    for key, value in exact.items():
        assert m[key] == value, key
    assert out["cross_checks"]["fora_preso_vs_log"]["match"] is True
