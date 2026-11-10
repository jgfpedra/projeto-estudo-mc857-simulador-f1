# Relatório de Referência Solo — Professor em Interlagos (Task 2)

- **Instrumento:** `prof_curva_audit_v1`
- **Pista:** `interlagos` (SHA-256: `c4617650983df9b1...`)
- **CSV:** `experiments/prof-curva-1/REF_INTERLAGOS_600S.csv` (SHA-256: `c00391ab21033dae1a03db2cd7f7fd6983baa47d67b0828bec503d93778e9b3a`)
- **Amostras:** 3000 ticks (5 Hz, 600 s)
- **Voltas Completadas:** 4

## 1. Saídas de Pista e Tempo Fora

- **Amostras fora de pista:** 737 de 3000 (24.6%)
- **Número total de excursões:** 20
- **Duração mediana de excursão:** 7.1 s
- **Deslocamento lateral máximo:** |lat| = 39.68 m

## 2. Diagnóstico das Quatro Curvas Crônicas de Interlagos

| Setor / Curva | Nome | Saídas | Taxa (saídas/volta) | Diagnóstico |
|---|---|---|---|---|
| `C01` | Descida do Lago (T4/T5) | 4 | 1.00 | CRÔNICA (100% das voltas) |
| `C06` | Bico de Pato (T10) | 4 | 1.00 | CRÔNICA (100% das voltas) |
| `C07` | Mergulho (T11) | 4 | 1.00 | CRÔNICA (100% das voltas) |
| `C08` | Junção (T12) | 4 | 1.00 | CRÔNICA (100% das voltas) |
| `Reta` | Reta / Loop Grama (pós-Junção) | 4 | 1.00 | CRÔNICA (100% das voltas) |

Demais curvas de Interlagos (C02 a C05, C09 a C12): **0 saídas**.

## 3. Tempos de Volta e Guarda de Ritmo (Decisão 3=b)

- **Tempos individuais por volta:** [138.7, 130.5, 127.5, 129.8] s
- **Melhor volta:** 127.5 s
- **Mediana (todas as voltas):** 130.15 s
- **Mediana (excluindo volta 1 / largada):** 129.8 s
- **Baseline histórica limpa:** 107.0 s
- **Teto da Guarda de Ritmo (+15%):** 123.05 s
- **Degradação na referência sem patch:** +21.31% (inflada por 26 s/volta de perambulação na grama)

## 4. Conclusão da Baseline

A medição solo sem patch de teto confirma integralmente a anatomia prevista:
1. As quatro saídas crônicas ocorrem em 100% das voltas (C01, C06, C07, C08);
2. A Junção (C08) e o looping consequente na grama (Reta) somam ~26 segundos de tempo perdido fora de pista por volta;
3. O Gate Primário da Task 4 exigirá **ZERO** saídas em C01, C06, C07 e C08, e zero saídas novas nas demais curvas;
4. A Guarda de Ritmo na Task 4 exigirá que a velocidade ajustada gere mediana de volta `<= 123.05 s` (<= 15% sobre a baseline limpa histórica de 107 s).
