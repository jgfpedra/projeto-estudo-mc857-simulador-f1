"""v15 FASE 3 — aluno de tráfego por RESÍDUO GATED (FOLLOW-ONLY).

A resposta por construção à pergunta "e se o treino degradar o solo?":
NÃO PODE. A base v10 é CONGELADA (pesos nunca atualizados); o resíduo é
uma rede pequena cuja saída inicializa em ZERO e só age quando há carro
à frente dentro da distância de frenagem (gate contínuo).

  a = tanh(m_solo + g·r_pred)

Com g=0 (sem tráfego): a = tanh(m_solo) = v10 EXATO (paridade 1e-6).

Componentes:
  - CompositeActor: Keras model (solo .keras congelado + residual TF)
  - NumpyCompositeActor: motor NumPy p/ o race runner (FASE 4)
  - SlotHysteresis: wrapper de estado por driver p/ compute_traffic_features
    (histerese de slots — slot-swap 2,38× nos contatos medido na FASE 5 A1)
"""
from __future__ import annotations

import math
from pathlib import Path
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent

OBS_SPEED = 100.0
KAPPA_SCALE = 25.0
A_BRAKE_REF = 10.0  # mesmo valor do env (f1_env.py)


def gate_distance(v_ego: float) -> float:
    """D(v) = clip(v²/(2·A_BRAKE_REF) + 30, 40, 120) m."""
    return float(np.clip(v_ego ** 2 / (2.0 * A_BRAKE_REF) + 30.0, 40.0, 120.0))


def gate_value(v_ego: float, d_ahead_min: float) -> float:
    """g = clip((D(v) − d_ahead_min)/20, 0, 1). Sem carro à frente no D → g=0."""
    D = gate_distance(v_ego)
    if d_ahead_min is None or d_ahead_min >= D:
        return 0.0
    return float(np.clip((D - d_ahead_min) / 20.0, 0.0, 1.0))


class SlotHysteresis:
    """Histerese de ranqueamento de slots (v15 FASE 3, lição FASE 5 A1).

    compute_traffic_features é PURA (permanece); este wrapper guarda o
    estado por driver: troca de slot só após N=5 ticks com ranking estável.
    Usado pelo env (um por carro) e pelo race runner (por driver) — a
    fórmula compartilhada NÃO é duplicada.
    """

    def __init__(self, n_stable: int = 5):
        self.n_stable = n_stable
        self._stable_count = 0
        self._last_ranking = None

    def filter(self, others, ego_s, half_width, track_len, v_ego,
               compute_fn):
        """Filtra `others` [(s, lat, v)] conforme a histerese e devolve a
        lista que compute_traffic_features consome."""
        from backend.model_train.reference_controller import signed_dist_s
        # ranqueia por |dist_s| (top-3 + demais como fallback)
        ranked = sorted(others, key=lambda o: abs(signed_dist_s(o[0], ego_s, track_len)))[:3]
        ranking_key = tuple(round(s, 1) for s, _, _ in ranked)
        if ranking_key == self._last_ranking:
            self._stable_count += 1
        else:
            if self._stable_count >= self.n_stable:
                self._last_ranking = ranking_key
                self._stable_count = 1
            elif self._last_ranking is None:
                self._last_ranking = ranking_key
                self._stable_count = 1
            # senão: mantém o ranking anterior (histerese)
        if self._last_ranking is None:
            return others
        # devolve só os carros do ranking estável (se existirem)
        stable_s = [s for s, _, _ in ranked]
        filtered = [o for o in others if o[0] in stable_s]
        return filtered if filtered else others


def build_residual_input(traffic_feats_12d, v_ego, kappa_ahead, prev_steer, prev_long):
    """Entrada 16d do resíduo: [12d tráfego, v_ego/OBS_SPEED, κ·25, prev_st, prev_lng]."""
    return np.concatenate([
        np.asarray(traffic_feats_12d, dtype=np.float32),
        [v_ego / OBS_SPEED, kappa_ahead * KAPPA_SCALE, prev_steer, prev_long],
    ]).astype(np.float32)


def build_residual_keras(n_in: int = 16):
    """Residual: 16d -> 128 -> 128 -> 2 (linear, init ZEROS)."""
    import tensorflow as tf
    inp = tf.keras.Input(shape=(n_in,), name='residual_in')
    x = tf.keras.layers.Dense(128, activation='relu', name='res_d1')(inp)
    x = tf.keras.layers.Dense(128, activation='relu', name='res_d2')(x)
    out = tf.keras.layers.Dense(2, activation=None, name='res_out',
                                kernel_initializer='zeros',
                                bias_initializer='zeros')(x)
    m = tf.keras.Model(inp, out, name='residual')
    return m


