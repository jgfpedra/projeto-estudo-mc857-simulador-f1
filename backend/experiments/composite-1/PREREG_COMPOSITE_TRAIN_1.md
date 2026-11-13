# PREREG_COMPOSITE_TRAIN_1

> **Status:** Pré-registro formal ratificado com Emendas Pré-Freeze do Proprietário (Etapa A2: pré-freeze, ZERO treino do corpus real, ZERO corrida, commit nenhum)  
> **Data:** 27 de Outubro de 2026  
> **Branch:** `feat/sanidade-produto`  
> **Git HEAD:** `0972bdce8ba201f2bd6b73283ee4b420dcbc3756`  
> **Corpus Pin:** Commit `33c75ce`, 20 shards + 2 audits (`A_audit.json` SHA dataset `5d29d1808695528c7a8bfc8e03cb335d95d5fab35ef16076b708dd3fca6b215b`, `B_audit.json` SHA dataset `2089d289c0f3b2adc01b0431c6af7bedb1a5522362101d4e9a39ab3ab3a593bc`)  
> **Linha Arquitetural:** `CompositeActor` / `NumpyCompositeActor` (Solo v10 CONGELADO + Gate Escalar × Resíduo Neural)

---

## 1. Contexto e Objetivos

O experimento `COMPOSITE-BASE-1` estabeleceu a calibração de base (closing `0972bdc`). O orçamento de corrida para esta etapa é **ZERO**.
O alvo de desempenho a ser melhorado pela linha composite é:
1. **Contatos (−36% / −44%):** Defender as reduções de colisão obtidas em relação ao solo puro.
2. **Ritmo Interlagos (−8 cruzamentos e fora +6,7pp):** Recuperar a perda de ritmo e reduzir o tempo fora da pista.
3. **Hesitações (+9 / +7):** Recuperar a fluidez de ultrapassagem e reentrada sem hesitações indevidas pós-manobra.
4. **Comportamento Degenerado ("Presos" 10/10):** "Presos" (10/10 em todos os carros) é degenerado e **NÃO** é alvo.

O objetivo do `COMPOSITE-TRAIN-1` é treinar um **novo resíduo neural** ($16 \to 2$) sobre o corpus balanceado de 48.000 amostras de treino para refinar a política residual, mantendo o ator solo v10 estritamente **CONGELADO** (bit-a-bit idêntico, jamais retreinado).

---

## 2. Arquitetura Citada do Fonte e Modo de Integração

### 2.1 Modelo Residual e Ator Composto
A arquitetura é estritamente espelhada dos fontes existentes no repositório:
- **Ator Composto (`model_train/residual_gated.py`):**
  - Linhas 105–140 (`CompositeActor`): Estrutura Keras $a = \tanh(m_{\text{solo}} + g \cdot r)$, onde $m_{\text{solo}}$ é a ativação linear pré-tanh do solo v10 congelado, $g \in [0, 1]$ é o gate escalar de tráfego, e $r \in \mathbb{R}^2$ é a saída do resíduo.
  - Linhas 142–187 (`NumpyCompositeActor`): Motor de inferência NumPy para o runner de corrida:
    ```python
    x = np.maximum(0.0, x @ w[0] + w[1])  # Dense(128, relu)
    x = np.maximum(0.0, x @ w[2] + w[3])  # Dense(128, relu)
    r = x @ w[4] + w[5]                   # Dense(2, linear)
    a = np.tanh(m_solo + g * r)
    ```
  - Linhas 92–102 (`build_residual_keras(n_in=16)`):
    - Camada de entrada: `Input(shape=(16,), name='residual_in')`
    - Camada oculta 1: `Dense(128, activation='relu', name='res_d1')`
    - Camada oculta 2: `Dense(128, activation='relu', name='res_d2')`
    - Camada de saída: `Dense(2, activation=None, name='res_out', kernel_initializer='zeros', bias_initializer='zeros')`
    - Inicialização em zeros garante que no início do treino $r = [0, 0]$, reproduzindo exatamente o comportamento do solo v10 isolado.
  - Linhas 189–198 (`export_residual_npz`): Exporta os tensores de pesos e vieses das camadas densas para um arquivo `.npz` com chaves `{layer_name}_{idx}` (`res_d1_0`, `res_d1_1`, `res_d2_0`, `res_d2_1`, `res_out_0`, `res_out_1`), compatíveis com `NumpyCompositeActor`.

