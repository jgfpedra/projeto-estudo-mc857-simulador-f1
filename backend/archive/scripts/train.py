"""Unified training runner for F1 Model Train.
Executável a partir de qualquer diretório.
Por padrão, executa o treinamento PPO vetorizado (vários ambientes).

Exemplos de uso:
    python backend/model_train/train.py
    python backend/model_train/train.py --n-envs 4 --iters 100
    python backend/model_train/train.py --mode bc
    python backend/model_train/train.py --mode all
    python backend/model_train/train.py --single-env
"""

import os
import sys
from pathlib import Path

# Configuração de diretórios e paths
MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent

# Auto-detect do virtualenv do projeto se executado fora dele
VENV_DIR = PROJECT_ROOT / "backend" / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
if sys.prefix != str(VENV_DIR) and VENV_PYTHON.exists():
    try:
        import gymnasium
        import tensorflow
    except ImportError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

# Propaga PYTHONPATH para subprocessos (multiprocessing spawn)
current_ppath = os.environ.get("PYTHONPATH", "")
ppaths = [p for p in current_ppath.split(os.pathsep) if p]
for p in [str(PROJECT_ROOT), str(MODEL_DIR)]:
    if p not in ppaths:
        ppaths.insert(0, p)
os.environ["PYTHONPATH"] = os.pathsep.join(ppaths)

from backend.model_train.train_multi_context_ppo import (
    MultiContextPPOAgent,
    make_env_fn,
    DEFAULT_BC_PATH,
    DEFAULT_REFERENCE_CSV,
    DEFAULT_ACTOR_PATH,
    DEFAULT_CRITIC_PATH,
)
from backend.model_train.f1_env import F1MultiContextEnv
from backend.model_train.model_multi_context import train_bc_model, DEFAULT_DATA_PATH, DEFAULT_MAPPINGS_PATH, DEFAULT_MODEL_PATH

def print_banner(mode: str, n_envs: int):
    print("=" * 70)
    print("🏎️   F1 SIMULATOR - PIPELINE DE TREINAMENTO")
    print(f"    Modo: {mode.upper()}")
    if mode == "ppo":
        print(f"    Ambientes Paralelos (AsyncVectorEnv): {n_envs}")
    print(f"    Diretório de Treinamento: {MODEL_DIR}")
    print(f"    Python Executável: {sys.executable}")
    print("=" * 70)

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="F1 Model Train Runner - Execute o treinamento a partir de qualquer pasta",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["ppo", "single", "bc", "data", "all"],
        default="ppo",
        help="Modo de treinamento: 'ppo' (vários ambientes RL), 'single' (RL 1 ambiente), 'bc' (Behavioral Cloning), 'data' (coleta fastf1), 'all' (BC + PPO)",
    )
    parser.add_argument("--n-envs", type=int, default=8, help="Número de ambientes paralelos para PPO")
    parser.add_argument("--iters", type=int, default=500, help="Número de iterações PPO")
    parser.add_argument("--steps-per-roll", type=int, default=256, help="Passos por rollout por ambiente")
    parser.add_argument("--epochs", type=int, default=10, help="Épocas por iteração de PPO ou de BC")
    parser.add_argument("--batch-size", type=int, default=256, help="Tamanho do batch")
    parser.add_argument("--driver-id", type=str, default="HAM", help="Piloto de referência")
    parser.add_argument("--track-id", type=int, default=0, help="ID da pista")
    parser.add_argument("--compound-id", type=int, default=0, help="ID do composto de pneus")
    parser.add_argument("--bc-path", type=str, default=str(DEFAULT_BC_PATH), help="Caminho do modelo BC")
    parser.add_argument("--track", type=str, default="interlagos", help="Pista para treino (default: interlagos)")
    parser.add_argument("--reference-csv", type=str, default=None, help="Caminho do CSV de referência (opcional)")
    parser.add_argument("--save-dir", type=str, default=str(MODEL_DIR), help="Diretório onde salvar checkpoints e modelos")
    parser.add_argument("--single-env", action="store_true", help="Atalho para rodar RL em ambiente único")

    args = parser.parse_args()

    mode = "single" if args.single_env else args.mode

    # 1. Modo Coleta de Dados
    if mode == "data":
        print_banner("data", 0)
        from backend.model_train.train_multi_context import collect_and_prepare_dataset
        collect_and_prepare_dataset(save_dir=args.save_dir)
        return

    # 2. Modo Behavioral Cloning (ou parte do 'all')
    if mode in ("bc", "all"):
        print_banner("bc", 0)
        bc_epochs = args.epochs if mode == "bc" else 150
        train_bc_model(
            output_model_path=args.bc_path,
            epochs=bc_epochs,
            batch_size=args.batch_size
        )
        if mode == "bc":
            return

    # 3. Modo PPO (Vários Ambientes ou Single Env)
    print_banner(mode, args.n_envs if mode != "single" else 1)

    ref_csv = None
    if args.reference_csv:
        ref_csv = Path(args.reference_csv)
        if not ref_csv.is_absolute() and not ref_csv.exists():
            if (MODEL_DIR / ref_csv).exists():
                ref_csv = MODEL_DIR / ref_csv
            elif (PROJECT_ROOT / ref_csv).exists():
                ref_csv = PROJECT_ROOT / ref_csv

    bc_model = Path(args.bc_path)
    if not bc_model.is_absolute() and not bc_model.exists():
        if (MODEL_DIR / bc_model).exists():
            bc_model = MODEL_DIR / bc_model
        elif (PROJECT_ROOT / bc_model).exists():
            bc_model = PROJECT_ROOT / bc_model

    if mode == "single":
        print(f"Iniciando PPO em ambiente único (pista={args.track}, driver={args.driver_id}, track_id={args.track_id})...")
        env = F1MultiContextEnv(
            track=args.track,
            reference_csv=str(ref_csv) if ref_csv else None,
            driver_id=args.driver_id,
            track_id=args.track_id,
            compound_id=args.compound_id
        )
        try:
            agent = MultiContextPPOAgent(
                obs_spaces=env.observation_space,
                act_dim=env.action_space.shape[0],
                bc_path=str(bc_model) if bc_model.exists() else None
            )
            agent.train(
                env=env,
                n_iters=args.iters,
                steps_per_roll=args.steps_per_roll * args.n_envs,
                epochs=args.epochs,
                batch_size=args.batch_size
            )
        finally:
            env.close()
    else:
        from gymnasium.vector import AsyncVectorEnv

        print(f"Criando {args.n_envs} ambientes paralelos (pista={args.track}, driver={args.driver_id}, track_id={args.track_id})...")
        env_fns = [
            make_env_fn(
                track=args.track,
                reference_csv=str(ref_csv) if ref_csv else None,
                driver_id=args.driver_id,
                track_id=args.track_id,
                compound_id=args.compound_id
            )
            for _ in range(args.n_envs)
        ]
        vec_env = AsyncVectorEnv(env_fns, context="spawn")
        try:
            agent = MultiContextPPOAgent(
                obs_spaces=vec_env.single_observation_space,
                act_dim=vec_env.single_action_space.shape[0],
                bc_path=str(bc_model) if bc_model.exists() else None
            )
            agent.train_vectorized(
                vec_env=vec_env,
                n_envs=args.n_envs,
                n_iters=args.iters,
                steps_per_roll=args.steps_per_roll,
                epochs=args.epochs,
                batch_size=args.batch_size,
                save_dir=args.save_dir
            )
        finally:
            vec_env.close()

if __name__ == "__main__":
    main()
