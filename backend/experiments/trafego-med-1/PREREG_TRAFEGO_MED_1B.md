# PREREG TRAFEGO-MED-1B — proveniência em dois níveis

**Estado:** freeze preparado em disco; aguardando commit/verificação do dono. Nenhum número de fase ou métrica de amostra foi produzido.

## Objetivo e limites

Etapa 3, report-only: decompor contatos e hesitações de corrida por fase, tipo de par e braço; localizar segmentos/carro; contar oportunidades de ultrapassagem não tomadas; medir contatos em janela de reentrada e a transferência do tumulto da largada para a primeira volta, reagrupamento ou rejoin. O resultado será uma recomendação textual de um único fator de decisão de grupo, com alternativa arquivada.

Orçamento: zero corridas e zero smokes; nenhuma alteração de produção, promoção, alteração de ambiente/física/observações, pool/cache/pista ou suíte. A suíte não será reexecutada sem mudança de produção. Nenhuma inferência causal será feita a partir desta leitura report-only.

## Freeze e proveniência

O censo prévio, metadata-only, é `0_INVENTARIO_METADATA.md`; esta etapa não o refaz nem altera. O SHA-256 fixado no manifest é `cfae366a07d3d75ef45b61d6892a91caf4b098091d7cf70f1011048baeb8c02b`. Ele registra 110 caminhos: 47 Tier A e 63 Tier B; 65 séries temporais, 41 sidecars de solver e 4 saídas publicadas da largada.

- **Tier A — rastreado:** SHA-256 do arquivo em disco deve coincidir com o SHA do blob `git show 8c9636d27671614001bc99f172780de796a08eb9:<path>`. Cada entrada conserva `disk_sha256`, `git_sha256` e `git_ref`.
- **Tier B — histórico sem blob:** disclosure `untracked` por arquivo; o manifest fixa SHA-256 em disco, bytes, linhas de dados, cabeçalho/colunas exigidas e caminho. Antes de métricas, o script re-hash, re-confere tamanho/schema e reconta linhas. Qualquer divergência é PARE.
- Os 110 caminhos estão exatamente em `tier_A` ou `tier_B`; saídas publicadas ficam classificadas e excluídas da análise. Sidecars ficam classificados como auxiliares, não como séries de 5 Hz.
- Fontes geométricas permitidas e fixadas no manifest: `interlagos_v2` (`164876196eb12174`), `interlagos_sf729_v2` (`e836910429769c27`) e `monaco_v2` (`67ca11dc211c8c78`). Um arquivo só recebe geometria quando sua identidade é comprovada por metadata ou pela atribuição nominal prévia registrada. Sem geometria fixada, regrouping, wrap/primeira volta, pareamento longitudinal e ultrapassagem ficam indisponíveis; não se transfere geometria de outro arquivo.
- O manifest também fixa o SHA-256 do script analítico. O dono commita preregistro, manifest e script juntos. Antes de abrir números, conferir `git show <commit>:<path>` contra o disco para preregistro e manifest; o script deve estar no mesmo commit e bater com seu SHA no manifest. Se o commit for impossível, somente a declaração expressa do dono “freeze aceito” permite continuar, com os SHAs do freeze registrados no handoff e disclosure no fechamento.

O script é `scripts/trafego_med_1_taxonomy.py`, versão 1.0. Seu selftest usa somente dados sintéticos em memória. O preflight falha em schema divergente antes da análise. O passe de elegibilidade lê somente `drv` e `t_s` para validar cada série candidata; série inelegível é listada com o motivo e não entra na carga para métricas.

## Censo e elegibilidade congelados

O manifest contém os 110 arquivos das famílias: ANTI-D3-1; CICLO LARGADA raw e saídas; D-v15/governor histórico; FASE 4 B3 precedente; FASE 4 v15 B3-prime; Monaco blind/composite forensic; Monaco/proj/rejoin telemetry; mistas legadas (i/ii/iii); prof-monaco-1 raw; v14-all FASE 4. A lista arquivo-a-arquivo, classificação A/B, cabeçalhos, braços, motivos, hashes e tamanho está no manifest.

Série candidata: cabeçalho com `tick,t_s,drv,speed,s,lat,th,brk,steer_rad,car_car`, braço rotulado, exatamente 10 drivers e cadência de 5 Hz (mediana de intervalos de 0,2 s; nenhum intervalo fora de 0,2 ± 0,1 s; `t_s` duplicado ou fora de ordem reprova). `offtrack` e `authority` são usados quando presentes; rejoin fica indisponível se ambos faltarem. Sidecar usa `sub,drv_a,drv_b,body_a,body_b,cx,cy,nx,ny,f_n,j_n,dv_a,dv_b,ax,ay,bx,by`. Nenhum candidato que falhe a validação entra em métricas; o motivo fica em `3c_run_coverage.csv`.

Os rótulos de braço são os do manifest e não serão reagrupados por conveniência após observar os resultados. Comparações agregadas ficam separadas por família **e** braço para não misturar estudos ou pistas distintos. Arquivos sem `t_mode` usam somente a reconstrução congelada dos limiares do `ReferenceController` no commit-fonte fixado: carro mais próximo à frente dentro de 60 m, mesma linha com `|Δlat| < 2,6 m`, `v_ego > v_ahead > 1 m/s`; gap abaixo de 6 m é `reopen` e não conta como `cap/close`. Se há `t_mode`, contam somente `cap` e `close`.

## Taxonomia e métricas

Precedência para rótulo único por amostra: LARGADA, REJOIN, REGROUP, CRUZEIRO. A precedência evita dupla contagem e mantém a janela de rejoin separada do reagrupamento.