### 2.2 Vetor de Entrada do Resíduo (16-dim)
Construído conforme `scripts/composite_corpus.py` (linhas 713–731, `build_residual_input`):
1. **Features de tráfego (12 dimensões):** 4 slots ordenados $\times$ 3 métricas $[d_s, d_{\text{lat}}, \Delta v]$.
2. **Velocidade do ego normalizada (1 dimensão):** $v_{\text{ego}} / 100.0$.
3. **Curvatura à frente escalada (1 dimensão):** $\kappa_{\text{ahead}} \times 25.0$.
4. **Esterço anterior (1 dimensão):** $\text{steer}_{t-1} \in [-1, 1]$.
5. **Aceleração/frenagem anterior (1 dimensão):** $\text{long}_{t-1} \in [-1, 1]$.
*Total:* 16 valores finitos (`float32`).

### 2.3 Alvo do Treinamento Residual (`r_targets`, 2-dim) e Disclosure Formal de Gate (Emenda O-4)
Construído conforme `scripts/composite_corpus.py` (linhas 861–864):
```python
clipped = [max(-0.98, min(0.98, value)) for value in a_teacher]
r_target = [math.atanh(value) - m for value, m in zip(clipped, m_solo)]
```
**Disclosure Formal (Emenda O-4):**
- O alvo de treino $r_{\text{target}}$ foi formulado sob a suposição matemática implícita de **gate $g=1$** no momento da coleta e extração do corpus.
- O schema dos shards do corpus armazena estritamente: `compound_id`, `ctx`, `drv`, `geometry_id`, `geometry_sha256`, `instrument_version`, `r_targets`, `res_inputs`, `run`, `source_git_sha256`, `source_sha256`, `split`, `t_s`, `telemetry`, `tick`, `track_id`. Os valores brutos de $a_{\text{teacher}}$, $m_{\text{solo}}$ e $g$ **NÃO** estão gravados nos registros do corpus.
- Portanto, todos os critérios offline de treino e validação (§5(b)) são calculados de forma estritamente **SEM-GATE** diretamente no espaço residual ($r \in \mathbb{R}^2$).
- Em simulação de corrida ao vivo, o escalar $g \in [0, 1]$ (computado dinamicamente pelas regras de aproximação de tráfego) modula a aplicação do resíduo via `NumpyCompositeActor.predict` (`residual_gated.py:171-181`): $a = \tanh(m_{\text{solo}} + g \cdot r)$.

### 2.4 Modo de Integração Futura (Apenas Documentado — ZERO Execução Nesta Etapa)
Para corridas de avaliação e diagnóstico futuras, a integração é realizada sem qualquer modificação em arquivos de produção:
- **`model_train/race_diagnostic.py` (linhas 1024–1026 e 1339–1350):**
  Suporta a flag `--residual-override <caminho_npz>`. Quando fornecida, carrega o arquivo de pesos do candidato no `NumpyCompositeActor`, exibindo os hashes SHA-256 do candidato e da baseline de controle.
- **`scripts/run_race_10_cars.py` (linhas 75, 85, 1817–1825):**
  O perfil de produção aponta para `model_train/v15_residual/residual_best_weights.npz`. Durante os testes de avaliação da etapa B/C, o candidato é avaliado via injeção pontual (`--residual-override`) ou por branch de validação controlada, mantendo o arquivo de produção intocado.

---

## 3. Localização do Pipeline Histórico de Treino (Disciplina 1F)