class CompositeActor:
    """solo (v10, congelado) + gate·residual -> tanh(m_solo + g·r).

    Keras: para treino (DAgger do resíduo) e eval.
    """

    def __init__(self, solo_path: str, residual_path: str = None):
        import tensorflow as tf
        self.solo = tf.keras.models.load_model(solo_path, compile=False)
        self.residual = build_residual_keras()
        if residual_path:
            self.residual = tf.keras.models.load_model(residual_path, compile=False)
        for layer in self.solo.layers:
            layer.trainable = False

    def forward_parts(self, obs_batch):
        """(m_solo [N,2], precisa do gate p/ completar)."""
        m = self.solo(obs_batch, training=False).numpy()
        return m

    def predict(self, obs_batch, res_in_batch, gate_batch):
        """a = tanh(m_solo + g·r). obs_batch: dict {telemetry, ctx, track_id, compound_id}."""
        m_solo = self.solo(obs_batch, training=False).numpy()
        r = self.residual.predict(res_in_batch, verbose=0) \
            if hasattr(self.residual, 'predict') else self.residual(res_in_batch).numpy()
        g = np.asarray(gate_batch, dtype=np.float32)[:, None]
        return np.tanh(m_solo + g * r)

    def freeze_hash(self):
        """Hash dos pesos do solo — para o teste de congelamento bit-a-bit."""
        import hashlib
        h = hashlib.sha256()
        for w in self.solo.get_weights():
            h.update(w.tobytes())
        return h.hexdigest()


class NumpyCompositeActor:
    """Motor NumPy do composite para o race runner (FASE 4 pré-requisito).

    Solo via NPZ (forward existente — a média linear PRÉ-tanh) + residual
    (2 densas em NumPy) + gate escalar → a = tanh(m_solo + g·r).
    """

    def __init__(self, solo_npz_path, residual_weights_path=None):
        import sys
        from pathlib import Path
        scripts = Path(__file__).resolve().parent.parent / 'scripts'
        for p_str in (str(scripts),):
            if p_str not in sys.path:
                sys.path.insert(0, p_str)
        import run_race_10_cars as R
        self.solo = R.NumpyNeuralActor(Path(solo_npz_path))
        self.res_w = None
        if residual_weights_path:
            data = np.load(str(residual_weights_path))
            self.res_w = {k: data[k] for k in data.keys()}

    def _residual_forward(self, x):
        """2×Dense(128, relu) + Dense(2, linear) em NumPy puro."""
        w = [self.res_w[k] for k in sorted(self.res_w.keys())]
        # assume ordem: d1_kernel, d1_bias, d2_kernel, d2_bias, out_kernel, out_bias
        x = np.maximum(0.0, x @ w[0] + w[1])
        x = np.maximum(0.0, x @ w[2] + w[3])
        return x @ w[4] + w[5]

    def predict(self, tels_edge_34, ctxs, trk_ids, cmp_ids, res_in, gates):
        """a = tanh(m_solo + g·r). m_solo vem do forward_linear (PRÉ-tanh)
        — v15 PASSO 3.0: atanh(tanh(m)) explode em float32 quando a política
        satura em ±0,99 nas retas; forward_linear elimina o problema."""
        m_solo = self.solo.forward_linear(tels_edge_34, ctxs, trk_ids, cmp_ids)
        g = np.asarray(gates, dtype=np.float32)[:, None]
        if self.res_w is not None and len(self.res_w) >= 6:
            r = self._residual_forward(np.asarray(res_in, dtype=np.float32))
        else:
            r = np.zeros_like(m_solo)
        return np.tanh(m_solo + g * r)

    def residual_forward_only(self, res_in):
        if self.res_w is not None and len(self.res_w) >= 6:
            return self._residual_forward(np.asarray(res_in, dtype=np.float32))
        return np.zeros((len(res_in), 2), dtype=np.float32)


def export_residual_npz(residual_keras, out_path):
    """Exporta os pesos do residual Keras p/ NPZ (mesma convenção do solo)."""
    weights = {}
    for layer in residual_keras.layers:
        w = layer.get_weights()
        if w:
            for idx, arr in enumerate(w):
                weights[f'{layer.name}_{idx}'] = arr
    np.savez(str(out_path), **weights)
    return out_path
