# PRÉ-REGISTO — FASE H-1: calibração do G4 em CONTROLES + congelamento condicional
# Commitado ANTES de qualquer execução. ZERO runs · ZERO pool (70-79 intactos) ·
# ZERO re-pin (v1s intocados; o loader permanece inalterado; TROCAR o canônico
# de monaco/spa = decisão do DONO, mesmo após freeze).
# Motivação: FASE-H-0-review R1-R5 (G4 FAIL = CALIBRAÇÃO, não geometria).

## 1. HIPÓTESE REGISTRADA (números do diagnóstico MARCADO da H-0 — motivação,
##    NUNCA dado de calibração)
O limiar κ≥0,02 (R≤50 m) do G4 sub-detecta curvas rápidas e NÃO mede
completude em pista rápida (não separa Spa COMPLETA de Spa_v1 TRUNCADA).
Diagnóstico pós-veredito da H-0: Monaco mirror 15→17 turns (κ≥0,02→0,01);
Spa mirror 5→23 (κ≥0,01) / ~19-21 (κ≈0,008); Spa_v1 truncada ~4-5 ≈ Spa
completa 5 (a κ≥0,02). Emenda ingênua não passa (R3 da review): κ* deve vir
de CONTROLES known-good, não dos alvos.

## 2. CONTAGENS OFICIAIS (fonte ÚNICA; ESCRITAS no prereg ANTES de qualquer
##    execução; banda de aceite = oficial ± 3, BORDAS INCLUSIVAS; pass com
##    margem 0 = flag "margem 0" no relatório)
Fonte: infoboxes "current Grand Prix Circuit" da Wikipédia EN —
formula1.com probeado PRIMEIRO e OMITIU o campo de turns nas race pages
(probe registrado 2026-10-20; fonte única recaída na Wikipedia). Data de
acesso: **2026-10-20**.

| pista | layout vigente | TURNS OFICIAIS | URL |
|---|---|---|---|
| Monaco | 2015–present (era do mirror: 2003-2019, 2021-2026) | **19** | en.wikipedia.org/wiki/Circuit_de_Monaco |
| Spa | 2007–present | **19** | en.wikipedia.org/wiki/Circuit_de_Spa-Francorchamps |
| Hungaroring | 2003–present | **14** | en.wikipedia.org/wiki/Hungaroring |
| Monza | 2000–present | **11** | en.wikipedia.org/wiki/Monza_Circuit |
| Zandvoort | 2020–present | **14** | en.wikipedia.org/wiki/Circuit_Zandvoort |
| Suzuka | 2003–present | **18** | en.wikipedia.org/wiki/Suzuka_Circuit |
| Interlagos | 5ª variação (desde 1999) | **15** | en.wikipedia.org/wiki/Interlagos_Circuit |

## 3. CONTROLES (declARADOS com justificativa; N = 5)
Todas as frozen EXCETO: **Monaco_v1** (artefato de spline documentado —
clearance 1,63 m), **Spa_v1** (truncada −37,9%) e **os dois alvos**
(Monaco-mirror, Spa-mirror). **Suzuka_v1 ENTRA** (crossover real =
geometria legítima; os pares próximos são a ponte/esses reais).
Interlagos contado **UMA VEZ** (v1/v2/sf729_v2 = geometria bit-idêntica;
usa-se a v2).
**CONTROLES (N=5): Hungaroring_v1, Monza_v1, Zandvoort_v1, Suzuka_v1,
interlagos_v2** — oficiais 14, 11, 14, 18, 15.

## 4. PROTOCOLO DE CALIBRAÇÃO (PINADO)
- Grade κ = {0,004; 0,005; …; 0,020} (17 valores, passo 0,001).
- Para cada κ: contar turns (picos de κ com separação mínima 30 m de arco —
  o MESMO detector da H-0, único parâmetro variando) em cada controle.
- **Regra de escolha de κ***: (i) maximizar o nº de controles in-band
  (|count − oficial| ≤ 3, bordas inclusivas); (ii) tiebreak: minimizar
  Σ|count(κ) − oficial| sobre os 5 controles; (iii) empate persistente
  (plateau) → midpoint do plateau.
- **κ* CONGELADO no prereg-result ANTES de olhar os alvos** (commit do CSV
  de calibração dos controles; depois, e só depois, os alvos rodam).
- **VALIDADE: ≥ N−1 = 4 dos 5 controles in-band com κ*** — critério exato.

## 5. REGRA ANTI-TAUTOLOGIA (explícita)
κ* é escolhido SÓ pelos controles; os números dos ALVOS (Monaco-mirror,
Spa-mirror) NÃO entram na escolha; o diagnóstico da H-0 entra como
MOTIVAÇÃO documentada (§1), nunca como dado de calibração.

## 6. ÁRVORE DE DECISÃO (ambos os ramos PINADOS antes dos dados)
- **RAMO A (κ* válido: ≥4/5 controles in-band)**: aplicar κ* aos alvos
  (banda ±3 sobre os oficiais 19/19 do §2).
  - PASS (ambos in-band) → **CONGELAR Monaco_mirror2021_v1.json e
    Spa_mirror_v1.json** (nomes INERTES ao loader) + **TESTE DE INÉRCIA**
    (load_track_frozen('monaco') → Monaco_v1; 'spa' → Spa_v1; mesmo com
    os mirrors no diretório) + suite delta declarado.
  - FAIL (qualquer alvo fora da banda) → **PARE honesto** (problema real
    do mirror); NADA congelado; diagnóstico por alvo.
- **RAMO B (nenhum κ* válido: <4/5)**: **G4 MORRE como gate** e vira
  descritor REPORT-ONLY (fingerprint de turns por κ no relatório);
  completude a cargo de G5 (comprimento) + G1/G2/G3; **mirrors ELEGÍVEIS
  de congelamento** (G1/G2/G3/G5 já PASS na H-0) com a crítica documentada
  no JSON de proveniência + o MESMO teste de inércia.

## 7. Orçamento e instrumento
- ZERO corridas; compute = builder/contador (segundos). Downloads: os 2
  SVGs dos alvos (probes já registrados na H-0).
- Suite delta declarado: **+2 testes** (t-inércia do loader — passa com ou
  sem mirrors: SE os arquivos mirror existem, ENTÃO 'monaco'/'spa'
  resolvem para os v1; t-métricas de gate dos artefatos — SÓ se congelados,
  recomputa G1/G3/G5 dos JSONs e confere) → **25F/303P/2S** se ambos
  congelados (ou 302P se o t-métricas ficar N/A-skipped).

## 8. PAREs permanentes
Corridas; pool; clima no runner; re-pin; edição em commits fechados;
errata não-aditiva; **TROCAR o canônico de monaco/spa (dono)**; olhar os
alvos antes de congelar κ*.
