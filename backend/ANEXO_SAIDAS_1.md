# ANEXO_SAIDAS_1 — Diagnóstico Pré-Registrado de Saídas Solo por Curva

Ciclo SAIDAS-1 · Branch `feat/sanidade-produto` · 2026-10-21  
Documento de encerramento e evidência do ciclo. Self-contained.  
**Decisão A×B**: ABERTA e CONGELADA — zero promoções, zero flips, zero alteração de leis de controle ou física.  
**Orçamento de corridas**: ZERO (re-análise mecânica estrita de artefatos existentes F4v15 s0).  
**Pools novos**: 76–79 permanecem VIRGENS.

---

## 1. Contexto e Reconciliação com as Âncoras F4v15

O dono reprovou ambos os perfis candidatos (A = v10-cego via `--profile race-blind`; B = composite via `--profile composite`) por qualidade de pilotagem: *"há curvas que eles saem mesmo estando sozinhos"*. Este ciclo executou o diagnóstico mecânico pré-registrado em `PREREG_SAIDAS_1.md` (commit `1c24988`) via o script auditável `scripts/saidas_verdict.py` (commit `7ea2f27`), com `--selftest` verde antes da leitura dos dados.

### 1.1. Reconciliação com as Âncoras F4v15 (Dentro da Tolerância Pré-Registrada)
| Perfil | Arquivo CSV Fonte | SHA256 / MD5 | % Fora Medido | % Fora Âncora | $\Delta$ (pp) | Episódios Medidos | Âncora Prereg | Dur. Mediana | Status |
|---|---|---|---|---|---|---|---|---|---|
| **A (v10-cego)** | `backend/experiments/f4v15-wiring/1_controle.csv` | `e84fdfc56257c712b1cf7bb13ddb0ee0` | **22,1167%** | **22,1%** | $+0,0167$ | **180** | 180 | 4,2 s | **PASS** ($\le 0,1\text{ pp}$) |
| **B (composite)** | `backend/experiments/f4v15-wiring/2_allcomposite.csv` | `89fdb023bcace2c42c940e86cb666e22` | **25,2133%** | **25,2%** | $+0,0133$ | **219** | 219 | 4,2 s | **PASS** ($\le 0,1\text{ pp}$) |

Reconciliação estrita com os marcos do projeto dentro da tolerância pré-registrada de $\le 0,1\text{ pp}$ (contatos 3674/2482/136/3/22,1 e 752/292/140/13/25,2 reproduzidos).

---

## 2. Respostas às Perguntas Pré-Registradas (Q1–Q4)

### Q1 — Quanto das saídas de pista é SOLO (sem tráfego envolvido)?

**Definição**: Nenhum outro carro a menos de $D=15\text{ m}$ (centro-a-centro euclidiano) na janela de $T=5,0\text{ s}$ anteriores ao início da excursão.  
**Estatística**: Bootstrap 95% CI com 10.000 reamostras (semente fixa `seed=42`).

| Perfil | Total Eventos | Taxa / 100 voltas | Eventos SOLO (D=15m) | **% SOLO** | **IC 95% Bootstrap** | Sensibilidade D=10m | Sensibilidade D=20m |
|---|---|---|---|---|---|---|---|
| **A (v10-cego)** | 180 | 180,0 | 84 | **46,7%** | **[39,4%, 53,9%]** | 57,2% (103/180) | 38,3% (69/180) |
| **B (composite)** | 219 | 219,0 | 183 | **83,6%** | **[78,5%, 88,1%]** | 88,1% (193/219) | 78,5% (172/219) |

**Leitura**:
- No **Perfil B (composite)**, **83,6% das saídas de pista ocorrem em isolamento completo** (sem nenhum carro a menos de 15 m nos 5 s prévios). O composite reduziu drasticamente contatos de tráfego (3674 $\to$ 752), mas as saídas que restam são quase inteiramente autônomas / intrínsecas à pilotagem solo.
- No **Perfil A (v10-cego)**, menos da metade das saídas é solo (**46,7%**); 53,3% envolvem proximidade com outros carros (disputas, desvios e colisões).
- Os intervalos de confiança de 95% **não se sobrepõem** ([39,4%, 53,9%] vs [78,5%, 88,1%]), confirmando objetivamente a queixa do dono com significância estatística inequívoca.

