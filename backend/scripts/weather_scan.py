"""CICLO ALAVANCA — REVALIDAÇÃO PASSO 0: scan OFFLINE do clima semeado (ZERO runs).

Mecanismo EXATO (derivado do código e validado contra 30 seeds do corpus):
- rng = weather_rng_from_seed(seed) (sha256 "<seed>//weather"); transições
  avaliadas por WeatherModel.step(lap) a cada VOLTA COMPLETADA POR CARRO
  (engine/simulation.py:669, 10 draws por "onda" de cruzamentos).
- O race_diagnostic dirige engine._step_tick DIRETAMENTE (loop próprio) — o
  engine.run() com o step(lap=1) da largada NÃO executa no headless: os draws
  começam na 1ª onda de voltas reais (label = state.lap+1 = 2).
- Corrida de 600 s com pace ~133-155 s/volta completa 4 voltas → ondas
  labels 2,3,4,5 × 10 carros = 40 draws (v6+ nunca ocorre).
- TEOREMA DO PREFIXO (evidência s9/s10): carros encravados param de completar
  voltas → a corrida consome MENOS draws → as transições IN-RACE são um
  PREFIXO do scan. Seed declarada SECA (sem DAMP/WET no scan) NUNCA vira
  úmida in-race; seed declarada DAMP pode autorreduzir-se por truncagem.

Classificação (pinada no PREREG_ALAVANCA_REVALIDA):
  SECA  = sem transição para DAMP/WET nas ondas 2-5 (CLOUDY-only = seca:
          grip 0,98; s33/36/39 do re-gate C passaram par/wand 0/0)
  DAMP  = ao menos uma transição para DAMP/WET nas ondas 2-5 (grip ≤0,75)
Guardrail preregistrado: >5/10 damp na década → PARE antes de rodar.

    .venv/bin/python scripts/weather_scan.py --check     # valida contra o corpus
    .venv/bin/python scripts/weather_scan.py 40 49        # declara a década
"""
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from domain.weather import WeatherModel, WeatherKind, BASE_CONDITIONS, weather_rng_from_seed

CORPUS = BACKEND / "experiments"
WAVES = (2, 3, 4, 5)   # ondas de voltas de uma corrida headless de 600 s


def scan(seed):
    """Transições de uma corrida saudável de 600 s ( WeatherModel real,
    consumindo os uniforms de jitter — caminho idêntico ao engine)."""
    m = WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY],
                    rng=weather_rng_from_seed(seed))
    out = []
    for lap in [w for w in WAVES for _ in range(10)]:
        prev = m.current.kind
        m.step(lap)
        if m.current.kind != prev:
            out.append((lap, prev.value, m.current.kind.value))
    return out


def header_transitions(path):
    head = open(path).readline()
    m = re.search(r"weather_transitions=\[(.*?)\]", head)
    if not m or not m.group(1).strip():
        return []
    return [(int(a), b, c) for a, b, c in re.findall(
        r"\((\d+),\s*<WeatherKind\.(\w+)[^>]*>,\s*<WeatherKind\.(\w+)[^>]*>\)",
        m.group(1))]


def classify(transitions):
    wet = {t for _, _, t in transitions}
    return "DAMP" if wet & {"DAMP", "WET"} else "SECA"


def main(argv):
    if argv and argv[0] == "--check":
        KNOWN = {s: CORPUS / "diag-r2-r13" / f"race_diag_r10_blind_s{s}.csv" for s in range(10)}
        KNOWN.update({s: CORPUS / "diag-r2-r13" / f"race_diag_r13_b_s{s}.csv" for s in range(10, 20)})
        KNOWN.update({s: CORPUS / "diag-alv-seco" / f"race_diag_alv2_s{s}.csv" for s in range(30, 40)})
        exact = pref = bad = 0
        for s, path in sorted(KNOWN.items()):
            if not path.exists():
                print(f"[check] s{s}: corpus ausente — SKIP")
                continue
            got, want = scan(s), header_transitions(path)
            if got == want:
                exact += 1
                print(f"[check] s{s}: EXATO    {got}")
            elif got[:len(want)] == want:
                pref += 1
                print(f"[check] s{s}: PREFIXO  in-race={want} ⊂ scan={got}")
            else:
                bad += 1
                print(f"[check] s{s}: DIVERGE  scan={got} csv={want}")
        print(f"\n[check] exatos={exact} prefixos={pref} divergentes={bad} "
              f"({'VALIDADO — teorema do prefixo' if bad == 0 else 'NÃO usar'})")
        return 0 if bad == 0 else 1
    lo, hi = int(argv[0]), int(argv[1])
    rows = [(s, classify(t), t) for s in range(lo, hi + 1) for t in [scan(s)]]
    print(f"=== PASSO 0 — SCAN OFFLINE seeds {lo}-{hi} (WeatherModel real, ondas 2-5 ×10 carros) ===")
    for s, cls, t in rows:
        print(f"  s{s}: {cls:5s} | {'; '.join(f'v{a}:{b}->{c}' for a, b, c in t) or 'sem transicoes'}")
    n_damp = sum(1 for _, c, _ in rows if c == "DAMP")
    print(f"\ndamp: {n_damp}/{len(rows)} | guardrail preregistrado: >5/10 damp -> PARE antes de rodar")
    out = CORPUS / "diag-alv-seco" / f"weather_scan_s{lo}_s{hi}.csv"
    with open(out, "w") as f:
        f.write("seed,clima,transicoes\n")
        for s, cls, t in rows:
            desc = "; ".join(f"v{a}:{b}->{c}" for a, b, c in t) or "sem transicoes"
            f.write(f'{s},{cls},"{desc}"\n')
    print(f"-> {out}")
    return 0 if n_damp <= 5 else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
