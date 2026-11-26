# PREREG PROJ-GATE-2 — autópsia do PARE (report-only, Monaco)

**Data:** 2026-10-24 (America/Sao_Paulo)  
**Status:** protocolo congelado antes da decomposição.  
**Decisão permitida:** recomendar somente V-A2, V-B ou arquivar.  
**Escopo:** análise offline report-only. Zero simulações/smokes; sem suíte; sem
alteração em produção, pools, caches, pista ou referência da suíte. A flag
continua default-OFF e não há promoção neste ciclo.

## Pergunta e hipóteses congeladas

Decidir se os números do PARE de PROJ-GATE-1 sustentam (a) V-A2, âncora
deslizante com continuidade de ramo; (b) V-B, probe/gate do ponteiro do env;
ou (c) arquivar esta bifurcação causal até existir instrumentação identificável.

- **H1 — alvo congelado inadequado:** a última pose on-track usada como âncora
  escolhe um ramo ruim quando o alvo está perto e cruza pernas de curva. Só será
  apoiada por reconstrução fiel do alvo/âncora da implementação frozen e
  associação observável ao resultado. Se não puder ser reconstruída, marcar
  **LOSING / não identificável**, nunca inferir a geometria a partir de `s`.
- **H2 — ponteiro vivo remoto:** durante off-track, o ponteiro vivo do env fica
  a mais de 32 m de ramo/arco local em amostras. O CSV não declara campo de
  ponteiro interno do env. `ns_raw` é um proxy do runner obtido por busca global
  de segmento a partir de XY; resultados desse proxy não serão chamados de
  ponteiro interno nem de evidência causal de H2.
- **H3 — g2 mal especificado para esse diagnóstico:** determinar pela fonte
  frozen o que `s`, `cum_dist` e `ns_raw` representam. g2 conta pares em que
  `|Δs_wrapped − Δcum_dist|` cruza cortes; não será reinterpretado como
  teleporte/localidade sem medida direta de ramo.

## Fontes autorizadas e pinos

Ler somente os seguintes artefatos (SHA-256 completo), verificando bytes de
disco contra `git show` no commit indicado antes de abrir dados:

