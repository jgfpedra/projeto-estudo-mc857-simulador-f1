
---

## 8. Erratas R5-a e R5-b (ERRATA-SAIDAS-1-review, 2026-10-22; consolidadas no PROF-MONACO-1 P0)

Reconciliação prescrita pela review executada pelo probe commitado
`backend/scripts/prof_monaco_p0.py` (output em
`backend/experiments/prof-monaco-1/p0_reconcile_output.txt`), recomputando do
`eventos_saidas_detalhados.csv` BRUTO:

- **R5-a (C07 IQR-B)**: original 24,2 vs republicado 23,6 → **CANÔNICO =
  23,6 km/h** (raw = 23,6327, n=42; o número republicado confirma; o
  "original 24,2" era display-slip do PARE — cenário iii da review reforçado).
  C07-A raw = 21,9853 → 22,0 exato (compatível com o republicado).
  NÃO-gating: qualquer valor em 22-24 sustenta "heterogêneo = insumo do
  professor"; o lead carrega o número canônico 23,6.
- **R5-b (Reta-B solo)**: original 16/20 = 80% vs errata 11/20 = 55% →
  **CANÔNICO = 11/20 = 55,0%** (raw confere exatamente; o "original 16/20"
  era display-slip). A ratificação da tabela republicada SEGUE em ambos.
- **Proveniência R1**: `git diff 36cdff3 ce895cd -- backend/experiments/saidas-1/`
  = vazio (nenhuma célula de dados tocada) — ratificação ÍNTEGRA.
- **NIT-2**: a re-execução do veredito regenera as 6 tabelas BYTE-IDÊNTICAS.
- **NIT-3**: C10 = 'Senna S (T1/T2)' s∈[2748,3; 2852,3] κmax 0,0311 no
  catálogo do código — rotulagem CONFIRMADA por geometria (primeiro complexo
  pós-SF); ressalva de margem ±30 m documentada (96 de 114 m da zona F0).
