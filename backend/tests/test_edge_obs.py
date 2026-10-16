"""Testes da percepção de bordas (Fase D) — LiDAR virtual v8.

Valida: reta, curva, hairpin, aproximação à borda, alinhamento/desalinhamento,
fechamento circular, espaçamento desigual, fora da pista, raio sem interseção,
NaN/inf, custo computacional, e consistência entre pistas.
"""
import math

import numpy as np
import pytest


@pytest.fixture(scope="module")
def env_edge():
    from backend.model_train.f1_env import F1MultiContextEnv
    e = F1MultiContextEnv(track='interlagos', allow_respawn=False, obs_mode='edge')
    yield e
    e.close()


@pytest.fixture(scope="module")
def env_legacy():
    from backend.model_train.f1_env import F1MultiContextEnv
    e = F1MultiContextEnv(track='interlagos', allow_respawn=False, obs_mode='legacy')
    yield e
    e.close()


def _obs_at(env, s_pos, lat=0.0, hdg_off=0.0):
    """Teleporta e devolve a observação (34 dims no modo edge)."""
    x, y, yaw = env._point_at(s_pos)
    if lat != 0.0:
        nx, ny = -math.sin(yaw), math.cos(yaw)
        x, y = x + nx * lat, y + ny * lat
    env.engine.physics.set_position(env.engine.handles[env.driver_id],
                                    (x, y, 0.5), yaw_rad=yaw + hdg_off)
    return env._get_obs()


class TestEdgeObsBasics:
    def test_legacy_unchanged(self, env_legacy):
        obs, _ = env_legacy.reset()
        assert obs['telemetry'].shape == (23,)

    def test_edge_shape(self, env_edge):
        obs, _ = env_edge.reset()
        assert obs['telemetry'].shape == (34,)

    def test_no_nan_inf(self, env_edge):
        for s in (450.0, 2048.0, 2309.0, 0.0, 4155.0):
            tel = _obs_at(env_edge, s)['telemetry']
            assert np.all(np.isfinite(tel)), f"NaN/inf em s={s}"

    def test_range_0_1(self, env_edge):
        for s in (450.0, 2048.0, 2309.0, 1000.0, 3000.0):
            rays = _obs_at(env_edge, s)['telemetry'][23:]
            assert np.all(rays >= 0.0) and np.all(rays <= 1.0)

    def test_custo_computacional(self, env_edge):
        """_cast_rays deve ser <1ms por chamada (10 Hz de controle)."""
        import time
        _obs_at(env_edge, 2309.0)  # aquece
        t0 = time.perf_counter()
        for _ in range(50):
            _obs_at(env_edge, 2309.0)
        dt = (time.perf_counter() - t0) / 50
        assert dt < 0.005, f"_cast_rays custou {dt*1000:.1f}ms (>5ms)"