---

### Q2 — QUAIS curvas concentram as saídas? (Top-5 e Taxas)

Traçado segmentado em 11 complexos de curva (C01 a C11) a partir da curvatura física $|\kappa| > 0,006\text{ m}^{-1}$ de Interlagos v2 ($L=4160,4\text{ m}$, SF em $2655\text{ m}$).

#### Top-5 Curvas no Perfil A (v10-cego) — Total 180 eventos:
1. **C01 — Descida do Lago (T4/T5)** ($s \in [-32, 128]\text{ m}$): **48 saídas (26,7%)** | 48,0/100v | 52,1% solo
2. **C06 — Bico de Pato (T10)** ($s \in [1888, 1964]\text{ m}$): **40 saídas (22,2%)** | 40,0/100v | 55,0% solo
3. **C08 — Junção (T12)** ($s \in [2276, 2344]\text{ m}$): **40 saídas (22,2%)** | 40,0/100v | 52,5% solo
4. **C07 — Mergulho (T11)** ($s \in [2012, 2092]\text{ m}$): **37 saídas (20,6%)** | 37,0/100v | 43,2% solo
5. **C09 — Subida dos Boxes (T13/T14)** ($s \in [2468, 2564]\text{ m}$): **7 saídas (3,9%)** | 7,0/100v | 0,0% solo
- *Concentração*: As 4 principais curvas concentram **91,7%** (165/180) de todas as saídas do v10-cego.

#### Top-5 Curvas no Perfil B (composite) — Total 219 eventos:
1. **C01 — Descida do Lago (T4/T5)** ($s \in [-32, 128]\text{ m}$): **50 saídas (22,8%)** | 50,0/100v | 84,0% solo
2. **C07 — Mergulho (T11)** ($s \in [2012, 2092]\text{ m}$): **42 saídas (19,2%)** | 42,0/100v | 95,2% solo
3. **C08 — Junção (T12)** ($s \in [2276, 2344]\text{ m}$): **41 saídas (18,7%)** | 41,0/100v | 90,2% solo
4. **C06 — Bico de Pato (T10)** ($s \in [1888, 1964]\text{ m}$): **38 saídas (17,4%)** | 38,0/100v | 100,0% solo
5. **Reta — Reta Oposta / Retas Gerais**: **20 saídas (9,1%)** | 20,0/100v | 55,0% solo
*(Seguida de C10 Senna S com 10 saídas / 4,6%)*
- *Concentração*: As 4 principais curvas concentram **78,1%** (171/219) de todas as saídas do composite.

**Leitura**: Ambos os perfis falham exatamente nos **mesmos quatro pontos críticos**:
- **Descida do Lago (T4/T5)**: freada em descida pós-Reta Oposta.
- **Bico de Pato (T10)**: curva mais lenta e fechada do circuito (100% solo no composite!).
- **Mergulho (T11)**: compressão e transição rápida (95,2% solo no composite!).
- **Junção (T12)**: entrada de tração pré-subida dos boxes (90,2% solo no composite!).

---

### Q3 — MODO de Saída: Slide, Spin ou Linha Reta?

**Definição (Janela de 2,0 s pré-evento)**:
- **SPIN**: $|\dot{\psi}| \ge 45^\circ/\text{s}$ sustentado por $\ge 0,5\text{ s}$ ($\ge 3$ ticks a 5 Hz).
- **SLIDE**: Ângulo entre vetor velocidade $\vec{v}$ e heading do chassi $\psi$ (sideslip $\beta$) $\ge 10^\circ$ sem critério de spin.
- **LINHA-RETA**: Caso contrário (sem rotação violenta e sem deriva $\ge 10^\circ$).

