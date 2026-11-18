"""PISTA-IDENT-1 — testes do módulo track_resolution + wiring (prereg 3758661 §6).

t_g1_reexport: `from backend.model_train.f1_env import
    resolve_track/load_track_frozen` continua funcionando (compat) — o
    módulo novo é a FONTE (source-of-truth check).
t_g2_fail_loud: resolve_track('Pista-inexistente') levanta
    TrackResolutionError com a lista; allow_fallback=True devolve o
    preset de Interlagos (comportamento antigo preservado atrás da flag).
t_g3_identity: track_identity devolve os campos (requested/efetiva/
    fonte/sha/wp/L); hash DETERMINÍSTICO entre chamadas; mirror-first
    resolve as 3 canônicas com o sha canônico do arquivo frozen.
t_g3_g2_wiring: f1_env expõe allow_track_fallback (default False) e
    track_identity no __init__; eval_teacher_solo tem o import + flag.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def test_t_g1_reexport():
    from backend.model_train import f1_env
    from backend.domain import track_resolution
    # re-export de compat: os imports históricos continuam
    assert f1_env.resolve_track is track_resolution.resolve_track
    assert f1_env.load_track_frozen is track_resolution.load_track_frozen
    assert f1_env.FASTF1_DEFAULT_EVENT == "São Paulo"
    # o módulo novo é a FONTE (o f1_env não redefine)
    assert "def resolve_track" in (Path(__file__).resolve().parent.parent
                                  / "domain" / "track_resolution.py").read_text()


def test_t_g2_fail_loud_e_fallback():
    from backend.domain.track_resolution import (TrackResolutionError,
                                                resolve_track)
    with pytest.raises(TrackResolutionError) as ei:
        resolve_track(track="Pista-inexistente", year=2024)
    assert "interlagos" in str(ei.value), "lista de opções ausente"
    assert "Monaco" in str(ei.value) or "mirrors" in str(ei.value).lower()
    # fallback preserva o comportamento antigo (preset Interlagos)
    t = resolve_track(track="Pista-inexistente", year=2024,
                      allow_fallback=True)
    assert "Interlagos" in t.name
    assert len(t.waypoints) == 240  # preset legado


def test_t_g3_identity_e_mirror_first():
    from backend.domain.track_resolution import (load_track_frozen,
                                                resolve_track,
                                                track_identity)
    t = load_track_frozen("Monaco")
    id1 = track_identity(t, requested="Monaco", fonte="mirror")
    id2 = track_identity(t, requested="Monaco", fonte="mirror")
    for k in ("requested", "efetiva", "fonte", "sha256", "n_wp", "length_m"):
        assert k in id1
    assert id1["sha256"] == id2["sha256"], "hash não-determinístico"
    assert id1["n_wp"] == 834 and abs(id1["length_m"] - 3335.2) < 0.5
    # mirror-first: resolve_track devolve o próprio frozen (sha canônico)
    t2 = resolve_track(track="Monaco")
    assert t2.frozen_sha256 == t.frozen_sha256 == "67ca11dc211c8c78"
    ti = resolve_track(track="interlagos")
    assert ti.frozen_sha256 == "164876196eb12174"
    ts = resolve_track(track="spa")
    assert ts.frozen_sha256 == "4b05f2c3bbc625fc"


def test_t_g3_g2_wiring():
    import inspect
    from backend.model_train import f1_env
    sig = inspect.signature(f1_env.F1MultiContextEnv.__init__)
    assert sig.parameters["allow_track_fallback"].default is False
    src = inspect.getsource(f1_env.F1MultiContextEnv.__init__)
    assert "self.track_identity = track_identity(" in src
    ev = (Path(__file__).resolve().parent.parent
          / "model_train" / "eval_teacher_solo.py").read_text()
    assert "--allow-track-fallback" in ev
    assert "IDENTIDADE" in ev
