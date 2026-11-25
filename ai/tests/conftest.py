import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "app"))

# usa o f1.db real, já commitado no repositório
DB_PATH = os.environ.get(
    "F1_DB_PATH_OVERRIDE",
    str(Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed" / "f1.db")
)
os.environ["F1_DB_PATH_OVERRIDE"] = str(DB_PATH)
