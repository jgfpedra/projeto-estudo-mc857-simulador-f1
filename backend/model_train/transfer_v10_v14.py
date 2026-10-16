"""PASSO 1 (FASE 3 v14) — transferência de pesos v10 (edge 48d) → v14 (traffic 60d).

Decisão: NÃO fazer BC-do-zero. O v14 herda TODA a habilidade de pilotagem do
v10; os 12 rows de TRÁFEGO da primeira Dense começam ZEROS — a rede v14
inicialmente é EXATAMENTE o v10 (paridade verificada por teste, atol 1e-6)
e é INVARIANTE às dims de tráfego até que o DAgger as atualize por gradiente.

Mapeamento por LINHA da primeira Dense — a ordem do concat do actor é
[telemetry, ctx_numeric, emb_trk(8), emb_cmp(4)] (train_multi_context_ppo.py,
_build_actor; idêntico ao NumpyNeuralActor.forward da corrida):

    v14 rows 0-33   <- v10 rows 0-33   (34d edge: base 23 + 11 raios LiDAR)
    v14 rows 34-45  <- ZEROS           (12d traffic — a rede começa IGNORANDO)
    v14 rows 46-47  <- v10 rows 34-35  (ctx_numeric)
    v14 rows 48-55  <- v10 rows 36-43  (embedding track 8d)
    v14 rows 56-59  <- v10 rows 44-47  (embedding compound 4d)

Bias da 1ª Dense e TODAS as camadas profundas (256/128/64/32/mean) e
embeddings: cópia direta.

TESTE DE PARIDADE (tests/test_v14_transfer.py) — obrigatório antes de treinar:
v14 com os 12 dims de tráfego ZERADOS + a mesma obs edge/ctx/emb do v10 deve
produir saídas IDÊNTICAS (atol 1e-6). Sem ele, a transferência não é confiável.

Uso:
  .venv/bin/python model_train/transfer_v10_v14.py \
      --src model_train/v10_dagger/dagger_actor_best.keras \
      --out model_train/v14_traffic/init_from_v10.keras
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
BACKEND = MODEL_DIR.parent
for p in (str(PROJECT_ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')

import numpy as np

# Dimensões do remap (contrato da obs 'traffic' — ver f1_env.py):
N_EDGE_TEL = 34      # rows 0-33: base 23 + 11 raios (idêntico ao v10)
N_TRAFFIC_TEL = 12   # rows 34-45: zeros no warm start
N_TOTAL_TEL = N_EDGE_TEL + N_TRAFFIC_TEL   # 46


def build_traffic_actor(act_dim: int = 2):
    """Constrói o esqueleto v14 (telemetria 46d) com a MESMA arquitetura do
    actor do projeto (fonte única: MultiContextPPOAgent._build_actor)."""
    import tensorflow as tf
    from gymnasium import spaces
    from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent
    obs_spaces = {
        'telemetry': spaces.Box(-5.0, 5.0, (N_TOTAL_TEL,), dtype=np.float32),
        'ctx_numeric': spaces.Box(-5.0, 5.0, (2,), dtype=np.float32),
    }
    agent = MultiContextPPOAgent(obs_spaces, act_dim=act_dim)
    return agent.actor


def _layers_by_type(model, type_name: str):
    """Camadas por nome de tipo (robusto a Keras 2/3: os objetos carregados
    podem não casar com isinstance das classes do runtime)."""
    return [l for l in model.layers if type(l).__name__ == type_name]


def transfer_edge_to_traffic(src_actor, dst_actor):
    """Copia v10 (48d) -> v14 (60d) com o remap de rows da 1ª Dense.

    Pareamento por ORDEM + shape (os nomes auto-gerados do Keras não são
    estáveis entre builds — mesmo critério do NumpyNeuralActor).
    Retorna dst_actor (modificado in place) e um dict de diagnóstico.
    """
    import tensorflow as tf

    src_denses = _layers_by_type(src_actor, 'Dense')
    dst_denses = _layers_by_type(dst_actor, 'Dense')
    if len(src_denses) != len(dst_denses):
        raise ValueError(f"Arquiteturas divergentes: {len(src_denses)} Dense no "
                         f"src vs {len(dst_denses)} no dst")
    if int(src_denses[0].kernel.shape[0]) != 48 or int(dst_denses[0].kernel.shape[0]) != 60:
        raise ValueError(
            f"Esperado src 48d -> dst 60d na 1ª Dense, encontrado "
            f"{int(src_denses[0].kernel.shape[0])} -> {int(dst_denses[0].kernel.shape[0])}. "
            f"Use o checkpoint v10 com --obs-mode edge e o dst com obs 'traffic'.")

    diag = {'dense_remapped': 1, 'dense_copiadas': 0, 'embeddings': 0}
    # --- 1ª Dense: remap de rows (tel edge | zeros traffic | ctx | embs) ---
    w_src = src_denses[0].get_weights()      # [kernel (48,256), bias (256,)]
    k_src, b_src = np.asarray(w_src[0]), np.asarray(w_src[1])
    k_new = np.zeros_like(np.asarray(dst_denses[0].get_weights()[0]))
    k_new[0:N_EDGE_TEL] = k_src[0:N_EDGE_TEL]                  # edge (34)
    k_new[N_EDGE_TEL:N_TOTAL_TEL] = 0.0                       # traffic (12) = ZERO
    k_new[N_TOTAL_TEL:N_TOTAL_TEL + 2] = k_src[N_EDGE_TEL:N_EDGE_TEL + 2]        # ctx (2)
    k_new[N_TOTAL_TEL + 2:N_TOTAL_TEL + 2 + 8 + 4] = k_src[N_EDGE_TEL + 2:48]    # embs (12)
    # kernel remapeado + bias HERDADO do v10 (o do esqueleto novo é aleatório)
    dst_denses[0].set_weights([k_new, b_src.copy()])

    # --- Denses profundas: cópia direta (shape idêntico) ---
    for s, d in zip(src_denses[1:], dst_denses[1:]):
        sw, dw = s.get_weights(), d.get_weights()
        if len(sw) != len(dw) or any(a.shape != b.shape for a, b in zip(sw, dw)):
            raise ValueError(f"Shape incompatível na Dense profunda: "
                             f"{[a.shape for a in sw]} vs {[b.shape for b in dw]}")
        d.set_weights(sw)
        diag['dense_copiadas'] += 1

    # --- Embeddings: cópia direta por shape (20,8) e (5,4) ---
    src_embs = _layers_by_type(src_actor, 'Embedding')
    dst_embs = _layers_by_type(dst_actor, 'Embedding')
    for d in dst_embs:
        match = [s for s in src_embs
                 if np.asarray(s.get_weights()[0]).shape == np.asarray(d.get_weights()[0]).shape]
        if not match:
            raise ValueError(f"Embedding {d.name} sem par no src por shape")
        d.set_weights(match[0].get_weights())
        diag['embeddings'] += 1
    return dst_actor, diag


def main():
    import argparse
    import tensorflow as tf
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='checkpoint v10 (.keras, obs edge 48d)')
    ap.add_argument('--out', required=True, help='checkpoint v14 de saída (não sobrescreva o src)')
    args = ap.parse_args()

    src = tf.keras.models.load_model(args.src, compile=False)
    dst = build_traffic_actor(int(src.outputs[0].shape[-1]))
    _, diag = transfer_edge_to_traffic(src, dst)

    out = Path(args.out)
    if out.resolve() == Path(args.src).resolve():
        raise SystemExit("ERRO: --out não pode ser o mesmo arquivo de --src")
    out.parent.mkdir(parents=True, exist_ok=True)
    dst.save(str(out))
    print(f"[transfer] {diag['dense_remapped']} Dense remapeada (rows: 34 edge | "
          f"12 zeros | 2 ctx | 12 emb) | {diag['dense_copiadas']} profundas copiadas | "
          f"{diag['embeddings']} embeddings")
    print(f"[transfer] salvo: {out}")
    print("[transfer] PARIDADE: rode tests/test_v14_transfer.py antes de treinar.")


if __name__ == '__main__':
    main()
