# Errata pré-resultados — provenance e hash do PARE

**Data:** 2026-10-24 (America/Sao_Paulo)  
**Aplica-se a:** `PREREG_REJOIN_TEL_1.md` (commit `cc879b0`).  
**Momento:** antes da suíte completa e antes do replay; nenhum resultado novo
foi aberto.

1. O hash pinado para `PARE_PROJ_GATE_1.md` foi transcrito com um caractere
   incorreto. O SHA-256 correto, verificado em disco e em
   `git show a278cbe:backend/experiments/proj-gate-1/PARE_PROJ_GATE_1.md`, é
   `6b89f7b03b2313b76c73117e795d0b9089da309fb4cccc6527edb3396673acb9`.
2. O hash `69f87d163a56fe310212158ff527f58bd891828ffd0e8c5f91c3f5d7d41a0491`
   identifica o diagnostic writer frozen antes do ciclo (checkout anterior,
   também `git show f2bd199:backend/model_train/race_diagnostic.py`). Após a
   implementação autorizada de v3.5, não comparar o arquivo de trabalho com
   esse hash histórico. A proveniência atual do writer é o commit de
   implementação `b42f694`; runner e dados frozen continuam com seus pinos.
3. `0_prepins.log` preserva a tentativa de verificação que aplicou essas duas
   comparações equivocadas. Ela não leu nem analisou resultados novos. A
   verificação corrigida será registrada separadamente, conferindo cada fonte
   com a referência Git correspondente e comparando o writer v3.5 com seu
   commit de implementação.

Esta errata corrige somente a proveniência documental da comparação. Não muda
fontes de dados, definição de métrica, schema, orçamento, gates ou regra de
encaminhamento.
