# PREREG PROJ-GATE-1 — V-A âncora pegadora de rejoin

**Status:** V-A RATIFICADA pelo dono; implementação de pesquisa, opt-in e
default-OFF. **Promoção:** nenhuma. Race default continua v10/Blind; Composite
permanece research-grade. `--prof-repair` continua OFF por conflito com pacing
pós-reentrada. Física, ambiente, observações, clima, fitness, odômetro e writer
v3.4 ficam fora do fator.

## Hipótese e fator único

Nos 112 eventos já congelados, todos tinham `authority=rejoin` e `offtrack=1`.
O p95 de Δs-proxy era 1.127,55 m em C3 e 25,34 m em C5, enquanto o p95 do
odômetro era 1,87–3,31 m. Esses números são motivação pública herdada; não
serão reclassificados neste ciclo.

O fator é estabilizar o alvo de REJOIN durante off-track no runner. A flag
exata `--proj-gate`, sem aliases, default `False`, habilita no CLI de
`model_train/race_diagnostic.py` uma âncora por carro:

1. Ao observar uma amostra on-track, salvar a última pose física `(x,y)`, o
   arco `s`, o segmento bruto `ns` e o ponto projetado global daquele tick.
2. Na primeira amostra off-track, congelar o alvo de rejoin derivado dessa
   âncora; manter o mesmo alvo até reaquisição. Nenhum nearest-segment vivo é
   consultado para construir o alvo durante off-track.
3. Em off→on, usar a projeção global viva já calculada pelo runner e substituir
   a âncora pela leitura recém-readquirida. A próxima saída usa essa âncora.
   Se a corrida começa off-track sem âncora, usar o caminho legado até existir
   uma amostra on-track.
4. `s=0` e a volta pelo início da pista continuam válidos. A reaquisição usa
   `argmin` global existente em todos os segmentos; não restringir ao segmento
   anterior nem escolher segmento remoto que não seja o nearest global.
5. A âncora afeta somente a geometria do alvo de rejoin. Não muda `v_plan`,
   observação 46d traffic/edge, política/ator, física, `cum_dist`, lap/lap time,
   clima, fitness, authority fora do rejoin nem qualquer coluna do writer v3.4.
   Sem flag, o caminho legado deve ser byte-idêntico.

## Pontos do checkout verificados na FASE 0

| Caminho | Localização antes do freeze | Uso no ciclo |
|---|---|---|
| Projeção global do runner | `scripts/run_race_10_cars.py:724-740` | Fornece `s`, XY projetado e `argmin` global. |
| Estado off-track e alvo de gap-check | `scripts/run_race_10_cars.py:919-920,1049-1057` | Consumidor rejoin alternativo; mesmo alvo ancorado se o gap-check estiver ativo. |
| Alvo principal de rejoin | `scripts/run_race_10_cars.py:1073-1105` | Bearing para a projeção + ahead; ponto primário do fator. |
| Telemetria do runner | `model_train/race_diagnostic.py:981-1005` | CSV v3.4 mantém s/XY/ns_raw existentes, sem nova coluna. |
| CLI e construção de controllers | `model_train/race_diagnostic.py:476-575,727-825` | Registrar e passar `--proj-gate`. |
| Professor e ambiente | `reference_controller.py:389-395,424-445`; `f1_env.py:607-627` | Referências revisadas; não entram no braço Composite nem recebem mudança de obs/env. |

Os apontadores R0 anteriores foram tratados como pistas, não fonte de linhas.
Os hashes de disco e `git show` da FASE 0 conferem; comandos, contagens e
hashes completos estão em `0_PREPINS_PROJ_GATE_1.log`.

## Orçamento e sequência congelada

Exatamente duas corridas formais, em série: R1 OFF e R2 ON, ambas Monaco,
seed 0, 10 carros, 6000 ticks, 99 voltas, clima seeded, governor vplan,
variância `grid,compound`, alias `--track Monaco`. Zero smokes; pools e caches
intocados. Uma única execução serial da suíte no fechamento, depois de R1/R2
passarem seus gates. Selftest sintético do audit não lê simulações nem JSON.

### Freeze de preregistro

