# PREREG — FAIL-FORENSICS-1b (errata E3 + retomada Monaco)

**Status:** congelado antes de R3/R4; qualquer medição só começa após commit dedicado deste arquivo.
**Errata ratificada:** `88c3e0e` — governa 14 hesitações Composite Interlagos F4v15.
**Instrumento offline:** `ad5a88d` — `scripts/fail_forensics_verdict.py`; SHA-256 `dd8f05e814c1cccb388cb8e31dba3441428575467ee9a7a23420e379abbb75bf`.
**Comportamento do simulador:** congelado; nenhuma mudança em policy, física, pools, dados de pista ou ambiente.

## 1. Escopo e ratificação

Esta é uma retomada do FAIL-FORENSICS-1. As corridas 1–2 de Interlagos já
foram concluídas e seus CSVs/eventos reproduziram as âncoras F4v15 byte a byte;
permanecem entradas válidas. A única causa do PARE anterior foi a divergência
documental 13×14. Pela ratificação FF1-E3, **14 governa**; não há re-pin nem
edição retroativa do prereg, veredito, PARE ou relatório congelados da tentativa
anterior. B3' (HESIT ≤3) e ANTI-D3-1 (primário) permanecem FAIL.

Orçamento desta retomada: **duas corridas seriais** (R3 e R4) e no máximo um
re-smoke idêntico em seed 0 somente se um processo falhar antes de produzir um
CSV completo/legível. Resultado de âncora divergente não autoriza re-smoke:
aciona PARE imediato, sem R4 e sem re-pin.

## 2. Identidade frozen e entradas declaradas

### Pistas, pesos e instrumento

| Item | Identidade pré-fixada |
|---|---|
| Monaco frozen | `model_train/tracks_frozen/Monaco_v2.json`; SF 0; 834 waypoints; short SHA `67ca11dc211c8c78`; SHA-256 `af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2` |
| Interlagos frozen | `model_train/tracks_frozen/interlagos_v2.json`; SF 729; 1131 waypoints; short SHA `164876196eb12174`; SHA-256 `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613` |
| Ator v10 | `model_train/v10_dagger/dagger_actor_best.keras`; SHA-256 `b75ab0e56d64457589a7f2a869c4d4140dafb6ad7c6a6a03560dbfe6c0e94b2e`; NumPy weights SHA-256 `bc5ea6e288a4f0c36eb9257a1ac5d478c6cf51549a9b492ac0b89b90951b93e3` |
| Residual composite | `model_train/v15_residual/residual_best_weights.npz`; SHA-256 `6a2dbf53a69fcac70d97b91c59b431785240682f28bf262be26de4f62f96baa6` |
| Runner | `model_train/race_diagnostic.py`, checkout `feat/sanidade-produto`, HEAD `ad5a88d` antes deste prereg; Python e dependências do `backend/.venv` |
| Veredito offline | `scripts/fail_forensics_verdict.py`, commit `ad5a88d`, SHA-256 acima; não chama o simulador |

### Corridas 1–2 já entregues

As saídas abaixo são as reproduções em `experiments/fail-forensics-1/` e têm
os mesmos bytes das âncoras originais F4v15. Não reexecutar:

| Braço | CSV SHA-256 | `_events.csv` SHA-256 | Métricas de reconciliação |
|---|---|---|---|
| Cego Interlagos, seed 0 | `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733` | `11e8c657b6ffc6ab65d98fbeb7af56983d1658447f0b1093edc8a862444ca3b9` | 3674 contatos, 2482 pós-60s, rolante 136,0 s, 3 hesitações, fora 22,1% |
| Composite Interlagos, seed 0 | `512ba0d2553b1c3acacc69582a6877a883f570aee4cf72658a7925f164310155` | `1f79529e40117dd5eb3e53dcfe18ad6598e95d6ce2f1ccc83d377b82ccce7b54` | 752 contatos, 292 pós-60s, rolante 140,0 s, **14 hesitações**, fora 25,2% |

### Âncoras Monaco existentes para a taxonomia offline

Os CSVs s0–s4 de `experiments/prof-monaco-1/` são todas entradas declaradas.
Os hashes pinam os bytes completos (o comentário no cabeçalho registra o seed):

| Braço | s0 | s1 | s2 | s3 | s4 |
|---|---|---|---|---|---|
| Professor | `282a175c03f484ccc0e5872b20a4e5d9c98c0bdba7dafb7d825fe3708213dfc9` | `bf03432cd04dceaa0323c812fbe45ddf1d3365f45e7a4d1e1717c0cf038a1f49` | `7a3c4c6efa1f071b2e264a73ef24e1b4371d44ef9f20feeabd4cfe07833de946` | `fb47e7ec1985e1dcd5af8331dc761d3256010cca4120a269f022fffb02e850b8` | `45e32943d1207010bdf7d0fca0ea119ea462395c0d6cd63df530ca3d8ce9da9f` |
| Aluno cego | `f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0` | `0a46e4bc510bedc6e50911b8b7bf1b2cb021e9767bbaad768b32f2f02b9820af` | `6a7a44d2bfc06ba673d2da68a65000e787dd4e9fcadf7d9b8ccb82b9ddc6996e` | `201211cb2b5065047c5a1f8b3d2c42ab759f49b211b2972c0b8235069595df2d` | `44ef4d0f5f611bace546df48aa13581129a39e5fc4eeaf795a71dda92a07f3a4` |

