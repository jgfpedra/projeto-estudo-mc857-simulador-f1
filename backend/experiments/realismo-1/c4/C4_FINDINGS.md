# REALISMO-1 C4 — C4_GEOMETRY_CHECK

**Veredito:** `PARE`

**Motivo:** frame RMS 17.792229 m > 5.0 m

## Pré-validação

- Teste sintético C4: 7 passed.
- Regressões obrigatórias: 45 passed, 2 skipped.
- Pickles locais foram abertos diretamente por `pickle.load`, sem FastF1/rede.

## Voltas filtradas até o PARE

| Ano | Válidas | Lap 1 | Box | Chuva | Status | Posição |
|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 944 | 18 | 88 | 0 | 206 | 0 |
| 2023 | 986 | 17 | 103 | 0 | 0 | 0 |
| 2024 | 269 | 18 | 67 | 759 | 20 | 0 |

## Registro de frame

Ano processado: 2022; método: `procrustes_rigid`; direct RMS: `318.252703 m`; RMS Procrustes: `17.792229 m`; shift: `1872`; det(R): `1.000000000000`.

## PARE

O RMS excedeu o limite congelado de 5,0 m. A regra exige interrupção imediata, sem projeção, bins, tabela κ/raio ou decisão GEOMETRIA/FALLBACK.

Nenhum `interlagos_v3.json` foi criado.

## Decisão e Encerramento do Dono (2026-11-03)

1. **Homologação do PARE:**
   - O PARE duro por alinhamento de frame ($17,79\text{ m} > 5,0\text{ m}$) foi formalmente aceito e homologado pelo Dono.
   - Causa raiz: `interlagos_v2.json` possui comprimento de $4.160,4\text{ m}$ (interpolação spline de 15 vértices conceituais), enquanto a linha de telemetria real de corrida possui comprimento de $\approx 4.309\text{ m}$. A discrepância de escala intrínseca de $\approx 3,5\%$ impede qualquer registro rígido isométrico com $\text{RMS} \le 5,0\text{ m}$.
2. **Rejeição do Ramo GEOMETRIA:**
   - A criação de `interlagos_v3.json` e a alteração da geometria congelada de Interlagos estão definitivamente **rejeitadas e descartadas**.
   - O simulador preserva estritamente `interlagos_v2.json` sem modificações.
3. **Adoção do Ramo FALLBACK (A5):**
   - Conforme previsto pelo `PLANO_REALISMO_BOTS_1.md`, o programa adota o ramo FALLBACK da Junção.
   - O Ciclo C5 de simulação com v3 (7 corridas) fica cancelado por inexistência de v3.
   - Relatório de A5: O governor não atua nas saídas da Junção ($v_{plan}$ mínimo de $41,2\text{ km/h}$ com margem 1,15 só frearia acima de $47,4\text{ km/h}$, enquanto a velocidade mediana de saída é de $36,8\text{ km/h}$; $25$ das $41$ saídas da Junção são derrapagem lateral / oversteer, e não excesso de velocidade longitudinal).
4. **Próximo Passo Autorizado:**
   - Ciclo C4 formalmente encerrado.
   - Autorizada a abertura direta do **Ciclo C6 (P5 — Trenzinho: offset lateral por slot `--lat-offset-slots`, Tasks 13–14)**.