| Perfil | LINHA-RETA | SLIDE (Deriva $\ge 10^\circ$) | SPIN ($|\dot{\psi}| \ge 45^\circ/\text{s}$ sust. $\ge 0,5\text{s}$) | Total |
|---|---|---|---|---|
| **A (v10-cego)** | **106 (58,9%)** | **74 (41,1%)** | **0 (0,0%)** | 180 |
| **B (composite)** | **143 (65,3%)** | **76 (34,7%)** | **0 (0,0%)** | 219 |

**Leitura**:
- **Zero spins sustentados**: Os carros não rodam em pirueta descontrolada antes de sair da pista.
- **Predomínio de Linha Reta / Subesterço (59% a 65%)**: O modo mais frequente é a perda de trajetória tangencial — o carro abre a curva em linha reta ou com esterçamento insuficiente, indo parar além da zebra externa.
- **Presença expressiva de Slide (35% a 41%)**: Em ~35-41% das ocorrências, o carro desliza com ângulo de deriva superior a $10^\circ$ (sobreesterço ou escorregamento dinâmico em 4 rodas).

---

### Q4 — Velocidade na Entrada: O carro entra rápido demais ou perde o carro em velocidade plausível?

**Definição**: Velocidade escalar $v$ medida a exatamente $1,0\text{ s}$ antes do início do evento de saída ($5\text{ ticks}$ a 5 Hz).

| Curva | Perfil A — $v_{\text{med}}$ (km/h) | Perfil A — IQR (km/h) | Perfil B — $v_{\text{med}}$ (km/h) | Perfil B — IQR (km/h) |
|---|---|---|---|---|
| **C01 — Descida do Lago (T4/T5)** | **60,2 km/h** (16,7 m/s) | 2,4 km/h | **60,0 km/h** (16,7 m/s) | 3,7 km/h |
| **C06 — Bico de Pato (T10)** | **46,9 km/h** (13,0 m/s) | 0,7 km/h | **46,8 km/h** (13,0 m/s) | 1,3 km/h |
| **C07 — Mergulho (T11)** | **44,4 km/h** (12,3 m/s) | 22,0 km/h | **42,1 km/h** (11,7 m/s) | 23,6 km/h |
| **C08 — Junção (T12)** | **35,4 km/h** (9,8 m/s) | 3,2 km/h | **36,8 km/h** (10,2 m/s) | 6,7 km/h |
| **C09 — Subida dos Boxes (T13/T14)** | **73,1 km/h** (20,3 m/s) | 8,0 km/h | **54,8 km/h** (15,2 m/s) | 22,1 km/h |
| **C10 — Senna S (T1/T2)** | **59,4 km/h** (16,5 m/s) | 10,7 km/h | **51,9 km/h** (14,4 m/s) | 56,5 km/h |
| **C11 — Curva do Sol (T3)** | *(sem saídas)* | — | **200,0 km/h** (55,6 m/s) | 137,3 km/h |
| **C02 — Ferradura (T6/T7)** | *(sem saídas)* | — | **122,9 km/h** (34,1 m/s) | 29,5 km/h |
| **Reta / Outro** | **83,8 km/h** (23,3 m/s) | 20,9 km/h | **66,1 km/h** (18,4 m/s) | 84,7 km/h |

