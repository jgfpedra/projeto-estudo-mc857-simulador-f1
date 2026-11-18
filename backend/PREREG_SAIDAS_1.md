# PREREG_SAIDAS_1 — Diagnóstico pré-registrado de saídas solo por curva

Ciclo SAIDAS-1 · Branch `feat/sanidade-produto` · 2026-10-21 · Commitado ANTES de rodar veredito/dados.
Self-contained. Re-análise estrita de artefatos existentes. Orçamento de corridas: ZERO.
Fresh seed pool (76–79) permanece VIRGEM.

---

## 1. Contexto e Motivação

O dono assistiu aos dois perfis candidatos na GUI:
- **Perfil A**: v10-cego (`--profile race-blind`)
- **Perfil B**: composite (`--profile composite`)

E **REPROVOU AMBOS** por qualidade de pilotagem: *"há curvas que eles saem mesmo estando sozinhos"*.
A DECISÃO A×B (adotar composite como default ou manter v10-cego) está **ABERTA e CONGELADA** — nenhum perfil foi adotado; zero flips; o default do wiring não é decisão deste ciclo.
Este ciclo NÃO decide A×B e NÃO altera pilotagem. É um ciclo de **LEITURA/ANÁLISE** que produz o diagnóstico rigoroso para alimentar o ciclo seguinte (professor `Monaco_v2`).

---

## 2. Perguntas Pré-Registradas (Q1–Q4)

Por perfil A (v10-cego) e perfil B (composite):
- **Q1 — Quanto das saídas de pista é SOLO (sem tráfego envolvido)?**
  Proporção (%) de eventos de saída que ocorrem sem nenhum outro carro a menos de $D=15\text{ m}$ nos $T=5\text{ s}$ anteriores ao evento, com IC 95% via bootstrap.
- **Q2 — QUAIS curvas concentram as saídas?**
  Ranking de curvas por volume de saídas (top-5 e taxa por 100 voltas).
- **Q3 — MODO de saída: slide, spin/rolamento ou linha reta?**
  Distribuição percentual dos modos cinemáticos nos 2 s anteriores ao evento.
- **Q4 — Velocidade na entrada: o carro entra rápido demais ou perde o carro em velocidade plausível?**
  Mediana e IQR de velocidade $v$ a 1 s antes do evento por curva.

---

## 3. Definições Fixas (com arquivo:linha)

### 3.1. Evento de Saída de Pista
- **Definição canônica**: Início de episódio contíguo onde `offtrack == 1` (transição $0 \to 1$ ou tick 0 já fora).
- **Localização no código**:
  - `backend/model_train/race_diagnostic.py:855`: `offtrack=int(abs(lat_s) > ctrl_i._half_width)` onde `ctrl_i._half_width = 6.00 m`.
  - `backend/scripts/sanidade1b_verdict.py:130`: `dict(off=round(100 * df.offtrack.mean(), 1), ...)`
  - `backend/scripts/sanidade1b_verdict.py:86-96`: contagem de episódios de excursão contíguos (`durs.append((j - i) * ROW_S)` com `ROW_S = 0.2 s`).
- **Reconciliação obrigatória**:
  - Perfil A: média de `offtrack` fecha exatamente em **22,1%** (6635/30000 ticks = 22,12%), com 180 episódios e duração mediana de 4,2 s.
  - Perfil B: média de `offtrack` fecha exatamente em **25,2%** (7564/30000 ticks = 25,21%), com 219 episódios e duração mediana de 4,2 s (exatamente os 219 derivados no SANIDADE-1b).

### 3.2. Saída SOLO
- **Critério Primário**: Nenhum outro carro a menos de $D = 15\text{ m}$ (centro-a-centro euclidiano 2D) nos $T = 5\text{ s}$ (25 ticks a 5 Hz) anteriores ao início do evento:
  $$\min_{j \neq i, \, t \in [t_{\text{ev}} - 5.0, \, t_{\text{ev}}]} d_{ij}(t) \ge D$$
- **Critério Secundário / Sensibilidade**: $D \in \{10, 20\}\text{ m}$ na mesma janela temporal.
- **Reconstrução de Posição $(x, y)$**:
  O CSV canônico armazena $s$ (progresso na linha central em metros) e `obs4` (posição lateral normalizada). A posição lateral sinalizada em metros é:
  $$\text{slat} = \text{obs4} \times 6.00\text{ m} \quad (\text{patrimônio D0: } \texttt{backend/scripts/sanidade1b\_verdict.py:31})$$
  Com a linha central congelada `backend/model_train/tracks_frozen/interlagos_v2.json` (`sha256=164876196eb12174`), a posição mundial do centro do chassi é:
  $$x(t) = x_c(s(t)) - \text{slat}(t) \cdot \sin(\psi_{\text{track}}(s(t)))$$
  $$y(t) = y_c(s(t)) + \text{slat}(t) \cdot \cos(\psi_{\text{track}}(s(t)))$$
  Esta reconstrução fecha contra as coordenadas $(ax, ay)$ de colisão do `_events.csv` com erro sub-step de 0,23 m.

