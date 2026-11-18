# PREREG PASS-DIAG-1B — autópsia das tentativas de passagem

**Estado:** pré-freeze. Nenhuma amostra ou intervalo de tentativa foi analisado.  
**Escopo:** report-only; zero simulações, zero smokes, nenhuma mudança de produção e sem promoção.  
**Retomada:** handoff 01a17003-1bf0-7da3-b715-dba28a0ee48c, retomado após a ratificação do dono.

## Declaração de exposição autorizada pelo dono

Este ciclo considera conhecidos, antes do freeze, somente os seguintes fatos publicados:

- PASS-1: 17 inversões líquidas pós-largada; mediana R2 137,01 s contra limite 136,71 s; primeira volta R1 4.140 contra R2 171 contatos; pós-rejoin 29 contra 17; suíte 20F/375P/3S; zero amostras DECISION_ACTIVE em carve-outs.
- Inspeção de pinos anterior: o audit contém 5 registros em pass_decision_attempts; consumos pela decisão = 0.

Nenhum valor adicional de conteúdo de CSV, log, audit ou geometria é conhecido ou será impresso antes do freeze. Na verificação de schema pós-freeze, o script imprime apenas PASS/FAIL e nomes de campo; não imprime valores de linhas.

## Fontes e pinos pré-freeze

Os arquivos R1/R2 são Tier B: SHA-256 de disco fixado abaixo. A verificação na abertura da análise repete cada hash antes de abrir qualquer conteúdo. Qualquer divergência é PARE. O relatório e o audit também são fixados por hash e usados como evidência publicada, não como substitutos das séries R1/R2.

| Fonte | SHA-256 congelado |
|---|---|
| experiments/pass-1/1_R1_OFF.csv | 5cb49097fea9bb066e9bef5ae62f4ee7c6f9ceb70485448792d33b533ce5cdaa |
| experiments/pass-1/2_R2_ON.csv | 7d2c49b9b873fc4fc4888b1413cd47ae3b9dde040a4e1af111ac246c90e0a27c |
| experiments/pass-1/1_R1_OFF.log | f23a79771bd9f05d8e709f9bf67a93be8a93bf2e8129403db03972b0c0c23273 |
| experiments/pass-1/2_R2_ON.log | 213fb953c98e59a51e2178a9f05171560dd63ed15f675fcf6c2a86b33c783f1b |
| experiments/pass-1/4_AUDIT_PASS_1.json | 347216e6cf65f109ec82d927762bab5ffefea85c4913fca024891bf05e1a134b |
| experiments/pass-1/5_EXECUCAO_PASS_1.md | e4f6ac05383d481c862cf679edac171547ccbde81c44557ecd2072f295281a67 |

Geometria Tier A: model_train/tracks_frozen/interlagos_v2.json, commit de proveniência 8136d54ec45f9f49b38a5893a812928474109535, SHA-256 c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613. Disco e blob desse commit já foram comparados por hash nesta retomada.

## Q0 — pergunta primária

1. Classificar cada registro/intervalo de decisão em CONSUMIDA, ABORT-GAP, ABORT-TIMEOUT, ABORT-CONTATO ou TROCA-SEM-CONSUMO. CONSUMIDA exige diferença inicial de cum_dist (ego−alvo) negativa e alcance de pelo menos +10 m no intervalo. TROCA-SEM-CONSUMO exige que essa diferença fique positiva por pelo menos cinco amostras consecutivas (1,0 s), sem alcançar +10 m. Essa classe é evidência candidata de discrepância de bookkeeping, não prova automática de bug.
2. Reconstituir as inversões líquidas pós-largada usando o odômetro cum_dist: para cada par de pilotos, o estado de ordem muda quando a diferença relativa atravessa ±10 m; uma inversão positiva e uma reversão têm sinais opostos. Janela é o intervalo entre os limites de 10 m. O total líquido calculado deve ser comparado ao valor publicado 17.
3. Para cada inversão, registrar pilotos, tick/tempo, se ocorreu no intervalo ativo do mesmo par, em outro intervalo ativo, até 2 s após término/aborto, até 10 s de uma tentativa, ou fora dessas janelas. Registrar o lag assinado para o evento de tentativa mais próximo do mesmo piloto e do campo. Categorias temporais indicam coincidência; não provam causalidade. “Passagem consumida” exige tentativa consumida do mesmo par.
4. Veredito mecânico: bookkeeping se houver TROCA-SEM-CONSUMO sustentada junto a zero consumos registrados; perturbação de fila se inversões coincidirem temporalmente com decisão ativa/offset/aborto sem consumo do par; caso contrário, evidência inconclusiva. O dossiê deve separar observação de causalidade.

## Definições congeladas da PASS-DIAG-1

### Tentativas e desfechos

- Delimitar tentativas pelos intervalos [pass-decision] dos logs, confrontados com 2_R2_ON.csv e os registros de tentativa do audit. Um intervalo precisa ter piloto, alvo, tick/tempo inicial e final; parear eventos de início/fim pelo identificador, ou pelo par ordenado piloto/alvo quando não houver ID. Intervalo aberto, duplicado ou sem par correspondente: schema inválido, PARE.
- Uma tentativa só é classificada como CONSUMIDA se cum_dist(ego)−cum_dist(alvo) iniciar negativa e alcançar ≥+10 m dentro do intervalo.
- A classificação TROCA-SEM-CONSUMO descrita em Q0 tem precedência sobre códigos de aborto quando a trajetória demonstrar a troca sustentada; caso contrário, classificar pelo motivo de aborto do log.
- Motivos de aborto são normalizados para GAP, TIMEOUT ou CONTATO. Um motivo não reconhecido ou conflitante é PARE, sem inferência.

