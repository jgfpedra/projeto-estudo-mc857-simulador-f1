# Backend scripts

Os utilitários ficam agrupados por função:

- `simulation/`: execução de corrida, GUI de entrada e demonstrações;
- `visualization/`: integração de visualização ao vivo com PyBullet e navegador;
- `tracks/`: extração, geometria e espelhamento de circuitos;
- `analysis/`: métricas e diagnósticos gerais;
- `benchmarks/`: calibração e benchmarks de física;
- `training/`: corpus e treinamento de modelos;
- `experiments/<tema>/`: instrumentos de estudos e auditorias específicos.

Execute os comandos a partir de `backend/`, por exemplo:

```bash
.venv/bin/python scripts/simulation/run_race_10_cars.py --profile race-blind --laps 3
python scripts/visualization/run_live_compare.py --drivers 10
```

No Windows, substitua `.venv/bin/python` por `.venv\Scripts\python.exe`.

`base_metrics.py`, `saidas_verdict.py` e `sanidade1b_verdict.py` permanecem na raiz porque estudos e testes dependem dos hashes SHA-256 congelados desses módulos. Os caminhos mencionados em artefatos de `experiments/` são registros históricos das versões usadas na época.