| Fonte | Commit / referência | SHA-256 |
|---|---|---|
| R1 OFF CSV | `5c4bf9c` | `6698b55bad9cba1a167c952eab4381ee696a4191545cdecdd3db873e739b2ce7` |
| R1 OFF events | `5c4bf9c` | `b99007d0673b2b11727f50287451ffd1fe5439db1997065f4884f60b33252ce4` |
| R2 ON CSV | `5c4bf9c` | `b9ea18f28a26f2035fe61c9370eec7a70eb2bcaa342897d08a71baaf686a4edc` |
| R2 ON events | `5c4bf9c` | `88fa98130b73b881750dab5f54a1fae02d07ce2a2162e1586332afec0660ac6a` |
| Monaco frozen | `f2bd199`, `backend/model_train/tracks_frozen/Monaco_v2.json` | `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| Runner frozen | `f2bd199`, `backend/scripts/run_race_10_cars.py` | `6f13b59cfb7e709081483be85e2ad14d7295f65981dc8705ca8bcc9a9b8b03b3` |
| Diagnostic/writer frozen | `f2bd199`, `backend/model_train/race_diagnostic.py` | `69f87d163a56fe310212158ff527f58bd891828ffd0e8c5f91c3f5d7d41a0491` |
| Classifier v1.2 frozen | `f2bd199`, `backend/scripts/proj_fix_3_classify.py` | `bc0a7ba9a5a9e4194d6195f3bc830a7626133939b465829f8ee1225e30414bdd` |
| PARE PROJ-GATE-1 | `a278cbe` | `6b89f7b03b2313b76c73117e795d0b9089da309fb4cccc6527edb3396673acb9` |
| DOSSIÊ PROJ-FIX-1 | `f2bd199` | `663d4ad9ff561080d4c2e1fe8d981dd00da01a10a919bb21e1b418a44c80185f` |

Data paths are `backend/experiments/proj-gate-1/1_repro_off_monaco_s0.csv`, its
`_events.csv`, and `2_on_monaco_s0.csv`, its `_events.csv`. Published results
may be read only from `PARE_PROJ_GATE_1.md`, the PROJ-FIX-1 DOSSIÊ, and the
committed PROJ-GATE-1 execution artifacts. Frozen sources above are inspected
with `git show f2bd199:<path>`; current production files are not inputs.

## Fail-closed source/schema gate

Before calculating any metric, verify every pinned input's disk/Git hash and
validate exact schemas. CSV headers are the exact 71-column v3.4 header frozen
in R1 and R2:

```text
tick,t_s,drv,speed,s,lat,th,brk,steer_rad,g_long,stuck_t,contacts,car_car,impulse,impulse_dv,offtrack,authority,g_gate,r_norm,composite_active,res_0,res_1,res_2,res_3,res_4,res_5,res_6,res_7,res_8,res_9,res_10,res_11,res_12,res_13,res_14,res_15,w_kind,w_grip,w_trans,tyre_life,tyre_grip,cum_dist,obs0,obs1,obs2,obs3,obs4,obs5,obs6,obs7,obs8,obs9,obs10,obs11,obs12,obs13,obs14,obs15,obs16,obs17,obs18,obs19,obs20,obs21,obs22,imp_events,imp_dv,imp_dv_max,body_x,body_y,ns_raw
```

Event sidecars use the exact 17-column header frozen in R1 and R2:

```text
sub,drv_a,drv_b,body_a,body_b,cx,cy,nx,ny,f_n,j_n,dv_a,dv_b,ax,ay,bx,by
```

Each run must contain exactly 30,000 data rows, ten drivers, and each driver must have
ticks `0,2,...,5998` once each. Required numeric values must be finite;
`offtrack` is 0/1; `ns_raw` is an integer in `[0,833]`. Duplicate/missing rows,
unexpected columns, invalid values, or any source hash/provenance mismatch
means **PARE before decomposition**. The script prints expected headers before
opening any CSV. Its `--selftest` uses synthetic rows only and must not open
race inputs.

## Métricas pré-especificadas

Use a pista fechada de Monaco, 834 pontos/segmentos e comprimento de arco
`L=3335.2 m`; distância nominal por waypoint `L/834`. Sem projeção/interpolação
nova além das regras abaixo.

1. **Localidade de ramo do proxy `ns_raw`.** Em cada amostra, `wp*` é o waypoint
   de menor distância Euclidiana a `(body_x,body_y)`; `argmin` resolve empate
   pelo menor índice. Calcular `d_wp = min((ns_raw-wp*) mod 834,
   (wp*-ns_raw) mod 834) * L/834`. Local se `d_wp <= 32.0 m`, errado caso
   contrário. 32 m é o teto congelado por C5 (p95 publicado 30,69 m), acima do
   qual a região já era considerada afetada por C3. Reportar por R1/R2 e
   `offtrack=0/1`: denominador, fração errada, p95 linear de `d_wp`, máximo e
   histograma. Esta é geometria do proxy amostrado, não ponteiro interno.
2. **Janelas de reentrada.** Uma reentrada observável é o par de linhas
   consecutivas do mesmo carro com `offtrack:1→0`. Janela semiaberta de 10 s
   `[t_reentry,t_reentry+10)`, medida pelos `t_s` emitidos. Reportar por braço
   transições, linhas (janelas podem sobrepor), fração de linhas localmente
   erradas, p95 de `d_wp`, fração de janelas com qualquer erro e com erro em
   pelo menos duas amostras consecutivas. A amostragem é 5 Hz; não imputar
   ticks ausentes.
3. **Estratificação de erros.** Para amostras off-track, reportar por carro e
   por decil de `s` (decil circular `floor((s mod L)/L*10)`, rotulado como
   `pointer_s_decile`) contagem, fração errada e p95 `d_wp`; listar os dez
   episódios off-track com maior máximo `d_wp`, ordenados por máximo decrescente
   e depois carro/tick. Episódio é uma sequência contígua de linhas off-track
   de um carro; gaps encerram episódio.
4. **Reprodução e decomposição g2.** Para pares adjacentes emitidos do mesmo
   carro, contando quando a amostra atual está off-track, calcular
   `e=abs(wrap(Δs,L)−Δcum_dist)` com wrap centrado em zero. Congelar contagens
   `e>=10 m` e `e>=30 m`; R1 esperado 112/45 (controle do OFF publicado) e R2
   173/108 (publicado). Divergência aciona PARE. Para os pares R1 e R2, mapear
   a chave `(drv,tick_prev,tick)` aos pares métricos de
   `proj_fix_3_classify.py` v1.2 importado sem edição. C1/C2/C3 seguem
   literalmente seus limites `dxy=30 m`, `d_ns_raw=8`; os pares residuais são
   C5. Um inválido/C4 ou mapeamento não 1:1 aciona PARE. Reportar por braço e
   corte ge10/ge30 contagens por classe, p95 linear de `dxy` e `abs(d_ns_raw)`.
   Normalizar contagens ge10/ge30 por número de amostras off-track e por 1.000
   amostras off-track, permitindo comparação OFF 112/45 com ON 173/108.
5. **Hesitações e cruzamento.** Recriar literalmente a regra congelada do
   resumo do runner: por carro, restringir a `t_s>20 s`; cada sequência
   contígua de `speed<0.5 m/s` é um episódio quando
   `0.3 <= t_s[min(j,n-1)]-t_s[i] < 3.0`, onde `i` inicia a sequência, `j` é
   o primeiro índice não lento (ou `n`), e `n` é o comprimento após o corte.
   Confirmar R2 = 28; divergência aciona PARE. Reportar por hesitação o carro,
   tick inicial/final, `d_wp` e localidade do proxy, offtrack, proximidade no
   tempo a cada reentrada e se cai numa janela de 10 s. Não reportar distância
   alvo/âncora: esses pontos não são colunas do writer.
6. **Auditabilidade do alvo.** A partir exclusivamente do diff frozen de
   `f2bd199`, determinar se `(pose_xy,s,ns,projection_xy)` da última amostra
   on-track usada por R2 e o alvo cacheado podem ser reconstruídos exatamente
   para cada amostra off-track em que o gate os usa. O controller atualiza a
   âncora a cada `predict_batch` lógico; o CSV registra 5 Hz, não grava âncora
   nem alvo. Não substituir valores ausentes pelo último registro CSV. Se a
   reconstrução exata falhar por isso, registrar **H1 LOSING / métrica de
   distância alvo→reentrada não estimável** e mostrar o ponto exato do código;
   não usar hipótese ou estimativa como evidência.

## Critério de decisão congelado

- **V-A2** somente se H1 tiver reconstrução e evidência de alvo errado em alta
  frequência, e a análise mostrar que o proxy do ponteiro é local nas janelas
  relevantes. Se recomendada, especificar âncora deslizante que avança durante
  off-track somente entre candidatos contíguos do ramo atual, com carve-out
  para os dois endpoints oficiais de reentrada; sidecar de alvo somente com
  flag ON e OFF byte-idêntico; gates de não-piora mantidos. Calibração de
  distância e mudança de writer v3.5 ficam fora deste ciclo.
- **V-B** somente se houver evidência direta do ponteiro interno remoto em
  amostras e regra candidata de estabilidade local no ramo.
- **Arquivar** se a evidência apontar para métrica mal especificada/outra
  causalidade ou se H1/H2 não forem identificáveis com as fontes congeladas.
  Arquivar esta bifurcação significa encerrar a hipótese neste ciclo, sem
  afirmar ausência de defeito.

Não criar limiares posteriores aos 32 m, 10 s, cortes g2, regra de hesitação ou
regras acima. Não usar classificações causais do tipo “curva cruzada” sem
reconstrução exata. Saída final é um único encaminhamento.

## Implementação, execução e outputs

Depois deste commit, criar `backend/scripts/proj_gate_2_autopsy.py` v1.0.
Somente leitura dos inputs autorizados; `--selftest` sintético; saídas falham
se já existirem. Executar uma vez em modo audit e gravar artefatos novos:

- `backend/experiments/proj-gate-1/autopsia/3_branch_geometry.json`
- `backend/experiments/proj-gate-1/autopsia/4_g2_class_decomposition.json`
- `backend/experiments/proj-gate-1/autopsia/5_veredito.md`
- log do selftest e log da execução, com SHA-256 dos inputs, fontes, schemas e
  outputs. Não editar ou substituir artefatos de PROJ-GATE-1.

O veredito registrará scorecard H1/H2/H3 com evidência e limites, as tabelas
das métricas, hashes/proveniência dupla, e o único encaminhamento. Qualquer
gatilho de PARE acima interrompe a decomposição e é documentado, sem corrigir
código/dados depois de observados os resultados. Ao fechamento, fazer uma
linha em `PROJECT_STATE.md`, entradas em `model_train/AUDITORIA_RL.md` e
`worklog.md`, e handoff de encerramento. A referência da suíte permanece
intacta e não é executada.