Os cinco arquivos de dados de cada braço têm linhas idênticas entre seeds; só
o comentário de cabeçalho difere. Assim são cinco arquivos, mas uma realização
de dados por braço. A réplica `prof_s0_rep.csv` é byte-idêntica a `prof_s0.csv`
(SHA `282a175c…`); `aluno_s0_rep.csv` é byte-idêntica a `aluno_s0.csv`
(SHA `f43c760a…`). Não tratar seeds 0–4 como cinco realizações independentes.

## 3. Ordem e comandos das novas corridas

Executar de `backend/`, sempre uma corrida de simulador por vez; cada stdout e
stderr será escrito com `tee` no log do worktree durante o mesmo passo.
Adicionar ao log, antes do próximo processo, o SHA-256 completo da pista e do
CSV (e do `_events.csv` quando existir).

### R3 — cego Monaco solo, somente leak-check

Replicar o instrumento/condições `PROF-MONACO-1` no seed 0 e comparar o CSV
produzido byte a byte com `experiments/prof-monaco-1/aluno_s0.csv`, SHA-256
esperado `f43c760a1dca3d7ca5697ec15c2960fd8c6a66541f35cd565fe9a725cf0ffca0`.
Monaco `Monaco_v2.json`, um carro, 600 s (`6000` ticks), `edge`, v10, seed 0,
clima seeded (âncora teve zero transições), governor `vplan`, variância off.

```bash
set -o pipefail
.venv/bin/python model_train/race_diagnostic.py \
  --controller neural --actor model_train/v10_dagger/dagger_actor_best.keras \
  --obs-mode edge --n-cars 1 --ticks 6000 --laps 99 \
  --track monaco --seed 0 --weather seeded --gov vplan --variance off \
  --out experiments/fail-forensics-2/3_blind_monaco_s0.csv 2>&1 \
  | tee experiments/fail-forensics-2/3_blind_monaco_s0.log
sha256sum model_train/tracks_frozen/Monaco_v2.json \
  experiments/fail-forensics-2/3_blind_monaco_s0.csv \
  >> experiments/fail-forensics-2/3_blind_monaco_s0.log
if cmp -s experiments/fail-forensics-2/3_blind_monaco_s0.csv \
     experiments/prof-monaco-1/aluno_s0.csv; then
  echo "ANCHOR_MATCH aluno_s0.csv" >> experiments/fail-forensics-2/3_blind_monaco_s0.log
else
  echo "ANCHOR_MISMATCH aluno_s0.csv — PARE; R4 não executar" \
    >> experiments/fail-forensics-2/3_blind_monaco_s0.log
  exit 1
fi
```

**Gate R3:** verificar no log a identidade `Monaco_v2`, SF/short SHA, seed,
clima e configuração; comparar com `cmp` e SHA esperado. Qualquer byte/config
divergente = completar `PARE.md` desta retomada e parar antes de R4; não
reanalisar nem re-pin.

### R4 — composite Monaco, primeira realização N=1

Somente após R3 passar. Mesmo caminho composite da etapa Interlagos: 10 carros,
6000 ticks, laps 99, Monaco frozen, seed 0, clima seeded, `vplan`, variância
`grid,compound`, residual pinado acima. Executar exatamente uma vez; não há
gate de performance, intervalo, claim estatístico ou promoção. Divulgar
explicitamente `N=1`.

```bash
set -o pipefail
.venv/bin/python model_train/race_diagnostic.py \
  --profile composite --n-cars 10 --ticks 6000 --laps 99 \
  --track monaco --seed 0 --weather seeded --gov vplan \
  --variance grid,compound \
  --out experiments/fail-forensics-2/4_composite_monaco_s0.csv 2>&1 \
  | tee experiments/fail-forensics-2/4_composite_monaco_s0.log
sha256sum model_train/tracks_frozen/Monaco_v2.json \
  model_train/v15_residual/residual_best_weights.npz \
  experiments/fail-forensics-2/4_composite_monaco_s0.csv \
  experiments/fail-forensics-2/4_composite_monaco_s0_events.csv \
  >> experiments/fail-forensics-2/4_composite_monaco_s0.log
```

