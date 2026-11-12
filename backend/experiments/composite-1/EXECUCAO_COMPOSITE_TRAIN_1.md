# EXECUCAO_COMPOSITE_TRAIN_1 — treino formal do modelo residual Composite

Data: 2026-10-27 (America/Sao_Paulo).
Branch: `feat/sanidade-produto`.
Freeze de referência (Etapa A2): `b7096dbe39c2385dbf41b88e2cddf2fc6a402098`.
Commit de proveniência: `c186ef2`.

---

## 1. Contexto

Instrumento congelado em `b7096db` (SHA `2f084e0e…`): prereg 195 linhas, script 731 linhas, testes 263 linhas, collect-only 460 testes. Orçamento desta etapa: exatamente 2 treinos (Run 1 candidato + Run 2 réplica obrigatória), ZERO corrida, ZERO promoção, ZERO edição de código.

---

## 2. Fase B-0 — Gate g0 (suíte completa)

Log: `experiments/composite-1/train-1/0_full_suite_train_1.log` (SHA-256 `bf0517329d3ee61e3324653660441e021267fe087476fda3b33172b2f7b9e045`).

- **Coleta:** 460 testes (453 baseline + 7 focados de `test_train_composite_residual.py`).
- **Resultado:** Exit code 1 esperado; **20 failed, 437 passed, 3 skipped**, 105 warnings em 269.91s.
- **Fail-set:** As 20 canônicas exatas (nenhuma de `test_train_composite_residual`). ZERO falhas novas.

---

## 3. Fase B-1 — Run 1 candidato (seed 42)

Log: `experiments/composite-1/train-1/1_run_1_candidato.log` (SHA-256 `35f34040a3b9281a429e5b337aaa5e9b8f254d63b76b2f816edc0a6f5bd33b92`).
Métricas: `experiments/composite-1/train-1/composite_residual_candidato_1_metrics.json` (SHA-256 `3f2ecc40c0661eccb8f5b348bb34eb08a7f2a0b3a3a5bda8ee7aadfe3ada2bbb`).

### 3.1 Contagens
- **Train:** 48.000 total (case_A = 24.000, case_B = 24.000).
- **Validation:** 6.000 total (case_A = 3.000, case_B = 3.000).

### 3.2 Métricas de Validação Offline (sem gate, espaço residual)

| Métrica | Valor | Gate | Veredicto |
|---|---|---|:---:|
| `huber_cand` | 0.20700 | ≤ 0.80 × `huber_null` = 0.46914 | **PASS** |
| `huber_null` | 0.58643 | — | — |
| `val_loss_improvement_ratio` | 0.35298 | — | — |
| `mae_r1` (MAE(r_cand, r_target)) | 0.47035 | < `mae_zeros` = 0.88732 | **PASS** |
| `mae_zeros` (MAE(0, r_target)) | 0.88732 | — | — |
| `mean_norm_r` (‖r_cand‖₂ média) | 1.42214 | ≤ 2.0 | **PASS** |
| `nan_inf_count` | 0 | == 0 | **PASS** |
| `best_epoch` | 41 | — | — |
| `best_val_loss` | 0.20700 | — | — |

**Os 4 gates O-1 passaram sem exceção.**

### 3.3 Hashes de Proveniência (calculados após exportação pelo instrumento)

| Artefato | SHA-256 |
|---|---|
| `.keras` (candidato) | `f237ac9e382a7c5f73b6c37dcbf9c0e0473bd49b8d259cb79e2d2408accb1b0d` |
| `.npz` (candidato) | `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` |
| Script (`train_composite_residual.py`) | `2f084e0e4ee832debc88fce7e733753f6e65e00336b41fb2b62d30ecb3ed06bf` |
| Git HEAD | `b7096dbe39c2385dbf41b88e2cddf2fc6a402098` |
| Corpus audit A (dataset) | `5d29d1808695528c7a8bfc8e03cb335d95d5fab35ef16076b708dd3fca6b215b` |
| Corpus audit B (dataset) | `2089d289c0f3b2adc01b0431c6af7bedb1a5522362101d4e9a39ab3ab3a593bc` |

---

## 4. Fase B-2 — Run 2 réplica obrigatória (seed 42)

