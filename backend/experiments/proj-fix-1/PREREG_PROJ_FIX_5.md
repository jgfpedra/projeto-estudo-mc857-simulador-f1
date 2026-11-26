# PREREG — PROJ-FIX-5: anatomia dos ponteiros e desenho do gate (report-only)

**Data:** 2026-10-23
**Estado:** pré-registro fechado antes da execução da anatomia.
**Decisão de comportamento:** nenhuma neste ciclo; ratificação permanece com o dono.

## 1. Escopo e orçamento

Este ciclo mede, offline, os saltos do ponteiro nas 112 linhas já publicadas do
mapa NIT-2 ≥10 m: C3=46 e C5=66. Em seguida localiza, por leitura apenas, o
cálculo e os consumidores do ponteiro e registra um desenho report-only para um
gate de projeção. Não atribui causalidade, não altera produção, runner, física,
observação, pistas congeladas, pools ou testes. Zero simulações e zero smokes; a
suíte permanece na referência 20F/352P/3S sem reexecução.

As métricas públicas de PROJ-FIX-4 são motivação histórica e não serão
recalculadas nem reapresentadas como achados novos. Nenhum agregado novo será
produzido antes do commit de freeze deste preregistro, do instrumento e do
selftest sintético.

## 2. Fontes permitidas e gates de integridade

O modo de análise do instrumento pode abrir **somente** os dois arquivos abaixo;
não abrirá replay, logs de corrida, geometria congelada, código de produção nem
outros CSVs.

| Fonte | SHA-256 pinado |
|---|---|
| `classificacao_v12/mapa_nit2_ge10.csv` | `1f75e75b50ac9d6a78f96b12f04ca0ac422cbff8ec1546d8cafb7aa791f5008f` |
| `classificacao_v12/resumo_classes.json` | `9744db80cb2c55400aac4bc75351af59c89fb7963c0163dbe63b42c5abf5cb05` |

Qualquer divergência de hash encerra a execução antes de ler ou publicar
métricas. A reconciliação é obrigatória: 112 linhas no mapa e no resumo;
C3=46/C5=66 em ambos; headline ≥30 m = 45/45 C3 no resumo; e os campos
históricos/mapeados do bloco `reconciliation` precisam concordar. Também devem
reproduzir-se, a partir do mapa, 112/112 `authority=rejoin`, 112/112
`offtrack=1`, os totais 46/66 e 112 checkpoints únicos por
`(drv,tick_prev,tick)`. Divergência em qualquer fechamento = PARE, sem emitir
tabelas de métricas.

## 3. Definições congeladas da anatomia

1. Para cada classe C3 e C5, calcular p50, p95 e máximo **com sinal** para
   `delta_s_wrapped_m`, `delta_cum_dist_m` e `d_ns_raw`. “À frente” permanece
   positivo; não se toma valor absoluto. Quantis usam interpolação linear na
   posição `p*(n-1)` da lista ordenada. Todos os valores precisam ser finitos.
2. Por carro, contar eventos e calcular a média do intervalo entre eventos
   consecutivos, ordenados por `tick_s`; reportar em segundos e também em
   `tick` quando houver pelo menos dois eventos. Um carro com menos de dois
   eventos recebe intervalo médio `null`.
3. **Eventos por volta:** os dois arquivos pinados não contêm número total de
   voltas nem identidade de volta por evento. Como `s` é justamente o ponteiro
   sob investigação, não será usado para inferir voltas ou preencher esse
   denominador. A coluna `eventos_por_volta` ficará `null`, acompanhada da
   razão “denominador de voltas ausente nas fontes permitidas”. A média
   inter-evento é a cadência temporal observável; não será rotulada como
   cadência por volta.
4. A coerência por autoridade agrupa as linhas pela coluna `authority` e
   confirma total e distribuição por classe. O checkpoint auditável é a chave
   de evento disponível no mapa `(drv,tick_prev,tick)`; a chave deve ser única
   e seus totais C3/C5 devem reproduzir 46/66. O instrumento não alegará existir
   uma coluna separada de odômetro que o mapa não fornece.
