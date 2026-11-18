# EXECUÇÃO YIELD-1C — PARE/SUNSET

## Freeze e exposição

- Freeze do prereg: `b9f9061e74e0c98c5186b2d7960c841848665d48`.
- `PREREG_YIELD_1C.md` conferiu entre blob e disco:
  `341987689558cef4f01c50eb3ab1073dc7343ead9d8fe76e159612c6828207c2`.
- Código congelado em `d4b4eb067f3205d6a9e33062a461a1380bd50495`.
  O diff contra esse commit foi vazio para `race_diagnostic.py`,
  `reference_controller.py` e `test_pass_decision.py`.
- A suíte não foi reexecutada, conforme o prereg; a referência permanece
  20 falhas conhecidas / 380 passes / 3 skips.
- A R2-Y contaminada de YIELD-1B foi preservada como evidência:
  `2_R2_Y.log`, SHA-256
  `38aa106552fb3ab46bda308ac7361188ee33094e654bce0ec070dac863494096`.
- A exposição desta execução é o desvio anterior de comando; a R2-Y2 usou o
  modo standalone correto, sem `--pass-decision`.

## Comando e conclusão da corrida

Foi conferido flag a flag e executado uma única vez, em foreground, no
worktree principal, com as cinco variáveis congeladas unset:

```text
timeout --signal=TERM 2400s .venv/bin/python model_train/race_diagnostic.py \
  --controller professor --leader-yield --ticks 6000 --laps 99 \
  --track interlagos --seed 0 --weather seeded --variance off \
  --grid f1 --rejoin bearing \
  --out experiments/yield-1/2_R2_Y2.csv
```

O pipeline com `tee` terminou com exit 0. O CSV tem 30.000 linhas de dados
(mais duas linhas de metadados e o cabeçalho), 54 colunas, e o log registra
30.000 linhas produzidas. Não houve retry ou segunda corrida.

| Artefato | Resultado | SHA-256 |
|---|---:|---|
| `2_R2_Y2.csv` | 30.000 linhas de dados | `5cb49097fea9bb066e9bef5ae62f4ee7c6f9ceb70485448792d33b533ce5cdaa` |
| `2_R2_Y2.log` | exit 0 | `9190c14ffeb7e75e1bfaec96903490995e8a96a238da5e3d66da0400bfa8c916` |
| `2_R2_Y2_events.csv` | 291.997 eventos solver | `af8d8428d1380f2a80e309ba3a5653df1b93a528d8ff22dbe74ac1f6328171f1` |
| `4_AUDIT_YIELD_1C.json` | auditoria offline | `84143cf0509267b588669f325bb41f19a6b68fb2325a2b1285aef3bd156fb332` |

O CSV R2-Y2 é byte-idêntico ao baseline R1
`experiments/pass-1/1_R1_OFF.csv`, cujo hash é o mesmo
`5cb49097fea9bb066e9bef5ae62f4ee7c6f9ceb70485448792d33b533ce5cdaa`.

## Auditoria g2–g5

| Gate | Resultado |
|---|---|
| g2 — consumo por par | **FAIL**: os dez carros reportaram `engaged=0`, `consumed=0`, `aborted=0`; não houve par-alvo nem passagem com 10 m de vantagem |
| g3 — não-piora vs R1 | **PASS relativo**: a trajetória CSV é byte-idêntica a R1; contatos 5 Hz 4.156, hesitações 0, 32 voltas completas e mediana 134,0 s |
| g4 — transferência/carve-outs | **PASS estrutural**: nenhum yield ficou ativo e não houve engajamento em carve-out |
| g5 — paridade | **PASS**: não existe `t*` porque nenhum gatilho ocorreu; a igualdade byte a byte cobre toda a corrida |

O log também registra 8/10 carros com pelo menos uma volta, 12.143 amostras
fora do asfalto e 4.156 contatos carro-carro. Esses números são idênticos ao
R1 por causa da igualdade byte a byte; não constituem evidência de consumo.

## Veredito

**PARE/SUNSET definitivo da linha yield.** A execução standalone foi limpa,
mas o gate obrigatório g2 falhou com consumo zero. Conforme o prereg, arquiva-se
o mecanismo de cedência com o log e a auditoria como causa, encerra-se a
sublinha de passagem da Etapa 3 (cap-release e cedência) e o próximo pivô é a
Etapa 4. Não há promoção, não há nova corrida e o race default v10 permanece
intocado; `--leader-yield` continua default-OFF.