Log: `experiments/composite-1/train-1/2_run_1_replica.log` (SHA-256 `f00a735fb14eecba2e6e4011f7e3959467ed98b0190ae434261284230a211865`).
Métricas: `experiments/composite-1/train-1/composite_residual_replica_1_metrics.json` (SHA-256 `ab232883cc8a253f71b06b616bddd710acd92233889b4dcc886d4b3d99480359`).

### 4.1 Métricas da Réplica

Todas as métricas numéricas são **IDÊNTICAS** ao Run 1:

| Métrica | Candidato | Réplica | Δ |
|---|---|---|:---:|
| `huber_cand` | 0.20699818432331085 | 0.20699818432331085 | **0.0** |
| `huber_null` | 0.5864295363426208 | 0.5864295363426208 | **0.0** |
| `mae_r1` | 0.4703496992588043 | 0.4703496992588043 | **0.0** |
| `mae_zeros` | 0.8873178958892822 | 0.8873178958892822 | **0.0** |
| `mean_norm_r` | 1.4221404790878296 | 1.4221404790878296 | **0.0** |
| `best_epoch` | 41 | 41 | **0** |

### 4.2 Hashes da Réplica

| Artefato | SHA-256 |
|---|---|
| `.keras` (réplica) | `e9e633a32aebecfee67188a439fe50d065d71c2e6ecebb918f868c57164b766e` |
| `.npz` (réplica) | `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` |

---

## 5. Fase B-3 — Comparador offline de réplica

Log: `experiments/composite-1/train-1/3_replica_comparacao.log` (SHA-256 `02a1c8bb52a6d80136a090fdc2b60998488c4808a166ab59bf8f2d9da934d0a6`).

### 5.1 Resultado do Comparador

```json
{
  "delta_val_loss": 0.0,
  "diffs_by_layer": {
    "res_d1_0": 0.0,
    "res_d1_1": 0.0,
    "res_d2_0": 0.0,
    "res_d2_1": 0.0,
    "res_out_0": 0.0,
    "res_out_1": 0.0
  },
  "max_diff_w": 0.0,
  "passes_gate": true
}
```

### 5.2 Disclosure de Replicação Perfeita Byte-a-Byte

Os dois arquivos `.npz` (candidato e réplica) têm SHA-256 **IDÊNTICOS**:
- Candidato: `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60`
- Réplica:   `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60`

Isso constitui replicação **PERFEITA byte-a-byte** dos pesos treinados. A divergência de ponto flutuante é rigorosamente zero em todas as 6 camadas (kernel e bias das 3 camadas densas). O arquivo `.keras` difere apenas em metadados de serialização internos do Keras (timestamps), mas o conteúdo numérico — exportado para NPZ via `export_residual_npz` — é bit-a-bit idêntico.

Os gates duros ratificados ($|\Delta \text{val\_loss}| < 10^{-4}$ e $\max |\Delta W| < 10^{-5}$) são satisfeitos com folga máxima (ambos = 0.0).

---

## 6. Fase B-4 — Proveniência

Commit de proveniência: `c186ef2` ("Provenance COMPOSITE-TRAIN-1 treino formal e replicacao"), contendo os 10 artefatos:

| # | Arquivo | SHA-256 |
|---|---|---|
| 1 | `0_full_suite_train_1.log` | `bf051732…` |
| 2 | `1_run_1_candidato.log` | `35f34040…` |
| 3 | `2_run_1_replica.log` | `f00a735f…` |
| 4 | `3_replica_comparacao.log` | `02a1c8bb…` |
| 5 | `composite_residual_candidato_1.keras` | `f237ac9e…` |
| 6 | `composite_residual_candidato_1_weights.npz` | `6210fff6…` |
| 7 | `composite_residual_candidato_1_metrics.json` | `3f2ecc40…` |
| 8 | `composite_residual_replica_1.keras` | `e9e633a3…` |
| 9 | `composite_residual_replica_1_weights.npz` | `6210fff6…` |
| 10 | `composite_residual_replica_1_metrics.json` | `ab232883…` |

---

## 7. Interpretação e Recomendações

### 7.1 Qualidade do Modelo Candidato

O modelo residual candidato atingiu:
- **Redução de 64,7% na perda Huber** em relação à baseline nula ($0.20700 / 0.58643 = 0.353$), superando com larga margem o critério mínimo de 20% de redução ($\le 0.80 \times \text{null}$).
- **Redução de 47,0% no MAE residual** ($0.47035$ vs $0.88732$ da baseline nula), indicando que o resíduo aprendeu a aproximar significativamente os alvos $r_{\text{target}} = \text{atanh}(\text{clip}(a_{\text{teacher}}, 0.98)) - m_{\text{solo}}$.
- **Norma média do resíduo predito de 1.422** (dentro do limite de segurança de 2.0), sem evidência de saturação descontrolada.
- **Zero valores NaN/Inf** em todas as ativações e pesos.

