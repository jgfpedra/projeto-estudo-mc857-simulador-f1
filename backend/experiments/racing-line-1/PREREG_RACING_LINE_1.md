# PREREG_RACING-LINE-1 — linha suavizada local do professor

**Data:** 2026-11-06 (America/Sao_Paulo)
**Branch:** `feat/sanidade-produto`
**Estado:** abertura; aguardando Freeze do Dono
**Programa de origem:** PROF-CURVA-1, encerrado em PARE no commit `a0e9139`.

## 1. Hipótese e escopo

O mapa de viabilidade do PROF-CURVA-1 mostrou que o teto local de `v_plan` é
inviável: a Guarda de Ritmo estoura no piso teórico e a Descida do Lago não é
explicada por excesso de velocidade do plano. Este ciclo testa uma hipótese
diferente: uma linha virtual local, geometricamente mais suave, pode reduzir a
demanda lateral e a cascata na Junção sem impor um teto longitudinal global.

O único candidato desta preregistração é uma curva circular de raio **18 m**
na Junção de Interlagos, em torno de `s≈2318`. O candidato é report-only até
que a geometria passe os gates offline e uma implementação opt-in seja
congelada. Não há autorização para corrida nesta abertura.

## 2. Constantes e fontes congeladas

As pistas são lidas apenas dos arquivos locais:

| pista | arquivo frozen | identidade pinada |
|---|---|---|
| Interlagos | `backend/model_train/tracks_frozen/interlagos_v2.json` | `164876196eb12174` |
| Monaco | `backend/model_train/tracks_frozen/Monaco_v2.json` | `67ca11dc211c8c78` |

As regiões e os eventos são definidos pelas funções canônicas
`build_corner_definitions`, `match_corner` e `extract_excursions`, sem
recalcular limites manualmente após observar resultados. A janela inicial da
Junção será a região C08 produzida pela geometria frozen; os limites efetivos
serão registrados no JSON do mapa antes de qualquer corrida.

Constantes fixadas antes da execução:

- raio do arco candidato: `R = 18,0 m`;
- continuidade: posição e tangente C1 nos dois limites;
- linha fora da janela: exatamente a linha frozen de referência;
- corredor permitido: faixa da pista frozen, sem ampliar largura;
- reamostragem: a mesma resolução da geometria de referência, sem editar o
  arquivo frozen;
- corrida, se autorizada: professor solo, 600 s, N=0..4, duas pistas, série;
- nenhum `--prof-curva`, governor novo, matriz de 10 carros ou treino.

O raio 18 m é uma proposta geométrica do encaminhamento do PROF-CURVA-1; ele
não é derivado de uma nova busca pós-resultado e não pode ser ajustado depois
de observar os gates.

## 3. Construção determinística do candidato

O instrumento deve executar a seguinte construção, sem fallback silencioso:

1. carregar a pista frozen local e verificar o SHA pinado;
2. obter a janela C08 pela definição canônica de curva;
3. encontrar um arco circular de `R=18 m` tangente às direções da linha nos
   limites da janela;
4. substituir somente os pontos internos à janela e preservar os pontos
   externos;
5. rejeitar se não houver solução, se houver descontinuidade C1, se o arco
   sair do corredor, se houver auto-interseção ou se a linha não fechar;
6. medir o erro de projeção para a pista e escrever todos os limites,
   parâmetros, hashes e métricas no JSON;
7. repetir em processo separado e exigir JSON byte-idêntico (`cmp=0`).

O arquivo frozen nunca é sobrescrito. Se o arco exigir mover os limites,
alterar a largura, trocar a pista, suavizar outros setores ou escolher um
raio diferente, o resultado é PARE e exige nova preregistração.

## 4. Mecanismo futuro, isolado e opt-in

Se o mapa offline passar, a implementação futura deverá operar somente no
professor solo, consultando a linha virtual para a referência geométrica. Ela
não poderá:

- modificar `VelocityProfile`, `v_plan` ou o governor de produção;
- modificar a física, a pista frozen, o grid ou o caminho não-professor;
- engajar por default;
- aceitar uma pista com SHA desconhecido;
- ser chamada por carros que não sejam professor.