### Pace empírico R1 — referência escolhida pelo dono

- Construir perfil congelado a partir de 1_R1_OFF.csv: velocidade observada speed, somente amostras on-track (offtrack=0), após 60 s, em ceil(L/10 m) bins iguais de s mod L (largura aproximadamente 10 m); L é o comprimento da geometria congelada.
- Em cada bin, usar a mediana de speed. Bins sem amostra usam interpolação linear circular entre centros de bins preenchidos; se houver um único bin preenchido, usar seu valor global; nenhum bin preenchido é PARE.
- Para cada tentativa, somar em seus intervalos 5 Hz o tempo observado e o tempo de referência Δcum_dist / v_R1(s_mid). Custo = tempo observado − tempo de referência, em segundos. Reportar p50/p95 por desfecho e a soma das janelas de tentativa.
- Para evitar dupla contagem, também reportar a soma sobre a união temporal dos intervalos por piloto. Comparar o resultado com a diferença de medianas de volta publicada (137,01−134,03 s, aproximadamente 2,98 s) apenas como escala; janelas de decisão não estabelecem atribuição causal do gap integral.

### Curvatura

- Calcular κ absoluto em m⁻¹ na posição s mod L do início da tentativa, usando o waypoint mais próximo em arco e a curvatura discreta dos três waypoints vizinhos na geometria congelada.
- Faixas: κ < 0,02; 0,02 ≤ κ ≤ 0,06; κ > 0,06. Reportar outcome e número de tentativas por faixa.

### Reentrada e contatos

- Episódio off-track/rejoin: amostra com offtrack=1 ou authority contendo rejoin (case-insensitive). Janela pós-reentrada inicia na primeira amostra normal seguinte e dura 10 s; janelas do mesmo piloto que se sobrepõem são unidas.
- Contatos são a soma de car_car nas amostras. Como o CSV não fornece identidade do outro carro no contato, “participante de tentativa” significa que o piloto da linha está como ego/alvo de uma tentativa ativa; a classificação é proxy, não pareamento exato do contato.
- Para a diferença publicada 29 vs 17, mostrar por piloto e janela de reentrada: contatos, tentativas ativas, tempo da tentativa mais próxima e lag. Se a geometria/coluna não permitir essa classificação, reportar a limitação.

### Primeira volta

- Primeira volta por piloto: amostras com cum_dist < L. Agregar contatos em bins de 5 s para R1 e R2. Sobrepor início/fim das tentativas R2. Reportar ambos os valores de amostras com contato e soma de car_car; comparar à âncora publicada R1 4.140 → R2 171 e identificar quando ocorre a queda relativa.

### Folga nos cinco registros expostos

- Para cada tentativa, reportar duração, menor separação longitudinal absoluta do par (diferença de s envelopada em [-L/2,L/2]) e progresso lateral do ego (máximo |lat(t)-lat(início)|).
- “Quase-consumo” é aborto com progresso lateral ≥0,5 m e separação mínima ≥8 m. Essa métrica substitui a pergunta original sobre folga dos consumos; não pressupõe passagem consumida.

## Schema congelado

CSV de corrida: exigir exatamente 54 nomes de coluna, sem duplicatas, e presença de tick, t_s, drv, speed, s, lat, car_car, offtrack, cum_dist, authority e p_state. Dados congelados do PASS-1: 30.000 linhas por CSV, 10 pilotos, 3.000 amostras por piloto; ticks pares de 0 a 5.998, passo de 2 ticks; t_s em grade de 0,2 s. O script não imprime valores de linha em nenhuma falha de schema.

## Script e execução

- Script congelado: scripts/pass_1_diag.py, versão 1.0. Selftest usa somente estruturas sintéticas em memória e não abre CSV/log real.
- Pré-análise: validar os dois blobs do prereg/script contra o commit informado, depois verificar os hashes das fontes. O script exige --frozen-commit em modo análise e falha antes de abrir conteúdo se qualquer hash divergir.
- Schema pós-freeze: imprimir PASS/FAIL e apenas nomes de coluna/chaves; nunca imprimir valores de conteúdo durante a validação.
- Outputs novos e não sobrescritos em experiments/pass-1/autopsia/: 1_Q0_TENTATIVAS.csv, 2_Q0_INVERSOES.csv, 3_PACE_CURVATURA.csv, 4_REENTRADA_CONTATOS.csv, 5_PRIMEIRA_VOLTA.csv, 6_RESUMO.json.
- Após qualquer número novo, prereg e script permanecem imutáveis. Outputs são criados somente depois da validação integral.

## Freeze e PARE

1. Prereg e script em disco; selftest sintético; registrar SHA-256 dos dois.
2. Dono commita prereg e script e informa o hash.
3. Verificar git show <commit>:<path> byte-idêntico ao disco para os dois arquivos.
4. Só então executar análise, rehash dos Tier B e abrir conteúdo.

PARE obrigatório: hash divergente; qualquer valor de conteúdo pré-freeze além da declaração autorizada; detalhe de tentativa antes do freeze; schema divergente; conflito de intervalo/pareamento; tentativa de editar prereg/script após novos números; qualquer sim/smoke ou mudança de produção.