**Leitura (Rotulagem R2 ratificada)**:
- **C01 (Lago) e C06 (Bico de Pato)**: IQRs estreitos ($\le 3,7\text{ km/h}$; C06 IQR 0,7 a 1,3 km/h; C01 IQR 2,4 a 3,7 km/h) a velocidades moderadas (47 km/h e 60 km/h). Trata-se de **repetição determinística**: o carro faz rigorosamente a mesma linha em todas as voltas e falha no mesmo ápice por subesterço/falta de raio.
- **C07 (Mergulho)**: IQR largo ($22,0\text{ a }23,6\text{ km/h}$), com velocidades espalhadas entre 31 e 72 km/h. Reflete **heterogeneidade de modos de falha** (entradas em aproximação rápida vs aproximação lenta pós-tráfego), que exigirá tratamento diferenciado pelo professor.
- **C08 (Junção)**: IQR intermediário ($3,2\text{ a }6,7\text{ km/h}$) em velocidade baixa ($35\text{ a }37\text{ km/h}$). Falha crônica de fechamento de raio em curva de baixa tração.
- Nas quatro curvas, as velocidades de saída são **plausíveis para curvas de raio $R \approx 5\text{--}16\text{ m}$ (classe hairpin)**. Os carros **não saem por descontrole em velocidade absurda**, mas por incapacidade do controlador neural em manter a trajetória no limite de aderência em curvaturas fechadas/médias.
- Saídas de alta velocidade ($> 120\text{ km/h}$) ocorrem raramente e apenas no Perfil B em curvas de raio longo (Curva do Sol, Ferradura).

---

## 3. Tabela Síntese Completa: Curva × Perfil

| Curva ID | Curva Nome | Perfil | Eventos | Taxa / 100v | % Solo | Modos (LR/SL/SP) | $v_{\text{1s}}$ Mediana | $v_{\text{1s}}$ IQR |
|---|---|---|---|---|---|---|---|---|
| **C01** | Descida do Lago (T4/T5) | A (v10-cego) | 48 | 48 | 52,1% | LR:43 / SL:5 / SP:0 | 60,2 km/h | 2,4 km/h |
| **C01** | Descida do Lago (T4/T5) | B (composite) | 50 | 50 | 84,0% | LR:43 / SL:7 / SP:0 | 60,0 km/h | 3,7 km/h |
| **C02** | Ferradura (T6/T7) | A (v10-cego) | 0 | 0 | 0,0% | — | — | — |
| **C02** | Ferradura (T6/T7) | B (composite) | 4 | 4 | 100,0% | LR:4 / SL:0 / SP:0 | 122,9 km/h | 29,5 km/h |
| **C05** | Pinheirinho (T9) | A (v10-cego) | 0 | 0 | 0,0% | — | — | — |
| **C05** | Pinheirinho (T9) | B (composite) | 3 | 3 | 100,0% | LR:3 / SL:0 / SP:0 | 153,4 km/h | 41,7 km/h |
| **C06** | Bico de Pato (T10) | A (v10-cego) | 40 | 40 | 55,0% | LR:17 / SL:23 / SP:0 | 46,9 km/h | 0,7 km/h |
| **C06** | Bico de Pato (T10) | B (composite) | 38 | 38 | 100,0% | LR:18 / SL:20 / SP:0 | 46,8 km/h | 1,3 km/h |
| **C07** | Mergulho (T11) | A (v10-cego) | 37 | 37 | 43,2% | LR:19 / SL:18 / SP:0 | 44,4 km/h | 22,0 km/h |
| **C07** | Mergulho (T11) | B (composite) | 42 | 42 | 95,2% | LR:21 / SL:21 / SP:0 | 42,1 km/h | 23,6 km/h |
| **C08** | Junção (T12) | A (v10-cego) | 40 | 40 | 52,5% | LR:17 / SL:23 / SP:0 | 35,4 km/h | 3,2 km/h |
| **C08** | Junção (T12) | B (composite) | 41 | 41 | 90,2% | LR:16 / SL:25 / SP:0 | 36,8 km/h | 6,7 km/h |
| **C09** | Subida dos Boxes (T13/T14) | A (v10-cego) | 7 | 7 | 0,0% | LR:5 / SL:2 / SP:0 | 73,1 km/h | 8,0 km/h |
| **C09** | Subida dos Boxes (T13/T14) | B (composite) | 5 | 5 | 40,0% | LR:5 / SL:0 / SP:0 | 54,8 km/h | 22,1 km/h |
| **C10** | Senna S (T1/T2) | A (v10-cego) | 4 | 4 | 0,0% | LR:1 / SL:3 / SP:0 | 59,4 km/h | 10,7 km/h |
| **C10** | Senna S (T1/T2) | B (composite) | 10 | 10 | 20,0% | LR:9 / SL:1 / SP:0 | 51,9 km/h | 56,5 km/h |
| **C11** | Curva do Sol (T3) | A (v10-cego) | 0 | 0 | 0,0% | — | — | — |
| **C11** | Curva do Sol (T3) | B (composite) | 6 | 6 | 66,7% | LR:5 / SL:1 / SP:0 | 200,0 km/h | 137,3 km/h |
| **Reta** | Reta / Outro | A (v10-cego) | 4 | 4 | 0,0% | LR:4 / SL:0 / SP:0 | 83,8 km/h | 20,9 km/h |
| **Reta** | Reta / Outro | B (composite) | 20 | 20 | 55,0% | LR:19 / SL:1 / SP:0 | 66,1 km/h | 84,7 km/h |

