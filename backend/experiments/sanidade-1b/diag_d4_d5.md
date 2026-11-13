# SANIDADE-1b — Diagnóstico D4/D5 (READ-ONLY; probes commitados antes do uso)

> Fonte: CSVs commitados do SANIDADE-0 (gates s70-73, bundle ON) + F4v15
> (fricção 0,05 de referência). slat = obs4 × hw (6,00) — D0 patrimônio.
> Probe: scripts/sanidade1b_diag.py (commitado antes de cada uso).
> Legitimidade: antecede o prereg e informa os tetos do M3-v2.

## D4 — decomposição do custo do M3 v1 (pergunta: fricção ou esterço?)

| corrida | fora% | rol | excursões | breaker eps (car·s) | exc pós-breaker | exposição preventivo (car·s) | exc pós-exposição | shove ≤1s | sem gatilho |
|---|---|---|---|---|---|---|---|---|---|
| G1 v0 s70 (fric+brk, SEM prev) | 25,7 | 149 | 160 | 6 (6,2) | 3 | 595,6 (n/a — v0 não tem prev) | 54 | 0 | 103 |
| G3 v0 s72 (fric+brk, SEM prev) | 25,6 | 145 | 166 | 11 (17,6) | 5 | 596,0 (n/a) | 39 | 0 | 122 |
| G2 comp s71 (M3 completo) | 30,0 | 153 | 191 | 0 (0,0) | 0 | 193,6 | 28 | 0 | 163 |
| G4 comp s73 (M3 completo) | 30,3 | 165 | 202 | 3 (8,8) | 0 | 213,2 | 36 | 0 | 166 |
| REF v0 s0 (fric 0,05, SEM M3) | 22,1 | 136 | 180 | — | — | 1255,2 (n/a) | 90 | 1 | 89 |
| REF comp s0 (fric 0,05, SEM M3) | 25,2 | 140 | 219 | — | — | 272,0 | 21 | 0 | 198 |

**Leitura D4:**
1. **FRICÇÃO INOCENTE**: shove (excursão com contato ≤1 s antes) ≈ 0 em TODOS
   os braços — gates (0,01) e refs (0,05) idênticos. A hipótese "o empurrão
   com fricção baixa lança carros pra fora" NÃO se sustenta nos dados.
2. **BREAKER marginal**: 0-11 episódios por corrida, 0-17,6 car·s; excursões
   pós-breaker 0-5. Custo de pace pequeno (o lift é raro e curto).
3. **PREVENTIVO é o custo dominante**: o braço comp passa ~194-213 car·s com
   parceiro lateral no corredor 2,5 m/10 m; a taxa de excursão DURANTE
   janela de exposição DOBRA com o preventivo ativo (G2 28/193,6 = 0,144/s;
   G4 36/213,2 = 0,169/s vs REF comp 21/272,0 = 0,077/s) — o offset +0,25 rad
   empurra carros para fora nas janelas. NOTA: a exposição em si CAIU com M3
   (272→194/213 car·s — o preventivo separa pares de verdade); o problema é o
   esterço crônico ENQUANTO o par está junto.
4. Os Δfora/Δrol do braço comp são dominados pelo M2 (predição da review:
   +6,6pp de fora — vide prereg), com contribuição modesta do preventivo
   (+7-15 excursões/janela ≈ +0,4-0,9pp).

## D5 — anatomia do deadlock s72 (GAS×PIA, 10,2 s @t=13,2-23,2)

- **Par**: GAS (trás, Δs +2,9..+4,9) × PIA (frente). Ambos REENTRANDO de
  excursões da largada (slat de −5,6/−7,5 convergindo ao centro a 2,6-6 m/s).
- **PIA preso pelo M2**: authority=rejoin_gap a janela inteira — o gap-check
  do perceptive (X=20 auto no bundle) segura PIA em crawl 4 m/s na borda.
- **GAS sobre o breaker**: authority=anti_glue por 60 ticks (6,0 s) — o
  breaker ENGAJOU (GAS é o de trás; cede com lift+offset). O esterço gravado
  (~−0,3-−0,4) confirma a ação, mas a v=3 m/s a separação lateral é lenta e
  AMBOS convergem ao centro em paralelo: Δlat oscila 0,99-1,93 sem abrir >3.
- **Diagnóstico**: o deadlock é ARTEFATO DA INTERAÇÃO M2×M3 no bundle —
  dois carros reentrando em paralelo, um seguro pelo gap-hold do M2 e o
  outro sob o breaker do M3; a métrica de colados (|Δlat|<2 ∧ Δs<5,5)
  conta reentradas paralelas como "coladas". O breaker v1 não tem
  competência para este regime (o parceiro na grama/borda + velocidade de
  crawl tornam o offset ineficaz).
- **Implicação para o M3-v2**: nos gates v2 o M2 está OFF (isolamento) — o
  gap-hold não existirá; mas o v2 precisa de defesa: REVERT quando o alvo
  está off-track (não perseguir separação contra quem está na grama) e
  competência por velocidade (abaixo de v de crawl o breaker abre mão e
  registra — a separação fica por conta do domínio do rejoin).

## Tetos do M3-v2 informados por D4/D5 (entram no prereg ANTES do código)
1. **Preventivo** (o custo dominante): duração máx por episódio contíguo
   1,0 s (depois cooldown até separar ≥3 m ou 2 s); máx 10 episódios por
   par por corrida; só com velocidade relativa |Δv| < 8 m/s; REVERT se o
   próprio carro OU o parceiro ficar off-track.
2. **Breaker**: teto de duração 4 s por episódio (desiste e registra — não
   persegue separação eterna a crawl); competência por velocidade: lift
   total + 0,4 rad só abaixo de 25 m/s; acima, ação suave (th ≤ 0,5 +
   0,15 rad); REVERT se o alvo sai da pista; máx 8 episódios por par por
   corrida.
3. **Fricção**: mantida (inocente pelos dados; parte do pin do dono).

Output integral do probe: probe_d4_d5_output.txt (verbatim, ao lado).
