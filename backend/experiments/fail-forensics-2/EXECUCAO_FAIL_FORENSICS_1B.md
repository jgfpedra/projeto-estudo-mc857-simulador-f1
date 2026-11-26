# FAIL-FORENSICS-1b — execução e fechamento

**Status:** Etapa 1 concluída, diagnóstico report-only. Nenhuma mudança de
comportamento, retreino, promoção ou re-pin foi feita.

## Execuções

Após autorização explícita do dono, R3 foi executada uma vez com o alias CLI
`--track Monaco`. A pista resolvida foi `Monaco Grand Prix (mirror 2021)`,
SF 0, 834 waypoints, short SHA `67ca11dc211c8c78`; o SHA-256 frozen foi
`af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`. O CSV
R3, `3_blind_monaco_s0.csv`, tem SHA-256
`f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0` e passou
`cmp` byte a byte contra `prof-monaco-1/aluno_s0.csv`: **ANCHOR_MATCH**. Foram
3000 linhas, zero transições de clima, 45,0% de amostras fora e uma hesitação
conforme o instrumento. Os dois logs de resolução inválida anteriores são
preservados e não produziram CSV nem dados.

Como o gate de R3 passou, a única R4 autorizada foi executada: Composite
Monaco, 10 carros, 6000 ticks, seed 0, `grid,compound`, clima seeded, governor
`vplan`. Foi a primeira medição exploratória, **N=1**, sem gate de performance.
Houve zero transições de clima. Hashes registrados:

| Artefato | SHA-256 |
|---|---|
| Monaco frozen | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| residual v15 | `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6` |
| CSV R4 | `6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022` |
| eventos solver-side R4 | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |

R4 produziu 30.000 linhas, 110.794 pontos de contato solver-side agrupados em
29 episódios, 1.477 amostras de contato carro-carro no resumo do runner,
12.945/30.000 amostras fora (43,15%), 346 episódios off-track, 120 janelas
presas e 12 hesitações. O proxy de salto de projeção registrou 112/50/45
eventos nos limiares ≥10/20/30 m, com p95 de erro 1.122,90 m.

## Veredito offline

O classificador consumiu as 14 entradas preregistradas: Interlagos cego e
composite; cinco arquivos Monaco professor e cinco aluno; R3 cego; R4
composite. Os cinco arquivos por braço Monaco repetem os mesmos dados e só
mudam o comentário de seed no cabeçalho; não são cinco realizações
independentes. R3 reproduz o aluno existente, e R4 permanece N=1. O CSV
classificado e o relatório completo estão em `veredito/`.

Na tabela pista × braço × causa, recuperação domina em Interlagos cego (106
saídas, 51 janelas presas, 3 hesitações), Interlagos composite (154, 68, 13),
Monaco aluno/cego (28, 12, 1 por arquivo) e Monaco composite (280 saídas, 93
janelas presas, 11 hesitações, 111 saltos). No Monaco composite também foram
classificados 29 episódios de contato e 55 saídas como curva; a atribuição
mecânica usa a precedência congelada e não é prova contrafactual.

Os CSVs não guardam coordenadas XY nem o índice cru de `nearest_segment`.
Assim, “salto” é o proxy preregistrado `|Δs_wrapped − Δcum_dist|`, e os índices
de segmento usados para localizar eventos são derivados de `s` na geometria
frozen. A recomendação para Etapa 2 é registrar XY e o índice bruto de
`nearest_segment` sincronizados com odômetro, autoridade e pontos do solver;
definir e revisar o corredor/bordas permitidos de Monaco antes de qualquer
gate. B3' (hesitações ≤3) e ANTI-D3-1 (primário) continuam FAIL. Nenhum gate
novo foi criado.

## Arquivos e verificações

- `3_blind_monaco_s0.csv` e `.log`; R3 coincide byte a byte com `aluno_s0.csv`.
- `4_composite_monaco_s0.csv`, `_events.csv` e `.log`; metadata e hashes da
  pista/residual foram gravados no log no mesmo passo.
- `veredito/relatorio.md`, `resumo_corridas.csv`, `eventos_classificados.csv`,
  `saltos_projecao.csv`, `causas_pista_braco.csv` e `casos_exemplares.csv`.
- Os selftests golden do classificador e do veredito de saídas passaram antes
  das corridas. A suíte após a errata E3 ficou em 20F/349P/3S; nenhum código
  de comportamento ou teste mudou nesta medição.
