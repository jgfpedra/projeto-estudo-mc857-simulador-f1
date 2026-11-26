# PREREG_C8 — mecanismo de gap-check na reentrada

**Data:** 2026-11-06
**Branch:** `feat/sanidade-produto`
**Estado:** aguardando Freeze do Dono. Este preregistro não autoriza simulação.

## 1. Escopo e dados congelados

O C8-A é report-only e deriva a anatomia exclusivamente dos dez artefatos do
C8-0 (`INT_N0..N4` e `MON_N0..N4`). Os oito artefatos ON do C7
(`N=5..8`, Interlagos e Monaco) entram somente como disclosure. Não haverá
simulação, treino ou alteração de código de produção nesta etapa.

Os dados `N=9..12` permanecem selados para a Fase C8-C e não podem ser
consumidos por C8-B.

## 2. Regra de ouro das constantes

**Toda constante numérica do C8 sai só do N=0: o perfil de velocidade na grama e os limiares do gap-check (gap, janela, teto). A anatomia de risco da reentrada (carro atrás × à frente, gap na reentrada), medida em N=0..4 e no C7 ON, entra como disclosure: ela só escolhe a forma do gap-check (direção e ponto de entrada) e nunca fixa um número.**

Em particular, `N=1..4` e C7 ON não podem ser usados para recalibrar o perfil,
o limiar de gap, a janela pós-retorno ou o teto de velocidade.

## 3. Mecanismo C8

O C8 combina:

1. **Perfil de velocidade na grama:** durante `offtrack`, limitar a velocidade
   por uma função monotônica do tempo fora e/ou de `abs(lat)`, derivada apenas
   da série `c8-0/INT_N0.csv` e `MON_N0.csv`. O perfil deve ser publicado no
   relatório de análise antes de qualquer implementação.
2. **Ponto de entrada do gap-check:** no primeiro frame `offtrack=1` para
   proteger a saída e novamente no frame de transição `offtrack=1 -> 0`,
   usando gaps longitudinais separados em `ahead` e `behind`.
3. **Precedência:** o gap-check tem precedência estrita sobre a concessão de
   autoridade do handoff `align` e sobre a rampa `--rejoin-ramp`. Nenhuma
   reentrada é liberada enquanto o gap não satisfizer o limiar congelado.
4. **CLI aditiva:** a flag do C8 será opt-in, default `OFF`, e não poderá
   alterar qualquer byte de uma corrida que não a habilite. A forma nominal
   é `--c8-gap-check` com opt-out explícito equivalente, se necessário.

Os detalhes de implementação permanecem fora deste preregistro até o Freeze.

## 4. Matriz de medição C8-B

Após autorização explícita do Dono:

- **2 controles OFF:** uma réplica Interlagos e uma réplica Monaco em `N=0`,
  com comparação byte a byte contra `C8-0/INT_N0` e `C8-0/MON_N0`,
  incluindo CSV principal, sidecar, log e extrações.
- **10 corridas ON:** Interlagos e Monaco em `N=0..4`, com a flag C8
  habilitada e demais defaults de produção preservados.
- **48 leituras determinísticas:** 12 corridas × 2 extratores × 2 leituras;
  cada par deve passar `cmp=0`, com `integrity.ok=true` e cross-hash canônico
  conferido.

Toda execução será serial e partirá de `backend/` com o prefixo explícito:

```text
cd /home/jovitor/unicamp/projeto-estudo-mc857-simulador-f1/backend && .venv/bin/python ...
```

## 5. Gates formais contra C8-0

| Gate | Critério |
|---|---|
| Primário | redução material de FORA-PRESO e/ou tempo fora, medida contra o OFF pareado de C8-0; a definição e o limiar material devem ser congelados antes da corrida |
| B-1 | contatos totais ON <= OFF + 2 sigma |
| R-1 | voltas totais ON >= 95% do OFF pareado |
| R-2 | fora% ON não piora mais que 1 ponto percentual contra OFF |
| Reentrada segura | novas saídas em até 5 s pós-retorno não podem aumentar; qualquer aumento exige PARE e análise do Dono |

Qualquer falha, divergência de bytes, ausência de sidecar ou cross-hash
divergente é PARE imediato. O C8 não será promovido por atender apenas o gate
primário se algum gate de não-regressão falhar.

## 6. Governança

O pacote C8-A (`c8a_rejoin_anatomy.py`, testes e `C8A_FINDINGS.md`) é
report-only. Este preregistro deve permanecer staged para revisão e Freeze do
Dono. Nenhum commit será realizado pelo executor, e nenhuma corrida poderá ser
iniciada antes do Freeze.