O pipeline histórico de treino do resíduo v15 (`residual_best_weights.npz`) reside em:
- **`model_train/train_dagger.py` (linhas 187–203, `train_residual_bc`):**
  - **Função de Perda:** `tf.keras.losses.Huber(delta=1.0)`
  - **Otimizador:** `tf.keras.optimizers.Adam(learning_rate=1e-3)`
  - **Batch Size:** `256`
  - **Input Shape:** `(-1, 16)`
  - **Target Shape:** `(-1, 2)`
  - **Seleção:** `val_loss = float(hist.history['val_loss'][-1])`
- **`model_train/train_dagger.py` (linhas 551–570):**
  - Linha 556: Salva checkpoints iterativos: `residual_iter{N}.keras`.
  - Linha 565: Copia o melhor modelo para `residual_best.keras`.
  - Linhas 568–570: Exporta os pesos em NPZ:
    ```python
    from backend.model_train.residual_gated import export_residual_npz
    export_residual_npz(residual, out / 'residual_best_weights.npz')
    ```
O instrumento implementado em `scripts/train_composite_residual.py` espelha diretamente essas linhas históricas, eliminando reinvenções e garantindo conformidade matemática e arquitetural com o pipeline do projeto.

---

## 4. Divisão dos Dados e Protocolo de Selamento

O corpus é composto por 20 shards e 2 audits gerados sob a regra `rank-80/10/10-per-run-v1`:
- **TRAIN (48.000 amostras):**
  - Caso A (24.000): `{PIA, NOR, LEC, HAM, PER, RUS, GAS, ALO}` (3.000 amostras por piloto)
  - Caso B (24.000): `{PIA, RUS, GAS, LEC, HAM, NOR, PER, ALO}` (3.000 amostras por piloto)
- **VALIDATION (6.000 amostras):**
  - Caso A (3.000): `{SAI}`
  - Caso B (3.000): `{VER}`
  - *Função:* Define o critério de parada (early-stopping) e seleção do melhor checkpoint (`best_epoch`).
- **TEST (6.000 amostras — SELADO):**
  - Caso A (3.000): `{VER}` (`A_A_ON_dump.jsonl_VER.json`)
  - Caso B (3.000): `{SAI}` (`B_B_ON_dump.jsonl_SAI.json`)
  - **REGRA DE SELAMENTO ESTREITO:** O bucket de teste está estritamente **SELADO**.
  - O instrumento `scripts/train_composite_residual.py` possui asserts e blacklist ativa: se qualquer chamada tentar carregar o split `"test"`, acessar os arquivos selados, ou se qualquer registro contiver `"split": "test"`, a execução aborta imediatamente com `SealedTestBucketViolationError` (PARE imediato).

---

## 5. Decisões Ratificadas com Emendas Pré-Freeze do Proprietário

### (a) Orçamento de Treino e Prova de Reprodutibilidade com Réplica Obrigatória (Emenda O-3)
- **Orçamento Formal da Etapa B:** Exatamente **2 treinos**:
  1. **Run 1:** Treino formal do candidato (`seed=42`).
  2. **Run 2:** Réplica obrigatória (`seed=42`), executada com os mesmos hiperparâmetros exatos (50 épocas, batch size 256, Adam lr=1e-3, Huber loss delta=1.0).
- **Isolamento de Nomenclatura da Réplica:**
  - A réplica grava **APENAS** artefatos com o sufixo `_replica`:
    - `experiments/composite-1/train-1/composite_residual_replica_1.keras`
    - `experiments/composite-1/train-1/composite_residual_replica_1_weights.npz`
    - `experiments/composite-1/train-1/composite_residual_replica_1_metrics.json`
  - A réplica **NUNCA** sobrescreve o candidato `composite_residual_candidato_1`.
  - **Checagem de Não-Pré-existência (Espelho da Emenda B.1):** Qualquer arquivo de saída já existente no início de um treino real resulta em aborto imediato (`FileExistsError`).
