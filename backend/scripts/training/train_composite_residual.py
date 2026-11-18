#!/usr/bin/env python3
"""Instrumento de treino do modelo neural residual para Composite Actor (COMPOSITE-TRAIN-1).

Linha composite: solo v10 CONGELADO (jamais retreinado) + gate * residual (16d -> 2d).
Entrada: 16-dim (12d tráfego + speed/100 + kappa*25 + prev_steer + prev_long).
Saída: 2-dim delta r_targets = atanh(clip(a_teacher, 0.98)) - m_solo.

Disclosure Formal de Formulação (Emenda O-4):
- O resíduo foi formulado no corpus sob suposição implícita de gate g=1.
- O corpus NÃO armazena a_teacher, m_solo nem gate (schema canônico restrito aos campos de log e r_targets).
- Todos os critérios de validação offline (§5(b)) são estritamente SEM-GATE e no espaço residual (r_targets).
- Em simulação de corrida, o escalar g in [0, 1] modula a aplicação da saída residual no
  NumpyCompositeActor.predict (residual_gated.py:171-181) via tanh(m_solo + g * r).
  O MAE no espaço de ação com saturação tanh é métrica de corrida delegada a COMPOSITE-BASE-2.

Segurança e Gates de Split:
- TRAIN: A {PIA,NOR,LEC,HAM,PER,RUS,GAS,ALO} + B {PIA,RUS,GAS,LEC,HAM,NOR,PER,ALO} = 48.000 amostras
- VALIDATION: A {SAI} + B {VER} = 6.000 amostras
- TEST (A {VER} + B {SAI} = 6.000) SELADO: QUALQUER leitura do bucket test é estritamente proibida
  e dispara exceção imediata SealedTestBucketViolationError (PARE).
- Checkpoint de candidato: artefato isolado sob experiments/composite-1/train-1/; colisão com produção proibida.
- Réplica obrigatória (Emenda O-3): Run 2 com mesmos parâmetros grava estritamente com sufixo _replica.
  Divergência |delta_val_loss| >= 1e-4 ou max|delta_W| >= 1e-5 aciona PARE imediato.
"""

from __future__ import annotations

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)


import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np

# Garante backend no sys.path para importações canônicas
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from model_train.residual_gated import build_residual_keras, export_residual_npz  # noqa: E402


# ---------------------------------------------------------------------------
# Constantes de Proveniência e Auditoria Congeladas
# ---------------------------------------------------------------------------

GIT_HEAD_BASELINE = "0972bdce8ba201f2bd6b73283ee4b420dcbc3756"

CORPUS_AUDIT_DATASET_SHAS = {
    "case_A_dataset_sha256": "5d29d1808695528c7a8bfc8e03cb335d95d5fab35ef16076b708dd3fca6b215b",
    "case_B_dataset_sha256": "2089d289c0f3b2adc01b0431c6af7bedb1a5522362101d4e9a39ab3ab3a593bc",
    "case_A_audit_file_sha256": "3631168758e5531b194352ff94004a9f90d8d6423fa7ace9a95a27d6d7586cf3",
    "case_B_audit_file_sha256": "e9066ab8bba40858c50b702b14135a9b277d990415fedf93a73c4136cc43c9e5",
}


# ---------------------------------------------------------------------------
# Exceções e Gates de Segurança
# ---------------------------------------------------------------------------

class SealedTestBucketViolationError(RuntimeError):
    """Disparado se qualquer arquivo, shard ou registro do split TEST for acessado."""
    pass


class OutputCollisionError(RuntimeError):
    """Disparado se o caminho de saída colidir com artefatos de produção."""
    pass


SEALED_TEST_SHARDS = frozenset({
    "A_A_ON_dump.jsonl_VER.json",
    "B_B_ON_dump.jsonl_SAI.json",
})

ALLOWED_SPLITS = frozenset({"train", "validation"})

SPLIT_MANIFEST: dict[str, dict[str, list[str]]] = {
    "A": {
        "train": ["PIA", "NOR", "LEC", "HAM", "PER", "RUS", "GAS", "ALO"],
        "validation": ["SAI"],
        "sealed_test": ["VER"],
    },
    "B": {
        "train": ["PIA", "RUS", "GAS", "LEC", "HAM", "NOR", "PER", "ALO"],
        "validation": ["VER"],
        "sealed_test": ["SAI"],
    },
}

FORBIDDEN_OUTPUT_SUBSTRINGS = (
    "v15_residual",
    "v10_dagger",
    "v14_dagger",
    "model_train/v15_residual",
    "residual_best_weights.npz",
    "residual_best.keras",
)


