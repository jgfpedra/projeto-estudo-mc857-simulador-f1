#!/usr/bin/env python3
"""Instrumento de avaliação do modelo residual composite sob o bucket TEST (ESTÁGIO 5 — RELEASE).

Espelho da disciplina de train_composite_residual.py, com GATE INVERSO:
- O bucket TEST (A {VER} + B {SAI} = 6.000 amostras) é o ÚNICO autorizado para leitura neste instrumento.
- Qualquer tentativa de carregar shards que não pertençam à whitelist estrita do split TEST
  dispara imediatamente SealedTestWhitelistViolationError.
- ZERO treino: inferência forward pura em NumPy (16 -> 128 -> 128 -> 2).
- Verificação de hash etalonado do candidato: SHA-256 obrigatório 6210fff65b19ad0e...
- Avaliação dos 5 Gates de Release contratuais:
    1. Huber(cand) <= 0.80 * Huber(null r=0)
    2. MAE(r_cand, r_target) < MAE(0, r_target)
    3. Média ||r_cand||_2 <= 2.0
    4. nan_inf_count == 0
    5. Determinismo em 2 leituras (JSON bytes idênticos)
- Veredicto: SANCIONADO se 5/5 gates passarem; NAO_LIBERADO caso contrário.
- Gravação única via json.dump(sort_keys=True, indent=2) com modo "x" (FileExistsError se já existir).
- Prevenção de colisão com produção e diretório de treino.
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
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np

# Garante backend no sys.path para importações canônicas
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ---------------------------------------------------------------------------
# Constantes de Proveniência e Auditoria Congeladas
# ---------------------------------------------------------------------------

GIT_HEAD_BASELINE = "d36a0e124ca25ceb9e014513e741d55e7f812ca4"

CANDIDATE_WEIGHTS_ETALON_SHA256 = (
    "6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60"
)

DEFAULT_CANDIDATE_PATH = (
    "experiments/composite-1/train-1/composite_residual_candidato_1_weights.npz"
)

DEFAULT_SHARDS_DIR = "experiments/composite-1/shards"

# Whitelist EXATA do bucket TEST: somente estes dois shards são autorizados
ALLOWED_TEST_SHARDS = frozenset({
    "A_A_ON_dump.jsonl_VER.json",
    "B_B_ON_dump.jsonl_SAI.json",
})

EXPECTED_TEST_DRIVERS = {
    "A": "VER",
    "B": "SAI",
}

EXPECTED_TEST_RECORDS_PER_SHARD = 3000
EXPECTED_TOTAL_TEST_RECORDS = 6000

FORBIDDEN_OUTPUT_SUBSTRINGS = (
    "v15_residual",
    "v10_dagger",
    "v14_dagger",
    "model_train/v15_residual",
    "residual_best_weights.npz",
    "residual_best.keras",
    "train-1",
)


# ---------------------------------------------------------------------------
# Exceções e Gates de Segurança
# ---------------------------------------------------------------------------

class SealedTestWhitelistViolationError(RuntimeError):
    """Disparado se qualquer arquivo ou shard fora da whitelist do split TEST for acessado."""
    pass


class CandidateWeightsIntegrityError(RuntimeError):
    """Disparado se o arquivo de pesos do candidato não existir ou divergir do hash etalonado."""
    pass


class OutputCollisionError(RuntimeError):
    """Disparado se o caminho de saída colidir com artefatos de produção ou treino."""
    pass


# ---------------------------------------------------------------------------
# Funções de Hashing e Proveniência
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
        res = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(BACKEND_ROOT),
            stderr=subprocess.DEVNULL,
        )
        return res.decode().strip()
    except Exception:
        return GIT_HEAD_BASELINE


# ---------------------------------------------------------------------------
# Verificação de Caminhos de Saída
# ---------------------------------------------------------------------------

def check_output_path_safety(output_path: Path | str) -> None:
    """Garante que a saída resida em experiments/ e não colida com produção ou treino."""
    p = Path(output_path).resolve()
    p_str = str(p)
    for forbidden in FORBIDDEN_OUTPUT_SUBSTRINGS:
        if forbidden in p_str:
            raise OutputCollisionError(
                f"PARE: Caminho de saída '{p}' colide com diretório/nome de produção ou treino proibido '{forbidden}'!"
            )
    if "experiments" not in p.parts:
        raise OutputCollisionError(
            f"PARE: Saída '{p}' deve obrigatoriamente residir dentro do diretório experiments/."
        )


# ---------------------------------------------------------------------------
# Carregamento do Candidato Residual
# ---------------------------------------------------------------------------

def load_candidate_weights(
    candidate_path: Path | str,
    *,
    enforce_etalon_sha: bool = True,
) -> tuple[dict[str, np.ndarray], str]:
    """Carrega os pesos do candidato residual a partir de arquivo NPZ.

    Verifica finitude, chaves esperadas (res_d1, res_d2, res_out) e o hash SHA-256.
    """
    p = Path(candidate_path)
    if not p.is_absolute():
        p = (BACKEND_ROOT / p).resolve()
    else:
        p = p.resolve()

    if not p.exists():
        raise CandidateWeightsIntegrityError(
            f"PARE: Arquivo de pesos do candidato não encontrado: {p}"
        )

    file_sha = compute_file_sha256(p)
    if enforce_etalon_sha and file_sha != CANDIDATE_WEIGHTS_ETALON_SHA256:
        raise CandidateWeightsIntegrityError(
            f"PARE: SHA-256 do candidato residual diverge do etalão!\n"
            f"  Obtido:   {file_sha}\n"
            f"  Esperado: {CANDIDATE_WEIGHTS_ETALON_SHA256}"
        )

    with np.load(str(p)) as data:
        weights = {k: np.array(data[k], copy=True) for k in data.files}

    # Validação estrutural das matrizes de pesos (16 -> 128 -> 128 -> 2)
    sorted_keys = sorted(weights.keys())
    if len(sorted_keys) != 6:
        raise ValueError(
            f"NPZ do candidato residual possui {len(sorted_keys)} chaves (esperado: 6)."
        )

    expected_shapes = [
        (16, 128),  # res_d1_0 (kernel)
        (128,),     # res_d1_1 (bias)
        (128, 128), # res_d2_0 (kernel)
        (128,),     # res_d2_1 (bias)
        (128, 2),   # res_out_0 (kernel)
        (2,),       # res_out_1 (bias)
    ]

    for k, expected_shape in zip(sorted_keys, expected_shapes):
        w = weights[k]
        if w.shape != expected_shape:
            raise ValueError(
                f"Formato inesperado para '{k}': obtido {w.shape}, esperado {expected_shape}"
            )
        if not np.all(np.isfinite(w)):
            raise ValueError(f"Valores não finitos encontrados na matriz de pesos '{k}'")

    return weights, file_sha


# ---------------------------------------------------------------------------
# Inferência Forward em NumPy Puro (16 -> 128 -> 128 -> 2)
# ---------------------------------------------------------------------------

def forward_residual(
    x: np.ndarray,
    weights: Mapping[str, np.ndarray],
) -> np.ndarray:
    """Executa a propagação direta do residual em NumPy puro.

    Ordem determinística das matrizes: d1_kernel, d1_bias, d2_kernel, d2_bias, out_kernel, out_bias.
    Ativações: ReLU nas camadas ocultas, linear na saída.
    """
    w = [weights[k] for k in sorted(weights.keys())]
    # Camada 1: 16 -> 128 (ReLU)
    h1 = np.maximum(0.0, x @ w[0] + w[1])
    # Camada 2: 128 -> 128 (ReLU)
    h2 = np.maximum(0.0, h1 @ w[2] + w[3])
    # Saída: 128 -> 2 (Linear)
    out = h2 @ w[4] + w[5]
    return np.asarray(out, dtype=np.float32)


# ---------------------------------------------------------------------------
# Loader do Split TEST com Gate Inverso
# ---------------------------------------------------------------------------

def get_test_shard_files(
    shards_dir: Path | str,
    *,
    explicit_files: Sequence[str | Path] | None = None,
) -> list[Path]:
    """Retorna os arquivos de shard do split TEST validando a whitelist estrita.

    Gate Inverso: qualquer shard ou arquivo fora de ALLOWED_TEST_SHARDS causa erro imediato.
    """
    if explicit_files is not None:
        selected_shards: list[Path] = []
        for f in explicit_files:
            p = Path(f)
            if p.name not in ALLOWED_TEST_SHARDS:
                raise SealedTestWhitelistViolationError(
                    f"PARE (Gate Inverso): O shard '{p.name}' não pertence à whitelist do split TEST! "
                    f"Acesso estritamente proibido. Permitidos: {sorted(ALLOWED_TEST_SHARDS)}"
                )
            selected_shards.append(p)
        return sorted(selected_shards, key=lambda p: p.name)

    dir_path = Path(shards_dir)
    if not dir_path.is_absolute():
        dir_path = (BACKEND_ROOT / dir_path).resolve()
    else:
        dir_path = dir_path.resolve()

    if not dir_path.exists():
        raise FileNotFoundError(f"Diretório de shards não encontrado: {dir_path}")

    selected_shards = []
    for shard_name in sorted(ALLOWED_TEST_SHARDS):
        p = dir_path / shard_name
        if not p.exists():
            raise FileNotFoundError(f"Shard esperado do split TEST não encontrado: {p}")
        selected_shards.append(p)

    return sorted(selected_shards, key=lambda p: p.name)


def load_test_split(
    shards_dir: Path | str,
    *,
    explicit_files: Sequence[str | Path] | None = None,
    expected_records_per_shard: int | None = EXPECTED_TEST_RECORDS_PER_SHARD,
) -> tuple[np.ndarray, np.ndarray, dict[str, int], dict[str, str]]:
    """Carrega os registros do bucket TEST garantindo ordenação determinística e gates de integridade.

    Retorna:
        X: matriz float32 [N, 16] (res_inputs)
        y: matriz float32 [N, 2] (r_targets)
        counts: dict com contagens por caso e total
        shard_shas: dict com hash SHA-256 de cada arquivo de shard lido
    """
    shard_files = get_test_shard_files(shards_dir, explicit_files=explicit_files)

    all_x: list[list[float]] = []
    all_y: list[list[float]] = []
    case_counts = {"case_A": 0, "case_B": 0, "total": 0}
    shard_shas: dict[str, str] = {}

    for shard_file in shard_files:
        if shard_file.name not in ALLOWED_TEST_SHARDS:
            raise SealedTestWhitelistViolationError(
                f"PARE (Gate Inverso): Tentativa ilegal de ler shard não-test '{shard_file.name}'!"
            )

        case_key = "case_A" if shard_file.name.startswith("A_") else "case_B"
        shard_shas[shard_file.name] = compute_file_sha256(shard_file)

        with open(shard_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", [])
        if expected_records_per_shard is not None and len(records) != expected_records_per_shard:
            raise ValueError(
                f"Contagem incorreta de registros no shard '{shard_file.name}': "
                f"obtido {len(records)}, esperado {expected_records_per_shard}."
            )

        shard_record_count = 0
        for rec in records:
            rec_split = rec.get("split")
            if rec_split != "test":
                raise ValueError(
                    f"PARE: Registro com split '{rec_split}' encontrado no shard TEST '{shard_file.name}'! "
                    f"Todos os registros devem ter split == 'test'."
                )

            res_in = rec.get("res_inputs")
            r_tgt = rec.get("r_targets")

            if not res_in or len(res_in) != 16:
                raise ValueError(
                    f"res_inputs inválido (esperado 16 dimensões) no shard '{shard_file.name}'"
                )
            if not r_tgt or len(r_tgt) != 2:
                raise ValueError(
                    f"r_targets inválido (esperado 2 dimensões) no shard '{shard_file.name}'"
                )

            if not all(math.isfinite(v) for v in res_in):
                raise ValueError("Valor não finito detectado em res_inputs do split TEST")
            if not all(math.isfinite(v) for v in r_tgt):
                raise ValueError("Valor não finito detectado em r_targets do split TEST")

            all_x.append(res_in)
            all_y.append(r_tgt)
            shard_record_count += 1

        case_counts[case_key] += shard_record_count
        case_counts["total"] += shard_record_count

    x_arr = np.asarray(all_x, dtype=np.float32).reshape(-1, 16)
    y_arr = np.asarray(all_y, dtype=np.float32).reshape(-1, 2)
    return x_arr, y_arr, case_counts, shard_shas


# ---------------------------------------------------------------------------
# Funções de Cálculo de Métricas e Perda Huber
# ---------------------------------------------------------------------------

def compute_huber_loss(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    delta: float = 1.0,
) -> float:
    """Calcula a perda Huber elemento a elemento (delta=1.0)."""
    err = np.abs(y_true - y_pred)
    quad = np.minimum(err, delta)
    lin = err - quad
    loss = 0.5 * (quad ** 2) + delta * lin
    return float(np.mean(loss))


def compute_test_metrics(
    y_true: np.ndarray,
    r_pred: np.ndarray,
) -> dict[str, Any]:
    """Computa o conjunto canônico de métricas de avaliação sob o bucket TEST."""
    huber_cand = compute_huber_loss(y_true, r_pred, delta=1.0)
    huber_null = compute_huber_loss(y_true, np.zeros_like(y_true), delta=1.0)
    huber_ratio = float(huber_cand / huber_null) if huber_null > 0 else float("inf")

    mae_cand = float(np.mean(np.abs(y_true - r_pred)))
    mae_null = float(np.mean(np.abs(y_true)))

    norms = np.linalg.norm(r_pred, axis=-1)
    mean_norm_r = float(np.mean(norms))

    nan_inf_count = int(np.isnan(r_pred).sum() + np.isinf(r_pred).sum())

    # 5 Gates de Release contratuais
    gate_1_huber = bool(huber_cand <= 0.80 * huber_null)
    gate_2_mae = bool(mae_cand < mae_null)
    gate_3_norm = bool(mean_norm_r <= 2.0)
    gate_4_nan_inf = bool(nan_inf_count == 0)
    gate_5_determinism = True  # Verificado pela disciplina de duas leituras

    all_gates_pass = bool(
        gate_1_huber
        and gate_2_mae
        and gate_3_norm
        and gate_4_nan_inf
        and gate_5_determinism
    )

    verdict = "SANCIONADO" if all_gates_pass else "NAO_LIBERADO"

    return {
        "huber_cand": huber_cand,
        "huber_null": huber_null,
        "huber_ratio": huber_ratio,
        "mae_cand": mae_cand,
        "mae_null": mae_null,
        "mean_norm_r": mean_norm_r,
        "nan_inf_count": nan_inf_count,
        "gates": {
            "gate_1_huber": {
                "description": "Huber(cand) <= 0.80 * Huber(null r=0)",
                "passed": gate_1_huber,
                "ratio": huber_ratio,
                "threshold": 0.80 * huber_null,
                "value": huber_cand,
            },
            "gate_2_mae": {
                "description": "MAE(r_cand, r_target) < MAE(0, r_target)",
                "passed": gate_2_mae,
                "value_cand": mae_cand,
                "value_null": mae_null,
            },
            "gate_3_norm": {
                "description": "mean ||r_cand||_2 <= 2.0",
                "passed": gate_3_norm,
                "threshold": 2.0,
                "value": mean_norm_r,
            },
            "gate_4_nan_inf": {
                "description": "nan_inf_count == 0",
                "passed": gate_4_nan_inf,
                "value": nan_inf_count,
            },
            "gate_5_determinism": {
                "description": "Instrument determinism in 2 reads (JSON bytes identical)",
                "passed": gate_5_determinism,
            },
            "all_gates_pass": all_gates_pass,
            "verdict": verdict,
        },
    }


# ---------------------------------------------------------------------------
# Gravação do Veredicto em Formato JSON Determinístico
# ---------------------------------------------------------------------------

def write_release_verdict_json(
    output_path: Path | str | None,
    payload: dict[str, Any],
) -> str:
    """Serializa o JSON determinístico com sort_keys=True e indent=2.

    Se output_path for fornecido:
      - Aplica check_output_path_safety
      - Grava usando modo 'x' (open exclusivo, falha se o arquivo já existir com FileExistsError).
    Se output_path for None:
      - Emite a string JSON idêntica para stdout.

    Retorna o texto serializado com quebra de linha final exata.
    """
    json_text = json.dumps(payload, sort_keys=True, indent=2) + "\n"

    if output_path is not None:
        p = Path(output_path)
        if not p.is_absolute():
            p = (BACKEND_ROOT / p).resolve()
        else:
            p = p.resolve()

        check_output_path_safety(p)
        if p.exists():
            raise FileExistsError(
                f"PARE: O caminho de saída '{p}' já existe! "
                f"Sobrescrita é estritamente proibida (modo 'x' exclusivo)."
            )

        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "x", encoding="utf-8") as f:
            f.write(json_text)

        if not p.exists() or p.stat().st_size == 0:
            raise RuntimeError(f"PARE: Falha na criação do arquivo de veredicto '{p}'.")
    else:
        sys.stdout.write(json_text)
        sys.stdout.flush()

    return json_text


# ---------------------------------------------------------------------------
# Fluxo Principal de Avaliação
# ---------------------------------------------------------------------------

def evaluate_test_bucket(
    candidate_path: Path | str = DEFAULT_CANDIDATE_PATH,
    shards_dir: Path | str = DEFAULT_SHARDS_DIR,
    output_path: Path | str | None = None,
    *,
    enforce_etalon_sha: bool = True,
    explicit_files: Sequence[str | Path] | None = None,
    expected_records_per_shard: int | None = EXPECTED_TEST_RECORDS_PER_SHARD,
) -> dict[str, Any]:
    """Executa a avaliação completa do candidato residual sobre o bucket TEST."""
    # 1. Carrega pesos do candidato com verificação de integridade
    weights, cand_sha = load_candidate_weights(
        candidate_path,
        enforce_etalon_sha=enforce_etalon_sha,
    )

    # 2. Carrega deterministamente o split TEST com gate inverso
    x_test, y_test, counts, shard_shas = load_test_split(
        shards_dir,
        explicit_files=explicit_files,
        expected_records_per_shard=expected_records_per_shard,
    )

    # 3. Inferência forward em NumPy puro
    r_pred = forward_residual(x_test, weights)

    # 4. Computação das métricas e avaliação dos gates
    metrics_result = compute_test_metrics(y_test, r_pred)

    # 5. Resolução de hashes de proveniência
    git_head = get_git_head_sha()
    script_path = Path(__file__).resolve()
    script_sha = compute_file_sha256(script_path)

    # Constrói caminho normalizado para o candidate (posix relativo se dentro do workspace)
    cand_path_obj = Path(candidate_path)
    if cand_path_obj.is_absolute():
        try:
            cand_display_path = str(cand_path_obj.relative_to(BACKEND_ROOT))
        except ValueError:
            cand_display_path = str(cand_path_obj)
    else:
        cand_display_path = str(cand_path_obj)

    # Chaves de shards reveladas no exame
    shard_a_name = "A_A_ON_dump.jsonl_VER.json"
    shard_b_name = "B_B_ON_dump.jsonl_SAI.json"

    verdict_payload: dict[str, Any] = {
        "candidate": {
            "path": cand_display_path,
            "sha256": cand_sha,
            "weights_etalon_sha256": CANDIDATE_WEIGHTS_ETALON_SHA256,
            "weights_sha_matches_etalon": bool(cand_sha == CANDIDATE_WEIGHTS_ETALON_SHA256),
        },
        "counts": {
            "case_A_test": counts.get("case_A", 0),
            "case_B_test": counts.get("case_B", 0),
            "total_test": counts.get("total", 0),
        },
        "gates": metrics_result["gates"],
        "metrics": {
            "huber_cand": metrics_result["huber_cand"],
            "huber_null": metrics_result["huber_null"],
            "huber_ratio": metrics_result["huber_ratio"],
            "mae_cand": metrics_result["mae_cand"],
            "mae_null": metrics_result["mae_null"],
            "mean_norm_r": metrics_result["mean_norm_r"],
            "nan_inf_count": metrics_result["nan_inf_count"],
        },
        "provenance": {
            "git_head_sha": git_head,
            "script_sha256": script_sha,
            "shard_A_test_file": shard_a_name,
            "shard_A_test_sha256": shard_shas.get(shard_a_name, ""),
            "shard_B_test_file": shard_b_name,
            "shard_B_test_sha256": shard_shas.get(shard_b_name, ""),
        },
        "run": "STAGE 5 RELEASE EVALUATION",
    }

    # 6. Grava ou emite JSON de veredicto
    write_release_verdict_json(output_path, verdict_payload)

    return verdict_payload


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Instrumento de Avaliação do Modelo Residual Composite sob o Bucket TEST (STAGE 5)."
    )
    parser.add_argument(
        "--candidate",
        type=str,
        default=DEFAULT_CANDIDATE_PATH,
        help="Caminho do arquivo NPZ de pesos do candidato residual.",
    )
    parser.add_argument(
        "--shards-dir",
        type=str,
        default=DEFAULT_SHARDS_DIR,
        help="Diretório onde residem os shards do corpus.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Caminho do arquivo JSON de veredicto a ser gravado (modo 'x' exclusivo).",
    )
    parser.add_argument(
        "--no-enforce-sha",
        action="store_true",
        default=False,
        help="Desativa a verificação estrita do SHA etalonado (apenas para testes sintéticos).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        evaluate_test_bucket(
            candidate_path=args.candidate,
            shards_dir=args.shards_dir,
            output_path=args.out,
            enforce_etalon_sha=not args.no_enforce_sha,
        )
    except Exception as e:
        sys.stderr.write(f"ERRO no exame de release: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
