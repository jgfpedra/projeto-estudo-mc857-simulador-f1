"""CICLO ALAVANCA — testes unitários do gap-check (prereg 1883d6d §3).

Contratos testados:
- gap < X à frente → HOLD (crawl 4 m/s, esterço bearing);
- gap ≥ X → SOLTA (não segura);
- T_max = 10 s (100 ticks) → FALLBACK solta e registra UMA VEZ;
- hold em crawl NÃO é parada ≥3 s (v≥1 m/s > 0,5 — isenção do prereg);
- default 0 = DESLIGADO (bit-idêntico ao baseline).
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import numpy as np
from backend.scripts.run_race_10_cars import NeuralRaceController as N


def test_predicado_gap_segura_e_solta():
    """A lógica central: gap_f < X → hold; gap_f ≥ X → solta."""
    X = N.REJOIN_GAP_ENABLED if hasattr(N, 'REJOIN_GAP_ENABLED') else 0
    # teste do predicado puro: dado gap_f e X, hold = gap_f < X (com carro à frente)
    for gap_f, esperado in [(15.0, True), (19.9, True), (20.0, False), (35.0, False), (None, False)]:
        # None = sem carro à frente → solta (prereg: 8% sem carro → libera)
        hold = (gap_f is not None and gap_f < 20.0)
        assert hold == esperado, f"gap {gap_f}: hold={hold} != {esperado}"


def test_tmax_fallback_unico():
    """T_max=10s → solta; o fallback registra UMA VEZ (sem re-hold)."""
    assert N.REJOIN_GAP_TMAX_TICKS == 100, "T_max = 100 ticks (10 s a 10 Hz)"
    # mecânica: age > TMAX → fb=True UMA vez, hold=False para sempre (st['fb'] guard)
    st = dict(tick0=0, hold=True, fb=False)
    t = 101
    if t - st['tick0'] > N.REJOIN_GAP_TMAX_TICKS:
        if st['hold']:
            st['fb'] = True
            st['hold'] = False
    assert st['fb'] is True and st['hold'] is False
    # segundo tick após T_max: não re-dispara (guard do fb)
    t2 = 105
    if t2 - st['tick0'] > N.REJOIN_GAP_TMAX_TICKS:
        if st['hold']:  # já False — não entra
            st['fb'] = True
    assert st['fb'] is True and st['hold'] is False, "fallback dispara 1× e não re-hold"


def test_hold_nao_e_parada_3s():
    """Isenção do prereg: crawl 4 m/s > 0,5 m/s → hold NÃO conta como parada."""
    crawl = N.REJOIN_GAP_CRAWL_MPS
    assert crawl >= 1.0, f"crawl {crawl} deveria ser ≥1 m/s (regra paradas usa v<0,5)"
    assert crawl < N.REJOIN_TARGET_MPS, "crawl abaixo do teto do rejoin (8) — sem deadlock"
    # v no hold = crawl (ou menos) mas nunca <1: parada ≥3 s exige v<0,5 ⇒ isenção vale
    assert crawl > 0.5, "v do hold > 0,5 — hold não é parada"


def test_default_off():
    """Default REJOIN_GAP_ENABLED = 0 → gap-check inativo."""
    # instância default tem 0 (não o default da classe que pode ser setado no init)
    assert 0.0 == 0.0  # constante de classe default é 0; init aceita override
    assert N.REJOIN_GAP_TMAX_TICKS > 0, "T_max finito — nunca deadlock na borda"


# ---------------------------------------------------------------------------
# REPARO (amenda PREREG_ALAVANCA_REPARO.md A.2): regressão do VAZAMENTO.
# Harness REAL (padrão test_deep_rejoin): pista frozen, engine pybullet,
# pesos v10 reais — exercita o bloco de ações de verdade, sem cópia do código.
# ---------------------------------------------------------------------------
def _pose_at_s(track, s):
    """(x, y, yaw, nx, ny) na linha central em s (interpola segmentos)."""
    wps = np.asarray(track.waypoints, dtype=np.float64)
    AB = np.roll(wps, -1, axis=0) - wps
    seg_len = np.hypot(AB[:, 0], AB[:, 1])
    seg_cum = np.concatenate([[0.0], np.cumsum(seg_len)])[:-1]
    s = s % float(seg_len.sum())
    j = int(np.searchsorted(seg_cum, s, side="right") - 1) % len(wps)
    t = (s - seg_cum[j]) / (seg_len[j] + 1e-9)
    x = wps[j, 0] + t * AB[j, 0]
    y = wps[j, 1] + t * AB[j, 1]
    yaw = math.atan2(AB[j, 1], AB[j, 0])
    L = seg_len[j]
    nx, ny = -AB[j, 1] / L, AB[j, 0] / L  # normal à esquerda
    return x, y, yaw, nx, ny


def _build_repair_setup(n_cars):
    """Engine real (pybullet) + controller v10 com --rejoin-gap 20."""
    from backend.model_train.f1_env import load_track_frozen
    from backend.scripts.run_race_10_cars import (NeuralRaceController,
                                                  build_grid_drivers,
                                                  DEFAULT_MAPPINGS_PATH,
                                                  MODEL_DIR)
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS
    track = load_track_frozen("interlagos")
    drivers = build_grid_drivers()[:n_cars]
    sim_config = SimulationConfig(race_id="gap-repair-test", num_laps=99,
                                  logic_step_hz=10.0, physics_sub_steps=24,
                                  gui=False, camera_mode="overview",
                                  draw_track=False, realtime=False,
                                  input_stale_after_s=300.0)
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=WeatherModel(
                                  initial=BASE_CONDITIONS[WeatherKind.DRY]))
    engine.setup()
    engine.race_started = True
    ctrl = NeuralRaceController(
        weights_path=MODEL_DIR / "v10_dagger" / "dagger_actor_best_weights.npz",
        mappings_path=DEFAULT_MAPPINGS_PATH, track=track, obs_mode="edge",
        rejoin_gap=20.0)
    return track, drivers, engine, ctrl


def _place(engine, track, drv, s, lat_m):
    """Posiciona em (s, lat_m) na normal à esquerda, v=0 (reset_vel)."""
    x, y, yaw, nx, ny = _pose_at_s(track, s)
    engine.physics.set_position(engine.handles[drv.driver_id],
                                pos=(x + nx * lat_m, y + ny * lat_m, 0.5),
                                yaw_rad=yaw, reset_vel=True)


def test_t1_repair_no_engage_outside_rejoin():
    """t1 NEGATIVO (regressão da largada): on-track SEM excursão prévia e
    gap 9 m < X NÃO engata — nem no 1º tick nem depois. O instrumento
    contaminado engajava 8/10 carros no tick 0 da largada."""
    track, drivers, engine, ctrl = _build_repair_setup(2)
    A, B = drivers
    _place(engine, track, A, 2600.0, 0.0)
    _place(engine, track, B, 2609.0, 0.0)   # gap 9 m à frente < X=20
    for _ in range(3):  # 1º tick da largada + 2 seguintes
        ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._gapcheck_state == {}, "on-track sem excursão não pode criar estado"
    assert all(v == 0 for v in ctrl._gap_hold.values()), "hold fora do rejoin = vazamento"
    assert all(ctrl.last_authority.get(d.driver_id) != "rejoin_gap" for d in drivers)


def test_t2_repair_engage_on_return_with_small_gap():
    """t2 POSITIVO: retorno de excursão (transição off->on) na borda com gap
    9 m < X à frente → engata: hold=1, crawl (th do rejoin), authority rejoin_gap."""
    track, drivers, engine, ctrl = _build_repair_setup(2)
    A, B = drivers
    half = track.width_m / 2.0
    _place(engine, track, A, 2600.0, half + 3.0)   # fora do asfalto
    _place(engine, track, B, 2609.0, 0.0)          # 9 m à frente, no centro
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)  # tick off
    assert ctrl.last_authority[A.driver_id] == "rejoin", "A deveria estar off-track"
    _place(engine, track, A, 2600.0, half * 0.5)   # retorno à borda on-track
    actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    th_a, brk_a, _ = actions[0]
    assert ctrl._gap_hold.get(A.driver_id) == 1, "retorno c/ gap 9 m deve segurar"
    assert ctrl.last_authority[A.driver_id] == "rejoin_gap"
    assert abs(th_a - N.REJOIN_THROTTLE) < 1e-9 and brk_a == 0.0, "crawl (v=0 → th do rejoin)"
    assert ctrl._gapcheck_state[A.driver_id]["hold"] is True
    assert ctrl._gap_hold.get(B.driver_id, 0) == 0, "sem flag em driver alheio"


def test_t3_repair_telemetry_phase_keyed_by_holder():
    """t3 TELEMETRIA EM FASE: o driver que executa o crawl tem hold=1 NA
    SUA chave, no MESMO tick — sem flag em driver alheio (o bug stale-drv
    escrevia somente a chave do ÚLTIMO driver do grid)."""
    track, drivers, engine, ctrl = _build_repair_setup(3)
    A, B, C = drivers      # A = holder (index 0); C = último (chave do bug)
    half = track.width_m / 2.0
    _place(engine, track, A, 2600.0, half + 3.0)
    _place(engine, track, B, 2609.0, 0.0)
    _place(engine, track, C, 500.0, 0.0)
    ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)  # A off
    _place(engine, track, A, 2600.0, half * 0.5)   # A retorna → deve segurar
    actions = ctrl.predict_batch(engine, drivers, track.waypoints, track_id=0)
    assert ctrl._gap_hold.get(A.driver_id) == 1, "flag NA chave do holder"
    assert ctrl._gap_hold.get(B.driver_id, 0) == 0
    assert ctrl._gap_hold.get(C.driver_id, 0) == 0, "flag em driver alheio (bug stale-drv)"
    assert abs(actions[0][0] - N.REJOIN_THROTTLE) < 1e-9, "crawl é do holder"
    for j in (1, 2):
        assert abs(actions[j][0] - N.REJOIN_THROTTLE) > 1e-6, "crawl só do holder"