# ---------------------------------------------------------------------------
# Verificação de Colisão de Produção e Pré-existência
# ---------------------------------------------------------------------------

def check_output_path_safety(
    output_keras: Path | str,
    output_npz: Path | str,
    output_metrics: Path | str | None = None,
) -> None:
    """Valida se os caminhos de saída não colidem com produção nem usam nomes reservados."""
    paths_to_check = [Path(output_keras).resolve(), Path(output_npz).resolve()]
    if output_metrics:
        paths_to_check.append(Path(output_metrics).resolve())

    for p in paths_to_check:
        p_str = str(p)
        for forbidden in FORBIDDEN_OUTPUT_SUBSTRINGS:
            if forbidden in p_str:
                raise OutputCollisionError(
                    f"PARE: Caminho de saída '{p}' colide com caminho de produção proibido '{forbidden}'!"
                )
        if "experiments" not in p.parts:
            raise OutputCollisionError(
                f"PARE: Checkpoint '{p}' deve obrigatoriamente residir dentro do diretório experiments/."
            )


def check_no_existing_outputs(
    output_keras: Path | str,
    output_npz: Path | str,
    output_metrics: Path | str,
) -> None:
    """Garante que nenhum dos artefatos de saída já exista no início de um treino real (Emenda B.1 / O-3)."""
    for p in (Path(output_keras), Path(output_npz), Path(output_metrics)):
        if p.exists():
            raise FileExistsError(
                f"PARE: Artefato de saída já existe antes do início do treino: {p}. "
                f"Sobrescrita é estritamente proibida (emenda B.1 / O-3)."
            )


# ---------------------------------------------------------------------------
# Hashing e Proveniência
# ---------------------------------------------------------------------------

def compute_file_sha256(path: Path | str) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Arquivo para cálculo de SHA256 não encontrado: {p}")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def get_git_head_sha() -> str:
    """Obtém o hash SHA-256 do commit git HEAD."""
    try:
        res = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(BACKEND_ROOT))
        return res.decode().strip()
    except Exception:
        return GIT_HEAD_BASELINE


# ---------------------------------------------------------------------------
# Shard Loader Determinístico com Gate de Selamento
# ---------------------------------------------------------------------------

def get_shard_files_for_split(shards_dir: Path | str, split: str) -> list[Path]:
    """Retorna a lista ordenada e determinística de shards para o split solicitado.

    Se split == 'test' ou qualquer tentativa de acessar shards de teste ocorrer,
    dispara SealedTestBucketViolationError.
    """
    if split == "test":
        raise SealedTestBucketViolationError(
            "PARE: O bucket TEST (A VER + B SAI = 6.000) está SELADO. Leitura estritamente proibida!"
        )
    if split not in ALLOWED_SPLITS:
        raise ValueError(f"Split desconhecido '{split}'. Permitidos: {sorted(ALLOWED_SPLITS)}")

    shards_path = Path(shards_dir).resolve()
    if not shards_path.exists():
        raise FileNotFoundError(f"Diretório de shards não encontrado: {shards_path}")

    selected_shards: list[Path] = []
    for run_id in ("A", "B"):
        drivers = SPLIT_MANIFEST[run_id][split]
        for drv in drivers:
            filename = f"{run_id}_{run_id}_ON_dump.jsonl_{drv}.json"
            if filename in SEALED_TEST_SHARDS:
                raise SealedTestBucketViolationError(
                    f"PARE: Shard de teste selado '{filename}' detectado no split '{split}'!"
                )
            shard_file = shards_path / filename
            if not shard_file.exists():
                raise FileNotFoundError(f"Shard esperado não encontrado: {shard_file}")
            selected_shards.append(shard_file)

    # Ordenação determinística lexicográfica
    return sorted(selected_shards, key=lambda p: p.name)


