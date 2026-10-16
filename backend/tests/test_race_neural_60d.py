"""PASSO 1 (FASE 4 v14) — race runner neural 60d.

1. PARIDADE NumPy↔Keras estendida ao ator 60d sobre ≥1000 obs REAIS do env
   (n_traffic=8, o ator pilotando — distribuição de deploy). O NPZ é o mesmo
   caminho de produção (extração por camada, resolução por shape no
   NumpyNeuralActor).
2. VALIDAÇÃO DE SHAPE com erro explícito: ator 60d + obs_mode edge/legacy →
   ValueError claro; 60d + traffic → constrói com input_dim=60.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
for p in (str(PROJECT_ROOT), str(PROJECT_ROOT / 'backend'),
          str(PROJECT_ROOT / 'backend' / 'scripts')):
    if p not in sys.path:
        sys.path.insert(0, p)

V14_ACTOR = (PROJECT_ROOT / 'backend' / 'model_train' / 'v14_traffic'
             / 'dagger_actor_best_s2_n8.keras')


def _export_npz(keras_path: Path, npz_path: Path):
    """Extração de pesos idêntica à de produção (ensure_npz_weights_exist)."""
    import tensorflow as tf
    model = tf.keras.models.load_model(str(keras_path), compile=False)
    weights = {}
    for layer in model.layers:
        w = layer.get_weights()
        if w:
            for idx, arr in enumerate(w):
                weights[f'{layer.name}_{idx}'] = arr
    np.savez(str(npz_path), **weights)
    return model


@pytest.fixture(scope='module')
def v14_pair(tmp_path_factory):
    """(modelo keras, npz exportado) do ator v14 de 60 entradas."""
    pytest.importorskip('tensorflow')
    if not V14_ACTOR.exists():
        pytest.skip(f"checkpoint v14 ausente: {V14_ACTOR}")
    d = tmp_path_factory.mktemp('v14_npz')
    npz = d / 'v14_weights.npz'
    model = _export_npz(V14_ACTOR, npz)
    return model, npz


class TestShapeValidation:
    def test_actor_60d_rejects_edge_mode_with_explicit_error(self, v14_pair):
        import run_race_10_cars as R
        _, npz = v14_pair
        with pytest.raises(ValueError, match="INCOMPATÍVEL"):
            R.NeuralRaceController(weights_path=npz, obs_mode='edge',
                                   mappings_path=None, track=None)

    def test_actor_60d_rejects_legacy_mode_with_explicit_error(self, v14_pair):
        import run_race_10_cars as R
        _, npz = v14_pair
        with pytest.raises(ValueError, match="INCOMPATÍVEL"):
            R.NeuralRaceController(weights_path=npz, obs_mode='legacy',
                                   mappings_path=None, track=None)

    def test_actor_60d_builds_in_traffic_mode(self, v14_pair):
        import run_race_10_cars as R
        _, npz = v14_pair
        ctrl = R.NeuralRaceController(weights_path=npz, obs_mode='traffic',
                                      mappings_path=None, track=None)
        assert ctrl.actor.input_dim == 60
        assert ctrl.actor.act_dim == 2


class TestDeployProfiles:
    """PASSO 5 (FASE 4 v14): --profile substitui o default por mtime — os 3
    candidatos de deploy devem existir, com obs correta, e o default
    documentado é 'race' (v10)."""

    def test_profiles_exist_default_race_obs_correct(self):
        import run_race_10_cars as R
        assert R.DEFAULT_PROFILE == 'race'
        assert set(R.PROFILES) == {'race', 'quali', 'traffic', 'composite'}
        for name, prof in R.PROFILES.items():
            assert prof['keras'].exists(), f"profile {name}: {prof['keras']} ausente"
        assert R.PROFILES['race']['obs_mode'] == 'edge'
        assert R.PROFILES['quali']['obs_mode'] == 'edge'
        assert R.PROFILES['traffic']['obs_mode'] == 'traffic'
        # 3 candidatos DISTINCTOS (o default por mtime escolhia errado entre eles)
        paths = {str(R.PROFILES[k]['keras'].resolve()) for k in R.PROFILES}
        assert len(paths) == 3


class TestNumpyKerasParity60d:
    def test_parity_on_1000_real_obs(self, v14_pair):
        """≥1000 obs REAIS (env n_traffic=8, ator keras pilotando): o motor
        NumPy da corrida deve reproduzir o Keras (atol 2e-5, float32)."""
        import run_race_10_cars as R
        from backend.model_train.f1_env import F1MultiContextEnv
        model, npz = v14_pair
        np_actor = R.NumpyNeuralActor(npz)

        env = F1MultiContextEnv(track='interlagos', obs_mode='traffic',
                                n_traffic=8, allow_respawn=False,
                                grip_override=None)
        try:
            obs, _ = env.reset(seed=0)
            collected, steps = [], 0
            while len(collected) < 1000 and steps < 4000:
                collected.append({k: np.asarray(v).copy() for k, v in obs.items()})
                m = model({k: np.asarray(v)[None] for k, v in obs.items()},
                          training=False).numpy()[0]
                obs, r, term, trunc, info = env.step(np.tanh(m))
                steps += 1
                if term or trunc:
                    obs, _ = env.reset(seed=steps)
            assert len(collected) >= 1000, f"coletou {len(collected)} obs"

            tels = np.stack([c['telemetry'] for c in collected])
            ctxs = np.stack([c['ctx_numeric'] for c in collected])
            trks_2d = np.stack([c['track_id'] for c in collected]).astype(np.int32)   # (N,1) — spec do input
            cmps_2d = np.stack([c['compound_id'] for c in collected]).astype(np.int32)
            trks, cmps = trks_2d[:, 0], cmps_2d[:, 0]   # 1-D p/ o motor NumPy
            assert tels.shape == (len(collected), 46)

            keras_out = model({'telemetry': tels, 'ctx_numeric': ctxs,
                               'track_id': trks_2d, 'compound_id': cmps_2d},
                              training=False).numpy()
            np_out = np_actor.forward(tels, ctxs, trks, cmps)
            # CONTRATO v2: o motor NumPy aplica tanh DENTRO do forward (devolve
            # a AÇÃO final); o Keras devolve a média linear — o squash vai fora
            # (a = tanh(m), ver eval_policy/race). Comparação é ação-vs-ação.
            keras_action = np.tanh(keras_out)
            max_diff = float(np.abs(keras_action - np_out).max())
            np.testing.assert_allclose(
                np_out, keras_action, atol=2e-5,
                err_msg=f"NumPy engine divergiu do Keras (max diff {max_diff:.2e})")
        finally:
            env.close()


class TestRegistryResolution:
    """FASE 0.8 (v15): --profile resolve pelo ALIAS do registry com fallback
    para o caminho de arquivo; os 3 aliases devolvem checkpoint existente e
    coerente com o PROFILES."""

    def test_resolve_deploy_aliases_exist_and_match_profiles(self):
        import run_race_10_cars as R
        from backend.model_train import tracking
        for alias in ('race', 'quali', 'traffic'):
            p = tracking.resolve_deploy(alias)
            assert p is not None and Path(p).exists(), \
                f"alias {alias} não resolveu para arquivo existente"
            # com registry vazio cai no fallback = mesmo arquivo do PROFILES;
            # com registry populado = o mesmo deploy registrado
            assert Path(p).resolve() == Path(R.PROFILES[alias]['keras']).resolve()
