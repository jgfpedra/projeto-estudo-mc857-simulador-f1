# PROJ-FIX-3 — PARE em g0 por hash esperado divergente

**Data:** 2026-10-23
**Estado:** PARE obrigatório antes de g1/g2 e da classificação.
**Orçamento:** zero corridas novas; zero smokes; nenhum agregado por classe.

## Freeze

O prereg PROJ-FIX-3, o classificador v1.2 e o selftest foram congelados no
commit `2330e9f`, antes de qualquer agregado por classe. O selftest sintético
passou. A suíte não foi reexecutada; a referência permanece 20F/352P/3S.

- `PREREG_PROJ_FIX_3.md`: SHA-256
  `d1bd9190183e50ff841e008ee5e4610d135765bfe5e449e056bbe33c8d13b1b2`.
- `proj_fix_3_classify.py` v1.2: SHA-256
  `bc0a7ba9a5a9e4194d6195f3bc830a7626133939b465829f8ee1225e30414bdd`.
- Selftest v1.2: SHA-256
  `3b9453b828cc35f31386c6c6d5e285e6b61624cb2209c777f3c438a91e1aa127`.
- Diagnóstico limitado à chave ALO: SHA-256
  `0efe1bc82568d39a92076539d5cf5e708b38926a03bdc5d19abe0d519de40990`.

## PARE em g0

O g0 confirmou os hashes esperados para replay, sidecar, log do replay, âncora
R4, tabela NIT-2, script v1.1, log PARE v1.1 e prereg PROJ-FIX-2. Porém, o
prereg congelado PROJ-FIX-3 espera SHA-256
`a3e7dd187f96116f5edf3c34a6e613af7357105b6fe454c4217a9b64cbb502ac` para
`PARE_PROJ_FIX_2.md`, enquanto o arquivo preservado tem SHA-256
`e287e5bdbc6a746089f0b53dd3a30e4d25b0ae43405bf3ef8ce9b5af2f0aa08c`.

O hash esperado ficou desatualizado após a revisão final do PARE v2 antes do
commit anterior. Como o prereg v3 já estava congelado, não o corrigi após o
gate. Log bruto `12_g0_sha256.log`, SHA-256
`a3321d81148c421437ca4168ca29a80444ec41c6ea4e14f9314d61073f130486`.

PARE acionado imediatamente: g1/g2, g3 e g4 não foram executados. Nenhuma
contagem de classe, p95, mapa NIT-2 ou anatomia C5 foi produzida. O diagnóstico
da única chave ALO continua apenas como Fase 0; nenhuma outra chave foi lida.
O prereg e o instrumento v1.2 permanecem intocados após o freeze. A retomada
requer novo prereg com hashes atuais e novo freeze antes de qualquer agregado.

Nenhuma simulação, smoke, alteração de comportamento, controle, física, pool
ou pista frozen foi executada ou modificada.