def load_corpus_split(
    shards_dir: Path | str,
    split: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Carrega deterministamente um split do corpus garantindo gates de segurança.

    Retorna:
        X: matriz float32 [N, 16] (res_inputs)
        y: matriz float32 [N, 2] (r_targets)
        counts: dict com contagem total e quebra por caso (case_A, case_B)
    """
    shard_files = get_shard_files_for_split(shards_dir, split)

    all_x: list[list[float]] = []
    all_y: list[list[float]] = []
    case_counts = {"case_A": 0, "case_B": 0, "total": 0}

    for shard_file in shard_files:
        if shard_file.name in SEALED_TEST_SHARDS:
            raise SealedTestBucketViolationError(
                f"PARE: Tentativa de leitura de shard selado '{shard_file.name}'!"
            )

        case_key = "case_A" if shard_file.name.startswith("A_") else "case_B"

        with open(shard_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", [])
        for rec in records:
            rec_split = rec.get("split")
            if rec_split == "test":
                raise SealedTestBucketViolationError(
                    f"PARE: Registro com split 'test' encontrado no shard '{shard_file.name}'!"
                )
            if rec_split != split:
                raise ValueError(
                    f"Registro no shard '{shard_file.name}' tem split '{rec_split}' divergente de '{split}'"
                )

            res_in = rec.get("res_inputs")
            r_tgt = rec.get("r_targets")

            if not res_in or len(res_in) != 16:
                raise ValueError(f"res_inputs inválido (esperado 16 dims) no shard {shard_file.name}")
            if not r_tgt or len(r_tgt) != 2:
                raise ValueError(f"r_targets inválido (esperado 2 dims) no shard {shard_file.name}")

            # Verificação de finitude
            if not all(math.isfinite(v) for v in res_in):
                raise ValueError("Valor não finito encontrado em res_inputs")
            if not all(math.isfinite(v) for v in r_tgt):
                raise ValueError("Valor não finito encontrado em r_targets")

            all_x.append(res_in)
            all_y.append(r_tgt)
            case_counts[case_key] += 1
            case_counts["total"] += 1

    x_arr = np.asarray(all_x, dtype=np.float32).reshape(-1, 16)
    y_arr = np.asarray(all_y, dtype=np.float32).reshape(-1, 2)
    return x_arr, y_arr, case_counts


# ---------------------------------------------------------------------------
# Métricas e Critérios de Validação Offline (Emenda O-1 / O-4)
# ---------------------------------------------------------------------------

def compute_huber_loss(y_true: np.ndarray, y_pred: np.ndarray, delta: float = 1.0) -> float:
    """Calcula a perda Huber elemento a elemento."""
    err = np.abs(y_true - y_pred)
    quad = np.minimum(err, delta)
    lin = err - quad
    loss = 0.5 * (quad ** 2) + delta * lin
    return float(np.mean(loss))


def calculate_null_residual_huber_loss(y_val: np.ndarray, delta: float = 1.0) -> float:
    """Calcula a perda Huber da baseline nula (r = 0), espelhando o solo v10 isolado."""
    return compute_huber_loss(y_val, np.zeros_like(y_val), delta=delta)


def write_metrics_json(output_path: Path | str, metrics_data: dict[str, Any]) -> Path:
    """Grava o metrics JSON via json.dump com sort_keys=True, indent=2 (Emenda O-2)."""
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, sort_keys=True, indent=2)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"PARE: Falha crítica na escrita de {out} (arquivo inexistente ou vazio).")
    return out


# ---------------------------------------------------------------------------
# Treinamento do Modelo Residual (Huber Loss, Adam)
# ---------------------------------------------------------------------------

def train_residual_candidate(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    *,
    epochs: int = 50,
    lr: float = 1e-3,
    batch_size: int = 256,
    seed: int = 42,
    output_keras: Path | str | None = None,
    output_npz: Path | str | None = None,
    verbose: int = 0,
) -> dict[str, Any]:
    """Treina o modelo Keras residual espelhando o pipeline histórico de train_dagger.py.

    - Arquitetura: build_residual_keras(16) -> Dense(128, relu) -> Dense(128, relu) -> Dense(2, zeros)
    - Função de Perda: tf.keras.losses.Huber(delta=1.0)
    - Otimizador: tf.keras.optimizers.Adam(learning_rate=lr)
    - Early Stopping / Seleção: baseado no menor val_loss
    """
    import tensorflow as tf

    # Configuração determinística de sementes
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass

    if output_keras and output_npz:
        check_output_path_safety(output_keras, output_npz)

    model = build_residual_keras(n_in=16)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=lr),
        loss=tf.keras.losses.Huber(delta=1.0),
    )

    null_val_loss = calculate_null_residual_huber_loss(y_val, delta=1.0)

    # Callback para guardar os melhores pesos com base no val_loss
    class BestWeightTracker(tf.keras.callbacks.Callback):
        def __init__(self):
            super().__init__()
            self.best_val_loss = float("inf")
            self.best_weights = None
            self.best_epoch = 0

        def on_epoch_end(self, epoch, logs=None):
            logs = logs or {}
            val_loss = logs.get("val_loss", float("inf"))
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.best_weights = self.model.get_weights()
                self.best_epoch = epoch + 1

    tracker = BestWeightTracker()

    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[tracker],
        verbose=verbose,
    )

    # Restaura melhores pesos
    if tracker.best_weights is not None:
        model.set_weights(tracker.best_weights)

    # Predição offline no split de validação (sem gate, espaço residual)
    r_pred = model(X_val, training=False).numpy()

    final_train_loss = float(history.history["loss"][-1])
    best_val_loss = float(tracker.best_val_loss)
    huber_cand = compute_huber_loss(y_val, r_pred, delta=1.0)
    improvement_ratio = float(huber_cand / null_val_loss) if null_val_loss > 0 else 1.0

    # Critérios de validação offline ratificados (Emenda O-1 / O-4)
    # (b)1: Huber cand <= 0.80 * Huber null
    passes_huber = bool(huber_cand <= 0.80 * null_val_loss)

    # (b)2: MAE(r_cand, r_target) < MAE(zeros, r_target) no espaço residual
    mae_r1 = float(np.mean(np.abs(y_val - r_pred)))
    mae_zeros = float(np.mean(np.abs(y_val)))
    passes_mae = bool(mae_r1 < mae_zeros)

    # (b)3: Norma média <= 2.0 e zero NaN/Inf
    norms = np.linalg.norm(r_pred, axis=-1)
    mean_norm_r = float(np.mean(norms))
    passes_norm = bool(mean_norm_r <= 2.0)
    nan_inf_count = int(np.isnan(r_pred).sum() + np.isinf(r_pred).sum())
    passes_nan_inf = bool(nan_inf_count == 0)

    # Validação e exportação dos artefatos
    saved_keras_path = None
    saved_npz_path = None
    if output_keras:
        k_path = Path(output_keras).resolve()
        k_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(k_path))
        saved_keras_path = str(k_path)

    if output_npz:
        n_path = Path(output_npz).resolve()
        n_path.parent.mkdir(parents=True, exist_ok=True)
        export_residual_npz(model, n_path)
        saved_npz_path = str(n_path)

    return {
        "epochs_requested": epochs,
        "epochs_trained": len(history.history["loss"]),
        "best_epoch": tracker.best_epoch,
        "final_train_loss": final_train_loss,
        "best_val_loss": best_val_loss,
        "huber_cand": huber_cand,
        "huber_null": null_val_loss,
        "val_loss_improvement_ratio": improvement_ratio,
        "mae_r1": mae_r1,
        "mae_zeros": mae_zeros,
        "mean_norm_r": mean_norm_r,
        "nan_inf_count": nan_inf_count,
        "passes_huber_gate": passes_huber,
        "passes_mae_gate": passes_mae,
        "passes_norm_gate": passes_norm,
        "passes_nan_inf_gate": passes_nan_inf,
        "saved_keras_path": saved_keras_path,
        "saved_npz_path": saved_npz_path,
        "seed": seed,
    }


# ---------------------------------------------------------------------------
# Comparador de Réplica (Emenda O-3)
# ---------------------------------------------------------------------------

def compare_candidate_and_replica(
    candidate_npz_path: Path | str,
    replica_npz_path: Path | str,
    candidate_metrics_path: Path | str,
    replica_metrics_path: Path | str,
) -> dict[str, Any]:
    """Compara o candidato e a réplica com gates duros ratificados (Emenda O-3).

    Gates: |delta_val_loss| < 1e-4 E max|delta_W| < 1e-5.
    Se violado: PARE imediato, sem retry, sem escolher o melhor run.
    """
    cand_npz = np.load(str(candidate_npz_path))
    repl_npz = np.load(str(replica_npz_path))

    cand_keys = sorted(cand_npz.keys())
    repl_keys = sorted(repl_npz.keys())
    if cand_keys != repl_keys:
        raise RuntimeError(
            f"PARE: Chaves de pesos divergem entre candidato e réplica: {cand_keys} vs {repl_keys}"
        )

    max_diff_w = 0.0
    diffs_by_layer: dict[str, float] = {}
    for k in cand_keys:
        diff = float(np.max(np.abs(cand_npz[k] - repl_npz[k])))
        diffs_by_layer[k] = diff
        if diff > max_diff_w:
            max_diff_w = diff

    with open(candidate_metrics_path, "r", encoding="utf-8") as f:
        cand_met = json.load(f)
    with open(replica_metrics_path, "r", encoding="utf-8") as f:
        repl_met = json.load(f)

    val_loss_cand = float(cand_met["best_val_loss"])
    val_loss_repl = float(repl_met["best_val_loss"])
    delta_val_loss = abs(val_loss_cand - val_loss_repl)

    GATE_VAL_LOSS_LIMIT = 1e-4
    GATE_WEIGHT_LIMIT = 1e-5

    passes = (delta_val_loss < GATE_VAL_LOSS_LIMIT) and (max_diff_w < GATE_WEIGHT_LIMIT)
    res = {
        "delta_val_loss": delta_val_loss,
        "max_diff_w": max_diff_w,
        "diffs_by_layer": diffs_by_layer,
        "passes_gate": passes,
    }

    if not passes:
        raise RuntimeError(
            f"PARE: Gate de réplica violado! delta_val_loss={delta_val_loss:.6e} (limite {GATE_VAL_LOSS_LIMIT}), "
            f"max_diff_w={max_diff_w:.6e} (limite {GATE_WEIGHT_LIMIT}). Sem retry, sem escolher o melhor run."
        )

    return res


# ---------------------------------------------------------------------------
# CLI do Instrumento
# ---------------------------------------------------------------------------

def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Instrumento de Treino do Modelo Residual (COMPOSITE-TRAIN-1)",
    )
    parser.add_argument(
        "--shards-dir",
        type=Path,
        default=BACKEND_ROOT / "experiments" / "composite-1" / "shards",
        help="Diretório contendo os shards JSON do corpus.",
    )
    parser.add_argument(
        "--output-keras",
        type=Path,
        default=None,
        help="Caminho para o checkpoint .keras (default varia por --replica).",
    )
    parser.add_argument(
        "--output-npz",
        type=Path,
        default=None,
        help="Caminho para os pesos .npz (default varia por --replica).",
    )
    parser.add_argument(
        "--output-metrics",
        type=Path,
        default=None,
        help="Caminho para o arquivo de métricas JSON (default varia por --replica).",
    )
    parser.add_argument(
        "--replica",
        action="store_true",
        help="Executa como Run 2 (réplica obrigatória), gerando sufixo _replica.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Número de épocas de treinamento (default 50, espelha histórico).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Tamanho do lote (default 256, espelha histórico).",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Taxa de aprendizado Adam (default 1e-3, espelha histórico).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Semente pseudo-aleatória fixa (default 42).",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Modo de verificação com dados sintéticos reduzidos (sem ler 48k).",
    )
    parser.add_argument(
        "--execute-train",
        action="store_true",
        help="Flag obrigatória para disparar o treino real na etapa B (bloqueada na etapa A/A2 pre-freeze).",
    )
    return parser.parse_args(argv)


def resolve_output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    """Resolve caminhos de saída conforme o modo (candidato vs réplica)."""
    base_dir = BACKEND_ROOT / "experiments" / "composite-1" / "train-1"
    suffix = "_replica" if args.replica else ""
    keras_name = f"composite_residual_replica_1.keras" if args.replica else "composite_residual_candidato_1.keras"
    npz_name = f"composite_residual_replica_1_weights.npz" if args.replica else "composite_residual_candidato_1_weights.npz"
    metrics_name = f"composite_residual_replica_1_metrics.json" if args.replica else "composite_residual_candidato_1_metrics.json"

    k_path = args.output_keras or (base_dir / keras_name)
    n_path = args.output_npz or (base_dir / npz_name)
    m_path = args.output_metrics or (base_dir / metrics_name)

    return Path(k_path), Path(n_path), Path(m_path)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_keras, output_npz, output_metrics = resolve_output_paths(args)

    if args.fixture:
        print("[FIXTURE] Executando verificação em escala reduzida (dados sintéticos)...")
        rng = np.random.RandomState(args.seed)
        x_tr = rng.randn(32, 16).astype(np.float32)
        y_tr = rng.randn(32, 2).astype(np.float32)
        x_va = rng.randn(16, 16).astype(np.float32)
        y_va = rng.randn(16, 2).astype(np.float32)

        res = train_residual_candidate(
            x_tr, y_tr, x_va, y_va,
            epochs=2,
            batch_size=16,
            seed=args.seed,
            verbose=0,
        )
        print(f"[FIXTURE] Treino sintético concluído. val_loss={res['best_val_loss']:.4f}")
        return 0

    if not args.execute_train:
        print(
            "[PARE / PRE-FREEZE] COMPOSITE-TRAIN-1 etapa A2 está em pre-freeze.\n"
            "O treinamento do corpus completo (48.000 amostras) está BLOQUEADO até a ratificação do freeze pelo proprietário.\n"
            "Nenhum treino foi disparado. Utilize a suíte de testes focados para validar o instrumento."
        )
        return 0

    # Execução real (reservada para etapa B pós-freeze)
    # Valida caminhos de saída contra colisão e pré-existência (Emenda B.1 / O-3)
    check_output_path_safety(output_keras, output_npz, output_metrics)
    check_no_existing_outputs(output_keras, output_npz, output_metrics)

    print(f"[TRAIN] Carregando train split de {args.shards_dir}...")
    x_train, y_train, train_counts = load_corpus_split(args.shards_dir, "train")
    print(f"[TRAIN] Train carregado: shape {x_train.shape} (counts: {train_counts})")

    print(f"[TRAIN] Carregando validation split de {args.shards_dir}...")
    x_val, y_val, val_counts = load_corpus_split(args.shards_dir, "validation")
    print(f"[TRAIN] Validation carregado: shape {x_val.shape} (counts: {val_counts})")

    run_label = "Run 2 (replica)" if args.replica else "Run 1 (candidato)"
    print(f"[TRAIN] Disparando treinamento formal: {run_label} (seed={args.seed})...")

    metrics = train_residual_candidate(
        x_train,
        y_train,
        x_val,
        y_val,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        seed=args.seed,
        output_keras=output_keras,
        output_npz=output_npz,
        verbose=1,
    )

    # Verificação dura dos critérios de validação offline ratificados (Emenda O-1)
    if not metrics["passes_huber_gate"]:
        raise RuntimeError(
            f"PARE: Critério Huber violado! Huber(cand)={metrics['huber_cand']:.6f} > "
            f"0.80 * Huber(null)={0.80 * metrics['huber_null']:.6f}"
        )
    if not metrics["passes_mae_gate"]:
        raise RuntimeError(
            f"PARE: Critério MAE violado! MAE(R1)={metrics['mae_r1']:.6f} >= "
            f"MAE(zeros)={metrics['mae_zeros']:.6f}"
        )
    if not metrics["passes_norm_gate"]:
        raise RuntimeError(
            f"PARE: Critério de norma violado! mean_norm_r={metrics['mean_norm_r']:.6f} > 2.0"
        )
    if not metrics["passes_nan_inf_gate"]:
        raise RuntimeError(
            f"PARE: Valores NaN/Inf encontrados no split de validação!"
        )

    # Cálculo dos hashes de proveniência após exportação
    sha_keras = compute_file_sha256(output_keras)
    sha_npz = compute_file_sha256(output_npz)
    sha_script = compute_file_sha256(Path(__file__).resolve())
    sha_git_head = get_git_head_sha()

    # Construção do payload do metrics JSON (Emenda O-2)
    metrics_payload: dict[str, Any] = {
        "run": run_label,
        "is_replica": args.replica,
        "seeds": {
            "python": args.seed,
            "numpy": args.seed,
            "tensorflow": args.seed,
        },
        "hparams": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "loss": "Huber(delta=1.0)",
            "optimizer": "Adam",
        },
        "counts": {
            "train": {
                "total": train_counts["total"],
                "case_A": train_counts["case_A"],
                "case_B": train_counts["case_B"],
            },
            "validation": {
                "total": val_counts["total"],
                "case_A": val_counts["case_A"],
                "case_B": val_counts["case_B"],
            },
        },
        "huber_cand": metrics["huber_cand"],
        "huber_null": metrics["huber_null"],
        "val_loss_improvement_ratio": metrics["val_loss_improvement_ratio"],
        "mae_r1": metrics["mae_r1"],
        "mae_zeros": metrics["mae_zeros"],
        "mean_norm_r": metrics["mean_norm_r"],
        "nan_inf_count": metrics["nan_inf_count"],
        "best_epoch": metrics["best_epoch"],
        "best_val_loss": metrics["best_val_loss"],
        "sha256_keras": sha_keras,
        "sha256_npz": sha_npz,
        "sha256_script": sha_script,
        "sha256_git_head": sha_git_head,
        "corpus_audits": CORPUS_AUDIT_DATASET_SHAS,
    }

    # Gravação única via json.dump com ordenação de chaves (Emenda O-2)
    write_metrics_json(output_metrics, metrics_payload)
    print(f"[TRAIN] Métricas registradas em: {output_metrics}")
    print(f"[TRAIN] Concluído com sucesso: best_val_loss={metrics['best_val_loss']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
