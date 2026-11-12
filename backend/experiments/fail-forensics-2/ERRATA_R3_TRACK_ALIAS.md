# Errata operacional — alias válido para Monaco no CLI

**Adendo a:** prereg `16910ef` e errata operacional inicial `0ddb10e`.
**Estado:** nenhuma simulação foi iniciada; R3 ainda não tem CSV válido.

As duas tentativas de R3 falharam em `load_track_frozen` antes de carregar o
ator ou iniciar o engine. `--track monaco` procura `monaco_v1.json`; a primeira
errata então sugeriu `--track Monaco_v2`, que procura `Monaco_v2_v1.json`. Os
dois caminhos estão ausentes e nenhum dos processos gerou CSV. O primeiro
wrapper marcou incorretamente `ANCHOR_MISMATCH` porque comparou um arquivo
inexistente; esse rótulo foi substituído por `COMPARISON_NOT_VALID` no log
`3_blind_monaco_attempt_invalid_track.log`. O segundo log é
`3_blind_monaco_attempt_invalid_track_v2.log`.

Preflight read-only confirmou que o alias correto do CLI é **`Monaco`**: ele
carrega `Monaco Grand Prix (mirror 2021)`, 834 waypoints, SF 0, L=3335,2346 m,
short SHA `67ca11dc211c8c78`, do arquivo frozen declarado no prereg, SHA-256
`af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2`. A linha
de R3/R4 deve usar `--track Monaco`; seed, atores, número de carros, ticks,
clima, governor, variância e âncora permanecem inalterados.

As duas invocações foram anteriores à simulação e não constituem dados nem
divergência de âncora. A única tentativa extra permitida para falha pré-CSV
foi usada na segunda invocação, que também não carregou pista. Não haverá
terceira invocação sem autorização do dono. R3 permanece pendente; como R4
depende da validação byte a byte de R3, R4 não foi iniciada.

## Fechamento após autorização do dono (2026-10-23)

O dono autorizou uma invocação corrigida de R3 com `--track Monaco`. R3 passou
no gate: `3_blind_monaco_s0.csv` é byte-idêntico a `prof-monaco-1/aluno_s0.csv`
(SHA-256 `f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0`).
Com o gate satisfeito, a única R4 condicional autorizada também foi concluída.
Detalhes, métricas e hashes em `EXECUCAO_FAIL_FORENSICS_1B.md`; o preregistro
congelado não foi alterado.
