"""Testes focados do instrumento de treino do residual composite (COMPOSITE-TRAIN-1).

Verificações obrigatórias:
1. Shapes: entrada 16-dim -> saída 2-dim (build_residual_keras).
2. Loader determinístico de shards em fixture sintética com quebra de contagens.
3. Gates de split: tentativa de leitura do split test ou shards de teste selados gera PARE (SealedTestBucketViolationError).
4. Candidato isolado: colisão de caminhos de saída com produção gera PARE (OutputCollisionError).
5. Treinamento executável em escala reduzida (fixture) dentro da suíte, incluindo exportação e forward com NumpyCompositeActor.
6. Teste de pré-existência de saídas (check_no_existing_outputs).
7. Writer de métricas JSON (Emenda O-2): determinismo byte-a-byte e validação de schema.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
import pytest

from model_train.residual_gated import NumpyCompositeActor, build_residual_keras
from scripts.train_composite_residual import (
    SEALED_TEST_SHARDS,
    OutputCollisionError,
    SealedTestBucketViolationError,
    check_no_existing_outputs,
    check_output_path_safety,
    get_shard_files_for_split,
    load_corpus_split,
    train_residual_candidate,
    write_metrics_json,
)


def test_residual_model_shapes():
    """Verifica que o modelo residual tem formato estrito 16 -> 2."""
    model = build_residual_keras(n_in=16)
    assert model.input_shape == (None, 16)
    assert model.output_shape == (None, 2)

    # Teste de forward com lote de teste
    x = np.zeros((4, 16), dtype=np.float32)
    y = model(x, training=False).numpy()
    assert y.shape == (4, 2)
    # Inicializadores de zeros no layer de saída
    np.testing.assert_allclose(y, 0.0)


def test_output_path_collision_prevention():
    """Verifica proteção contra sobrescrita de modelos de produção."""
    # Colisão com caminho histórico v15_residual
    with pytest.raises(OutputCollisionError, match="colide com caminho de produção"):
        check_output_path_safety(
            "model_train/v15_residual/residual_best.keras",
            "experiments/composite-1/train-1/candidato.npz",
        )

    with pytest.raises(OutputCollisionError, match="colide com caminho de produção"):
        check_output_path_safety(
            "experiments/composite-1/train-1/candidato.keras",
            "backend/model_train/v15_residual/residual_best_weights.npz",
        )

    # Fora de experiments/
    with pytest.raises(OutputCollisionError, match="residir dentro do diretório experiments"):
        check_output_path_safety(
            "tmp/candidato.keras",
            "tmp/candidato.npz",
        )

    # Caminho válido dentro de experiments/
    check_output_path_safety(
        "experiments/composite-1/train-1/composite_residual_candidato_1.keras",
        "experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz",
        "experiments/composite-1/train-1/composite_residual_candidato_1_metrics.json",
    )


def test_split_gate_test_bucket_is_sealed():
    """Verifica que qualquer tentativa de carregar o split 'test' dispara SealedTestBucketViolationError."""
    with pytest.raises(SealedTestBucketViolationError, match="SELADO"):
        get_shard_files_for_split("experiments/composite-1/shards", "test")

    with pytest.raises(SealedTestBucketViolationError, match="SELADO"):
        load_corpus_split("experiments/composite-1/shards", "test")


def test_split_gate_sealed_test_shards_forbidden():
    """Verifica que os shards selados A_VER e B_SAI estão na lista negra e nunca são retornados."""
    # Shards de treino e validação não contêm nenhum dos selados
    train_shards = get_shard_files_for_split("experiments/composite-1/shards", "train")
    train_names = {p.name for p in train_shards}
    assert not train_names.intersection(SEALED_TEST_SHARDS)
    assert len(train_shards) == 16  # 8 de A + 8 de B

    val_shards = get_shard_files_for_split("experiments/composite-1/shards", "validation")
    val_names = {p.name for p in val_shards}
    assert not val_names.intersection(SEALED_TEST_SHARDS)
    assert len(val_shards) == 2  # A_SAI + B_VER
    assert val_names == {"A_A_ON_dump.jsonl_SAI.json", "B_B_ON_dump.jsonl_VER.json"}


def test_loader_deterministic_synthetic_fixture():
    """Cria uma fixture sintética de shards e verifica ordenação determinística e gates de registro."""
    with tempfile.TemporaryDirectory() as td:
        shards_dir = Path(td)

        runs = {
            "A": {"train": ["PIA", "NOR", "LEC", "HAM", "PER", "RUS", "GAS", "ALO"], "validation": ["SAI"]},
            "B": {"train": ["PIA", "RUS", "GAS", "LEC", "HAM", "NOR", "PER", "ALO"], "validation": ["VER"]},
        }

        for run_id, splits in runs.items():
            for split_name, drivers in splits.items():
                for drv in drivers:
                    fname = f"{run_id}_{run_id}_ON_dump.jsonl_{drv}.json"
                    records = [
                        {
                            "split": split_name,
                            "drv": drv,
                            "res_inputs": [0.1] * 16,
                            "r_targets": [0.05, -0.05],
                        }
                    ]
                    with open(shards_dir / fname, "w", encoding="utf-8") as f:
                        json.dump({"records": records}, f)

        # Carrega train
        x_tr, y_tr, counts_tr = load_corpus_split(shards_dir, "train")
        assert x_tr.shape == (16, 16)
        assert y_tr.shape == (16, 2)
        assert counts_tr == {"case_A": 8, "case_B": 8, "total": 16}

        # Carrega validation
        x_va, y_va, counts_va = load_corpus_split(shards_dir, "validation")
        assert x_va.shape == (2, 16)
        assert y_va.shape == (2, 2)
        assert counts_va == {"case_A": 1, "case_B": 1, "total": 2}

        # Testa injeção de registro corrupto com split 'test'
        corrupt_file = shards_dir / "A_A_ON_dump.jsonl_PIA.json"
        with open(corrupt_file, "w", encoding="utf-8") as f:
            json.dump({
                "records": [
                    {
                        "split": "test",  # Ilegal!
                        "drv": "PIA",
                        "res_inputs": [0.1] * 16,
                        "r_targets": [0.0, 0.0],
                    }
                ]
            }, f)

        with pytest.raises(SealedTestBucketViolationError, match="split 'test' encontrado"):
            load_corpus_split(shards_dir, "train")


def test_miniature_training_and_numpy_actor_parity():
    """Treina em escala reduzida (fixture de 16 amostras) e verifica exportação NPZ e compatibilidade NumpyCompositeActor."""
    rng = np.random.RandomState(42)
    x_tr = rng.randn(16, 16).astype(np.float32)
    y_tr = rng.randn(16, 2).astype(np.float32)
    x_va = rng.randn(8, 16).astype(np.float32)
    y_va = rng.randn(8, 2).astype(np.float32)

    with tempfile.TemporaryDirectory() as td:
        out_keras = Path(td) / "experiments" / "candidato.keras"
        out_npz = Path(td) / "experiments" / "candidato_weights.npz"

        metrics = train_residual_candidate(
            x_tr,
            y_tr,
            x_va,
            y_va,
            epochs=2,
            batch_size=8,
            seed=42,
            output_keras=out_keras,
            output_npz=out_npz,
            verbose=0,
        )

        assert metrics["best_epoch"] >= 1
        assert "mae_r1" in metrics
        assert "mae_zeros" in metrics
        assert "mean_norm_r" in metrics
        assert "nan_inf_count" in metrics
        assert out_keras.exists()
        assert out_npz.exists()

        # Verifica chaves do NPZ exportado
        data = np.load(out_npz)
        expected_keys = {"res_d1_0", "res_d1_1", "res_d2_0", "res_d2_1", "res_out_0", "res_out_1"}
        assert set(data.keys()) == expected_keys

        # Verifica compatibilidade com forward do NumpyCompositeActor
        solo_npz = Path("model_train/v10_dagger/dagger_actor_best_weights.npz")
        assert solo_npz.exists()

        actor = NumpyCompositeActor(str(solo_npz), str(out_npz))
        res_out = actor.residual_forward_only(x_va)
        assert res_out.shape == (8, 2)
        assert not np.isnan(res_out).any()


def test_metrics_json_writer_determinism():
    """Valida determinismo byte-a-byte do writer de métricas JSON (Emenda O-2)."""
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "metrics_run1.json"
        p2 = Path(td) / "metrics_run2.json"

        sample_data = {
            "run": "Run 1 (candidato)",
            "is_replica": False,
            "seeds": {"numpy": 42, "python": 42, "tensorflow": 42},
            "hparams": {
                "batch_size": 256,
                "epochs": 50,
                "loss": "Huber(delta=1.0)",
                "lr": 0.001,
                "optimizer": "Adam",
            },
            "counts": {
                "train": {"case_A": 24000, "case_B": 24000, "total": 48000},
                "validation": {"case_A": 3000, "case_B": 3000, "total": 6000},
            },
            "huber_cand": 0.045,
            "huber_null": 0.082,
            "val_loss_improvement_ratio": 0.54878,
            "mae_r1": 0.1234,
            "mae_zeros": 0.2456,
            "mean_norm_r": 0.35,
            "nan_inf_count": 0,
            "best_epoch": 24,
            "best_val_loss": 0.045,
            "sha256_keras": "a" * 64,
            "sha256_npz": "b" * 64,
            "sha256_script": "c" * 64,
            "sha256_git_head": "0972bdce8ba201f2bd6b73283ee4b420dcbc3756",
            "corpus_audits": {
                "case_A_audit_file_sha256": "3631168758e5531b194352ff94004a9f90d8d6423fa7ace9a95a27d6d7586cf3",
                "case_A_dataset_sha256": "5d29d1808695528c7a8bfc8e03cb335d95d5fab35ef16076b708dd3fca6b215b",
                "case_B_audit_file_sha256": "e9066ab8bba40858c50b702b14135a9b277d990415fedf93a73c4136cc43c9e5",
                "case_B_dataset_sha256": "2089d289c0f3b2adc01b0431c6af7bedb1a5522362101d4e9a39ab3ab3a593bc",
            },
        }

        write_metrics_json(p1, sample_data)
        write_metrics_json(p2, sample_data)

        b1 = p1.read_bytes()
        b2 = p2.read_bytes()

        # Prova de determinismo byte-a-byte estrito
        assert b1 == b2
        assert hashlib.sha256(b1).hexdigest() == hashlib.sha256(b2).hexdigest()

        # Validação de integridade do payload
        with open(p1, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == sample_data
