# EXECUCAO_PROF_GRIP_1 — Avaliação Formal dos Gates e Closing

**Data:** 2026-11-07  
**Branch:** `feat/sanidade-produto`  
**Commit de Origem / Task 2 Freeze:** `54ef40f`  
**Preregistro:** `PREREG_PROF_GRIP_1.md` (SHA `6568b9a8…`)  
**Matriz Executada:** 12 corridas solo de 600 s (2 controles OFF `cmp=0` + 10 ON com `--variedade N`, N=0..4)  

---

## 1. Verificação de Integridade e Bit-Identidade

- **Corridas:** 12/12 exit=0, 3.002 linhas de telemetria por CSV, sidecars de evento vazios (solo sem contatos).
- **Bit-Identidade OFF Provada:**
  - `CTRL_Interlagos_OFF.csv`: `cmp=0` contra o controle histórico do PROF-CONTROL-1.
  - `CTRL_Monaco_OFF.csv`: `cmp=0` contra o controle histórico do PROF-CONTROL-1.
- **Diversidade Mecânica Real ON:** Realizações independentes confirmadas via `--variedade 0..4` registradas nos logs e banners.
- **Extrações Determinísticas:** 24 extrações via `prof_curva_metrics.py --mode off` com 12/12 pares `cmp=0`.

---

## 2. Resultados Consolidados

### Interlagos (5 Realizações Independentes, `--variedade N`)

| Corrida | Fora % | Excursões | C01 (Lago) | C06 (Bico) | C07 (Mergulho) | C08 (Junção) | Reta | Mediana de Volta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **CTRL_OFF** | 24,567% | 20 | 4 | 4 | 4 | 4 | 4 | 130,195 s |
| **ON N0** | 24,533% | 20 | 4 | 4 | 4 | 4 | 4 | 130,195 s |
| **ON N1** | 24,367% | 19 | **3** | 4 | 4 | 4 | 4 | 129,639 s |
| **ON N2** | 24,067% | 19 | **3** | 4 | 4 | 4 | 4 | 129,005 s |
| **ON N3** | 24,667% | 20 | 4 | 4 | 4 | 4 | 4 | 130,428 s |
| **ON N4** | 24,433% | 20 | 4 | 4 | 4 | 4 | 4 | 130,069 s |

### Mônaco (5 Realizações Independentes, `--variedade N`)

| Corrida | Fora % | Excursões | C05 | C12 | Mediana de Volta |
|---|---:|---:|---:|---:|---:|
| **CTRL_OFF** | 56,933% | 41 | 3 | 4 | 211,786 s |
| **ON N0** | 56,933% | 41 | 3 | 4 | 211,786 s |
| **ON N1** | 56,167% | 41 | 3 | 3 | 208,258 s |
| **ON N2** | 56,633% | 41 | 3 | 4 | 212,844 s |
| **ON N3** | 57,000% | 42 | **4** | 4 | 213,340 s |
| **ON N4** | 57,300% | 42 | **5** | **3** | 215,816 s |

---

## 3. Avaliação Formal dos Gates

1. **Gate Primário (Interlagos — Zero Saídas nas 4 Crônicas): REPROVADO (FAIL)**
   - O critério do preregistro exigia zero saídas em C01, C06, C07 e C08 em **cada realização ON**.
   - C06, C07 e C08 permaneceram com **4/4/4/4** saídas em todas as 5 realizações ON.
   - C01 melhorou marginalmente (3 saídas em N1 e N2), mas falhou em zerar (3/4 saídas).

2. **Gate Secundário (Mônaco — Δofftrack ≤ 0 e Zero Regressões Locais): REPROVADO (FAIL)**
   - Em N3 e N4, o offtrack aumentou (+0,07 pp e +0,37 pp).
   - Ocorreram regressões localizadas em C05: 3 saídas no controle $\to$ 4 saídas em N3 e 5 saídas em N4.

3. **Guarda de Ritmo (Mediana de Volta Interlagos ≤ 123,05 s): REPROVADO (FAIL)**
   - A mediana observada ficou entre 129,00 s e 130,43 s (> 123,05 s).
   - O próprio controle OFF histórico já operava a 130,20 s (carregando o arrasto de sair da pista).

---

## 4. Diagnóstico Físico e Causa Raiz do Não-Engajamento

A causa mecânica da ineficácia do `--prof-grip` nesta formulação foi identificada:
1. No controlador, a velocidade alvo histórica já possui uma margem de segurança fixa embutida:  
   $v_{\text{tgt, hist}} = 0,93 \cdot v_{\text{plan}}(s)$.
2. O teto preregistrado aplicava:  
   $v_{\text{cap}} = v_{\text{plan}}(s) \cdot \min\left(1, \sqrt{\frac{grip}{0,85}}\right) \cdot \sqrt{\frac{1}{1,10}} = v_{\text{plan}}(s) \cdot \text{fator}$.  
   Como $\sqrt{1 / 1,10} \approx 0,95346$, temos que mesmo com pneu novo ($grip = 0,85$), $\text{fator} = 0,9535$.
3. Como a guarda aplicava $v_{\text{tgt}} = \min(v_{\text{tgt, hist}}, v_{\text{cap}})$, o teto só começava a atuar quando:  
   $\text{fator} < 0,93 \iff \sqrt{\frac{grip}{0,85}} \cdot 0,9535 < 0,93 \iff grip < 0,8087$.
4. Como o pneu começa em 0,842 e só atinge 0,807 na última volta (Volta 5), o mecanismo foi **no-op em mais de 80% da corrida**. E na Volta 5, o corte efetivo de velocidade foi de apenas **0,14%** (~0,1 km/h), insuficiente para conter saídas de pista de 24 cm.

---

## 5. Veredito e Encerramento

- **Veredito:** **REPROVADO (FAIL)** em todos os gates formais.
- **Ação:** O ciclo `PROF-GRIP-1` é formalmente encerrado e arquivado nos ledgers.
- **Produção:** `--prof-grip` permanece desativado por padrão (default OFF bit-idêntico mantido).
