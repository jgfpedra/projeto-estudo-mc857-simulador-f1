"""Testes focados do instrumento de avaliação do bucket TEST (ESTÁGIO 5 — RELEASE).

Verificações obrigatórias (espelho do TRAIN-1, INVERTIDO):
1. Gate inverso: recusa qualquer shard não pertencente à whitelist estrita do split TEST
   (shards de treino, shards de validação ou arquivos arbitrários).
2. Recusa de candidato com hash divergente, arquivo inexistente ou arquitetura incompatível.
3. Proteção de caminhos: recusa de colisão com produção/treino e recusa de sobrescrita (FileExistsError com modo 'x').
4. Ordenação determinística dos registros de teste e inferência forward em NumPy puro.
5. Execução ponta-a-ponta em fixture sintética produzindo JSON com todas as chaves requeridas.
6. Determinismo byte-a-byte estrito do writer JSON entre múltiplas invocações.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

import numpy as np
import pytest

from scripts.eval_composite_residual_test import (
    ALLOWED_TEST_SHARDS,
    CANDIDATE_WEIGHTS_ETALON_SHA256,
    DEFAULT_CANDIDATE_PATH,
    CandidateWeightsIntegrityError,
    OutputCollisionError,
    SealedTestWhitelistViolationError,
    check_output_path_safety,
    compute_file_sha256,
    compute_huber_loss,
    compute_test_metrics,
    evaluate_test_bucket,
    forward_residual,
    get_test_shard_files,
    load_candidate_weights,
    load_test_split,
    write_release_verdict_json,
)


def test_eval_inverse_gate_and_safety_checks():
    """Valida o gate inverso de shards, proteção do candidato e integridade de caminhos."""
    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)

        # -------------------------------------------------------------------
        # 1. Gate Inverso: recusa de shards que não pertencem ao split TEST
        # -------------------------------------------------------------------
        invalid_shards = [
            tmp_dir / "A_A_ON_dump.jsonl_PIA.json",  # Shard de treino
            tmp_dir / "A_A_ON_dump.jsonl_SAI.json",  # Shard de validação
            tmp_dir / "B_B_ON_dump.jsonl_VER.json",  # Shard de validação
            tmp_dir / "random_file.json",
        ]
        for inv_shard in invalid_shards:
            with open(inv_shard, "w", encoding="utf-8") as f:
                json.dump({"records": []}, f)

        # get_test_shard_files com arquivos explícitos fora da whitelist deve falhar
        for inv_shard in invalid_shards:
            with pytest.raises(SealedTestWhitelistViolationError, match="Gate Inverso"):
                get_test_shard_files(tmp_dir, explicit_files=[inv_shard])

        # load_test_split com arquivos explícitos fora da whitelist deve falhar
        for inv_shard in invalid_shards:
            with pytest.raises(SealedTestWhitelistViolationError, match="Gate Inverso"):
                load_test_split(tmp_dir, explicit_files=[inv_shard])

        # Shard de teste legítimo na nomenclatura, mas contendo registro com split 'train'
        corrupt_test_shard = tmp_dir / "A_A_ON_dump.jsonl_VER.json"
        with open(corrupt_test_shard, "w", encoding="utf-8") as f:
            json.dump({
                "records": [
                    {
                        "split": "train",  # Ilegal em shard de teste!
                        "drv": "VER",
                        "res_inputs": [0.1] * 16,
                        "r_targets": [0.0, 0.0],
                    }
                ]
            }, f)

        with pytest.raises(ValueError, match="split 'train' encontrado"):
            load_test_split(tmp_dir, explicit_files=[corrupt_test_shard], expected_records_per_shard=None)

        # -------------------------------------------------------------------
        # 2. Recusa de candidato errado ou inexistente
        # -------------------------------------------------------------------
        non_existent = tmp_dir / "non_existent.npz"
        with pytest.raises(CandidateWeightsIntegrityError, match="não encontrado"):
            load_candidate_weights(non_existent)

        # Candidato sintético com hash divergente do etalão
        fake_candidate = tmp_dir / "fake_cand.npz"
        np.savez(
            str(fake_candidate),
            res_d1_0=np.zeros((16, 128), dtype=np.float32),
            res_d1_1=np.zeros((128,), dtype=np.float32),
            res_d2_0=np.zeros((128, 128), dtype=np.float32),
            res_d2_1=np.zeros((128,), dtype=np.float32),
            res_out_0=np.zeros((128, 2), dtype=np.float32),
            res_out_1=np.zeros((2,), dtype=np.float32),
        )

        with pytest.raises(CandidateWeightsIntegrityError, match="diverge do etalão"):
            load_candidate_weights(fake_candidate, enforce_etalon_sha=True)

        # Candidato com chaves/formatos incorretos (mesmo sem checar SHA)
        bad_format_cand = tmp_dir / "bad_format.npz"
        np.savez(str(bad_format_cand), invalid_key=np.zeros((10,), dtype=np.float32))
        with pytest.raises(ValueError, match="possui 1 chaves"):
            load_candidate_weights(bad_format_cand, enforce_etalon_sha=False)

        # Validação do candidato oficial etalonado existente (se disponível no repo)
        real_cand_path = Path(DEFAULT_CANDIDATE_PATH)
        if real_cand_path.exists():
            w_real, sha_real = load_candidate_weights(real_cand_path, enforce_etalon_sha=True)
            assert sha_real == CANDIDATE_WEIGHTS_ETALON_SHA256
            assert len(w_real) == 6

        # -------------------------------------------------------------------
        # 3. Proteção de Caminhos de Saída e Prevenção de Sobrescrita
        # -------------------------------------------------------------------
        with pytest.raises(OutputCollisionError, match="colide com diretório/nome de produção"):
            check_output_path_safety("backend/model_train/v15_residual/verdict.json")

        with pytest.raises(OutputCollisionError, match="colide com diretório/nome de produção"):
            check_output_path_safety("experiments/composite-1/train-1/verdict.json")

        with pytest.raises(OutputCollisionError, match="residir dentro do diretório experiments"):
            check_output_path_safety("tmp/verdict.json")

        # Caminho válido dentro de experiments/
        valid_out = tmp_dir / "experiments" / "composite-1" / "verdict.json"
        check_output_path_safety(valid_out)

        # Prevenção de sobrescrita: modo 'x' deve levantar FileExistsError
        valid_out.parent.mkdir(parents=True, exist_ok=True)
        valid_out.write_text("existing content", encoding="utf-8")
        with pytest.raises(FileExistsError, match="já existe"):
            write_release_verdict_json(valid_out, {"dummy": 123})


def test_eval_e2e_synthetic_and_determinism():
    """Valida execução ponta-a-ponta em fixture sintética e determinismo estrito do writer."""
    with tempfile.TemporaryDirectory() as td:
        root_dir = Path(td)
        shards_dir = root_dir / "shards"
        shards_dir.mkdir(parents=True, exist_ok=True)

        exp_dir = root_dir / "experiments" / "composite-1"
        exp_dir.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------------------------
        # 1. Criação de fixture sintética do candidato residual
        # -------------------------------------------------------------------
        cand_npz_path = exp_dir / "test_candidate.npz"
        rng = np.random.RandomState(42)

        w_d1 = (rng.randn(16, 128) * 0.05).astype(np.float32)
        b_d1 = np.zeros((128,), dtype=np.float32)
        w_d2 = (rng.randn(128, 128) * 0.05).astype(np.float32)
        b_d2 = np.zeros((128,), dtype=np.float32)
        w_out = (rng.randn(128, 2) * 0.05).astype(np.float32)
        b_out = np.zeros((2,), dtype=np.float32)

        np.savez(
            str(cand_npz_path),
            res_d1_0=w_d1,
            res_d1_1=b_d1,
            res_d2_0=w_d2,
            res_d2_1=b_d2,
            res_out_0=w_out,
            res_out_1=b_out,
        )

        # -------------------------------------------------------------------
        # 2. Criação de fixture sintética dos dois shards TEST (A_VER e B_SAI)
        # -------------------------------------------------------------------
        n_samples_per_shard = 20
        for shard_name, drv in (("A_A_ON_dump.jsonl_VER.json", "VER"), ("B_B_ON_dump.jsonl_SAI.json", "SAI")):
            records = []
            for i in range(n_samples_per_shard):
                # Features sintéticas realistas
                res_in = [float(0.1 * (k + 1) * (1 if i % 2 == 0 else -1)) for k in range(16)]
                # Targets com magnitude moderada
                r_tgt = [float(0.05 * (i % 5)), float(-0.02 * (i % 3))]
                records.append({
                    "split": "test",
                    "drv": drv,
                    "tick": i,
                    "res_inputs": res_in,
                    "r_targets": r_tgt,
                })

            with open(shards_dir / shard_name, "w", encoding="utf-8") as f:
                json.dump({"records": records}, f)

        # -------------------------------------------------------------------
        # 3. Execução Ponta-a-Ponta
        # -------------------------------------------------------------------
        out_json_1 = exp_dir / "STAGE5_RELEASE_VERDICT_run1.json"
        out_json_2 = exp_dir / "STAGE5_RELEASE_VERDICT_run2.json"

        result_1 = evaluate_test_bucket(
            candidate_path=cand_npz_path,
            shards_dir=shards_dir,
            output_path=out_json_1,
            enforce_etalon_sha=False,
            expected_records_per_shard=n_samples_per_shard,
        )

        result_2 = evaluate_test_bucket(
            candidate_path=cand_npz_path,
            shards_dir=shards_dir,
            output_path=out_json_2,
            enforce_etalon_sha=False,
            expected_records_per_shard=n_samples_per_shard,
        )

        # -------------------------------------------------------------------
        # 4. Validação de Estrutura e Chaves Requeridas
        # -------------------------------------------------------------------
        assert result_1["run"] == "STAGE 5 RELEASE EVALUATION"
        assert result_1["counts"] == {
            "case_A_test": n_samples_per_shard,
            "case_B_test": n_samples_per_shard,
            "total_test": 2 * n_samples_per_shard,
        }

        # Chaves de métricas
        metrics = result_1["metrics"]
        for key in ("huber_cand", "huber_null", "huber_ratio", "mae_cand", "mae_null", "mean_norm_r", "nan_inf_count"):
            assert key in metrics
            assert isinstance(metrics[key], (float, int))

        assert metrics["nan_inf_count"] == 0

        # Chaves de gates
        gates = result_1["gates"]
        for g_name in ("gate_1_huber", "gate_2_mae", "gate_3_norm", "gate_4_nan_inf", "gate_5_determinism"):
            assert g_name in gates
            assert "passed" in gates[g_name]

        assert "all_gates_pass" in gates
        assert gates["verdict"] in ("SANCIONADO", "NAO_LIBERADO")

        # Chaves de proveniência
        prov = result_1["provenance"]
        assert "git_head_sha" in prov
        assert "script_sha256" in prov
        assert prov["shard_A_test_file"] == "A_A_ON_dump.jsonl_VER.json"
        assert prov["shard_B_test_file"] == "B_B_ON_dump.jsonl_SAI.json"
        assert len(prov["shard_A_test_sha256"]) == 64
        assert len(prov["shard_B_test_sha256"]) == 64

        # -------------------------------------------------------------------
        # 5. Determinismo Byte-a-Byte Estrito
        # -------------------------------------------------------------------
        b1 = out_json_1.read_bytes()
        b2 = out_json_2.read_bytes()

        assert b1 == b2, "Os bytes dos JSONs gerados em duas invocações devem ser idênticos bit-a-bit!"
        assert hashlib.sha256(b1).hexdigest() == hashlib.sha256(b2).hexdigest()

        # Determinismo do writer com mesmo dicionário
        w1 = write_release_verdict_json(None, result_1)
        w2 = write_release_verdict_json(None, result_1)
        assert w1 == w2
        assert w1 == b1.decode("utf-8")
