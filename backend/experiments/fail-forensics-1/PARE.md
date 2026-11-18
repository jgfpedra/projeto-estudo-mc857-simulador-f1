# PARE — FAIL-FORENSICS-1

**Status:** ciclo interrompido no leak-check da etapa 2; nenhum veredito causal emitido.
**Prereg:** `1e9ceee` — `PREREG_FAIL_FORENSICS_1.md`, congelado antes das corridas.
**Veredito offline:** `d631a46` — `scripts/fail_forensics_verdict.py`, commitado antes das corridas.
**Mudança de comportamento:** nenhuma.

## Evidência da execução serial

| Etapa | Execução | CSV / evento | Resultado do leak-check |
|---|---|---|---|
| 1 | Cego, Interlagos, seed 0, 10 carros, 6000 ticks, `edge`, `vplan`, clima seeded seco, variância `grid,compound` | CSV SHA-256 `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733`; eventos SHA-256 `11e8c657b6ffc6ab65d98fbeb7af56983d1658447f0b1093edc8a862444ca3b9` | Ambos byte a byte idênticos às âncoras. Métricas: 3674 contatos, 2482 pós-60s, 136,0 s rolantes, 3 hesitações, 22,1% fora. |
| 2 | Composite, Interlagos, seed 0, 10 carros, 6000 ticks, `vplan`, clima seeded seco, variância `grid,compound` | CSV SHA-256 `512ba0d2553b1c3acacc69582a6877a883f570aee4cf72658a7925f164310155`; eventos SHA-256 `1f79529e40117dd5eb3e53dcfe18ad6598e95d6ce2f1ccc83d377b82ccce7b54` | Ambos byte a byte idênticos às âncoras. Métricas: 752 contatos, 292 pós-60s, 140,0 s rolantes, 25,2% fora. O runner reportou **14 hesitações**, enquanto o pin do pedido/estado dizia **13**. |

As etapas 3 e 4 não foram iniciadas, conforme a regra de PARE. Nenhuma tabela causal ou métrica de saltos foi calculada sobre esta bateria.

## Leak-check da contagem de hesitações

1. A reprodução Composite carregou a pista frozen com SF 729, short SHA `164876196eb12174`, SHA-256 completo `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613`; o clima teve zero transições. O residual carregado reportou SHA `6a2dbf53a69fcac7`.
2. CSV e eventos reproduzidos são byte a byte idênticos aos arquivos F4v15 existentes; portanto a simulação não divergiu da âncora bruta.
3. O log original `experiments/f4v15-wiring/2_allcomposite.log`, linha 71, também registra **14 hesitações**. A aplicação offline da fórmula atual de `race_diagnostic.py` ao CSV âncora reproduz 14 episódios. Os episódios contados são: ALO 435,8–436,2 s; GAS 68,2–69,2, 452,2–453,0 e 571,4–571,8 s; HAM 110,8–111,6 s; LEC 402,4–403,2 s; NOR 167,4–167,8 s; PER 280,4–281,0 e 559,6–560,2 s; PIA 427,0–427,6 e 475,2–475,6 s; VER 66,8–67,2, 68,8–69,4 e 205,6–206,0 s.
4. O bloco de contagem (`v<0,5 m/s`, `t>20 s`, duração `0,3 ≤ d < 3,0 s`) tem proveniência em `race_diagnostic.py` desde `439f402`; o log F4v15 arquivado e o CSV de âncora já refletem 14.

**Conclusão do leak-check:** não há sinal de diferença de simulação ou de clima. Há uma contradição documental no valor de hesitações esperado: o estado/prompt pinam 13, mas o log original e o CSV congelado sustentam 14. O prereg foi preservado sem re-pin pós-número; pelo critério pré-registrado, o ciclo para aqui.

Nota de proveniência: no run 1, uma aspa incorreta impediu o cabeçalho auxiliar de SHA antes da simulação; o próprio runner registrou SF e hash curto, e o SHA completo foi acrescentado ao mesmo log após a execução e conferido contra o prereg. CSV e eventos passaram a comparação byte a byte. Não houve efeito nos dados.

## Próximo passo necessário

O dono deve ratificar qual registro governa a contagem (13 no pin ou 14 no log/CSV original). Qualquer retomada das etapas Monaco exige novo prereg que resolva essa contradição antes de qualquer nova simulação; este ciclo não autoriza reexecução, re-pin nem interpretação causal.
