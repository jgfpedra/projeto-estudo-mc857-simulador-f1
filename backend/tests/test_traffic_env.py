"""Testes da FASE 2 v14: obs_mode='traffic' (46d) + fantasmas no env.

Cobre os requisitos do task v14:
  - obs 'traffic' = edge 34d + 12d (3 carros mais próximos por |dist_s|):
    [|dist_s|/100, Δv/OBS_SPEED, lat/half_width, ahead(1|0)]; zeros se
    menos de 3 visíveis; validação de shape com erro explícito;
  - fantasmas (n_traffic 0-9) dirigidos pelo professor de TRÁFEGO, grip
    nominal, espaçados no grid no reset;
  - fantasmas NÃO geram eventos de volta e NÃO contam no lap% do aluno
    (engine._no_lap_drivers);
  - obs do aluno NUNCA contém o próprio carro;
  - layout estável entre resets; env fecha limpo.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend')):
    if p not in sys.path:
        sys.path.insert(0, p)


# ---------------------------------------------------------------- fixtures

@pytest.fixture(scope='module')
def env_no_ghosts():
    from backend.model_train.f1_env import F1MultiContextEnv
    env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                            n_traffic=0, allow_respawn=False)
    yield env
    env.close()


@pytest.fixture(scope='module')
def env_one_ghost():
    from backend.model_train.f1_env import F1MultiContextEnv
    env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                            n_traffic=1, allow_respawn=False)
    yield env
    env.close()


@pytest.fixture(scope='module')
def env_nine_ghosts():
    from backend.model_train.f1_env import F1MultiContextEnv
    env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                            n_traffic=9, allow_respawn=False)
    yield env
    env.close()


def _traffic_block(obs):
    """Últimas 12 entradas da telemetria (bloco de tráfego)."""
    return obs['telemetry'][-12:]


# ------------------------------------------------------- shape e validação

class TestTrafficObsShape:
    def test_dim_46_and_space(self, env_no_ghosts):
        obs, _ = env_no_ghosts.reset(seed=0)
        assert obs['telemetry'].shape == (46,)
        assert env_no_ghosts.observation_space['telemetry'].shape == (46,)
        # ator v14: 46 tel + 2 ctx + 8 emb_track + 4 emb_compound = 60
        assert 46 + 2 + 8 + 4 == 60

    def test_edge_rays_present_in_traffic_mode(self, env_no_ghosts):
        """'traffic' INCLUI os 11 raios LiDAR do edge (34d base)."""
        obs, _ = env_no_ghosts.reset(seed=1)
        assert env_no_ghosts._edge_L is not None
        assert env_no_ghosts._cast_rays(0.0, 0.0, 0.0).shape == (11,)

    def test_invalid_n_traffic_rejected(self):
        from backend.model_train.f1_env import F1MultiContextEnv
        for bad in (-1, 10, 42):
            with pytest.raises(ValueError, match="n_traffic"):
                F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                  n_traffic=bad, allow_respawn=False)

    def test_invalid_obs_mode_still_rejected(self):
        from backend.model_train.f1_env import F1MultiContextEnv
        with pytest.raises(ValueError, match="obs_mode"):
            F1MultiContextEnv(track='interlagos', obs_mode='trafficx',
                              allow_respawn=False)


# ---------------------------------------------------------- conteúdo 12d

class TestTrafficFeatures:
    def test_zero_block_without_ghosts(self, env_no_ghosts):
        obs, _ = env_no_ghosts.reset(seed=0)
        np.testing.assert_array_equal(_traffic_block(obs), np.zeros(12))

    def test_one_ghost_fills_first_slot_only(self, env_one_ghost):
        obs, _ = env_one_ghost.reset(seed=0)
        blk = _traffic_block(obs)
        # slot 0: fantasma P1 a 9 m à frente, coluna esquerda (+1.9 m)
        assert blk[0] == pytest.approx(0.09, abs=1e-3)   # |dist_s|/100
        assert blk[1] == pytest.approx(0.0, abs=1e-3)    # (v_outro - v_ego)/100
        assert blk[2] == pytest.approx(1.9 / 6.0, abs=1e-3)  # lat/half_width
        assert blk[3] == pytest.approx(1.0)               # ahead
        # slots 1 e 2: zeros (menos de 3 visíveis)
        np.testing.assert_array_equal(blk[4:], np.zeros(8))

    def test_nine_ghosts_fill_three_slots(self, env_nine_ghosts):
        obs, _ = env_nine_ghosts.reset(seed=0)
        blk = _traffic_block(obs)
        # 3 mais próximos por |dist_s|: 9, 18 e 27 m (grid à frente)
        np.testing.assert_allclose(blk[0::4][:3], [0.09, 0.18, 0.27], atol=1e-3)
        assert (blk[3::4][:3] == 1.0).all()               # todos à frente
        assert np.isfinite(blk).all()

    def test_obs_never_contains_own_car(self, env_nine_ghosts):
        """O próprio carro teria |dist_s| = 0 — nenhum slot pode ser 0."""
        obs, _ = env_nine_ghosts.reset(seed=0)
        blk = _traffic_block(obs)
        dists = blk[0::4][:3]
        assert (dists > 0.05).all(), f"obs contém o próprio carro: {dists}"
        np.testing.assert_allclose(sorted(dists), [0.09, 0.18, 0.27], atol=1e-3)

    def test_layout_stable_between_resets(self, env_nine_ghosts):
        obs1, _ = env_nine_ghosts.reset(seed=0)
        blk1 = _traffic_block(obs1).copy()
        obs2, _ = env_nine_ghosts.reset(seed=0)
        blk2 = _traffic_block(obs2)
        np.testing.assert_allclose(blk1, blk2, atol=1e-6,
                                   err_msg="layout de tráfego mudou entre resets")

    def test_ghost_grid_in_front_of_student(self, env_nine_ghosts):
        """Fantasmas espaçados no grid À FRENTE do aluno (aluno = P10)."""
        env_nine_ghosts.reset(seed=0)
        snap = env_nine_ghosts._all_cars_snapshot()
        ego_s = [s for (d, s, _, _) in snap if d == env_nine_ghosts.driver_id][0]
        L = env_nine_ghosts._track_len_s
        from backend.model_train.reference_controller import signed_dist_s
        dists = sorted(signed_dist_s(s, ego_s, L) for (d, s, _, _) in snap
                       if d != env_nine_ghosts.driver_id)
        assert dists == pytest.approx([9.0, 18.0, 27.0, 36.0, 45.0, 54.0,
                                       63.0, 72.0, 81.0], abs=0.5)


# --------------------------------------------------- fantasmas dirigem

class TestGhostDriving:
    def test_ghosts_move_and_generate_no_laps(self):
        """Rollout curto: fantasmas dirigidos pelo professor de tráfego
        progridam fisicamente, permanecem lap=0 (não contam volta) e a obs
        do aluno continua finita. O aluno é pilotado pelo professor COM
        tráfego — o padrão de rotulação que a FASE 3 usará no DAgger."""
        from backend.model_train.f1_env import F1MultiContextEnv
        from backend.model_train.reference_controller import ReferenceController
        from backend.model_train.velocity_profile import VelocityProfile
        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                n_traffic=2, allow_respawn=False)
        try:
            vp = VelocityProfile(env._wps_arr, grip_mult=0.788, sf=0.80,
                                 ds_target=4.0, smooth_window_m=20.0)
            teacher = ReferenceController(env, velocity_profile=vp)
            env.reset(seed=0)
            for _ in range(30):
                a = teacher.action(traffic=env.traffic_for(env.driver_id))
                obs, r, term, trunc, info = env.step(a)
                assert np.isfinite(obs['telemetry']).all()
                if term or trunc:
                    break
            moved = [env.engine.cum_dist_m[g] for g in env._ghost_ids]
            assert min(moved) > 5.0, f"fantasmas não andaram: {moved}"
            assert all(env.engine.states[g].lap == 0 for g in env._ghost_ids), \
                "fantasma completou volta — devem ser lap-less (sem lap%)"
        finally:
            env.close()

    def test_traffic_for_excludes_self(self, env_nine_ghosts):
        """traffic_for(id) nunca inclui o próprio carro — fonte única da obs
        e dos rótulos da FASE 3 (professor vê o que a política vê)."""
        env_nine_ghosts.reset(seed=0)
        snap = env_nine_ghosts._all_cars_snapshot()
        ego = [t for t in snap if t[0] == env_nine_ghosts.driver_id][0]
        tf = env_nine_ghosts.traffic_for(env_nine_ghosts.driver_id)
        assert len(tf) == 9
        for (s, lat, v) in tf:   # nenhum elemento pode ser o próprio ego
            assert not (abs(s - ego[1]) < 1e-6 and abs(lat - ego[2]) < 1e-6
                        and abs(v - ego[3]) < 1e-6), "traffic_for incluiu o ego"
        # e os 9 são EXATAMENTE os fantasmas do snapshot (mesmas poses)
        ghosts = {(round(s, 6), round(lat, 6)) for (d, s, lat, v) in snap
                  if d != env_nine_ghosts.driver_id}
        tf_set = {(round(s, 6), round(lat, 6)) for (s, lat, v) in tf}
        assert tf_set == ghosts


# --------------------------------- engine: exclusão de voltas dos fantasmas

class TestNoLapDrivers:
    def test_no_lap_drivers_skip_completion_but_accumulate(self):
        """Mecanismo central da FASE 2: driver em engine._no_lap_drivers
        acumula cum_dist (recuperação por progresso continua funcionando)
        mas NÃO dispara _complete_lap — sem evento de volta, sem degradar
        pneu, sem avançar o clima. Driver normal no mesmo estado completa."""
        from backend.engine import SimulationEngine, SimulationConfig
        from backend.domain import (Driver, CarSpecs, TyreCompound, WeatherModel,
                                    WeatherKind, BASE_CONDITIONS, build_interlagos_track)
        specs = CarSpecs(name="F1 Car", power_kw=735.0, mass_kg=798.0,
                         fuel_capacity_kg=110.0)
        drivers = [Driver(driver_id='REAL', name='REAL', car_specs=specs,
                          starting_tyre_compound=TyreCompound.MEDIUM),
                   Driver(driver_id='GHOST0', name='GHOST0', car_specs=specs,
                          starting_tyre_compound=TyreCompound.MEDIUM)]
        cfg = SimulationConfig(race_id='t', num_laps=99, logic_step_hz=10.0,
                               physics_sub_steps=24, gui=False,
                               camera_mode='overview', draw_track=False,
                               realtime=False, input_stale_after_s=300.0)
        engine = SimulationEngine(config=cfg, track=build_interlagos_track(),
                                  drivers=drivers,
                                  weather_model=WeatherModel(
                                      initial=BASE_CONDITIONS[WeatherKind.DRY]))
        engine.setup()
        try:
            engine._no_lap_drivers = {'GHOST0'}
            track_len = engine.track.length_m
            for d in drivers:
                phys = engine.physics.get_state(engine.handles[d.driver_id])
                engine.last_pos[d.driver_id] = (phys['x'], phys['y'])
                engine.cum_dist_m[d.driver_id] = 2.0 * track_len
            engine._check_lap_completion()
            assert engine.states['REAL'].lap == 1, "driver normal deveria completar"
            assert engine.states['GHOST0'].lap == 0, \
                "fantasma NÃO pode completar volta (contaminaria clima/pneu)"
            assert engine.cum_dist_m['GHOST0'] == pytest.approx(2.0 * track_len), \
                "fantasma deve acumular progresso (recuperação por movimento)"
        finally:
            engine.physics.close()

    def test_default_engine_has_no_no_lap_drivers(self):
        """Sem _no_lap_drivers definido (corrida neural), o comportamento é
        idêntico ao de sempre — getattr com default vazio."""
        from backend.engine import SimulationEngine
        assert not getattr(SimulationEngine, '_no_lap_drivers', ())


# --------------------------------------- FASE 6: fantasmas parados + grid

class TestGhostHold:
    def test_ghost_hold_ignored_with_zero_traffic(self):
        """r2: com n=0, hold/sf_range são silenciosamente None (solo —
        o treino com mix round-robin precisa criar envs n=0 sem erro)."""
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                 n_traffic=0, ghost_hold_ticks=(150, 250),
                                 allow_respawn=False)
        assert env.ghost_hold_ticks is None
        env.close()

    def test_held_ghost_freezes_mid_episode(self):
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                n_traffic=2, allow_respawn=False,
                                ghost_hold_ticks=(60, 90), ghost_hold_n=1)
        try:
            from backend.model_train.reference_controller import signed_dist_s
            env.reset(seed=0)
            assert len(env._ghost_holds) == 1
            gid, hold = next(iter(env._ghost_holds.items()))
            # anda até DENTRO da janela de hold
            while env.steps < hold['start'] + 10:
                env.step(np.zeros(2, np.float32))
            assert hold['pose'] is not None, "hold ativo deve congelar a pose"
            s_before = env._all_cars_snapshot()
            s_held = next(s for (d, s, _, _) in s_before if d == gid)
            v_held = next(v for (d, _, _, v) in s_before if d == gid)
            assert v_held < 1.0, "fantasma em hold deve estar parado"
            for _ in range(15):                       # 1,5 s de hold
                env.step(np.zeros(2, np.float32))
            s_after = next(s for (d, s, _, _) in env._all_cars_snapshot() if d == gid)
            assert abs(s_after - s_held) < 1.0, "fantasma em hold não pode andar"
        finally:
            env.close()


class TestGridPosition:
    def test_mid_grid_has_ghosts_behind(self):
        """grid_position (5,7): fantasmas ocupam posições ANTES do aluno →
        existem carros ATRÁS (dist_s negativa) — a obs codifica ahead=0."""
        from backend.model_train.f1_env import F1MultiContextEnv
        from backend.model_train.reference_controller import signed_dist_s
        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                n_traffic=6, allow_respawn=False,
                                grid_position=(5, 7))
        try:
            env.reset(seed=0)
            snap = env._all_cars_snapshot()
            s_ego = next(s for (d, s, _, _) in snap if not d.startswith('GHOST'))
            dists = [signed_dist_s(s, s_ego, env._track_len_s)
                     for (d, s, _, _) in snap if d.startswith('GHOST')]
            behind = [d for d in dists if d < 0]
            ahead = [d for d in dists if d > 0]
            assert behind and ahead, (
                f"grid médio deve ter fantasmas atrás E à frente: {dists}")
        finally:
            env.close()

    def test_default_grid_all_ahead(self):
        from backend.model_train.f1_env import F1MultiContextEnv
        from backend.model_train.reference_controller import signed_dist_s
        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                n_traffic=4, allow_respawn=False)
        try:
            env.reset(seed=0)
            snap = env._all_cars_snapshot()
            s_ego = next(s for (d, s, _, _) in snap if not d.startswith('GHOST'))
            assert all(signed_dist_s(s, s_ego, env._track_len_s) > 0
                       for (d, s, _, _) in snap if d.startswith('GHOST'))
        finally:
            env.close()
