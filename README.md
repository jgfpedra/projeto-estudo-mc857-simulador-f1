# projeto-estudo-mc857-simulador-f1

João Guilherme Ferreira Pedra - RA: 248349 \
Luiz Fernando Lima Leite - RA: 248405 \
João Vitor Guilherme dos Santos - RA: 247232 \
Caio Zavarezzi Balieiro - RA: 195260 \
Guilherme Resende Braga - RA: 232517

Simulação de corrida F1 (PyBullet) com pilotos neurais treinados por DAgger
sobre um professor pure-pursuit, camada de corrida (governor de velocidade,
rejoin, recovery) e instrumento de medição canônico (contato solver-side,
clima e variância semeados, pistas congeladas com sha256).

## Quickstart — corrida GUI (10 carros)

```bash
cd backend
.venv/bin/python scripts/run_race_10_cars.py --profile race-blind --laps 3
```

Perfis disponíveis (`--profile`):

| Perfil | O que é | Quando usar |
|---|---|---|
| `race-blind` | **v10-cego** (DAgger sf=0,80, obs edge) — RACE DEFAULT do produto (veredito R10/R13) | corrida padrão |
| `composite` | v10 + residual gated r2 — research-grade: 1,5-3,5× menos contatos, mas sai mais da pista | experimentos de segurança |
| `quali` | v11b (sf=0,90, pace máximo) | volta rápida |
| `traffic` | v14 iter3 (obs 60d) | campo misto condicional |

## Quickstart — corrida diagnóstica headless (instrumento canônico)

```bash
cd backend
.venv/bin/python model_train/race_diagnostic.py \
  --profile composite --ticks 6000 --laps 99 --track interlagos \
  --seed 0 --gov vplan --variance grid,compound --out corrida.csv
```

O CSV (v3.3) traz clima/pneu por tick, impulso de contato do solver
(`imp_*` + `<out>_events.csv`), entrada 16d do residual (`res_*`) e o
cenário sorteado (grid/compostos) no cabeçalho.

**Canária solo** (valida o stack): adicione `--n-cars 1` — esperado ≥2
voltas, fora ≤25%, 0 wanderers.

## Regras de medição (aprendidas no ciclo v15 — ver PROJECT_STATE.md)

1. **Sequencial-puro**: nunca rode duas corridas em paralelo (o pybullet
   diverge a realização em t≈3-4s).
2. **Pistas**: só `--track interlagos` (frozen v2, SF 729, sha256
   `164876…`). FastF1 está offline — o env cai num preset que o v10
   nunca viu (canárias de env não valem).
3. **Seeds = realizações**: clima + grid + compostos derivam do `--seed`.
4. **Paradas contam do CSV**, não do log; **voltas = cruzamentos de SF − 1**.
5. **Medição sem commit não existe**: prereg + código commitados antes de
   qualquer run de medição.

## Comportamento conhecido (limitações documentadas)

- O composite evita contatos (1,5-3,5× menos que o v10-cego em 10/10
  seeds out-of-sample) mas sai da pista mais (25-54% fora) e hesita no
  retorno das excursões — não passou o gate de promoção (R13).
- Ultrapassagem lateral limpa não cabe na pista de 12m (teto aceito).
- Excursões em clima adverso geram contatos no retorno (44% das amostras
  de contato têm um carro fora) — a alavanca futura é percepção de
  tráfego no rejoin (alvo quantificado no PROJECT_STATE).

## Bootstrap de dados (uma vez)

O endpoint de circuitos precisa do `data/circuit_layouts_evolution.json`,
extraído do `f1db.db` (banco F1DB, **regenerável** — não está no git):

```bash
cd backend && .venv/bin/python scripts/fetch_track_layouts.py
```

## Testes

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```

## Documentação de fundo

- `backend/PROJECT_STATE.md` — estado completo do projeto, declaração de
  produto, cadeia causal R7b→R13.
- `backend/model_train/AUDITORIA_RL.md` — auditoria técnica.
- `experiments/README.md` — evidência bruta fora do git (CSVs R2-R13).

