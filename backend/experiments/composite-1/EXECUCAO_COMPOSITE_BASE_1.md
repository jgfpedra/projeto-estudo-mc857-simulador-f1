# EXECUCAO_COMPOSITE_BASE_1 — primeira medição quantitativa da linha Composite

Data: 2026-10-26 (America/Sao_Paulo).
Branch: `feat/sanidade-produto`.
Freeze de referência: `d1e811e1fef8282a38f386a80aab8631bf83ac33`.
Emenda operacional do dono (B.1): `84c44add218cf81014b61c42c467992e51d4ae52`.

---

## 1. Contexto e disclosure da quarentena

Entre 20:40 e 20:47 de 2026-10-26, antes do turno formal da etapa B, foi executado o teste de suíte g0 e iniciado um lançamento R1 com proveniência quebrada (`1_R1_INTERLAGOS_RACE.log` com exatos 42 bytes — banner PyBullet — por encerramento do processo antes do flush de stdout pelo `tee`). A física do simulador correu até o tick 5998/6000 com 30.002 linhas no CSV e sidecar completo, mas o log sem sumário impedia certificação de gate e leitura determinística pelo extrator.

Conforme a Emenda B.1 commitada em `84c44ad`:
- O log de suíte g0 de 20:44 (`0_full_suite_base_1.log`, SHA-256 `db0abd33…`) foi conferido, atestado (20F/430P/3S, fail-set byte-idêntico ao 1G) e commitado pelo dono.
- Os 3 artefatos do lançamento pré-formal de R1 foram movidos intactos para quarentena em `experiments/composite-1/quarantine_base_1_prelaunch_20h44/` com README e SHAs registrados (`main`: `8872feb3…`, `events`: `0fb20fc7…`, `log`: `8e95cc79…`). NUNCA foram nem serão lidos para métricas nem usados como proveniência.
- A pasta `experiments/composite-1/base-1/` foi liberada limpa para as 4 corridas formais, com orçamento estrito de 1 shot formal por corrida.

---

## 2. Fase B-0 — Gate g0 (suíte completa)

O log `experiments/composite-1/0_full_suite_base_1.log` (SHA-256 `db0abd330786cbfcae605fe3b19c9e5d78c74506da2849f1118a08b537e67561`), commitado no freeze operacional `84c44ad`, certifica:

- **Coleta:** 453 testes (446 do baseline 1G + 7 testes novos de `test_base_metrics.py`).
- **Resultado:** Exit code 1 esperado; **20 failed, 430 passed, 3 skipped, 99 warnings** em 196.60s.
- **Fail-set:** Byte-idêntico à referência congelada g0 1G (`0_full_suite_collect_1g.log`, SHA-256 `369874d3490956c53e651c9456590fb594121a2b552792f79c422a6b4a6d2357`). Zero falhas novas.

---

## 3. Fase B-1 — Matriz congelada de corridas (R1 → R4)

Todas as 4 corridas foram executadas serialmente em foreground com `set -o pipefail` e `timeout --signal=TERM 2400s`, sob o regime canônico: 10 carros, 6000 ticks, 99 laps, `--seed 0 --weather seeded --gov vplan --variance off --grid f1 --rejoin bearing`.

Antes de cada corrida, confirmou-se que nenhum dos 3 caminhos de saída pré-existia.

| Run | Pista | Perfil / Ator | Papel | Exit | Main CSV (linhas) | Events sidecar | Status Gate |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **R1** | Interlagos | `--profile composite` | Primário (Composite) | 0 | 30.002 | Presente (23.837 lin) | **PASS** |
| **R2** | Interlagos | `--actor v10_dagger --obs-mode edge` | Controle primário (race-blind) | 0 | 30.002 | Presente (34.318 lin) | **PASS** |
| **R3** | Monaco | `--profile composite` | Secundário (Composite) | 0 | 30.002 | Presente (23.043 lin) | **PASS** |
| **R4** | Monaco | `--actor v10_dagger --obs-mode edge` | Secundário (race-blind) | 0 | 30.002 | Presente (29.751 lin) | **PASS** |

### Hashes SHA-256 dos 12 artefatos de corrida

