# PROJ-FIX-2 — PARE antes da decomposição C1/C2/C3

**Data:** 2026-10-23
**Estado:** PARE obrigatório em g4; nenhuma decomposição declarada.
**Orçamento:** zero corridas de medição novas; zero smokes; replay existente reutilizado.

## Freeze e gates concluídos

O prereg e o classificador v1.1 foram congelados antes da classificação no commit
`8222dff`. O diff contra v1.0 contém somente docstring, `VERSION="1.1"` e
`PROJECTION_RUN="composite_monaco"`; selftest sintético PASS. A suíte não foi
reexecutada; a referência existente permanece 20F/352P/3S.

- PREREG `PREREG_PROJ_FIX_2.md`: SHA-256
  `a6eeeed29434a5767617e3c739f1435623d3c289ff6aa22a53bbb6b60baab28d`.
- Classificador `proj_fix_2_classify.py`: SHA-256
  `9d73a890964974b3f04d2261fe0806a21ec6b162b111aa89c28c7919c3704d8d`.
- Selftest sintético: SHA-256
  `f9f6a84ed8538b1ded286aa0ba65afef17bef166c9c5e73e75285de893b5f521`.
- Manifest de freeze: `6_freeze_manifest.log`.

g0 PASS: replay CSV `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7`,
events `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4`, log
`d88f14030e729716a730228fdca5e4dc8ac99d6dddeeab320a16e593496eb0a1`, âncora R4
`6360706f1b3dbf46ed3ad4998e3e3103cae14ea1054a084297cf2a5f423f1022` e tabela
NIT-2 `b9bcb14d9bb38dceabcbfddc9f90cb3b5bd2cc25fa6719a90ded52eb2b9bb739`
conferem com o prereg. Log g0 SHA-256
`f46cced1052ee362fb8bcd569b7dffc0e81e9fa07e43a4e13e28aebaa45ba942`.

g1 PASS: projeções do replay e da âncora iguais, SHA-256
`a2c96670e1c84198365468740929559a55f26e2c0f89b84ea7060dbc41044092`. g2 PASS:
71 campos por linha e 30.000 linhas. Log g1/g2 SHA-256
`b982ca2f1561128176945084f2d4839288008ed628a52859bf70de5753ac6d81`.

g3 PASS: `run=composite_monaco` seleciona 112 eventos ≥10 m, dos quais 45 ≥30 m;
`track=monaco`. Log SHA-256
`aa1e37ba7c7d8a6bfa19e475abb35f97df18f00a2db81bf0451487e0b4a17212`.

## PARE obrigatório em g4

A execução frozen v1.1 parou com:

`PARE: evento NIT-2 sem classe XY/ns_raw: ('ALO', 2130, 2132)`

Log bruto `9_classify_v11.log`, SHA-256
`3fe29ebed88da8bb67ea39cb4c14be500eb4131b75b8afebfd063e3d0a84e9ee`.
Nenhuma classificação completa, mapa 1:1 ou resumo por classe/p95 foi produzido.
Nenhuma conclusão C1/C2/C3 e nenhuma correção são propostas. O instrumento v1.1
permanece congelado e não foi alterado após o resultado. A retomada exige novo
prereg que resolva a chave do evento sem editar este instrumento.

Não houve novas simulações, smokes, alterações em controle/física, pools ou pistas
frozen. Os artefatos existentes permanecem preservados no diretório do ciclo.
