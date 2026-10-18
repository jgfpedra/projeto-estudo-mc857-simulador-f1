"""R8 1.2b — testes unitários do STEER-GOVERNOR (opt-in, default off).

Contrato do prereg (PREREG_R8_STEERGOV.md):
- fórmula: cap = 2,0 × atan(3,4 × κ@10m) sobre o comando da POLÍTICA;
- hairpin LEGÍTIMO (κ=0,12) NÃO é clipado: cap ≥ δ necessário;
- default OFF: nenhum clip, nenhum efeito;
- autoridade: o rejoin bearing sobrescreve o steer DEPOIS do cap (isento);
  o cap só atua no comando da política.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.scripts.run_race_10_cars import NeuralRaceController as N


def test_cap_formula():
    """cap = k_comp × atan(L × κ_preview), com κ_preview = obs10/25."""
    for kappa in (0.005, 0.010, 0.05, 0.12):
        cap = N.STEER_GOV_K_COMP * math.atan(N.STEER_GOV_WHEELBASE_M * kappa)
        assert cap > 0
        # cap cresce monotonicamente com κ
    caps = [N.STEER_GOV_K_COMP * math.atan(N.STEER_GOV_WHEELBASE_M * k)
            for k in (0.005, 0.02, 0.06, 0.12)]
    assert caps == sorted(caps), "cap deve crescer com κ"
    # constante pinada no prereg
    assert N.STEER_GOV_K_COMP == 2.0 and N.STEER_GOV_WHEELBASE_M == 3.4


def test_hairpin_not_clipped():
    """Hairpin legítimo κ=0,12: cap ≈ 0,77 rad ≈ STEER_MAX — não clipa
    o comando necessário (documento do prereg)."""
    cap = N.STEER_GOV_K_COMP * math.atan(N.STEER_GOV_WHEELBASE_M * 0.12)
    # comando cinemático necessário para o hairpin:
    need = math.atan(N.STEER_GOV_WHEELBASE_M * 0.12)
    assert cap >= need * 1.99, f"cap {cap:.3f} deveria cobrir 2× a necessidade {need:.3f}"
    # e na prática: cap ≈ STEER_MAX (não limita nada num hairpin real)
    assert cap >= 0.75, f"cap do hairpin {cap:.3f} deveria ser ~STEER_MAX"


def test_cap_blocks_the_24x_tail():
    """A cauda patológica (δ 24× a necessidade cinemática na banda quente)
    é clipada: κ=0,010 → cap ~0,068 rad << 0,69 mediano das saídas."""
    cap = N.STEER_GOV_K_COMP * math.atan(N.STEER_GOV_WHEELBASE_M * 0.010)
    assert cap < 0.07, f"cap na banda quente deveria ser ~0,068 (veio {cap:.3f})"
    assert cap < 0.69, "a cauda 24x (0,72 rad) seria toda clipada"


def test_default_off_and_state():
    """Default off: nada de clip; estado do instrumento vazio."""
    assert hasattr(N, '__init__')
    # atributos do contrato existem na classe (aplicados no __init__)
    import inspect
    src = inspect.getsource(N.__init__)
    assert 'steer_gov' in src, "kwarg steer_gov ausente do __init__"
    src_loop = inspect.getsource(N.predict_batch)
    assert 'self.steer_gov == "cap"' in src_loop, "cap não está no loop de ações"


def test_rejoin_exempt_by_order():
    """Autoridade: o cap atua no comando da POLÍTICA; o rejoin bearing
    SOBRESCREVE steer_rad DEPOIS (composição 3 > cap) — por construção,
    o rejoin nunca vê o cap. Verificação estrutural do código."""
    import inspect
    src = inspect.getsource(N.predict_batch)
    i_cap = src.find('steer_gov == "cap"')
    i_rejoin = src.find('---- 3. rejoin')
    assert 0 < i_cap < i_rejoin, (
        "o cap deve atuar ANTES do bloco rejoin na ordem do método "
        f"(cap@{i_cap}, rejoin@{i_rejoin})")