- **Gates Duros Ratificados de Reprodutibilidade:**
  Ao término do Run 2, o comparador offline inspeciona os dois arquivos `.npz` (chaves ordenadas) e os dois arquivos de métricas JSON. Se:
  $$\max |\Delta W| \ge 10^{-5} \quad \text{OU} \quad |\Delta \text{val\_loss}| \ge 10^{-4}$$
  **Gatilho de PARE Imediato:** A execução falha, é reportada e para imediatamente. Proibido tentar novamente (sem retry) e proibido escolher subjetivamente o melhor run.

### (b) Critérios de Sucesso em Validação Offline (Emenda O-1 / O-4)
Como o orçamento de corrida é ZERO nesta etapa, o critério de sucesso do treinamento é 100% offline sobre os 6.000 registros do split de validação (A SAI = 3.000, B VER = 3.000), estritamente sem gate e no espaço residual:
1. **Redução da Perda Huber vs Resíduo Nulo (Espaço Residual):**
   - Baseline nula: $L_{\text{Huber}}(\text{null})$ calculada com $r = [0, 0]$ (equivalente ao solo v10 isolado).
   - Critério obrigatório: $L_{\text{Huber}}(\text{candidato}) \le 0.80 \times L_{\text{Huber}}(\text{null})$ (redução mínima de 20% no erro de predição do vetor $r_{\text{target}}$).
2. **Aproximação de Delta Residual vs Linha Nula (Emenda O-1):**
   - Substituição do critério incomputável de ação:
     $$\text{MAE}(r_{\text{cand}}, r_{\text{target}}) < \text{MAE}(\mathbf{0}, r_{\text{target}})$$
     calculado diretamente sobre os 6.000 registros de validação, no espaço residual $r \in \mathbb{R}^2$ exatamente como armazenado nos registros.
3. **Métrica Proxy de Segurança e Estabilidade Numérica:**
   - Norma euclidiana média do resíduo predito: $\|r_{\text{cand}}\|_2 \le 2.0$ sobre todo o split de validação (previne saturação descontrolada da $\tanh$).
   - Integridade numérica: ZERO valores `NaN`, `Inf` ou nulos em qualquer ativação ou peso do modelo (`nan_inf_count == 0`).

> **Disclosure de Transferência de Métrica (Emenda O-1):**  
> Como o schema do corpus consolidado não armazena $m_{\text{solo}}$, $a_{\text{teacher}}$ nem o valor escalar do gate $g$, o cálculo do $\text{MAE}$ no espaço de ação saturada ($\tanh(m_{\text{solo}} + g \cdot r)$ vs $a_{\text{teacher}}$) é incomputável de forma offline. Essa métrica é formalmente transferida para o estágio de avaliação em corrida do `COMPOSITE-BASE-2`, onde o ator composto opera em malha fechada no simulador com telemetria viva, permitindo a mensuração da fidelidade da ação combinada sob saturação e das métricas cinemáticas resultantes.

### (c) Contrato de Métricas JSON e Isolamento de Checkpoints (Emenda O-2)
- **Contrato de Gravação:** O instrumento `scripts/train_composite_residual.py` grava obrigatoriamente o arquivo de métricas:
  `experiments/composite-1/train-1/composite_residual_candidato_1_metrics.json`
  utilizando `json.dump` com `sort_keys=True, indent=2` em gravação única atômica ao final do run real. Se a gravação falhar ou o arquivo não existir/estiver vazio, aciona-se PARE imediato.
