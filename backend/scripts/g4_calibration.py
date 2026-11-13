"""FASE H-1 — calibração do G4 em CONTROLES + congelamento condicional dos mirrors.

Prereg: PREREG_FASE_H1.md (commit 1f4af52, ANTES de qualquer execução).
Duas fases SEPARADAS por construção (anti-tautologia §5):

  FASE 1 (controles): varre a grade κ sobre os 5 CONTROLES frozen
  (Hungaroring 14, Monza 11, Zandvoort 14, Suzuka 18, interlagos_v2 15 —
  oficiais do §2, fonte única Wikipedia EN 2026-10-20), aplica a regra de
  escolha (i in-band máx | ii Σ|Δ| mín | iii midpoint do plateau) e CONGELA
  o κ* no CSV `experiments/g4_calibration_controles.csv` (commit ANTES dos
  alvos). Validade: ≥4/5 controles in-band.

  FASE 2 (alvos): lê o κ* DO CSV COMMITADO (nunca recomputa), aplica aos
  mirrors Monaco/Spa (oficiais 19/19) e executa a árvore §6:
  A(κ* válido): ambos in-band -> freeze (nomes inertes) ; qualquer fora ->
  PARE honesto, nada congelado.
  B(κ* inválido): G4 morre (report-only) -> mirrors elegíveis (G1/G2/G3/G5
  já PASS na H-0) -> freeze com a crítica documentada.

    .venv/bin/python scripts/g4_calibration.py controles
    .venv/bin/python scripts/g4_calibration.py alvos
"""
import json
import sys
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "scripts"))
from track_mirror_build import radii_and_turns, DS_M

FROZEN = BACKEND / "model_train" / "tracks_frozen"
OUT_CSV = BACKEND / "experiments" / "g4_calibration_controles.csv"

# §2/§3 do prereg — ESCRITOS antes da execução (nome curto -> (arquivo, oficial))
CONTROLES = {  # oficiais: Wikipedia EN, 2026-10-20
    "Hungaroring": ("Hungaroring_v1.json", 14),
    "Monza": ("Monza_v1.json", 11),
    "Zandvoort": ("Zandvoort_v1.json", 14),
    "Suzuka": ("Suzuka_v1.json", 18),
    "interlagos": ("interlagos_v2.json", 15),
}
ALVOS = {"monaco": 19, "spa": 19}     # oficiais §2
GRID = [round(0.004 + 0.001 * i, 3) for i in range(17)]   # 0,004..0,020
BAND = 3                              # oficial ±3, bordas inclusivas


def counts_at(kappa, wps):
    _, n, _ = radii_and_turns(wps, kappa_thresh=kappa)
    return n


def fase_controles():
    tracks = {}
    for short, (f, official) in CONTROLES.items():
        wps = np.array(json.loads((FROZEN / f).read_text())["waypoints"], dtype=np.float64)
        tracks[short] = (wps, official)
    rows = []
    for k in GRID:
        row = {"kappa": k}
        in_band = sad = 0
        for short, (wps, official) in tracks.items():
            c = counts_at(k, wps)
            row[short] = c
            in_band += abs(c - official) <= BAND
            sad += abs(c - official)
        row["in_band"], row["sum_absdiff"] = in_band, sad
        rows.append(row)
        cells = " ".join(f"{row[s]}({'ok' if abs(row[s] - tracks[s][1]) <= BAND else 'X'})"
                         for s in CONTROLES)
        print(f"  κ={k:.3f}: {cells} | in_band={in_band}/5 | Σ|Δ|={sad}")
    # regra de escolha (i/ii/iii)
    max_ib = max(r["in_band"] for r in rows)
    cand = [r for r in rows if r["in_band"] == max_ib]
    min_sad = min(r["sum_absdiff"] for r in cand)
    cand2 = [r["kappa"] for r in cand if r["sum_absdiff"] == min_sad]
    kstar = round(float(np.mean([min(cand2), max(cand2)])), 3)   # plateau -> midpoint
    valid = max_ib >= len(CONTROLES) - 1                        # >= N-1 = 4/5
    print(f"\n(i) in_band máx = {max_ib}/5 | (ii) Σ|Δ| mín = {min_sad} | "
          f"(iii) plateau {cand2} -> midpoint κ* = {kstar}")
    print(f"VALIDADE (>=4/5 in-band com κ*): {'VÁLIDO' if valid else 'INVÁLIDO -> RAMO B'}")
    # CONGELA o κ* no CSV (commit ANTES dos alvos)
    import csv
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
        fh.write(f"# kstar={kstar} valid={valid} fonte=Wikipedia_EN_2026-10-20 "
                 f"regra=i_max_in_band,ii_min_sum_absdiff,iii_plateau_midpoint\n")
    print(f"-> {OUT_CSV} (κ* CONGELADO; commit ANTES dos alvos)")
    return kstar, valid


def fase_alvos():
    # κ* lido DO CSV COMMITADO (nunca recomputa — anti-tautologia)
    kstar, valid = None, None
    for line in open(OUT_CSV):
        if line.startswith("# kstar="):
            import re
            m = re.search(r"kstar=([\d.]+) valid=(\w+)", line)
            kstar, valid = float(m.group(1)), m.group(2) == "True"
    assert kstar is not None, f"κ* ausente em {OUT_CSV} — rodar 'controles' e commitar antes"
    print(f"[alvos] κ* do CSV commitado: {kstar} | válido={valid}")
    if valid:
        # RAMO A: aplicar κ* aos alvos; ambos in-band -> freeze; senão PARE
        from track_mirror_build import build
        rcs = []
        for key, official in ALVOS.items():
            rc = build(key, write=False, g4_kappa=kstar, official_turns=official)
            rcs.append((key, rc))
        # re-executa escrevendo SÓ se ambos passaram (build(write=False) não escreve;
        # o freeze real repete o build determinístico com write=True)
        all_ok = all(rc == 0 for _, rc in rcs)
        if all_ok:
            print("[alvos] RAMO A: ambos in-band -> CONGELANDO")
            for key, official in ALVOS.items():
                build(key, write=True, g4_kappa=kstar, official_turns=official)
            print("[alvos] CONGELADOS os dois mirrors (nomes inertes ao loader)")
            return 0
        print("[alvos] RAMO A: FAIL de alvo -> PARE honesto (problema real do mirror); NADA congelado")
        return 1
    else:
        # RAMO B: G4 MORRE (report-only) -> mirrors elegíveis (G1/G2/G3/G5 PASS na H-0)
        from track_mirror_build import build
        print("[alvos] RAMO B: G4 morre como gate (fingerprint report-only); "
              "mirrors ELEGÍVEIS via G1/G2/G3/G5 -> CONGELANDO com a crítica documentada")
        for key, official in ALVOS.items():
            build(key, write=True, g4_kappa=kstar, official_turns=official, g4_gate=False)
        print("[alvos] CONGELADOS os dois mirrors (G4 report-only no JSON)")
        return 0


def main(argv):
    if argv and argv[0] == "controles":
        kstar, valid = fase_controles()
        return 0
    if argv and argv[0] == "alvos":
        return fase_alvos()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