```
# R1 Interlagos Composite
8872feb3e9a7c62963423f3c9fe5b7c5f2dfa91cad6f1d18cac0489a369844bd  experiments/composite-1/base-1/1_R1_INTERLAGOS_RACE.csv
0fb20fc74d84d5809c96e756d8a801bf6aecc98a25927c74d8e7fef27e69a32d  experiments/composite-1/base-1/1_R1_INTERLAGOS_RACE_events.csv
795f4241ac3ef7a35e25c2224f474d0ba45be27e4d380003343f51509cb2facc  experiments/composite-1/base-1/1_R1_INTERLAGOS_RACE.log

# R2 Interlagos Race-Blind
9d2a08427d4c5bdad0d6611df2caa7b4d7f02c5a5584c71a49d412c763c67e12  experiments/composite-1/base-1/2_R2_INTERLAGOS_RACE_BLIND.csv
4260568e2b453899cfc12e25576d780a2592338cd8909a369a7e4a3a3ce781ed  experiments/composite-1/base-1/2_R2_INTERLAGOS_RACE_BLIND_events.csv
7219adfd9809d0e3352104d0035afd6b30a7fc7ab2c8a39b150b77ca902f71a1  experiments/composite-1/base-1/2_R2_INTERLAGOS_RACE_BLIND.log

# R3 Monaco Composite
ad41941c1370b6c26a8c4d85e292c211d04493897183094df84eea5f1fef6d76  experiments/composite-1/base-1/3_R3_MONACO_RACE.csv
7cf6d556ff1499604485bd86bb5cd2846c9150dd64205dc9e68cc13fc42fb64d  experiments/composite-1/base-1/3_R3_MONACO_RACE_events.csv
1b1b32d6b41bf38f5f3b632edcf6d9803941a217a5a950740ff76ea0712018ae  experiments/composite-1/base-1/3_R3_MONACO_RACE.log

# R4 Monaco Race-Blind
15fb3da069adb7369741e90fdffca00f12cbe2abd75481b217c9c962bfacdd11  experiments/composite-1/base-1/4_R4_MONACO_RACE_BLIND.csv
8a5f461e010571341528a17ddf2aa612f245b74152755d3ef1e1596b5c4ca527  experiments/composite-1/base-1/4_R4_MONACO_RACE_BLIND_events.csv
533432f3872f3cb343ff0e57dc4f7fb6ab9499cff9d733704d5528ebb052877e  experiments/composite-1/base-1/4_R4_MONACO_RACE_BLIND.log
```

---

## 4. Fase B-2 — Extração e Determinismo (8 leituras, 2 por corrida)

O extrator report-only congelado (`scripts/base_metrics.py`, commit `d1e811e`) foi executado exatamente duas vezes para cada corrida:
1. Primeira leitura: gravação com flag `--out` (modo de criação exclusiva `x`, sem sobrescrita).
2. Segunda leitura: execução com os mesmos parâmetros para stdout, validando se o hash `metrics_sha256` reproduz idêntico bit a bit.

| Run ID | Arquivo de Métrica | SHA-256 do Arquivo JSON | `metrics_sha256` (1ª Leitura) | `metrics_sha256` (2ª Leitura) | Determinismo |
|---|---|---|---|---|:---:|
| `R1_INTERLAGOS_RACE` | `1_R1_INTERLAGOS_RACE_metrics.json` | `fe17ac20b5723167db537a8c811a5437a181d015da7207c029b5f5e40ab2e957` | `ecd3c4f8ef6551ce6ed6d0f4b60a174afb49637941d5147cae98594ec17035f8` | `ecd3c4f8ef6551ce6ed6d0f4b60a174afb49637941d5147cae98594ec17035f8` | **IDÊNTICO** |
| `R2_INTERLAGOS_RACE_BLIND` | `2_R2_INTERLAGOS_RACE_BLIND_metrics.json` | `72bcb350efb4216b27e75a11d50c9c5378feefa3a41c53be1f9e095d7228fbe0` | `e83106fb326b94833182a8f29e92035a67499e747db2b6042147fdb82d687f07` | `e83106fb326b94833182a8f29e92035a67499e747db2b6042147fdb82d687f07` | **IDÊNTICO** |
| `R3_MONACO_RACE` | `3_R3_MONACO_RACE_metrics.json` | `59e793e65e50bb8c54c912532baa48ae849625abcb03b3ccd341c8cf83365b5a` | `7ea9703af51a7522e9b2ee1d281f54f0b3959fd7bc84d7c177d16f8bcbfc193b` | `7ea9703af51a7522e9b2ee1d281f54f0b3959fd7bc84d7c177d16f8bcbfc193b` | **IDÊNTICO** |
| `R4_MONACO_RACE_BLIND` | `4_R4_MONACO_RACE_BLIND_metrics.json` | `a2e254a099e37b554bbfa1beab136bea0f1774b2b263d38fcc6def9dec253471` | `36d59241145f918cd7235503b122de0c8c79f2bc5285d686a00d72647e181a12` | `36d59241145f918cd7235503b122de0c8c79f2bc5285d686a00d72647e181a12` | **IDÊNTICO** |

