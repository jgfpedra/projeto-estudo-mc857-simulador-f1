# EXECUCAO_C8_0 — referência de produção

**Data:** 2026-11-06
**Branch:** `feat/sanidade-produto`
**Perfil:** `composite`
**Status:** execução concluída; aguardando PARE de Closing do Dono.

## 1. Comando e orçamento

As dez corridas foram executadas serialmente, a partir de `backend/`, com
`--profile composite`, `--n-cars 10`, `--ticks 6000`, `--laps 99`,
`--weather seeded`, `--gov vplan`, `--variance off`, `--grid f1`, `--seed 0`
e `--variedade N`. Os defaults promovidos ativaram
`--rejoin-handoff align` e `--rejoin-ramp`.

Cada corrida teve duas leituras de `base_metrics` e duas leituras de
`realismo_metrics`, totalizando 40 leituras determinísticas. Cada par foi
comparado com `cmp=0`.

## 2. Matriz D2

| corrida | pista | N | exit | linhas CSV | sidecar | rejoin-handoff | rejoin-ramp | integrity |
|---|---|---:|---:|---:|---|---|---|---|
| INT_N0 | Interlagos | 0 | 0 | 30.002 | não vazio | align | enabled=True | true |
| INT_N1 | Interlagos | 1 | 0 | 30.002 | não vazio | align | enabled=True | true |
| INT_N2 | Interlagos | 2 | 0 | 30.002 | não vazio | align | enabled=True | true |
| INT_N3 | Interlagos | 3 | 0 | 30.002 | não vazio | align | enabled=True | true |
| INT_N4 | Interlagos | 4 | 0 | 30.002 | não vazio | align | enabled=True | true |
| MON_N0 | Monaco | 0 | 0 | 30.002 | não vazio | align | enabled=True | true |
| MON_N1 | Monaco | 1 | 0 | 30.002 | não vazio | align | enabled=True | true |
| MON_N2 | Monaco | 2 | 0 | 30.002 | não vazio | align | enabled=True | true |
| MON_N3 | Monaco | 3 | 0 | 30.002 | não vazio | align | enabled=True | true |
| MON_N4 | Monaco | 4 | 0 | 30.002 | não vazio | align | enabled=True | true |

## 3. Métricas canônicas

O campo `canonical.metrics_sha256` do `realismo_metrics` coincide com o
`metrics_sha256` produzido por `base_metrics` em cada corrida. O hash próprio
do payload de `realismo_metrics` é reportado separadamente.

| corrida | voltas | contatos 5 Hz | fora (%) | base/canonical SHA-256 | realismo payload SHA-256 |
|---|---:|---:|---:|---|---|
| INT_N0 | 42 | 332 | 24,7 | `0c15d661a8d941f5f3e7b88e4d5ec65913a32589bdb954a8ad1d15e1aa386cde` | `366024a30a1791f260c9a9a3114510d2658bad6f8f0f85df17bcfb75184dab27` |
| INT_N1 | 42 | 248 | 24,3 | `f71f107d9927d354e8303eead2f27d68d1a56aca74bce5db461018427bac1601` | `f663911f7f4e3ea618834001ac72c0b2743d01cd7466959fa17aac469356e3ae` |
| INT_N2 | 42 | 457 | 25,4 | `e5ad4f421051ac0e268aac28985718977cf2242da73dce9ab70835930bdd0839` | `a74f2fe251f574dd147e9b4ae510a420791fea2b0340edb5f458939318f10c5a` |
| INT_N3 | 43 | 245 | 24,0 | `d58ef0e39542aa65a8c81e1ca258cf6c95a753c11f915a6873221a03c3c7f588` | `5932125f0a23c1862e3fb63f382d7b4de75fb47beeb4377355283cf7b5ce85fa` |
| INT_N4 | 42 | 440 | 25,0 | `926a282d0f082786c31e0e888d92709601eb1da718a7d2e27faf67f1d6af87fb` | `15ea7eb2245569a5b401b955d7d0456973e694f2a4cae8f9c37d0a732ece1aa9` |
| MON_N0 | 31 | 292 | 43,8 | `6da5f96f5fcd3d24134c9814f833d089adb30ed9a36229d67d51706ec5fe1ee4` | `d606b0ab96a2058da4f68192a2c8426b33144011d9a72e31de9ea62717ea671f` |
| MON_N1 | 31 | 607 | 45,1 | `a7f6b8c217002a3974cebbef3d451f967df8336b8798656ec08becaef9a94453` | `d566a1defc690def1ab5a24dc05d8713923d4176767ebc09c7c87c7476fa26ad` |
| MON_N2 | 30 | 303 | 45,9 | `b14dbb958c7851dddd43551f5d27efb5445093707cb343e081cee1bd64704cda` | `455f25d27beb84c9e41c56d84ea0a3f120f4efdbea320067e5e186917243ea61` |
| MON_N3 | 26 | 1003 | 45,8 | `b9b98e238b1562c157ee566b863c4cbf80b9fb0e79c526c7269dafef350d4bd8` | `22dbfc49a18d3f00b97997291624d9c4e3a6d41100398922096809e27586514a` |
| MON_N4 | 30 | 290 | 45,7 | `572ed98eb198f6153a070b64815a433f704190fd4d5d24544ca60df89585f094` | `5b2caf70add3c50daf16811edacd1adea12d19ff0d92a828f7c74b0d089e3eb1` |

## 4. Auditoria de determinismo

Para cada linha da matriz foram gerados:

- `<run>_base_metrics.json` e `<run>_base_metrics_read2.json`;
- `<run>_realismo.json` e `<run>_realismo_read2.json`;
- `cmp` byte a byte com exit code 0 em cada par;
- `integrity.ok=true`;
- igualdade entre `canonical.metrics_sha256` e `base_metrics.metrics_sha256`.

Assim, os 10 pares de leituras de `base_metrics` e os 10 pares de leituras de
`realismo_metrics` foram confirmados, totalizando as 40 leituras previstas.

## 5. Conclusão

O C8-0 foi executado dentro do orçamento fechado e dos critérios D2. As dez
referências de produção, seus sidecars, logs e extrações determinísticas estão
presentes. Este documento registra apenas a execução; não autoriza promoção
adicional, alteração de código ou commit pelo executor.
