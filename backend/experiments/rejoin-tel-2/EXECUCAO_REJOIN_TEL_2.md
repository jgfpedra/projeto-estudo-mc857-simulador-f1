# EXECUÇÃO REJOIN-TEL-2 — replay v3.5 e audit report-only

**Data:** 2026-10-24 (America/Sao_Paulo)
**Status:** corrida concluída; g1–g4 PASS; sem promoção ou mudança de código.
**Prereg congelado:** commit `9f9dc53`, SHA-256
`7ff5863263b381ca244452ec03ea62c0cbfc0efdc4650827abd308023e023820`.
**Código frozen:** `b42f694`; audit v1.0 SHA-256
`e106db7882edb58d603358855e86c5776373e0ddba28f676ee3ee7e6560f1d25`.

## Execução e proveniência

Foi executada exatamente uma corrida R4 canônica em foreground com `tee`,
timeout pré-declarado de 9 minutos, sem tarefa concorrente. Configuração:
composite, 10 carros, 6000 ticks, 99 laps, Monaco, seed 0, clima seeded,
governança `vplan`, variância `grid,compound`, `--writer-v35`. Exit code **0**;
tempo observado aproximado **3m18s** (criação/última gravação do log); nenhum
sinal ou timeout. O log registra 30.000 linhas e 110.794 eventos de contato.

| Artefato | SHA-256 |
|---|---|
| CSV v3.5 | `d950f7a60d47d125d829f5c4bf0302eadd9eb8ef7001cd17e690ba7950f6ac95` |
| Events v3.5 | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| Log da corrida | `5438a494449be5dd2fc275e1931a52449eadaed17c72523e69956f3c2bb80280` |
| Log de g2 prefixo | `6226c7dc7c3faeb9665f1f470f532466583500f450dc76c3e609ef5bf489fa26` |

Os pinos exigidos foram comparados em disco e por `git show`; todos coincidiram
com os SHAs congelados no prereg: âncora R4 `6360706f…`; replay v3.4
`6698b55b…`; events `b99007d0…`; Monaco frozen `af312595…`; suíte de referência
`8755ea47…`; audit v1.0 `e106db78…`. Antes do run, os caminhos de saída novos
estavam ausentes, não havia replay ativo e o diff de produção contra `b42f694`
era vazio. O log parcial de REJOIN-TEL-1 (42 bytes) continua preservado no
caminho original. O sidecar events desta corrida é byte-idêntico ao R4 v3.4
pinado (mesmo SHA).

## Gates

| Gate | Resultado e evidência |
|---|---|
| Pré-condições | **PASS** — proveniência dupla dos seis pins; nenhum drift em writer/runner/audit; nenhum processo órfão; saídas novas ausentes; timeout de 9 min congelado antes do run. |
| g1 — schema/completude | **PASS** — audit carregou 80 campos na ordem frozen e 30.000 linhas; 10 carros × 3.000 amostras, ticks `0,2,...,5998`, sem duplicatas ou lacunas; 345 janelas visíveis. |
| g2 — passividade | **PASS** — 30.001 linhas comparadas, cabeçalho incluído; `split(',')[:71]` byte-idêntico ao R4 v3.4 em todas; referência SHA `6698b55b…`, CSV novo SHA `d950f7a6…`. Log `3_g2_prefix.log`. |
| g3 — telemetria | **PASS** — audit v1.0 validou os 9 campos finitos e o schema frozen; IDs/idades e continuidade por carro; âncora estável durante cada janela off; zeros de alvo/κ quando ausentes; rumo de reentrada reconstruído pela geometria; 345 janelas, 344 reentradas e 1 janela censurada. A captura pass-through do alvo é propriedade do writer frozen e dos testes já aprovados em `b42f694`; o audit preserva a distinção de fase indicada no prereg. |
| g4 — suíte | **PASS como referência; não reexecutada** — log pinado em `8755ea47…`, resultado 20 falhas/363 passes/3 skips e as mesmas 20 identidades canônicas. |

O audit report-only gerou os seguintes arquivos em `autopsia/`:

| Saída | SHA-256 |
|---|---|
| `3_rejoin_windows.csv` | `1df9fdcff1082dffc0e9571b53e6cdc26d7f2daf1af59495e024a032f140e129` |
| `4_hesitations.csv` | `0a479deaf34b5ba4bdba92e384d4497c01cdefbac533cf43d28cc83d9ee3c89e` |
| `5_summary.json` | `74fccba9e9c5bafed52a9b150877f0598c4fb87da4e5fc31a8cf46cf60c08cf3` |
| `6_veredito.md` | `37164fe3220709908e46fe4bc5692f399c00536d3eadd8b65ebeb856b201fddc` |
| `7_hashes.json` | `b5cbc322252ce500c15c6c23b80b3f84d653192c08351862aadb54e2b5cf4302` |

## Achados e recomendação ao dono

- Reentradas com `|heading_err_deg| > 20°`: **302/344 (87,79%)**.
- Pearson entre erro angular assinado e segunda saída em até 10 s:
  **−0,3613 (n=344)**. O sinal é negativo, não positivo.
- Tempo de retorno observado por janela: **p50 5,70 s; p95 24,74 s; máximo
  36,80 s**. Uma janela foi censurada à direita.
- Hesitações R4: **12 no total**, igual ao número OFF publicado; **11** foram
  associadas a uma reentrada anterior em até 10 s. A referência ON publicada
  é 28. Tempo de retorno R2-ON não existe nas fontes autorizadas.

**Recomendação única: opção (b)** — arquivar a hipótese angular da Etapa 2 com
os critérios deste ciclo evidenciados e avançar à Etapa 3. Embora a maioria das
reentradas exceda 20°, a associação com a segunda saída é negativa; portanto,
a assinatura combinada frozen para RECUP-2 não ocorreu. Isto não demonstra
ausência de defeito angular nem identifica causalidade. Nenhuma correção foi
implementada, nenhuma promoção ocorreu, a flag continua default-OFF e a suíte
de referência permanece intacta.
