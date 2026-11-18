# Errata pré-análise — PROJ-FIX-5 v1.0

O primeiro preflight do instrumento parou antes de escrever tabelas ou métricas:
o preregistro chamou o tempo por evento de `tick_s`, mas o mapa congelado nomeia
essa coluna `t_s`. A coluna representa o timestamp em segundos já previsto na
definição de intervalo inter-evento; nenhum outro campo, fórmula, fonte ou gate
muda.

O registro original permanece congelado e imutável. O instrumento corrigido
continua v1.0 e passa a ler `t_s`; o selftest sintético será reexecutado e um
manifesto novo congelará esta errata, o script e o log antes de qualquer nova
tentativa de anatomia. A primeira tentativa está registrada em
`20_PARE_schema_preflight.log`; ela não publicou nenhum número novo.