### 3.3. Modo de Saída (Janela de 2 s anteriores ao evento, 10 ticks a 5 Hz)
- **SPIN**: Taxa de guinada sustentada $|\dot{\psi}| \ge 45^\circ/\text{s}$ ($\ge 0,7854\text{ rad/s}$) sustentada por $\ge 0,5\text{ s}$.
  - Em amostragem discreta a $5\text{ Hz}$ ($\Delta t = 0,2\text{ s}$): primário $\ge 3$ ticks consecutivos ($0,6\text{ s} \ge 0,5\text{ s}$); sensibilidade $\ge 2$ ticks ($0,4\text{ s}$).
- **SLIDE**: Ângulo entre vetor velocidade $\vec{v}$ e heading do chassi $\psi$ (ângulo de sideslip / deriva lateral) $|\beta| \ge 10^\circ$ sem critério de spin:
  $$\beta = \text{wrap}\left(\arctan2(v_y, v_x) - \psi\right)$$
  onde $\vec{v} = (\Delta x / \Delta t, \Delta y / \Delta t)$ é derivado por diferenças finitas de posição (com guarda para $v < 1,0\text{ m/s}$ onde $\beta = 0$).
- **LINHA-RETA**: Caso contrário (o carro segue sua linha/subesterça para fora sem rotação violenta e sem deriva $\ge 10^\circ$).
- **Variantes documentadas**:
  - *Variante 1 (Primária / Física)*: Heading do chassi derivado da telemetria de observação `obs5` ($\sin(\psi_{\text{err}})$) e `obs6` ($\cos(\psi_{\text{err}})$) somado ao heading do segmento da pista:
    $$\psi_{\text{chassis}} = \psi_{\text{track}}(s) + \arctan2(\text{obs5}, \text{obs6})$$
    que reproduz o `phys['heading_rad']` exato do simulador (`backend/model_train/race_diagnostic.py:1152-1161`).
  - *Variante 2 (Puramente Cinemática / Trajetória)*: Heading aproximado pela direção da velocidade $\arctan2(\Delta y, \Delta x)$. Por definição trigonométrica, nesta variante o ângulo entre velocidade e heading é $0^\circ$ (SLIDE degenerado), servindo como controle negativo de rotação pura de trajetória.

### 3.4. Curvas do Traçado (Interlagos v2)
- **Geometria fonte**: `backend/model_train/tracks_frozen/interlagos_v2.json` (1131 waypoints, comprimento canônico $L = 4160,4\text{ m}$, linha de largada/chegada em $s = 2655,0\text{ m}$).
- **Curvatura**: calculada via `compute_kappa_profile(wps, ds_target=4.0, smooth_window_m=30.0)` (`backend/model_train/velocity_profile.py:85-140`).
- **Limiar de Curva**: $|\kappa| > 0,006\text{ m}^{-1}$ ($R < 166,7\text{ m}$) com fusão de blocos contíguos com gap $< 40\text{ m}$ (multi-ápices contíguos).
  *Justificativa (2 linhas)*: O limiar $0,006\text{ m}^{-1}$ isola fielmente os 11 complexos de curva de Interlagos (T1 a T15 oficiais) contra o ruído de discretização da spline, enquanto o gap de 40 m unifica curvas compostas (Senna S, Descida do Lago, Ferradura) sem fundir trechos de reta intermediários.
- **Tabela de Curvas (C01 a C11 na ordem do traçado)**:
  - **C01** ($s \in [-32, 128]\text{ m}$ [wrap $4128..4160 \to 0..128$]): Descida do Lago (T4/T5) — $\kappa_{\max} = 0,0420$
  - **C02** ($s \in [220, 336]\text{ m}$): Ferradura (T6/T7) — $\kappa_{\max} = 0,0366$
  - **C03** ($s \in [988, 1124]\text{ m}$): Curva do Laranjinha (T8) — $\kappa_{\max} = 0,0436$
  - **C04** ($s \in [1176, 1240]\text{ m}$): Pinheirinho Entrada / Esse — $\kappa_{\max} = 0,0286$
  - **C05** ($s \in [1596, 1804]\text{ m}$): Pinheirinho (T9) — $\kappa_{\max} = 0,0284$
  - **C06** ($s \in [1888, 1964]\text{ m}$): Bico de Pato (T10) — $\kappa_{\max} = 0,0454$
  - **C07** ($s \in [2012, 2092]\text{ m}$): Mergulho (T11) — $\kappa_{\max} = 0,0533$
  - **C08** ($s \in [2276, 2344]\text{ m}$): Junção (T12) — $\kappa_{\max} = 0,0739$
  - **C09** ($s \in [2468, 2564]\text{ m}$): Subida dos Boxes / Arquibancadas (T13/T14) — $\kappa_{\max} = 0,0241$
  - **C10** ($s \in [2748, 2852]\text{ m}$): Senna S (T1/T2, pós-SF 2655 m) — $\kappa_{\max} = 0,0311$
  - **C11** ($s \in [3128, 3156]\text{ m}$): Curva do Sol (T3) — $\kappa_{\max} = 0,0081$
  - *Reta / Outro*: Trechos entre curvas (Reta Oposta, Reta dos Boxes, Reta entre T3 e T4).