### 7.2 Replicação Bit-a-Bit

A replicação byte-a-byte dos pesos NPZ (delta = 0.0 em todas as camadas) é a prova mais forte de determinismo possível. O flag `tf.config.experimental.enable_op_determinism()` combinado com as sementes fixas (Python, NumPy, TensorFlow) foi suficiente para garantir reprodutibilidade perfeita nesta máquina CPU.

### 7.3 Próximos Passos Recomendados

1. **COMPOSITE-BASE-2:** Avaliar o candidato em corrida via `--residual-override` com métricas cinemáticas no espaço de ação (MAE com saturação tanh + gate dinâmico), conforme disclosure de transferência de métrica da Emenda O-1.
2. **Promoção:** Estritamente proibida nesta fase. A promoção do candidato a produção só pode ocorrer após avaliação em corrida e ratificação explícita do dono.

---
*Fim da Execução COMPOSITE-TRAIN-1 (Etapa B).*

---

## 8. Apêndice do dono — verificação independente (pré-closing, 2026-10-27)

Verificação executada pelo dono antes do closing, sobre os bytes commitados em `c186ef2` e o estado staged:

1. **Provenance exato:** commit `c186ef2` contém EXATAMENTE os 10 artefatos listados (4 logs + 2 keras + 2 npz + 2 metrics); todos os SHA-256 recomputados e idênticos à tabela §6; git HEAD no JSON dos dois runs = `b7096dbe…` (o treino rodou no freeze, ANTES do provenance — coerente).
2. **Fail-set canônico:** os 20 `FAILED` do g0 desta etapa são(EXATAMENTE) os mesmos do `0_full_suite_base_1.log` — diff sorted = vazio; footer `20 failed, 437 passed, 3 skipped` ✓.
3. **3ª leitura do comparador:** `compare_candidate_and_replica(...)` re-executado pelo dono sobre os bytes commitados → `delta_val_loss = 0.0`, `max_diff_w = 0.0`, `passes_gate = True`.
4. **Pesos dentro dos containers `.keras`:** os SHAs dos `.keras` divergem (`f237ac9e…` vs `e9e633a3…`, metadados/timestamps de serialização — esperado); o dono carregou AMBOS via `tf.keras.models.load_model` e comparou peso a peso: **max diff = 0.0**. Os pesos erguem a identidade também dentro do container, para além do npz e do comparador.
5. **Números dos gatilhos recalcados dos JSON:** razão real `huber_cand/huber_null = 0.20699818/0.58642954 = 0,35298` (redução −64,7%, margem enorme sobre o limiar 0,80); `mae_r1 < mae_zeros` (−47,0%); `mean_norm_r = 1,4221 ≤ 2,0`; `nan_inf_count = 0`; contagens 48.000/6.000 com quebra 24k/24k e 3k/3k exatas — tudo numérico-conforme nos DOIS JSONs.
6. **Identidade do candidato para o BASE-2:** o artefato de aplicação em pista é `composite_residual_candidato_1_weights.npz` SHA `6210fff65b19ad0e51c561e332ae30fe875b5a390c389520d6e2f23cefd17c60` (byte-idêntico à réplica). Este SHA vai citado no prereg do BASE-2.
7. **Disclosure honesto para o BASE-2:** o ganho −64,7% é OFFLINE no espaço residual (BC sem-gate, g=1 no alvo); o efeito em pista sob gate dinâmico g∈[0,1] é DESCONHECIDO e só o BASE-2 mede. Nenhum critério de corrida foi pré-declarado por serem dados ainda não observados — o dono ratificará leitura qualitativa PÓS-números.
8. **Ledgers:** +1 linha idêntica em cada um dos 3, uncommitted, aguardando este closing.

Veredicto do dono: **COMPOSITE-TRAIN-1 FECHADO (alínea a — tudo conforme, nenhuma PARE acionada).
O dono commita EXECUCAO + ledgers no closing e abre COMPOSITE-BASE-2 (candidato em pista via --residual-override; promoção segue proibida).**