- **Esquema de Conteúdo Mínimo do JSON:**
  - `run`: Identificador do run (`"Run 1 (candidato)"` ou `"Run 2 (replica)"`).
  - `is_replica`: Booleano (`false` para Run 1, `true` para Run 2).
  - `seeds`: Dicionário com sementes (`python: 42, numpy: 42, tensorflow: 42`).
  - `hparams`: Hiperparâmetros congelados (epochs=50, batch_size=256, lr=1e-3, loss="Huber(delta=1.0)", optimizer="Adam").
  - `counts`: Contagens exatas de amostras com quebra por caso:
    - `train`: `total=48000`, `case_A=24000`, `case_B=24000`.
    - `validation`: `total=6000`, `case_A=3000`, `case_B=3000`.
  - `huber_cand`: Perda Huber no split de validação.
  - `huber_null`: Perda Huber da baseline nula ($r=0$).
  - `val_loss_improvement_ratio`: Razão $L_{\text{cand}} / L_{\text{null}}$.
  - `mae_r1`: $\text{MAE}(r_{\text{cand}}, r_{\text{target}})$ em validação.
  - `mae_zeros`: $\text{MAE}(\mathbf{0}, r_{\text{target}})$ em validação.
  - `mean_norm_r`: Média de $\|r_{\text{cand}}\|_2$ em validação.
  - `nan_inf_count`: Contagem de valores não-finitos (obrigatório 0).
  - `best_epoch`: Época de menor erro de validação.
  - `best_val_loss`: Menor `val_loss` atingido.
  - `sha256_keras`: Hash SHA-256 do arquivo `.keras` (calculado após salvamento).
  - `sha256_npz`: Hash SHA-256 do arquivo `.npz` (calculado após exportação).
  - `sha256_script`: Hash SHA-256 de `scripts/train_composite_residual.py`.
  - `sha256_git_head`: Hash SHA-256 do commit git HEAD (`0972bdce8ba201f2bd6b73283ee4b420dcbc3756`).
  - `corpus_audits`:
    - `case_A_dataset_sha256`: `5d29d1808695528c7a8bfc8e03cb335d95d5fab35ef16076b708dd3fca6b215b`
    - `case_B_dataset_sha256`: `2089d289c0f3b2adc01b0431c6af7bedb1a5522362101d4e9a39ab3ab3a593bc`
    - `case_A_audit_file_sha256`: `3631168758e5531b194352ff94004a9f90d8d6423fa7ace9a95a27d6d7586cf3`
    - `case_B_audit_file_sha256`: `e9066ab8bba40858c50b702b14135a9b277d990415fedf93a73c4136cc43c9e5`
- **Proibição de Colisão e Promoção:** Proibido gravar ou sobrescrever qualquer arquivo em `model_train/v15_residual/` ou qualquer subdiretório de produção. Promoção é estritamente PROIBIDA neste ciclo.

### (d) Condições Mandatórias de PARE (Gatilhos de Interrupção Imediata)
1. **Tentativa de Leitura do Split TEST:** Qualquer abertura de arquivo ou consulta a dados de teste (`A_A_ON_dump.jsonl_VER.json` ou `B_B_ON_dump.jsonl_SAI.json`).
2. **Execução de Treinamento na Etapa A/A2:** Qualquer disparo de treinamento no corpus real de 48k antes da autorização formal do freeze pelo proprietário.
3. **Execução de Corrida:** Qualquer execução de simulador ou corrida nesta etapa (orçamento = ZERO).
4. **Promoção de Modelo / Edição de Produção:** Qualquer alteração em `model_train/v15_residual/` ou nos arquivos de perfil de corrida.
5. **Divergência de Réplica (Emenda O-3):** Se na Etapa B $|\Delta \text{val\_loss}| \ge 10^{-4}$ OU $\max |\Delta W| \ge 10^{-5}$ entre Run 1 e Run 2.
6. **Pré-existência de Arquivos de Saída (Emenda B.1 / O-3):** Se os arquivos de saída já existirem no início de uma corrida real.
7. **Falha de Gravação do Metrics JSON (Emenda O-2):** Se o JSON de métricas não for gravado ou estiver vazio ao final da execução.
8. **Modificação de Ledgers ou Anexos na Etapa A/A2:** Edições em `PROJECT_STATE.md`, `worklog.md`, `AUDITORIA_RL.md` ou criação de novos anexos.
9. **Uso de PIP / Alteração de Dependências:** Jamais rodar `pip`.
10. **Commits no Repositório:** O executor não realiza commits no Git na etapa A/A2.

---
*Fim do Pré-Registro COMPOSITE-TRAIN-1 (Etapa A2).*
