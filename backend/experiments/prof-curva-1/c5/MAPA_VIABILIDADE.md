# PROF-CURVA-1 Task 5 — Mapa de viabilidade do teto local

**Data:** 2026-11-06 · **Método:** OFFLINE (zero corridas, zero rede) · **Script:**
`scripts/prof_curva_viabilidade.py` (commitado em `e5853aa` ANTES da execução) ·
**Saída canônica:** `c5/MAPA_VIABILIDADE.json` (determinístico, `cmp=0` em duas
execuções) · **Estado:** PARE para decisão do Dono.

## Método

Compara, nas duas pistas do estágio 0, o perfil `v_plan` baseline do professor
(`VelocityProfile` histórico) contra o perfil com teto
(`build_capped_velocity_profile`), com os parâmetros EXATOS do wiring
`--prof-curva` (grip 0,788, sf 0,80, ds 4 m, suavização 20 m) e a fronteira
default do wiring (`physics_frontier_current.json`, pares efetivos sem
QUEBRA: R 10→4, 16→6, 20→8, 25→10, 40→13 m/s; R>40 sem teto). Sobre o mapa
são sobrepostos os 308 eventos de saída observados no estágio 0
(`c0/{INT,MON}_N0..4_metrics.json`): o evento é "bind" quando o `v_plan`
capped em `s_onset` fica abaixo da velocidade de aproximação observada
(`v_1s_mps`) — ou seja, o mecanismo teria freado aquele carro antes da saída.

## Interlagos (sha `164876196eb12174`, 4160,4 m)

| grandezas | valor |
|---|---:|
| integral baseline (piso da volta) | 96,202 s |
| integral com teto | **131,041 s** |
| Δ (custo do teto) | **+34,839 s** |
| Teto da Guarda de Ritmo (prereg Task 2) | 123,05 s |
| **Guarda estourada no PISO?** | **SIM** (131,04 > 123,05) |

O teto engaja em **3.100 m dos 4.160 m da volta (74%)** em 3 segmentos:
264 m cruzando a linha (segmento circular; `s_lo/s_hi` no JSON são min/max,
não trajetória), 1.544 m (s 192–1732; R_min 22,9 m → cap 9,16 m/s) e
1.292 m (s 1852–3140; R_min 7,1 m → cap 3,38 m/s).

| crônica | bind | v_obs máx | cap em s_onset | R local |
|---|---|---:|---|---|
| C01 Descida do Lago | **0/22** | 17,61 m/s | 18,07–19,45 m/s | 107,5–140,2 m |
| C06 Bico de Pato | **4/20** | 13,95 m/s | 12,31–14,20 m/s | 36,6–57,9 m |
| C07 Mergulho | 20/20 | 13,01 m/s | 8,18–8,79 m/s | 20,4–22,0 m |
| C08 Junção | 20/20 | 10,14 m/s | 4,79–5,98 m/s | 12,4–15,9 m |
| Reta | 0/20 | 10,38 m/s | 35,35–36,23 m/s | 947–1753 m |

## Monaco (sha `67ca11dc211c8c78`, 3335,2 m)

Integral baseline 114,946 s → com teto **175,719 s** (**Δ +60,773 s**). O teto
engaja em **2.971 m dos 3.335 m (89%)**, com cap mínimo de 3,16–3,57 m/s
(rastejamento a ~11–13 km/h). Eventos: 206; bind 121. Por região: C03 15/15,
C05 15/15, C07 15/15, C12 20/21, C11 27/45, C04 15/30, C06 14/15, Reta 0/50.
Guarda Monaco report-only (sem referência Task 2): análogo +15% sobre a
mediana OFF observada (213,25 s → 245,24 s) não estoura no piso — mas o piso
só fica abaixo dele PORQUE a mediana OFF carrega 57% de tempo fora de pista;
a perda de ritmo limpo é de +53%.

## Leitura — três achados

1. **A Guarda de Ritmo estoura no PISO.** A volta corrida ON nunca pode ser
   mais rápida que a integral do plano (131,04 s) e o teto da guarda é
   123,05 s (107,0 s × 1,15, pinado no REF). Margem **−7,99 s mesmo no piso
   teórico**. Pelo §4 do prereg, isso é **PARE automático**: não se amplia o
   teto nem se promove o mecanismo.
2. **O Gate Primário é estruturalmente inalcançável.** Em C01 o teto nunca
   fica abaixo da velocidade observada (0/22; R 107–140 m ⇒ a_lat ≈ 2,2–2,9
   m/s² contra μg ≈ 7,7 m/s²): a saída crônica de C01 **não é pacing, é
   comportamental** — a premissa do programa (v_plan acima do raio viável)
   é falsificada para C01 e marginal para C06 (4/20; o cliff R=40→13 m/s da
   fronteira é que gera o bind parcial). Zero saídas em C01/C06 não é
   entregável por este mecanismo.
3. **A fronteira É o mecanismo inteiro — e nenhum dos dois critérios medidos
   serve.** LIMPO+MARGINAL (R 40→13 m/s) engaja 74–89% da volta e rasteja;
   o critério v2 "círculo estável" (permissivo: R 20 m → 22 m/s) não engajaria
   em **nenhum** evento (v_obs ≤ 13–14 m/s em todas as crônicas). Nenhum
   critério medido separa "quina que mata" de "curva normal" — a classe
   intermediária necessária não existe em nenhum dos instrumentos.

## Veredito

**PARE automático (§4 do PREREG_PROF_CURVA_1.md).** O mecanismo do teto local
de curvatura, como preregistrado e implementado (`--prof-curva`, default OFF,
preservado), é **inviável**: falha a Guarda no piso teórico e falha o Gate
Primário por estrutura. **ZERO corrida ON foi executada** — o orçamento de 10
corridas solo de 600 s está preservado. O código Task 3 permanece no repositório
como artefato research, default OFF, bit-idêntico.

**Encaminhamento já preregistrado** (§4 do prereg original): o próximo ciclo
autorizado deve avaliar **racing line suavizada, com curva geométrica de 18 m
na Junção**, em ciclo próprio — abertura, prereg e Freeze pelo Dono.

## Decisão pendente do Dono

1. Abrir o ciclo RACING-LINE-1 (racing line suavizada, 18 m na Junção);
2. ou re-escopar / arquivar a linha PROF-CURVA-1 (ex.: atacar C01 como
   defeito comportamental em outro programa).