---

## 4. Reconciliação ENTRE-Pins e Erratas da Revisão (R1–R4 Ratificadas)

Conforme a regra estabelecida no SANIDADE-1b e aplicada no VARIEDADE-1, com as erratas obrigatórias ratificadas na revisão do orquestrador (2026-10-21):

### 4.1. Disclose R1 — Consistência Aritmética Q1 × Q2 (Fechamento Exato 84 e 183)
- **Origem do Aparente Conflito**: No texto preliminar de reporte (tabela Markdown), a curva C09 (Subida dos Boxes) do Perfil A foi descrita com `% solo = 42,9%` por erro tipográfico de edição manual, o que sugeriria $3$ saídas solo e uma soma aparente de $25 + 22 + 21 + 16 + 3 = 87 > 84$.
- **Verificação Mecânica no Código e Tabelas**:
  O script `scripts/saidas_verdict.py` e todos os arquivos CSV emitidos (`tabela_q1_solo.csv`, `tabela_q2_curvas.csv`, `tabela_resumo_curva_perfil.csv`, `eventos_saidas_detalhados.csv`) **sempre registraram 0 saídas solo em C09 para o Perfil A (0/7 = 0,0%)**.
- **Soma Perfeita por Subconjuntos Disjuntos**:
  - **Perfil A (v10-cego)**:
    $$\sum \text{solo por curva} = 25 (\text{C01}) + 22 (\text{C06}) + 21 (\text{C08}) + 16 (\text{C07}) + 0 (\text{C09}) + 0 (\text{C10}) + 0 (\text{Reta}) = \mathbf{84}$$
    Igualando **exatamente** o total de saídas solo medido na pergunta Q1: $\mathbf{84 / 180 = 46,7\%}$ [IC 95%: 39,4% – 53,9%]. Nenhum número moveu; os dados brutos e CSVs emitidos já fechavam com precisão de 100%.
  - **Perfil B (composite)**:
    Top-4 concentra $42 (\text{C01}) + 40 (\text{C07}) + 37 (\text{C08}) + 38 (\text{C06}) = 157$ saídas solo (em 171 eventos); Reta soma $11$ solo (em 20 eventos); C10 soma $2$ solo (em 10 eventos). Fora do Top-6, restam 18 eventos contendo exatamente $13$ saídas solo ($4$ em C11, $2$ em C09, $4$ em C02, $3$ em C05), totalizando:
    $$\sum \text{solo por curva} = 157 + 11 + 2 + 13 = \mathbf{183}$$
    Igualando **exatamente** o total de saídas solo medido na pergunta Q1: $\mathbf{183 / 219 = 83,6\%}$ [IC 95%: 78,5% – 88,1%].
  - O script `saidas_verdict.py` agora inclui asserção fail-loud automatizada comprovando $\sum \text{solo Q2} == \text{total solo Q1}$ para ambos os perfis.

