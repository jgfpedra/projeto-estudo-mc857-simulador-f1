# PLANO_RACING-LINE-1 — linha suavizada local do professor

**Versão:** 1.0 · **Estado:** abertura; aguardando Freeze do Dono
**Data:** 2026-11-06 (America/Sao_Paulo)
**Branch:** `feat/sanidade-produto`

## 1. Motivo e objetivo

O PROF-CURVA-1 foi encerrado com PARE: o teto local de velocidade, mesmo no
piso teórico, ultrapassou a Guarda de Ritmo e não poderia eliminar a saída da
Descida do Lago. O próximo candidato autorizado no preregistro é uma linha
suavizada, não um novo teto de `v_plan`.

O RACING-LINE-1 avaliará uma linha virtual local do professor, com uma curva
geométrica de raio **18 m na Junção** (`s≈2318`), preservando a pista frozen e
os caminhos de produção. A hipótese é que reduzir a demanda geométrica da
trajetória, mantendo o ritmo longitudinal, elimine a cascata da Junção sem
introduzir lentidão global.

## 2. Escopo e não-objetivos

O candidato será aplicado somente ao professor solo e somente quando a flag
opt-in do ciclo estiver ligada. O professor histórico, os carros não-professor,
o governor de produção, a física, o grid e os arquivos de pista frozen ficam
intocados. A flag desligada deve permanecer byte-idêntica ao comportamento
atual.

Este ciclo não reabre o teto `--prof-curva`, não recalibra o skidpad, não altera
modelo, não altera `physics_frontier_current.json` e não executa matriz de 10
carros.

## 3. Tarefas

### Task 1 — abertura e preregistro (esta etapa)

Criar este plano, `PREREG_RACING_LINE_1.md` e a linha síncrona nos três
ledgers. Fazer stage e parar para o Freeze do Dono. Zero corrida e zero código
de produção.

### Task 2 — construção geométrica offline

Criar um instrumento report-only que, usando somente as pistas frozen locais,
construa a linha virtual candidata:

- localizar a janela C08 da Junção pelo `build_corner_definitions`/
  `match_corner` canônico;
- substituir apenas essa janela por um arco circular de raio 18 m;
- manter a posição e a tangente nos limites da janela, exigindo continuidade
  C1; se não houver arco válido com os limites congelados, emitir PARE;
- manter todos os setores externos à janela inalterados;
- conferir corredor, fechamento, ausência de auto-interseção e erro de
  projeção na pista frozen;
- executar duas leituras seriais e exigir `cmp=0`.

Nenhum resultado ON será usado para escolher os limites do arco. Os limites
serão definidos pelo C08 canônico antes da primeira execução do instrumento.

### Task 3 — mapa de viabilidade da linha

Sobrepor a linha candidata aos eventos OFF já medidos no estágio 0 e calcular,
por curva e por realização, deslocamento lateral, raio efetivo, erro de
projeção e previsão de permanência no corredor. O mapa deve ser determinístico,
report-only e independente do runner.

Se a linha de 18 m não couber na geometria ou não atingir C1, o ciclo para sem
corrida. Se couber, o mapa fixa os hashes e os parâmetros que entrarão na
implementação opt-in.

### Task 4 — implementação isolada no professor

Adicionar somente após novo Freeze a camada de linha virtual no caminho do
professor. A linha não pode chamar o teto `v_plan` nem alterar o governor.
Testar explicitamente que a flag OFF mantém o CSV histórico e que a flag ON é
rejeitada fora do professor.

### Task 5 — medições solo

Depois do Freeze da implementação, executar apenas corridas solo de 600 s:
Interlagos e Monaco, N=0..4, em série, com sidecar e duas leituras do
instrumento. Nenhuma matriz de 10 carros é autorizada.

### Task 6 — gates e closing

Comparar cada realização ON contra a referência OFF do estágio 0, publicar a
tabela por curva e por realização, avaliar os gates formais e parar em PARE
para o closing do Dono. Promoção não faz parte deste plano.

## 4. Gates resumidos

- **Primário Interlagos:** zero saídas em C01/Descida do Lago, C06/Bico de
  Pato, C07/Mergulho e C08/Junção, e zero saídas novas nos demais setores.
- **Monaco:** redução de fora de pista de pelo menos 5 pontos percentuais,
  sem piora em nenhuma curva.
- **Guarda de Ritmo:** nenhuma volta solo pode exceder 123,05 s, valor
  histórico de 107,0 s × 1,15 fixado no PROF-CURVA-1. O piso teórico acima
  desse limite é PARE automático.
- **Geometria:** arco C1, dentro do corredor, sem auto-interseção, sem
  alteração da pista frozen e com projeção determinística.
- **Integridade:** CSV de 3.002 linhas, sidecar presente, SHA da pista no
  cabeçalho, variedade no log, hashes do instrumento e `cmp=0` nas leituras.

Qualquer melhora agregada que venha acompanhada de regressão localizada falha
o gate; não haverá compensação entre curvas.

## 5. Referências congeladas

- Baseline OFF: `backend/experiments/prof-curva-1/c0/`.
- Interlagos frozen: SHA curto `164876196eb12174`.
- Monaco frozen: SHA curto `67ca11dc211c8c78`.
- Instrumento de eventos: funções canônicas de `backend/scripts/saidas_verdict.py`.
- PROF-CURVA-1 encerrado: `a0e9139`, mapa de inviabilidade em
  `backend/experiments/prof-curva-1/c5/`.

## 6. Governança

O ciclo segue a ordem: prereg staged → Freeze do Dono → instrumento offline →
implementação opt-in → corridas solo → relatório e ledgers → PARE/closing.
Este documento não autoriza Task 2–6. O estado atual é **PARE para Freeze do
Dono**.