Disclose a diferença de desenho: R3 é corrida solo com variância off para
reproduzir `aluno_s0`; R4 é 10-carros com `grid,compound`, como R1/R2. Ambos
fixam seed 0, Monaco_v2, climate seeded e código frozen, mas **não são braços
pareados pelo grid/variância**; não interpretar sua diferença como efeito
causal do residual. Zero transições de clima é condição a confirmar nos logs.

## 4. Contrato do conjunto offline

Entrada da taxonomia: as duas corridas Interlagos entregues acima; `prof_s0`–
`prof_s4` e `aluno_s0`–`aluno_s4` já existentes (cada uma sem CSV de contatos
solver-side, logo EVENTS `-`); R3 (EVENTS `-`); R4 com seu arquivo de eventos
solver-side. São 14 arquivos CSV no total, mas as réplicas Monaco s0–s4 por
braço têm uma única sequência de dados distinta. Nenhum CSV é filtrado.

O `scripts/fail_forensics_verdict.py` grava `resumo_corridas.csv`,
`eventos_classificados.csv`, `saltos_projecao.csv`, `causas_pista_braco.csv`,
`casos_exemplares.csv` e `relatorio.md` em
`experiments/fail-forensics-2/veredito/`. Labels distinguem `blind`, `aluno`,
`professor` e `composite`.

### Eventos e precedência causal

- **Off-track:** episódio contíguo de amostras `offtrack=1`; unidade = início.
- **Contato:** agrupar solver por tick/par; pontos do mesmo par até 10 ticks de
  distância são um episódio. Registrar pontos, soma de impulso normal e maior
  `Δv`. CSVs sem evento solver não afirmam contato.
- **Preso:** janela alinhada de 30 s, com qualquer amostra off-track, e
  `max(|lat|)>20 m` ou amplitude de `cum_dist <5 m`; unidade = janela/carro.
- **Hesitação:** todos os episódios contíguos de `speed<0,5 m/s`, após
  `t>20 s`, com duração `0,3–<3,0 s`, inclusive se a janela estiver off-track.
  Isso reproduz o contador que governa E3: 14 no Composite Interlagos. A antiga
  extração P1 era explicitamente on-track e por isso contava 13.
- **Salto de projeção:** comparar amostras adjacentes por carro,
  `Δs_wrapped` contra `Δcum_dist`. Métrica primária `|Δs_wrapped−Δcum_dist|`
  `≥30 m`; publicar também sensibilidade `≥10/20 m`, p50/p95, e localizar
  todos os eventos ≥10 m com tick, `s`, `lat`, velocidade, comandos, authority,
  `cum_dist` e índices anterior/seguinte de segmento derivados do `s` frozen.

Os CSVs não contêm `x,y` nem o índice cru do `nearest_segment`; esta bateria
não pode afirmar um salto bruto da busca nearest. A métrica congelada é o proxy
de continuidade `s`/odômetro, com segmento nearest **derivado de s** para
localização. Registrar essa limitação sem adicionar colunas ou mudar o runner.

Atribuir exatamente uma causa a cada evento classificado com esta precedência:

1. **COLISÃO:** o próprio contato; para off-track/preso/hesitação/salto, exigir
   impulso solver-side positivo do mesmo carro até 1,0 s antes.
2. **RECUPERAÇÃO:** sem colisão, authority `rejoin`, `recovery` ou
   `recovery_rejoin` no evento ou nos 10 s anteriores.
3. **CURVA:** sem anteriores, modo `SLIDE`/`SPIN` ou complexo de curva segundo
   `saidas_verdict.py`; guardar modo literal e complexo.
4. **TRAJETÓRIA:** caso restante, inclusive salto sem evidência anterior de
   colisão/recuperação e excursão sem slip extremo.

Cada registro classificado mantém tick/time, carro, `s`/`lat`, velocidade,
acelerador/freio/esterço, authority, impulso/`Δv` quando disponível, segmento
derivado, complexo/modo e causa. Atribuição mecânica de causa não é prova
contrafactual. O veredito deve conter tabela pista × braço × causa, saltos,
casos exemplares e recomendações ao dono para etapa 2 (recuperação em fases /
corridor). Sem gates novos nesta etapa.

## 5. Selftest golden e checagens obrigatórias

Antes de R3, após este prereg estar commitado:

```bash
.venv/bin/python scripts/fail_forensics_verdict.py --selftest
.venv/bin/python scripts/saidas_verdict.py --selftest
```

O primeiro precisa validar hashes e classificação dos anchors Monaco
professor/aluno, dados repetidos s0–s4, salto sintético, hashes e métricas dos
anchors Interlagos cego/composite (incluindo 14 hesitações). O segundo valida
os casos cinemáticos sintéticos e geometrias frozen Interlagos/Monaco.

Após R3, leak-check obrigatório antes de R4. Após R4, rodar o veredito somente
offline sobre as entradas listadas. O resultado Monaco Composite é N=1. Logs,
CSV, eventos, SHAs completos, relatório, veredito e updates em state/worklog
ficam versionados no worktree antes do fechamento.
