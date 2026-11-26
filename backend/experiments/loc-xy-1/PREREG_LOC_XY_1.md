# PREREG LOC-XY-1 — instrumentação CSV aditiva

**Estado:** preparado depois do baseline e antes de qualquer alteração de código.
**Base:** `7272973` (`docs(fail-forensics-1b): fechar medicao Monaco`).
**Ciclo:** LOC-XY-1; apenas telemetria aditiva; zero mudança de comportamento.

## 1. Identidade, estado e orçamento

- Estado canônico consultado: `backend/PROJECT_STATE.md` e
  `backend/model_train/AUDITORIA_RL.md`; FF-1b fechado; FF1-E3 vigente:
  Composite Interlagos = 14 hesitações.
- Histórico de largada/tráfego e recuperação consultado em `worklog.md` e
  `sessions/dsh-continuacao.md`.
- No início, `git status` continha somente o stray
  `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md`; ele permanece intocado e fora
  de stage.
- Orçamento: zero corridas de medição; uma corrida smoke de identidade, seed 0,
  Interlagos blind; zero seeds de pool consumidas; pistas frozen.
- Referência pré-mudança: `backend/experiments/fail-forensics-1/1_blind_interlagos_s0.csv`,
  SHA-256 `47df0ed834e8e8a6a5c2f114cee6ee745230ce0f37d7682890debe9d3f15c733`,
  30.000 linhas, 49 colunas, seed 0, Interlagos frozen, 10 carros.
- Identidade frozen Interlagos: `model_train/tracks_frozen/interlagos_v2.json`,
  SF 729, 1.131 waypoints, SHA-256
  `c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613`.

## 2. Contrato do CSV v3.4

O export `--out` ganha, no fim do header, exatamente nesta ordem:
`body_x`, `body_y`, `ns_raw`. No smoke blind: 49 colunas legadas + 3 novas =
52 no total. Não será adicionada `ns_dist`.

- `body_x` e `body_y`: coordenadas mundiais X/Y do centro de massa do chassi,
  em metros, lidas do `PhysicsEngine.get_state()` que já consulta
  `pybullet.getBasePositionAndOrientation`. O mundo usa X/Y no plano da pista e
  Z vertical; sinais positivos são os sentidos crescentes dos eixos mundiais
  armazenados na geometria frozen. A origem é a origem desse mesmo mundo.
- `ns_raw`: índice inteiro do waypoint inicial do segmento que vence a busca
  global `Track.nearest_segment(body_x, body_y)`, sem suavização, continuidade,
  hints ou pós-processamento. Para cada segmento fechado `i`, com
  `P_i=(x_i,y_i)`, `P_{i+1}` e `q=(body_x,body_y)`, a projeção é
  `t_i=clip(((q-P_i)·(P_{i+1}-P_i))/||P_{i+1}-P_i||², 0, 1)` e a distância é
  `d_i=||q-(P_i+t_i(P_{i+1}-P_i))||`; o resultado é o `i` do menor `d_i²` na
  varredura global atual. Segmentos com comprimento² `<1e-9` são ignorados e,
  em empate, o primeiro índice visitado permanece, por comparação estrita `<`.
- `RACE_DIAG_NO_XY=1`: não calcula/emite as três colunas e mantém o header
  v3.3. O arquivo resultante deve ser byte-idêntico à referência v3.3 de mesmo
  seed/configuração.

Fonte de XY somente leitura: `phys['x']`/`phys['y']` já devolvidos pelo getter
existente. Fonte do índice: método global de `Track`; sem chamadas a setters ou
alterações em objetos de simulação. Nenhuma lógica de controle, governor,
física, ordenação ou contador será tocada; os contadores canônicos 13/14 ficam
inalterados.

## 3. Suíte e testes novos

Baseline serial concluído antes do código: **20F/349P/3S**, log bruto
`0_baseline_pytest.log`, SHA-256
`dba9ff77f808e844be260bcf2a90b4e2ff46d8fff5f08e275ca6415467fdf7e3`.
São as 20 falhas canônicas conhecidas. Serão adicionados exatamente três casos:

1. Header v3.4: as três colunas novas são as últimas e seguem a ordem declarada.
2. Roundtrip `ns_raw`: uma linha do fixture frozen LOC-XY-1 confere o índice
   armazenado com uma re-derivação auxiliar independente sobre a geometria
   Interlagos frozen.
3. Kill-switch: escrever o fixture pré-mudança com colunas novas sintéticas e
   `RACE_DIAG_NO_XY=1` reproduz todos os bytes da referência v3.3.

**NIT aritmético pré-execução:** o pedido cita 20F/353P/3S, mas o baseline
observado é 20F/349P/3S; com exatamente três novos testes e falhas/skips
inalterados, a conta é 20F/352P/3S. Não será criado um quarto teste para
forçar a soma. O gate pós-código declara a contagem observada; PARE se surgir
qualquer falha fora das 20 canônicas ou se o conjunto canônico mudar. Se houver
um passe adicional não causado pelos três testes, registrar e explicar o delta.

## 4. Ordem fixa dos gates

1. Baseline acima (feito antes de alterações).
2. Adicionar os três testes especificados.
3. Reexecutar a suíte serial, declarar o resultado real, preservar as 20 falhas
   canônicas e os 3 skips; qualquer falha não canônica = PARE.
4. Uma única corrida smoke, serial, a partir de `backend/`:

   ```bash
   .venv/bin/python model_train/race_diagnostic.py \
     --actor model_train/v10_dagger/dagger_actor_best.keras --obs-mode edge \
     --n-cars 10 --ticks 6000 --laps 99 --track interlagos --seed 0 \
     --weather seeded --gov vplan --variance grid,compound \
     --out experiments/loc-xy-1/4_smoke_seed0_interlagos_blind_v34.csv
   ```

   A corrida roda uma vez com XY habilitado. A mesma tabela em memória/CSV será
   serializada pelo caminho do kill-switch para comparação com a referência,
   sem iniciar outro engine. Provar por hashes: (i) projeção das 49 colunas
   legadas do v3.4 == referência v3.3; (ii) serialização com o kill-switch ==
   referência byte a byte; (iii) as três colunas novas estão presentes,
   preenchidas e tipadas (`float`, `float`, inteiro). Qualquer divergência de
   comportamento/campo legado ou bit-id falha = PARE.
5. Selftests golden existentes (`fail_forensics_verdict.py --selftest` e
   `saidas_verdict.py --selftest`) permanecem passando.

## 5. Entregas e congelamento

- Relatório em `experiments/loc-xy-1/relatorio.md`, com hashes, comparação
  campo a campo, diff de código, decisão sobre `ns_dist` e limitações.
- Anexo aditivo em `model_train/AUDITORIA_RL.md`, seção LOC-XY-1 no
  `PROJECT_STATE.md` e entrada no `worklog.md`; nenhuma seção histórica será
  reescrita. Registrar NITs abertos/fechados conforme sua evidência.
- Logs brutos versionados. Commits dedicados: prereg + baseline antes do código;
  implementação + exatamente três testes; fechamento com evidências e livros.
- Stray `backend/backend/ANEXO_SAIDAS_1_ERRATAS.md` intocado, não staged.