- **LARGADA:** `t_s < 60 s`.
- **REJOIN:** `offtrack == 1` ou `authority == rejoin`; ao primeiro indicador que termina, abre janela inclusiva de 10 s. Se o outro indicador ainda estiver ativo, REJOIN continua por ele, sem renovar a janela.
- **REGROUP:** na janela retrospectiva inclusiva de até 60 s, pelo menos dois carros em `cap/close` no tick atual e velocidade média do líder abaixo de 10 m/s. O líder é o maior progresso acumulado; na ausência de `cum_dist`, progresso é reconstruído por wrap de `s` usando somente geometria fixada. A classificação de `cap/close` segue os limites acima, incluindo `D_AHEAD=60 m`, `LAT_SAME_LINE=2,6 m`, `V_MIN_FOLLOW=1 m/s`, `G_SAFE=6 m` do código fixado.
- **CRUZEIRO:** amostras restantes. Sem geometria fixada, o rótulo é `CRUZEIRO_REGROUP_NA` e a cobertura deixa claro que regroup não pôde ser classificado.
- **TIPO DE PAR:** `nose_a_tail` quando `|Δlat| < 3,5 m`; `lateral` quando `|Δlat| ≥ 3,5 m`.
- **OPORTUNIDADE NÃO TOMADA:** sequência de amostras a 5 Hz, por par líder/seguidor mais próximo, com gap longitudinal à frente ≥15 m, `|Δv| ≥1 m/s`, duração entre primeira e última amostra ≥3 s e sem troca sustentada de ordem que cruze a histerese congelada de 10 m. A oportunidade recebe a fase da primeira amostra qualificadora. Não há teto de gap. Sem geometria fixada, oportunidade fica indisponível.
- **CONTATOS:** `car_car > 0` contado como amostra de veículo a 5 Hz, coerente com o contador do runner (um contato físico pode aparecer para os dois carros); sidecar de solver é contado separadamente por evento/substep. Para atribuição derivada de par, exige flag positiva nos dois carros e `|Δs| < 8 m` no mesmo tick, precedente `mixed_summary`; wrap só é usado com geometria fixada. Sem geometria, o contato bruto continua contado, mas tipo/par derivado fica desconhecido. Mais de um par candidato no tick vira `par_ambiguo`, sem escolha arbitrária.
- **HESITAÇÕES:** regra congelada do runner: episódio contínuo `speed < 0,5 m/s`, com início após 20 s e duração `0,3 ≤ duração < 3,0 s`; fase é a da amostra inicial. As publicações anteriores 12 OFF/28 ON são âncoras de comparação, não valores esperados nem substitutos da regra.
- **Denominador:** contagens são apresentadas por corrida e agregadas dentro de família×braço, com taxa por 10.000 amostras veículo na fase. Cada série e sua cobertura permanecem visíveis.
- **Segmentos:** bandas de 100 m em `s` local, top 20 por corrida×fase×métrica×carro para amostras, contatos e hesitações. Wrap/normalização exige geometria fixada.
- **Contato de reentrada com counterpart on-track:** janela REJOIN de um lado e counterpart no mesmo tick com `offtrack == 0` e `authority != rejoin`; atribuição por par reconstruído. Eventos de solver em REJOIN aparecem em coluna própria, sem serem confundidos com flags 5 Hz.
- **Transferência da largada:** contatos em `t_s < 60 s`; primeira volta pós-largada de `t_s ≥60 s` até o primeiro wrap de `s` de cada carro; subdivisão dessa janela em REGROUP e REJOIN. Hesitações são reportadas para largada e primeira volta. Sem geometria fixada, primeira volta e contato de reentrada por par são NA, nunca zero. Resultado por corrida e agregado família×braço.

## Saídas previstas

Escritas somente após freeze verificado e apenas se os nomes estiverem livres; nunca sobrescrever saída existente:

1. `1_phase_pair_arm.csv` — matriz por corrida×família×braço×fase×tipo de par e métrica.
2. `1b_phase_pair_aggregate.csv` — agregado família×braço, com denominador e cobertura de corridas.
3. `2_top_segments_car.csv` — bandas/carro/fase.
4. `3_reentry_launch_transfer.csv` — transferência por corrida.
5. `3b_transfer_by_arm.csv` — transferência agregada família×braço.
6. `3c_run_coverage.csv` — elegibilidade e indisponibilidades por corrida.

## Gates e PARE

Antes de qualquer número: revalidar hash SHA do inventário e dupla proveniência Tier A; Tier B precisa bater todos os pinos de disco do manifest; confirmar commit do freeze ou a alternativa expressamente aceita pelo dono. Script, preregistro e manifest não podem mudar depois do freeze.

PARE sem continuar se houver hash/schema/tamanho/linhas divergentes, fonte ausente, caminho/freeze inconsistente, braço sem rótulo, saída não fresca, edição de produção, sim/smoke, corrida adicional, falha nova na suíte referenciada ou qualquer número produzido antes do freeze verificado. Nenhuma promoção ou exibição nesta etapa.

## Fechamento da etapa

Após a análise: registrar tabelas, hashes, cobertura e veredito em dossiê; recomendar exatamente um fator de decisão de grupo (cedência no follow, espaço/lado para passar ou rate-limit do reagrupamento), gates pré-esboçados opt-in/OFF bit-idêntico/não-piora de hesitações-contatos-fora/sem transferir largada e uma alternativa arquivada. Atualizar PROJECT_STATE com uma linha `Ver <path>`, AUDITORIA_RL.md, worklog e handoff. Este prereg não autoriza implementação nem promoção.