### 3.5. Velocidade de Entrada (Q4)
- Amostrada a $1,0\text{ s}$ antes do evento de saída ($5\text{ ticks}$ anteriores a $5\text{ Hz}$):
  $$v_{\text{entry}} = \text{speed}(t_{\text{ev}} - 1.0\text{ s})$$
- Reportada como mediana e amplitude interquartil (IQR = Q3 − Q1) por curva e perfil.

---

## 4. Dados Usados (Inventário F0)

- **Perfil A (v10-cego / race-blind)**:
  `backend/experiments/f4v15-wiring/1_controle.csv` (md5: `e84fdfc56257c712b1cf7bb13ddb0ee0`)
  `backend/experiments/f4v15-wiring/1_controle_events.csv` (md5: `e306744b5bb6f6c62d8d4f7858589ac2`)
  (Bit-idêntico a `sanidade-0/1_prot_v0.csv`, `sanidade-1b/1_prot_v0.csv`, `variedade-1/1_prot_v0.csv`).
- **Perfil B (composite)**:
  `backend/experiments/f4v15-wiring/2_allcomposite.csv` (md5: `89fdb023bcace2c42c940e86cb666e22`)
  `backend/experiments/f4v15-wiring/2_allcomposite_events.csv` (md5: `0ab49fbea73a085aff924e8ec9e142ac`)
  (Bit-idêntico a `sanidade-0/2_prot_comp.csv`, `sanidade-1b/2_prot_comp.csv`, `variedade-1/2_prot_comp.csv`).
- **Pista Canônica**:
  `backend/model_train/tracks_frozen/interlagos_v2.json` (`sha256=164876196eb12174`).

---

## 5. Plano de Análise Estatística

- Análise estritamente descritiva (diagnóstico).
- Estatísticas reportadas:
  - Contagem total de eventos e taxa por 100 voltas ($10\text{ carros} \times 10\text{ voltas} = 100\text{ voltas}$).
  - Fração solo (%) e intervalo de confiança bootstrap de 95% (percentil bca / percentil standard):
    - **10.000 reamostras**, com semente fixa **`seed = 42`** declarada aqui antes da execução.
  - Ranking de curvas (top-5) por volume de saídas.
  - Distribuição percentual de modos (LINHA-RETA, SLIDE, SPIN).
  - Mediana e IQR de velocidade de entrada por curva.
- Sem testes de hipótese formais (ciclo de leitura/análise).

---

## 6. Formato das Tabelas de Saída

As tabelas serão emitidas pelo script `scripts/saidas_verdict.py` no diretório `backend/experiments/saidas-1/`:
1. `tabela_q1_solo.csv`: perfil, total_eventos, eventos_solo, pct_solo, ci95_low, ci95_high, solo_10m, solo_20m.
2. `tabela_q2_curvas.csv`: perfil, curva_id, curva_nome, eventos, taxa_100v, pct_do_perfil, rank.
3. `tabela_q3_modos.csv`: perfil, modo, contagem, pct.
4. `tabela_q4_velocidade.csv`: perfil, curva_id, curva_nome, n, v_med_mps, v_iqr_mps, v_med_kmh, v_iqr_kmh.
5. `tabela_resumo_curva_perfil.csv`: curva x perfil completo com eventos, taxa/100v, % solo, modos e v entrada.

---

## 7. Critérios de Reconciliação com as Âncoras F4v15

1. A taxa temporal média de fora (`offtrack.mean()`) de cada perfil DEVE fechar bit-idêntica com os valores históricos das âncoras F4v15:
   - Perfil A: `round(100 * df.offtrack.mean(), 1) == 22.1%` (exatamente $22,1167\%$).
   - Perfil B: `round(100 * df.offtrack.mean(), 1) == 25.2%` (exatamente $25,2133\%$).
2. Total de episódios de excursão:
   - Perfil A: 180 episódios.
   - Perfil B: 219 episódios (exatamente a âncora de 219 excursões do SANIDADE-1b).
3. Caso qualquer discrepância ocorra, interromper imediatamente (fail-loud).

---

## 8. Confirmação Pós-Hoc (Revisão SAIDAS-1-review · 2026-10-21)

Em atenção aos NITs de processo da revisão do orquestrador (R5):
1. **Inventário F0 de Telemetria**: Confirmado presente e visível na Seção 4 acima com os hashes MD5 das âncoras F4v15 (`1_controle.csv` md5: `e84fdfc56257c712b1cf7bb13ddb0ee0` e `2_allcomposite.csv` md5: `89fdb023bcace2c42c940e86cb666e22`).
2. **Critério SLIDE e Sustentação**: No texto histórico pré-registrado (§3.3) e na implementação mecânica (`scripts/saidas_verdict.py`), o critério SLIDE é $|\beta| \ge 10^\circ$ pontual na janela de 2,0 s (com guarda de velocidade $v \ge 2,0\text{ m/s}$), sem exigência de sustentação temporal de $\ge 0,5\text{ s}$ (esta última foi exigência estrita apenas para o modo SPIN). Registra-se esta confirmação pós-hoc preservando a integridade histórica do texto original.

