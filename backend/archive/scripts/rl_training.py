# rl_training.py - Single-environment training runner
import os
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent

# Auto-detect project virtualenv if running outside venv and dependencies missing
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

from backend.model_train.f1_env import F1MultiContextEnv
from backend.model_train.train_multi_context_ppo import MultiContextPPOAgent, DEFAULT_BC_PATH, DEFAULT_REFERENCE_CSV, MODEL_DIR

def run_single_env_training(iters=500, steps_per_roll=2048, epochs=10, batch_size=256,
                            driver_id='HAM', track_id=0, compound_id=0,
                            track='interlagos', reference_csv=None, bc_path=None):
    bc_model = Path(bc_path or DEFAULT_BC_PATH)

    env = F1MultiContextEnv(
        track=track,
        reference_csv=reference_csv,
        driver_id=driver_id,
        track_id=track_id,
        compound_id=compound_id
    )

    try:
        agent = MultiContextPPOAgent(
            obs_spaces=env.observation_space,
            act_dim=env.action_space.shape[0],
            bc_path=str(bc_model) if bc_model.exists() else None
        )

        print("Iniciando fine-tuning RL Multi-Contexto (ambiente único)...")
        agent.train(env, n_iters=iters, steps_per_roll=steps_per_roll, epochs=epochs, batch_size=batch_size)
    finally:
        env.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Treinamento PPO Multi-Contexto em Ambiente Único")
    parser.add_argument("--iters", type=int, default=500, help="Número de iterações PPO (default: 500)")
    parser.add_argument("--steps-per-roll", type=int, default=2048, help="Passos por rollout (default: 2048)")
    parser.add_argument("--epochs", type=int, default=10, help="Épocas por iteração (default: 10)")
    parser.add_argument("--batch-size", type=int, default=256, help="Tamanho do batch (default: 256)")
    parser.add_argument("--driver-id", type=str, default="HAM", help="ID do piloto (default: HAM)")
    parser.add_argument("--track-id", type=int, default=0, help="ID da pista (default: 0)")
    parser.add_argument("--compound-id", type=int, default=0, help="ID do composto de pneu (default: 0)")
    parser.add_argument("--bc-path", type=str, default=str(DEFAULT_BC_PATH), help="Caminho do modelo BC base")
    parser.add_argument("--track", type=str, default="interlagos", help="Pista para treino (default: interlagos)")
    parser.add_argument("--reference-csv", type=str, default=None, help="Caminho do CSV de referência (opcional)")
    args = parser.parse_args()

    run_single_env_training(
        iters=args.iters,
        steps_per_roll=args.steps_per_roll,
        epochs=args.epochs,
        batch_size=args.batch_size,
        driver_id=args.driver_id,
        track_id=args.track_id,
        compound_id=args.compound_id,
        track=args.track,
        reference_csv=args.reference_csv,
        bc_path=args.bc_path
    )