---

## 5. Fase B-3 — Proveniência Git

Foram criados estritamente os 2 commits autorizados, após conferência dos hashes antes do staging:

1. **Commit 1 (12 artefatos de corrida):**
   `7cb4f1901eb45f25757e7f755d904c8033c0623f` (`7cb4f19`)  
   Mensagem: `"Provenance COMPOSITE-BASE-1 races R1-R4"`  
   Arquivos: 4 logs + 4 mains CSV + 4 events sidecars sob `experiments/composite-1/base-1/`.

2. **Commit 2 (4 métricas JSON):**
   `ceeaa2062f535593643785eeca0aabd807a3cd19` (`ceeaa20`)  
   Mensagem: `"Metrics COMPOSITE-BASE-1 (extractor d1e811e)"`  
   Arquivos: 4 JSONs de métricas sob `experiments/composite-1/base-1/` (o log g0 já constava commitado no freeze `84c44ad`).

---

## 6. Fase B-4 — Tabela de Comparação e Deltas Absolutos (Composite − Race-Blind)

Deltas absolutos computados diretamente das métricas extraídas (`Composite − race-blind`). Não há thresholds nem classificação PASS/FAIL (BASE-1 é estritamente descritivo e report-only).

| Métrica Extratora | Interlagos: R1 (Composite) | Interlagos: R2 (Race-Blind) | **Delta Interlagos (R1 − R2)** | Monaco: R3 (Composite) | Monaco: R4 (Race-Blind) | **Delta Monaco (R3 − R4)** |
|---|---:|---:|---:|---:|---:|---:|
| **Presos (carros)** | 10 | 10 | **0** | 10 | 10 | **0** |
| **Fora (%)** | 29,3% | 22,6% | **+6,7 pp** | 45,4% | 47,5% | **−2,1 pp** |
| **Hesitações** | 11 | 2 | **+9** | 15 | 8 | **+7** |
| **Contatos 5 Hz total** | 489 | 764 | **−275 (−36,0%)** | 388 | 696 | **−308 (−44,3%)** |
| **Contatos 5 Hz (t ≤ 60 s)** | 183 | 490 | **−307 (−62,7%)** | 302 | 428 | **−126 (−29,4%)** |
| **Eventos solver (linhas)** | 23.835 | 34.316 | **−10.481 (−30,5%)** | 23.041 | 29.749 | **−6.708 (−22,5%)** |
| **Voltas total (cruzamentos)** | 41 | 49 | **−8** | 33 | 32 | **+1** |

### Contatos por par do solver (top 5 pares por corrida)

- **R1 Interlagos Composite (total 15 pares ativos):**
  1. `GAS-NOR`: 12.781 (53,6%)
  2. `PER-SAI`: 6.573 (27,6%)
  3. `ALO-HAM`: 1.856 (7,8%)
  4. `ALO-GAS`: 911 (3,8%)
  5. `GAS-SAI`: 325 (1,4%)

- **R2 Interlagos Race-Blind (total 22 pares ativos):**
  1. `HAM-NOR`: 6.633 (19,3%)
  2. `PER-SAI`: 4.185 (12,2%)
  3. `ALO-GAS`: 4.043 (11,8%)
  4. `PIA-RUS`: 3.303 (9,6%)
  5. `ALO-VER`: 2.566 (7,5%)

- **R3 Monaco Composite (total 10 pares ativos):**
  1. `PIA-RUS`: 8.267 (35,9%)
  2. `PER-SAI`: 7.160 (31,1%)
  3. `ALO-GAS`: 3.938 (17,1%)
  4. `HAM-LEC`: 1.569 (6,8%)
  5. `HAM-RUS`: 816 (3,5%)