Este preregistro e `0_PREPINS_PROJ_GATE_1.log` são commit dedicados antes da
implementação. Em seguida, implementação, testes e audit v1.0 são commitados
antes de R1. Após esse commit, nenhuma edição de código/prereg até o fechamento;
erro de código durante o ciclo implica PARE, sem correção entre braços.

### R1 — OFF: reprodução da âncora

Executar em `backend/`, em um terminal serial:

```bash
env -u RACE_DIAG_NO_XY .venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track Monaco --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --out experiments/proj-gate-1/1_repro_off_monaco_s0.csv \
  2>&1 | tee experiments/proj-gate-1/1_repro_off_monaco_s0.log
```

g1 PASS somente se o CSV SHA-256 for
`6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` e o
sidecar `<out>_events.csv` SHA-256 for
`b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4`.
Qualquer divergência: PARE e não execute R2.

### R2 — ON: única medição

Após g1 PASS, repetir o mesmo comando uma única vez, adicionando somente
`--proj-gate` e usando `--out experiments/proj-gate-1/2_on_monaco_s0.csv`.
O log é `2_on_monaco_s0.log`; o sidecar usa o sufixo `_events.csv`.

O audit v1.0 recebe CSV v3.4, sidecar, log e pista frozen. Ele imprime a lista
de colunas obrigatórias antes de ler qualquer arquivo e falha fechado em
coluna ausente ou esquema diferente. Gates:

| Gate | Regra PASS |
|---|---|
| g2-proxy | Em pares consecutivos por carro cujo tick atual é off-track, `|Δs_wrapped − Δcum_dist| ≥10 m` em no máximo 2 pares e `≥30 m` em 0 pares. Reportar também `≥20 m`; não há exceções/cortes. |
| g3-reaquisição | Toda transição off→on coincide com `ns_raw` da busca global e com o segmento/arco global mais próximo derivado de XY; reportar contagem e zero escolha não-nearest. Inclui wrap `s=0`. |
| g4-não-piora | Contra R4 congelado: fora ≤43,15%; episódios off-track ≤346; janelas presas de 30 s ≤120; hesitações do resumo do runner ≤12; contatos pela métrica de linhas congelada ≤110.795; completude não inferior a 30.000 linhas/3000 ticks amostrados/10 carros, com sequência `0,2,...,5998` por carro. |
| g5-suite | Executar serialmente uma vez a suíte completa: baseline 20F/352P/3S + todos os testes novos; manter exatamente as 20 falhas canônicas, sem falha nova. |

Um gate R2 que falhar encerra o ciclo imediatamente. Não repetir corrida para
melhorar número. A contagem de contatos publicada neste protocolo é
`wc -l - 1`, exatamente como ratificada pelo dono; a auditoria também informa
os registros CSV após excluir comentário e cabeçalho, para transparência.

**Errata de schema pré-R1:** `--ticks 6000` são ticks lógicos; o writer do
diagnóstico amostra a cada 2 ticks (`t_s` em passos de 0,2 s). R4 contém 3000
ticks observados por carro, de 0 a 5998, e 30.000 linhas totais. A auditoria
confere essa sequência completa. O orçamento continua limitado a uma corrida
de 6000 ticks por braço; nenhum gate numérico foi mudado.

## Fechamento sem promoção

Se os gates permitirem fechamento, publicar `EXECUCAO_PROJ_GATE_1.md` com
gates ponto a ponto, comandos e proveniência dupla (disco e `git show`), uma
linha em `PROJECT_STATE.md`, entradas em `AUDITORIA_RL.md` e `worklog.md`, e
handoff. O veredicto final ao dono será entre: (a) habilitar a flag no ciclo de
avaliação seguinte; (b) abrir V-B para probe de contaminação env/obs; (c)
estender a Interlagos; (d) arquivar. Nenhuma classe C1/C2/C3/C5 fora dos
artefatos frozen anteriores será reanalisada neste ciclo.

## Condições de PARE

PARE sem continuação em caso de hash/proveniência divergente, R1 diferente do
replay byte a byte, gate R2 não PASS, falha nova na suíte, erro de código após
o freeze, edição pós-R2, schema inesperado, mudança em env/física/obs/pool/cache/
pista frozen ou tentativa de executar uma terceira corrida. Sem promoção ou
retreino neste ciclo.
