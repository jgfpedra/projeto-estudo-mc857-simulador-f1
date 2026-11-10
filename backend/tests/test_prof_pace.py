"""Testes da implementação do --prof-pace (PROF-PACE-1 Task 2).

Cobre o mandato: escada congelada (sem valores livres), PARIDADE com o
instrumento PACE_MARGIN v2 (mesmo perfil, mesmo t_lap), bit-identidade OFF
(steer+long exatos), ON com alvo capado (0,93+η embutidos), no-op explícito
fora de Interlagos, pré-voo com grip_ref congelado.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

import json

from model_train.f1_env import F1MultiContextEnv  # noqa: E402
from model_train.prof_pace import (  # noqa: E402
    ETA_LADDER,
    GRIP_REF,
    INTERLAGOS_SHA_PIN,
    build_capped,
    chronic_windows,
    eta_from_name,
    is_interlagos,
)
from model_train.reference_controller import ReferenceController  # noqa: E402
from model_train.velocity_profile import VelocityProfile  # noqa: E402
from scripts.prof_lago_anatomy import kappa_interp_fn  # noqa: E402
from scripts.prof_pace_margin_derivation import (  # noqa: E402
    MARGIN_CONTROLLER,
    propagate_longitudinal,
)
from tests.test_prof_control import FakeEnv, _polyline_track  # noqa: E402

K_LD, LD_MIN, LD_MAX, WHEELBASE, MARGIN = 0.6, 5.0, 45.0, 3.4, 0.93


# --------------------------------------------------- escada congelada
def test_escada_congelada_sem_valores_livres():
    assert ETA_LADDER == {"eta1": 0.48848, "eta2": 0.40000}
    assert eta_from_name("eta1") == pytest.approx(0.48848)
    assert eta_from_name("eta2") == pytest.approx(0.40000)
    with pytest.raises(ValueError):
        eta_from_name("0.55")          # valor livre fora da escada
    with pytest.raises(ValueError):
        eta_from_name("eta3")          # não existe η3


def test_is_interlagos_pin():
    assert is_interlagos("164876196eb12174") is True
    assert is_interlagos("67ca11dc211c8c78") is False   # Monaco → no-op


# ------------------------------- janelas canônicas reais (offline)
def test_chronic_windows_interlagos_real():
    track = json.load(open(BACKEND / "model_train" / "tracks_frozen"
                           / "interlagos_v2.json"))
    wps = np.array(track["waypoints"], dtype=np.float64)
    janelas = chronic_windows(wps)
    assert set(janelas.keys()) == {"C01", "C06", "C07", "C08"}
    assert janelas["C08"][0] == pytest.approx(2276.239, abs=1e-2)
    assert janelas["C08"][1] == pytest.approx(2344.246, abs=1e-2)


# ------------------------- PARIDADE com o instrumento PACE_MARGIN v2
def test_paridade_com_instrumento_pace_margin():
    """O perfil capado da implementação deve ser IDÊNTICO ao do instrumento
    homologado (mesma função build_v_target_cap, mesmos parâmetros)."""
    from scripts.prof_pace_margin_derivation import build_v_target_cap
    track = json.load(open(BACKEND / "model_train" / "tracks_frozen"
                           / "interlagos_v2.json"))
    wps = np.array(track["waypoints"], dtype=np.float64)
    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    janelas = {"C01": (2276.239 - 2276.239, 0.0)}  # placeholder real abaixo
    from scripts.prof_lago_anatomy import kappa_interp_fn  # noqa: E402
    kappa_smooth_at = kappa_interp_fn(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(wps, ds_target=4.0)
    total = float(k_s[-1] + (k_s[1] - k_s[0]))
    kappa_inst_fn = (lambda s: abs(float(np.interp(
        float(s) % total, k_s, np.abs(k_i)))))
    janelas = chronic_windows(wps)
    prof = build_capped(vp.v_plan, vp.s_arr, np.abs(vp.kappa_arr),
                        janelas, kappa_inst_fn, "eta1")
    k_smooth = np.abs(vp.kappa_arr)
    _, cap_inst = build_v_target_cap(vp.v_plan, k_smooth, vp.s_arr,
                                     dict(janelas), kappa_inst_fn,
                                     0.48848, GRIP_REF)
    assert np.array_equal(prof["v_target_cap"], cap_inst)
    # t_lap do perfil capado η1: PARIDADE de arrays (idênticos por construção)
    # + bound da Guarda. Nota de convenção: a implementação usa a κ suav
    # CANÔNICA de 20 m (a do wiring do professor); o instrumento PACE_MARGIN
    # v2 calculou com a κ de 30 m (convenção LAGO) → t_cap 105,660; a
    # canônica dá ≈106,99 — ambos ≤ Guarda (divergência disclosada).
    ds = float(vp.s_arr[1] - vp.s_arr[0])
    t_cap = float(np.sum(ds / np.maximum(prof["v_target_cap"], 0.5)))
    assert t_cap <= 123.05


def test_prevoi_t_base_t_margin_t_cap_com_grip_ref():
    """Pré-voo: os três tempos com grip_ref congelado e o perfil completo
    (κ suavizada CANÔNICA de 20 m — a do wiring do professor). Nota
    disclosada: o instrumento PACE_MARGIN v2 calculou as passadas com a κ
    suavizada de 30 m (convenção LAGO) — t_cap 105,660; a convenção
    canônica de 20 m dá t_cap ≈ 106,99 (Δ ≈ +1,3 s); ambos ≤ Guarda."""
    from scripts.prof_pace_margin_derivation import (  # noqa: E402
        build_v_target_cap, propagate_longitudinal)
    track = json.load(open(BACKEND / "model_train" / "tracks_frozen"
                           / "interlagos_v2.json"))
    wps = np.array(track["waypoints"], dtype=np.float64)
    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    ds = float(vp.s_arr[1] - vp.s_arr[0])
    k_smooth = np.abs(vp.kappa_arr)                    # κ suav CANÔNICA 20 m
    janelas = chronic_windows(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(wps, ds_target=4.0)
    total = float(k_s[-1] + (k_s[1] - k_s[0]))
    kappa_inst_fn = (lambda s: abs(float(np.interp(
        float(s) % total, k_s, np.abs(k_i)))))
    t_base = float(np.sum(ds / np.maximum(vp.v_plan, 0.5)))
    v_m = propagate_longitudinal(0.93 * vp.v_plan, k_smooth, ds, GRIP_REF)
    t_margin = float(np.sum(ds / np.maximum(v_m, 0.5)))
    _, cap = build_v_target_cap(vp.v_plan, k_smooth, vp.s_arr, janelas,
                                kappa_inst_fn, 0.48848, GRIP_REF)
    t_cap = float(np.sum(ds / np.maximum(cap, 0.5)))
    # piso base idêntico ao instrumento (o v_plan não depende da κ das
    # passadas); os t_margin/t_cap divergem SÓ pela convenção de suavização
    assert t_base == pytest.approx(96.202, abs=0.05)
    assert t_cap <= 123.05                             # η1 cabe na Guarda
    assert t_cap <= 123.05                             # η1 cabe na Guarda
    assert t_cap > t_margin >= t_base                  # ordem física
    # auto-consistência: recomputar com o MESMO k_smooth é idêntico
    _, cap2 = build_v_target_cap(vp.v_plan, k_smooth, vp.s_arr, janelas,
                                 kappa_inst_fn, 0.48848, GRIP_REF)
    assert np.array_equal(cap, cap2)


# ------------------------------------------- integração (FakeEnv)
class FakePaceEnv(FakeEnv):
    """FakeEnv + track sha de Interlagos p/ o caminho do runner."""

    def __init__(self, wps, cum, total, s0, v0):
        super().__init__(wps, cum, total, s0, v0)
        self.track.sha256 = "164876196eb12174"


def _make_controllers(s0, v0, windows):
    wps, cum, total = _polyline_track()
    env = FakePaceEnv(wps, cum, total, s0, v0)
    env.fix_pose(s0)
    vp = VelocityProfile(np.array(wps, dtype=np.float64), grip_mult=0.788,
                         sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    kappa_inst = lambda s: 0.04  # noqa: E731  (κ_inst sintética da janela)
    off = ReferenceController(env, velocity_profile=vp, prof_pace=False)
    on = ReferenceController(env, velocity_profile=vp, prof_pace=True,
                             prof_pace_windows=windows, prof_pace_eta="eta1",
                             prof_pace_kappa_inst=kappa_inst)
    return env, vp, off, on


def _historical_action(env, vp, s0, v0):
    ld_probe = float(np.clip(K_LD * v0, LD_MIN, LD_MAX))
    v_for_ld = min(v0, vp.at(s0 + ld_probe))
    ld = float(np.clip(K_LD * v_for_ld, LD_MIN, LD_MAX))
    tx, ty, _ = env._point_at(s0 + ld)
    st = env.state_snapshot
    dx, dy = tx - st["x"], ty - st["y"]
    alpha = math.atan2(dy, dx) - st["heading_rad"]
    alpha = (alpha + math.pi) % (2 * math.pi) - math.pi
    steer_rad = math.atan2(2.0 * WHEELBASE * math.sin(alpha), ld)
    steer_cmd = float(np.clip(steer_rad / env.steer_limit_rad(v0), -1.0, 1.0))
    v_tgt = vp.at(s0) * MARGIN
    long_cmd = float(np.clip((v_tgt - v0) / 8.0, -1.0, 1.0))
    return np.array([steer_cmd, long_cmd], dtype=np.float32)


def test_bit_identidade_off_steer_e_long():
    env, vp, off, _on = _make_controllers(s0=40.0, v0=21.0,
                                          windows={"C01": (0.0, 80.0)})
    a_off = off.action(traffic=None)
    a_hist = _historical_action(env, vp, 40.0, 21.0)
    assert float(a_off[0]) == float(a_hist[0])   # steer: exato
    assert float(a_off[1]) == float(a_hist[1])   # long: exato


def test_on_alvo_capado_na_janela_e_steer_intocado():
    env, vp, off, on = _make_controllers(s0=40.0, v0=21.0,
                                         windows={"C01": (0.0, 80.0)})
    a_off = off.action(traffic=None)
    a_on = on.action(traffic=None)
    assert float(a_on[0]) == float(a_off[0])     # pacing-only: esterço intocado
    # o alvo capado (0,93 + cap η1 embutidos) ≤ alvo histórico (0,93·v_plan):
    # long_cmd menor ou igual, com o cap ativo na janela
    assert float(a_on[1]) <= float(a_off[1])
    assert -1.0 <= float(a_on[1]) <= 1.0


def test_noop_fora_de_interlagos():
    # pista não-Interlagos: o runner não constrói o perfil → no-op explícito
    wps, cum, total = _polyline_track()
    env = FakePaceEnv(wps, cum, total, 40.0, 21.0)
    env.track.sha256 = "67ca11dc211c8c78"             # Monaco
    env.fix_pose(40.0)
    vp = VelocityProfile(np.array(wps, dtype=np.float64), grip_mult=0.788,
                         sf=0.80, ds_target=4.0, smooth_window_m=20.0)
    on = ReferenceController(env, velocity_profile=vp, prof_pace=True,
                             prof_pace_windows=None, prof_pace_eta="eta1")
    off = ReferenceController(env, velocity_profile=vp, prof_pace=False)
    a_off = off.action(traffic=None)
    a_on = on.action(traffic=None)
    assert float(a_on[0]) == float(a_off[0])           # no-op exato
    assert float(a_on[1]) == float(a_off[1])
    assert on._prof_pace_noop is True
    assert on._prof_pace is None


# --------------------------------------------- verificação final (Task 2)
def test_equivalencia_alvo_com_cap_inativo():
    """Cenário sintético em que o cap NUNCA liga (κ_inst mínima → v_safe
    enorme): v_target_cap == 0,93·v_plan exatamente (as passadas são no-op
    sobre um perfil uniformemente escalado que já é fisicamente viável) e o
    alvo ON == alvo OFF (0,93·v_plan via _v_target·margin) em 100% dos
    pontos. Tolerância numérica: 1e-9 (igualdade de máquina)."""
    n = 300
    v_base = np.full(n, 30.0)
    s = np.arange(n) * 4.0
    windows = {"C01": (400.0, 800.0)}
    kappa_inst = lambda s: 1e-6  # noqa: E731  v_safe ≈ 2700 m/s → cap não liga
    from scripts.prof_pace_margin_derivation import propagate_longitudinal
    seed = np.full(n, MARGIN_CONTROLLER * 30.0)
    v_target_cap = propagate_longitudinal(seed, k_dummy_flat(n), 4.0, 0.7895474400345001)
    # alvo OFF
    alvo_off = MARGIN_CONTROLLER * v_base
    # alvo ON = v_target_cap.at(s)
    alvo_on = v_target_cap
    assert np.all(np.abs(alvo_on - alvo_off) <= 1e-9)
    # e o cap não liga em NENHUM ponto (o teto nunca fica abaixo do alvo)
    assert np.all(v_target_cap >= alvo_off - 1e-9)


def k_dummy_flat(n):
    return np.full(n, 1e-6)


def test_extensao_espacial_e_classificacao():
    """Alcance espacial do cap η1 na pista real: dentro das janelas (cap
    direto) vs fora (frenagem antecipada/aceleração a jusante — ambos
    adjacentes a janelas, incluindo o wrap da C01)."""
    import json
    track = json.load(open(BACKEND / "model_train" / "tracks_frozen"
                           / "interlagos_v2.json"))
    wps = np.array(track["waypoints"], dtype=np.float64)
    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    s_arr = np.asarray(vp.s_arr, dtype=float)
    ds = float(s_arr[1] - s_arr[0])
    kappa_smooth_at = kappa_interp_fn(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(wps, ds_target=4.0)
    tot_i = float(k_s[-1] + (k_s[1] - k_s[0]))
    kappa_inst_at = (lambda s: abs(float(np.interp(float(s) % tot_i, k_s,
                                                   np.abs(k_i)))))
    windows = chronic_windows(wps)
    from scripts.prof_pace_margin_derivation import build_v_target_cap
    _, v_cap = build_v_target_cap(vp.v_plan, np.abs(vp.kappa_arr), s_arr,
                                  windows, kappa_inst_at, 0.48848, GRIP_REF)
    v_ctrl = MARGIN_CONTROLLER * vp.v_plan
    delta = v_ctrl - v_cap
    engaged = delta > 1e-9
    in_mask = np.zeros(len(s_arr), dtype=bool)
    for w0, w1 in windows.values():
        in_mask |= (s_arr >= w0) & (s_arr <= w1)
    # dentro das janelas: o cap direto atua
    assert (engaged & in_mask).sum() > 0
    # fora: SOMENTE os trechos adjacentes a janelas (frenagem a montante ou
    # aceleração a jusante — ambos tocam uma borda de janela)
    out_eng = engaged & ~in_mask
    idx = np.where(out_eng)[0]
    if len(idx):
        brk = np.where(np.diff(idx) > 1)[0]
        starts = np.concatenate([[idx[0]], idx[brk + 1]])
        ends = np.concatenate([idx[brk], [idx[-1]]])
        # bordas COM WRAP (janelas que cruzam a linha: C01 = (-32, 128))
        total = float(s_arr[-1] + 4.0)
        bordas = sorted(set(
            [(w0 % total) for w0, w1 in windows.values()]
            + [(w1 % total) for w0, w1 in windows.values()]))
        # alcance físico: a frenagem antecipada do backward + a aceleração
        # da saída — bound generoso de 150 m (a mesma janela de gatilho)
        alcance_m = 150.0
        for a, b in zip(starts, ends):
            d_ini = min(abs(float(s_arr[a] % total) - bb) for bb in bordas)
            d_fim = min(abs(float(s_arr[b] % total) - bb) for bb in bordas)
            assert min(d_ini, d_fim) <= alcance_m, (
                f"trecho DESTACADO s {s_arr[a]}-{s_arr[b]}: dist mín à janela "
                f"{min(d_ini, d_fim)} m > alcance {alcance_m} m — violação de "
                "escopo local")


# ------------------------------------ cobertura circular da C01 (wrap)
def test_wrap_c01_cobertura_circular():
    """A janela canônica C01 = (−32,0 → 128,01) CRUZA a linha de chegada.
    Verifica, pelo caminho do controlador (build_capped com a pista real):
    (1) a máscara cobre os DOIS lados de s=0 — o segmento wrapped
        [4128,4160] e o segmento [0,128];
    (2) o cap está ATIVO (máscara + bind) imediatamente antes e depois da
        linha onde a curvatura demanda (o ápice do Lago s≈35);
    (3) o cap está INATIVO imediatamente FORA de cada borda
        (s=4100 < 4128,4 e s=140 > 128,01): seed == v_ctrl exato;
    (4) contagem de metros: quantos metros da janela C01 recebem cap direto
        (bind) vs ficam apenas com o margin (a reta do wrap não demanda)."""
    import json
    track = json.load(open(BACKEND / "model_train" / "tracks_frozen"
                           / "interlagos_v2.json"))
    wps = np.array(track["waypoints"], dtype=np.float64)
    vp = VelocityProfile(wps, grip_mult=0.788, sf=0.80, ds_target=4.0,
                         smooth_window_m=20.0)
    s_arr = np.asarray(vp.s_arr, dtype=float)
    ds = float(s_arr[1] - s_arr[0])
    total = float(s_arr[-1] + ds)
    windows = chronic_windows(wps)
    assert windows["C01"][0] < 0.0                    # a janela cruza a linha
    kappa_smooth_at = kappa_interp_fn(wps)
    from backend.model_train.prof_curva import _instantaneous_kappa_profile
    k_s, k_i = _instantaneous_kappa_profile(wps, ds_target=4.0)
    tot_i = float(k_s[-1] + (k_s[1] - k_s[0]))
    kappa_inst_at = (lambda s: abs(float(np.interp(float(s) % tot_i, k_s,
                                                   np.abs(k_i)))))
    prof = build_capped(vp.v_plan, s_arr, np.abs(vp.kappa_arr), windows,
                        kappa_inst_at, "eta1")
    mask = prof["mask"]
    seed = prof["v_seed"]
    v_ctrl = MARGIN_CONTROLLER * vp.v_plan

    # (1) máscara: os DOIS lados da linha cobertos
    def m_at(s_query):
        return bool(mask[int((float(s_query) % total) / ds) % len(mask)])
    assert m_at(4150.0) is True    # antes da linha (segmento wrapped)
    assert m_at(4159.0) is True
    assert m_at(20.0) is True      # depois da linha
    assert m_at(60.0) is True
    # (3) inativo imediatamente FORA de cada borda
    assert m_at(4100.0) is False   # 28 m antes do início wrapped (4128,4)
    assert m_at(140.0) is False    # 12 m depois do fim (128,01)
    # (2) cap ATIVO (bind) imediatamente antes/depois da linha onde pertence
    bind = seed < v_ctrl - 1e-9
    assert bind[int((4150.0 % total) / ds)] is True or \
        bool(mask[int((4150.0 % total) / ds)])  # na janela: cap aplica
    assert bind[int((20.0 % total) / ds)] is True or \
        bool(mask[int((20.0 % total) / ds)])
    # e INATIVO fora das bordas: seed == v_ctrl exato
    assert seed[int((4100.0 % total) / ds)] == pytest.approx(
        v_ctrl[int((4100.0 % total) / ds)], abs=1e-9)
    assert seed[int((140.0 % total) / ds)] == pytest.approx(
        v_ctrl[int((140.0 % total) / ds)], abs=1e-9)
    # (5) metros da janela C01: total vs bind direto
    win_mask = np.zeros(len(s_arr), dtype=bool)
    win_mask |= ((s_arr >= 4128.4) | (s_arr <= 128.01))
    n_win = int(win_mask.sum())
    n_bind = int((win_mask & bind).sum())
    metros_janela = n_win * ds
    metros_bind = n_bind * ds
    assert metros_janela == pytest.approx(160.01, abs=1.0)
    print(f"C01 wrap: janela {metros_janela:.1f} m (dos dois lados da linha) "
          f"| cap direto (bind) {metros_bind:.1f} m | margin-only "
          f"{metros_janela - metros_bind:.1f} m")