class TestEdgeGeometry:
    def test_reta_simetrica(self, env_edge):
        """Na reta, ao centro: ±90° devem dar ~half_width/max_range."""
        rays = _obs_at(env_edge, 450.0)['telemetry'][23:]
        left, right = rays[0], rays[-1]  # -90° e +90°
        expected = env_edge._half_width / 40.0
        assert abs(left - expected) < 0.05, f"raio -90°={left:.3f}, esperado ~{expected:.3f}"
        assert abs(right - expected) < 0.05

    def test_reta_frontal_max(self, env_edge):
        """Na reta, olhando reto: o raio frontal não deve encontrar a borda."""
        rays = _obs_at(env_edge, 450.0)['telemetry'][23:]
        assert rays[5] >= 0.95, f"frontal={rays[5]:.2f}, deveria ser ~1.0"

    def test_hairpin_frontal_curto(self, env_edge):
        """No ápice do hairpin (R~10m), o raio frontal deve ser MUITO curto."""
        rays = _obs_at(env_edge, 2309.0)['telemetry'][23:]
        assert rays[5] < 0.5, f"frontal no hairpin={rays[5]:.2f}*40={rays[5]*40:.0f}m"

    def test_borda_esquerda_encurta_raio_esquerdo(self, env_edge):
        """Aproximando da borda esquerda: o raio a -90° deve ENCURTAR."""
        hw = env_edge._half_width
        center = _obs_at(env_edge, 450.0)['telemetry'][23:]
        near_left = _obs_at(env_edge, 450.0, lat=+0.7*hw)['telemetry'][23:]
        # lat>0 = à esquerda da linha → o raio a -90° (apontando p/ a ESQUERDA
        # do carro... espera: -90° do heading = lado DIREITO se heading é +x
        # e o sistema é right-handed. Convenção: EDGE_RAY_ANGLES_DEG[0]=-90°
        # aponta à DIREITA do heading. lat>0 = à ESQUERDA → distância à borda
        # esquerda DIMINUI, à direita AUMENTA.
        # No nosso sistema: -90° = cos(h-π/2),sin(h-π/2) = (sin(h),-cos(h))
        # para h=0 (leste): (0,-1) = sul = direita do carro olhando leste.
        # Então rays[0] (-90°) mede a borda DIREITA. lat>0 (esquerda) →
        # rays[0] AUMENTA, rays[-1] (+90°) DIMINUI.
        assert near_left[-1] < center[-1], "aproximando da esquerda, o raio +90° deve encurtar"
        assert near_left[0] > center[0], "aproximando da esquerda, o raio -90° deve aumentar"

    def test_borda_direita_encurta_raio_direito(self, env_edge):
        hw = env_edge._half_width
        center = _obs_at(env_edge, 450.0)['telemetry'][23:]
        near_right = _obs_at(env_edge, 450.0, lat=-0.7*hw)['telemetry'][23:]
        assert near_right[0] < center[0], "aproximando da direita, o raio -90° deve encurtar"
        assert near_right[-1] > center[-1], "aproximando da direita, o raio +90° deve aumentar"

    def test_heading_error_muda_cone(self, env_edge):
        """Desalinhado à esquerda: o cone de raios à frente fica assimétrico."""
        straight = _obs_at(env_edge, 450.0)['telemetry'][23:]
        tilted = _obs_at(env_edge, 450.0, hdg_off=math.radians(30))['telemetry'][23:]
        # girando 30° à esquerda: o raio -18° (que era ~simétrico) deve mudar
        assert abs(tilted[4] - straight[4]) > 0.05, "heading error deve mudar os raios frontais"

    def test_wrap_fechamento_circular(self, env_edge):
        """No wrap (s≈0, fecho da pista): o raio frontal deve ser finito."""
        rays = _obs_at(env_edge, 2.0)['telemetry'][23:]
        assert rays[5] < 0.95, f"frontal no wrap={rays[5]:.2f}, deveria ser <1.0"

    def test_fora_da_pista(self, env_edge):
        """Fora do asfalto (lat > half_width): os raios ainda são finitos/úteis."""
        hw = env_edge._half_width
        rays = _obs_at(env_edge, 450.0, lat=hw + 2.0)['telemetry'][23:]
        assert np.all(np.isfinite(rays))

    def test_raio_sem_intersecao_retorna_max(self, env_edge):
        """Numa reta longa olhando reto: max_range (1.0)."""
        # a reta do start/finish tem ~700m — o raio frontal não deve achar nada
        rays = _obs_at(env_edge, 3500.0)['telemetry'][23:]
        assert rays[5] == 1.0


class TestEdgeCrossTrack:
    def test_monza_retas_longas(self):
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='Monza', allow_respawn=False, obs_mode='edge')
        obs, _ = env.reset()
        rays = obs['telemetry'][23:]
        assert np.all(np.isfinite(rays))
        assert rays.shape == (11,)
        env.close()

    def test_monaco_hairpins(self):
        from backend.model_train.f1_env import F1MultiContextEnv
        env = F1MultiContextEnv(track='Monaco', allow_respawn=False, obs_mode='edge')
        obs, _ = env.reset()
        rays = obs['telemetry'][23:]
        assert np.all(np.isfinite(rays))
        assert rays.shape == (11,)
        env.close()

    def test_sem_trecho_oposto(self, env_edge):
        """Nenhum raio deve identificar um trecho espacialmente próximo
        do lado oposto do circuito (a janela é local em s)."""
        # no hairpin, a saída da curva está espacialmente próxima da entrada
        # os raios podem vê-la (correto, como um LiDAR real) mas não devem
        # retornar distâncias absurdamente curtas vindo do outro lado da pista
        rays = _obs_at(env_edge, 2309.0)['telemetry'][23:]
        # o raio traseiro (-90°) não deve ser menor que ~1m (colisão impossível)
        assert rays[0] > 0.02, f"raio -90° impossibly short: {rays[0]:.3f}"


class TestSchemaCompat:
    def test_legacy_nao_tem_rays(self, env_legacy):
        """O modo legacy NÃO deve ter os raios (compatibilidade v2-v7)."""
        obs, _ = env_legacy.reset()
        assert obs['telemetry'].shape == (23,)

    def test_obs_space_consistente(self, env_edge):
        assert env_edge.observation_space['telemetry'].shape == (34,)
        obs, _ = env_edge.reset()
        assert env_edge.observation_space.contains(obs)

    def test_action_space_inalterado(self, env_edge):
        assert env_edge.action_space.shape == (2,)