- **R4 Monaco Race-Blind (total 17 pares ativos):**
  1. `PIA-RUS`: 7.271 (24,4%)
  2. `HAM-LEC`: 5.265 (17,7%)
  3. `NOR-VER`: 3.868 (13,0%)
  4. `LEC-NOR`: 3.029 (10,2%)
  5. `GAS-NOR`: 2.666 (9,0%)

---

## 7. Disclosures honestos de medição

1. **Voltas por cruzamento de s:** O runner foi executado com o teto temporal de 6000 ticks a 10 Hz (600 s) e `--laps 99`. As "voltas total" reportadas (32–49 voltas somadas dos 10 carros, média de 3–5 voltas por carro) refletem cruzamentos físicos do marco inicial da pista (`s < s_anterior − 2000 m`), e não conclusão de 99 voltas regulamentares.
2. **Contatos por par:** Os eventos do sidecar registram cada ponto de contato por subpasso do solver de física (24 subpassos por tick de 0,1 s). Não são contatos físicos macroscópicos deduplicados.
3. **Calibração histórica A-OFF:** A corrida A-OFF não faz parte do contraste pareado de BASE-1. O A-OFF utilizou variância de grid e de compostos (`variance grid,compound`), enquanto o protocolo pareado R1–R4 utilizou variância estritamente desligada (`variance off`). A-OFF serviu exclusivamente para validação célula a célula das fórmulas do extrator.
4. **Segurança vs. Mobilidade:** A linha Composite demonstrou redução consistente e substancial de contatos carro-carro (−36% a −44% total; −29% a −63% no primeiro minuto da largada) e menor espalhamento de pares de colisão. Em contrapartida, em Interlagos registrou maior permanência fora da pista (+6,7 pp) e mais hesitações (+9 episódios).

---

## 8. Veredicto da Etapa B

Todos os gates foram estritamente cumpridos:
- g0 pinado conferido e auditado sem falhas novas.
- 4 corridas formais com exit 0, 30.002 linhas e sidecars completos.
- Extração de métricas 100% determinística (hashes idênticos entre leituras).
- Proveniência selada nos commits `7cb4f19` e `ceeaa20`.
- Nenhum código de produção alterado, nenhum treino executado, nenhum dump gravado.

Recomendação: O dono pode ratificar o fechamento de COMPOSITE-BASE-1 e autorizar a abertura da etapa **COMPOSITE-TRAIN-1**.

---

## 9. Apêndice do dono — verificação independente e disclosure de determinismo

Verificação executada pelo dono antes do closing (2026-10-27), sobre os bytes commitados em `7cb4f19`/`ceeaa20`:

1. **Identidade byte-a-byte formal vs quarentena (R1).** O main CSV e o events CSV da corrida R1 FORMAL têm SHA-256 idênticos aos do lançamento abortado em quarentena (main `8872feb3e9a7c62963423f3c9fe5b7c5f2dfa91cad6f1d18cac0489a369844bd`, events `0fb20fc74d84d5809c96e756d8a801bf6aecc98a25927c74d8e7fef27e69a32d`); o log diverge (`795f4241…` formal, 5.390 bytes com sumário completo do runner, vs os 42 bytes do banner em quarentena). Isto é a replicação de determinismo mais forte do projeto: dois lançamentos independentes (≈1 h de diferença, stdout quebrado vs íntegro) produziram física idêntica byte a byte, coerente com o precedente A-OFF/A-ON''. A re-execução formal foi real — a proveniência formal provém do log completo e do gate da execução nova; os bytes de quarentena permanecem intocados e jamais lidos para métricas (a comparabilidade de SHAs é resultado da determinismo, não cópia).
2. **Determinismo do extrator (3ª leitura por corrida).** O dono re-extraiu os 4 relatórios diretamente dos bytes formais; `metrics_sha256` reproduz EXATO em 4/4 (`ecd3c4f8…`, `e83106fb…`, `7ea9703a…`, `36d59241…`) — três leituras independentes por corrida, todas idênticas.
3. **Tabela §6 recomputada** pelos valores dos JSON de métrica: exata, número a número, incluindo os 14 deltas.
4. **Leitura honesta adicional para o TRAIN-1:** a métrica legado "presos" é degenerada neste regime — 10/10 carros em TODOS os 4 runs (e no A-OFF histórico). Não discrimina perfis neste limite e NÃO deve ser alvo de otimização ou release-criteria em ciclos futuros.
