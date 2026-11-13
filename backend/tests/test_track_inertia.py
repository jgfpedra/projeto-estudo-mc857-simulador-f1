"""ADOÇÃO-H-2 — testes do flip canônico (prereg 8c14f9f §7).

t-inércia (REESCRITO — flip da adoção): pós-swap, load_track_frozen
('Monaco') resolve para **Monaco_v2.json** (= conteúdo mirror,
sha 67ca11dc211c8c78) e 'Spa' para **Spa_v2.json** (sha
4b05f2c3bbc625fc) — a prioridade {key}_v2.json EXISTENTE do loader faz a
troca sem que o loader tenha sido tocado.

t-novo (+1): os v1s em `archive/tracks_frozen_v1/` permanecem artefatos
VÁLIDOS — leitura DIRETA do JSON + sha de conteúdo conferido +
Track.from_waypoints constrói. [DISCLOSE: o loader NÃO consulta archive/
(INTOCADO por PARE) — "loadável" = via JSON direto.]
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.model_train.f1_env import load_track_frozen
from backend.domain.track import Track

BACKEND = Path(__file__).resolve().parent.parent
FROZEN = BACKEND / "model_train" / "tracks_frozen"
ARCHIVE = BACKEND / "archive" / "tracks_frozen_v1"

# pós-ADOÇÃO-H-2: o canônico de Monaco/Spa é o CONTEÚDO mirror (v2)
CANONICO = {"Monaco": "67ca11dc211c8c78", "Spa": "4b05f2c3bbc625fc"}
V1_ARQUIVADOS = {"Monaco_v1.json": "07e7ef4dd6af4517",
                  "Spa_v1.json": "f83365bf26d0b1b1"}


def test_t_inercia_loader_flip_para_o_mirror():
    """'Monaco' -> Monaco_v2 (mirror); 'Spa' -> Spa_v2. A prioridade
    {key}_v2.json do loader (intocado) faz a troca da adoção."""
    for key, want in CANONICO.items():
        t = load_track_frozen(key)
        assert t.frozen_sha256 == want, \
            f"load_track_frozen('{key}') = {t.frozen_sha256} != mirror {want}"
        assert len(t.waypoints) > 100
    # os v1 não estão mais no diretório frozen (arquivados)
    assert not (FROZEN / "Monaco_v1.json").exists()
    assert not (FROZEN / "Spa_v1.json").exists()
    assert not (FROZEN / "Monaco_mirror2021_v1.json").exists(), \
        "cópia inerte duplicada proibida (prereg §1)"


def test_t_novo_v1_arquivados_validos():
    """v1s em archive/ permanecem artefatos válidos: sha conferido e
    Track.from_waypoints constrói (o loader não vê archive/ — por design)."""
    import hashlib
    for fname, want in V1_ARQUIVADOS.items():
        p = ARCHIVE / fname
        assert p.exists(), f"{fname} ausente do archive (NUNCA deletar!)"
        d = json.loads(p.read_text())
        raw = json.dumps({k: v for k, v in d.items() if k != "sha256"},
                         sort_keys=True).encode()
        got = hashlib.sha256(raw).hexdigest()[:16]
        assert got == want == d["sha256"], f"{fname}: sha {got} != {want}"
        t = Track.from_waypoints(name=d["name"],
                                 waypoints=[tuple(w) for w in d["waypoints"]],
                                 width_m=float(d.get("width_m", 12.0)))
        assert len(t.waypoints) == d["n_wp"]