A flag OFF deve ser byte-idêntica ao baseline. A flag ON fora do professor
deve falhar explicitamente. O código só será escrito depois do Freeze da
Task 2/3 correspondente.

## 5. Gates formais

### Gate Primário — Interlagos

Em cada realização ON, zero excursões em C01/Descida do Lago, C06/Bico de
Pato, C07/Mergulho e C08/Junção, e zero excursões novas em qualquer outra
região. A tabela por realização é obrigatória; melhora agregada não compensa
regressão localizada.

### Gate Monaco

`fora_ON <= fora_OFF - 5 pp` na comparação agregada definida pelo instrumento,
sem aumento de excursões, `|lat|` máximo ou tempo fora em qualquer curva.

### Guarda de Ritmo

O maior tempo de volta solo ON deve ser comparado à Guarda de 123,05 s pinada
no PROF-CURVA-1. Se o candidato ultrapassar esse teto para permanecer limpo,
é PARE automático; não se reduz o raio nem se relaxa a guarda.

### Gates de geometria e integridade

O candidato deve passar C1, corredor, fechamento, auto-interseção, projeção e
determinismo antes de qualquer corrida. Cada corrida futura deve ter exit 0,
3.002 linhas, sidecar, SHA de pista, variedade no log e duas métricas com
`metrics_sha256` idêntico.

## 6. Orçamento e ordem de execução

O orçamento máximo futuro é de dez corridas solo de 600 s (N=0..4 em duas
pistas), mais leituras determinísticas dos instrumentos. Não há 10 carros,
treino, rede, alteração de cache ou promoção.

Ordem obrigatória:

1. Freeze do presente plano/prereg;
2. mapa geométrico offline em duas leituras;
3. PARE se a geometria falhar; caso contrário, prereg/Freeze da implementação;
4. implementação isolada e testes OFF/ON;
5. corridas solo e extrações;
6. gates, relatório, linha nos três ledgers e PARE para closing.

## 7. Critérios de PARE

PARE imediato se houver falta de pista frozen, SHA divergente, solução
geométrica não C1, arco fora do corredor, auto-interseção, `cmp≠0`, alteração
OFF, saída fora do escopo do professor, violação da Guarda de Ritmo ou falha
de qualquer gate formal. Nenhum desses casos autoriza ajustar o candidato
post hoc.

**Estado desta abertura:** zero corrida, zero alteração de produção, zero
alteração da pista frozen; aguardando Freeze do Dono.

## Emenda nº 1 — Limites Derivados por Bi-Tangência

**Data:** 2026-11-07 · **Origem:** PARE §7 da Task 2 ratificado pelo dono em
`f7faaed` (resíduo 3,19 m nos limites congelados; raiz bi-tangente registrada).

A construção do §3 passa a adotar **limites derivados por bi-tangência** para
a janela C08/Junção, ratificando a raiz dominante registrada em
`c2/GEOMETRIA_C08.json`:

- **s_a = 2282,417 m** e **s_b = 2342,863 m** — pontos de tangência exatos do
  círculo com a linha frozen (giro −139,89°, resíduo < 1e-6 m);
- **R = 18,0 m permanece estritamente inalterado**;
- pista frozen intocada; as regras de governança (§2, §6, §7) e os gates
  formais (§5) permanecem íntegros;
- o instrumento de validação deve **re-derivar a raiz da geometria frozen** e
  conferir os limites ratificados (tolerância 0,01 m) antes de construir;
- os gates de geometria do candidato — corredor (|lat| ≤ 6,0 m da linha
  central frozen), C1 (desvio angular < 1,0° nas duas emendas), fechamento
  (< 1e-4 m) e zero auto-interseção — passam a ser avaliados sobre a linha
  virtual em `scripts/racing_line_1_corredor.py`, com arco discretizado a
  ds ≤ 1,0 m e duas leituras seriais `cmp=0`.

Nenhuma outra constante ou regra muda. Corrida segue proibida nesta etapa;
o estado após a validação é **PARE para Freeze do Dono**.
