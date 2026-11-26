# Errata operacional — nome frozen da pista de R3

**Adendo a:** `PREREG_FAIL_FORENSICS_1B.md` (`16910ef`).
**Antes de qualquer corrida válida; sem dado de simulação observado.**

A primeira invocação da linha de comando R3 usou `--track monaco`. O resolver
case-sensitive tentou abrir `tracks_frozen/monaco_v1.json`, ausente, e lançou
`FileNotFoundError` antes de carregar pista/atores ou iniciar o simulador. Não
foi produzido CSV. O wrapper então executou `cmp` contra um arquivo inexistente
e gravou uma linha `ANCHOR_MISMATCH` incorreta; a linha foi removida e o log
preservado como `3_blind_monaco_attempt_invalid_track.log`, com anotação de que
a comparação não foi válida. Portanto não há divergência de âncora nem corrida
R3 concluída.

A pista declarada no prereg continua a mesma: o arquivo frozen é
`model_train/tracks_frozen/Monaco_v2.json` (SHA-256
`af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`). O nome
correto e case-sensitive para o CLI é `--track Monaco_v2`. Na próxima
invocação, somente esse argumento textual muda; seed, ator, observação, solo,
6000 ticks, clima seeded, governor, variância off, destino e âncora esperada
continuam exatamente como pré-registrados. Esta invocação usa o único re-smoke
contingente reservado para falha anterior à produção de CSV. Qualquer
divergência byte a byte no CSV válido resultante aciona PARE imediato e impede
R4; não haverá nova tentativa.
