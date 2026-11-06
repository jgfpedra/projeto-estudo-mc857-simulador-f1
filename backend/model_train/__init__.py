"""Model training package for F1 simulator.
Provides neural network models, reinforcement learning environment and training scripts.
"""

from pathlib import Path
import sys
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

# Ensure child processes from multiprocessing inherit PYTHONPATH
current_ppath = os.environ.get("PYTHONPATH", "")
ppaths = [p for p in current_ppath.split(os.pathsep) if p]
for p in [str(PROJECT_ROOT), str(MODEL_DIR)]:
    if p not in ppaths:
        ppaths.insert(0, p)
os.environ["PYTHONPATH"] = os.pathsep.join(ppaths)