### 4.2. Errata R2 — Rotulagem Precisa de IQR de Velocidade
- A dispersão de velocidade $1\text{ s}$ pré-saída foi devidamente segregada:
  - **C01 e C06**: IQR estreitíssimo ($\le 3,7\text{ km/h}$; C06 0,7 a 1,3 km/h; C01 2,4 a 3,7 km/h), caracterizando **repetição determinística** volta a volta no mesmo ponto.
  - **C07 (Mergulho)**: IQR largo ($22,0\text{ a }23,6\text{ km/h}$), com velocidades espalhadas entre 31 e 72 km/h, caracterizando **heterogeneidade de modos de falha**.
  - **C08 (Junção)**: IQR intermediário ($3,2\text{ a }6,7\text{ km/h}$) em velocidade baixa ($35\text{ a }37\text{ km/h}$).

### 4.3. Errata R3 — Correção de Grandeza (Eventos de Saída)
- A métrica reportada nas tabelas refere-se estritamente à **proporção de eventos de saída** ($91,7\%$ em A e $78,1\%$ em B concentrados nas 4 curvas), não ao tempo acumulado fora da pista.

### 4.4. Errata R4 — Rotulagem Canônica da Reconciliação
- Classificação ajustada para: "Reconciliação dentro da tolerância pré-registrada de $\le 0,1\text{ pp}$" ($22,1167\%$ vs $22,1\%$ [$\Delta = 0,0167\text{ pp}$] em A; $25,2133\%$ vs $25,2\%$ [$\Delta = 0,0133\text{ pp}$] em B; 180 e 219 eventos exatos; duração mediana 4,2 s exata).

### 4.5. Confirmações de Processo (R5)
1. **Inventário F0**: devidamente preservado e registrado no PREREG (`1c24988`, §4) com hashes MD5 íntegros.
2. **Definição de SLIDE**: tanto no prereg quanto no script mecânico, o critério pré-registrado é o ângulo de sideslip $|\beta| \ge 10^\circ$ pontual na janela prévia (com $v \ge 2,0\text{ m/s}$), sem exigência de sustentação de $0,5\text{ s}$ (que aplica-se unicamente ao SPIN).
3. **Persistência de Memória**: handoff via MCP `ai-memory` registrado com ID `01a15f49-85a7-7e61-a33b-5ad91a18aa31`.

---

## 5. Leads para o Professor Monaco_v2 e Próximos Passos

1. **Leads de Engenharia (R6)**:
   - **Retas no Perfil B**: 20 saídas (9,1%), das quais 55% a 80% são solo. Saídas em retas não decorrem de curvatura; o pré-registro do professor deve separar saídas limpas de saídas decorrentes de recuperação / re-entrada instável (efeito cascata de rejoin).
   - **Validação Cruzada com CICLO LARGADA**: O atrator da volta 1 pós-largada ($s \approx 31\text{--}35\text{ m}$, Senna S) não figura no Top-5 do Perfil A. Isso corrobora perfeitamente o DOSSIE_LARGADA: o storm inicial é estritamente induzido por contato no bolo, enquanto as saídas do SAIDAS-1 são patologias de pilotagem solo no miolo da volta.
   - **Cinemática de Curva Fechada**: As velocidades de entrada em C06 e C08 (35 a 47 km/h) são geometricamente compatíveis com raios de curvatura $R \approx 5\text{--}16\text{ m}$ (classe hairpin). O gargalo é falta de autoridade de esterçamento / aderência lateral sob baixa velocidade, e não descontrole por excesso de velocidade.
2. **Uso como Régua de Regressão (R7)**:
   - O script `scripts/saidas_verdict.py` torna-se o instrumento oficial de desfecho do ciclo do professor Monaco_v2 (baseline fixado nas tabelas deste ciclo).
3. **Decisão A×B**:
   - Permanece **ABERTA e CONGELADA** com o dono do projeto: o Perfil B troca contatos de tráfego ($-80\%$) por saídas solo ($83,6\%$), mantendo tempo fora ligeiramente superior ($25,2\%$ vs $22,1\%$). Nenhuma alteração de default foi realizada. Zero consumo de seeds novas (76–79 virgens).