5. A execução publica JSON e tabelas Markdown somente depois de todos os gates
   passarem. A saída inclui os hashes de ambas as fontes, deste preregistro, do
   instrumento, do selftest e dos próprios relatórios.

O selftest é sintético, determinístico e autocontido: valida quantis, sinal,
agrupamento e o caminho de `PARE` para contagens divergentes. `--selftest` não
abre CSV, JSON nem qualquer arquivo de entrada.

## 4. Localização read-only

Depois do freeze e da anatomia, inspecionar em checkout o cálculo/consumo do
ponteiro `s`/nearest waypoint, incluindo projeção de projeto, alvo de rejoin
`bearing da projeção + 10 m`, observação edge, contagem de volta e proxy do
writer. Registrar caminhos e linhas atuais, verificando também as referências
históricas `race_diagnostic.py:327-364` e `reference_controller.py:448-453`.
Nenhum arquivo de produção será editado.

## 5. Desenho report-only para PROJ-GATE-1

### Fator único: gate do ponteiro com âncora pegadora

- **On-track:** o ponteiro só avança entre waypoints contínuos e dentro de uma
  janela de luz `v·dt`. A regra de calibração e sua unidade serão registradas no
  dossiê a partir dos percentis publicados na Fase 2; não se escolhe um
  multiplicador pós-número neste ciclo.
- **Off-track:** congelar o ponteiro na última âncora on-track; readquirir
  somente após evento explícito da autoridade de rejoin. Preservar exceções
  não críticas para lap-wrap em `s=0` e para a primeira aquisição de RAS.
- **Carve-outs invioláveis:** contagem de voltas, lap time e `cum_dist` não
  mudam. O corredor de readmissão deriva apenas da geometria congelada
  (waypoints e meia-largura paramétrica); não declara borda física. A
  superfície dirigível de Mônaco não está ratificada.

### Variantes para ratificação do dono

- **V-A — runner/rotulação:** altera telemetria e alvo de rejoin; mantém física
  e observação intactas. Candidato primário para destravar a cascata do
  PROF-REPAIR sem retirar o perfil v10-cego padrão.
- **V-B — nível do ambiente:** altera comportamento e observação; exige bit-off
  idêntico no sinal NEURAL e gates mais pesados. Riscos a avaliar: alteração da
  observação de tráfego (46d) e promessas FR0 ainda não fatiadas.

### Matriz de gates pré-declarada para o ciclo PROJ-GATE-1

| Gate | Critério pinado |
|---|---|
| OFF | bit-idêntico ao replay/âncora. |
| ON — salto | p95 de Δs off-track entre pares ≥10 m tende a zero em repetição de Mônaco. |
| ON — ALO | o evento `(ALO,2130,2132)` deixa de ser salto do ponteiro. |
| Segurança/controle | contatos e hesitações não pioram. |
| Geometria | zero atalhos por trechos adjacentes explicitamente verificado em Mônaco. |
| Regressão | suíte de referência permanece intacta. |

### Hipótese de contaminação do alvo de rejoin

Hipótese, não conclusão: o alvo atual `bearing da projeção + 10 m` pode ser
contaminado quando o ponteiro corre à frente durante off-track. No regime ON,
medir isso com probe lateral de reentrada `nhist`; a leitura não autoriza mudar
o alvo neste ciclo.

## 6. Veredicto reservado ao dono

O relatório apresentará as quatro saídas sem selecionar uma em nome do dono:
(a) implementar V-A com a matriz acima; (b) implementar V-B com gates bit-off;
(c) esconder somente no instrumento/writer, sem comportamento; ou (d) mover.
Até a ratificação, registrar “aguardando decisão do dono” e apontar este dossiê
no WORKLOG e em `backend/PROJECT_STATE.md`.
