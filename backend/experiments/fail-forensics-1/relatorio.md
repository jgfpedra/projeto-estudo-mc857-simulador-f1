# FAIL-FORENSICS-1 — relatório de execução interrompida

## Veredito

**PARE no leak-check da etapa 2.** A corrida 1 (cego, Interlagos) e a corrida 2 (Composite, Interlagos) reproduziram os CSVs e eventos solver-side byte a byte. Porém, o Composite reportou 14 hesitações contra o valor 13 pinado no estado e no pedido. O log original F4v15 e a recontagem offline do CSV congelado também dão 14.

Isso aponta para uma âncora documental inconsistente, não para diferença nas corridas. A regra do prereg proíbe re-pin depois do número e manda parar diante de divergência; por isso as corridas Monaco não foram iniciadas e não há análise causal neste relatório.

| Pista × braço | N | Fora | Contatos | Pós-60s | Rolante | Hesitações | Integridade |
|---|---:|---:|---:|---:|---:|---:|---|
| Interlagos × cego | 1 | 22,1% | 3674 | 2482 | 136,0 s | 3 | CSV e eventos byte-idênticos |
| Interlagos × Composite | 1 | 25,2% | 752 | 292 | 140,0 s | 14 (pin: 13) | CSV e eventos byte-idênticos |

Clima: seed 0 DRY, sem transições. O Composite carregou o residual esperado. A divergência específica e a evidência de código/arquivo estão em [PARE.md](PARE.md). As etapas 3 e 4 e o veredito causal permanecem não executados.

## Dados preservados

Os dois CSVs, os dois arquivos de eventos solver-side e os logs das etapas executadas estão nesta pasta. Nenhum resultado do instrumento causal offline foi gerado, para evitar interpretar uma bateria que acionou o PARE.

## Recomendação para retomada

Ratificar a contagem de hesitações que deve governar a âncora. Se a contagem for alterada, registrar a evidência e a decisão antes de abrir novo prereg para as duas medições Monaco; não editar retrospectivamente o prereg congelado desta tentativa.
