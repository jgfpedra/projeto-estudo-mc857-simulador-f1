# tracks_frozen_v1 — pistas da era-1 ARQUIVADAS (ADOÇÃO-H-2, 2026-10-20)

Pistas congeladas da era FastF1-telemetria, substituídas como canônicas pelos
mirrors F1DB (FASE H-1/H-2). **NUNCA deletar** — registros "era v1" dos
números históricos (B', 51-eps, teacher_benchmark).

| arquivo | sha256 (conteúdo) | destino | motivo do arquivamento |
|---|---|---|---|
| Monaco_v1.json | 07e7ef4dd6af4517 | → Monaco_v2.json (mirror 2021, sha 67ca11dc211c8c78) | ARTEFATO de spline: clearance 1,71 m (audit FASE G) / 1,63 m (H3 H-0); 56 pares <8 m; 45 riscos de hint; ABORTA no runner atual ("reta antes da SF = 0 m") |
| Spa_v1.json | f83365bf26d0b1b1 | → Spa_v2.json (mirror 2007-2026, sha 4b05f2c3bbc625fc) | TRUNCADA −37,9% (4.352 m vs oficial 7.004 m; R8: provável erro mi→m — HIPÓTESE ABERTA); professor-solo fora 45,4% vs 32% do mirror |

O loader `load_track_frozen` NÃO consulta este diretório (INTOCADO por
PARE): os v1s são artefatos históricos, carregáveis apenas por leitura
direta do JSON (Track.from_waypoints). Proveniência: FASE G (dsh), FASE H-0
(82b12c6), H-1 (e405298), ADOÇÃO-H-2 (prereg 8c14f9f).
