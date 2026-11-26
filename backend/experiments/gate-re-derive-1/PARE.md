# PARE — GATE-RE-DERIVE-1

**Data:** 2026-10-23 · **branch:** `feat/sanidade-produto` · **decisão:** **Ramo 2 — comprimento report-only**.

## Registro e decisão

O prereg efetivo é o v0 verbatim (`backend/PREREG_GATE_RE_DERIVE_1_v0.md`) mais o adendo vinculante congelado no commit `194a709` (`backend/PREREG_GATE_RE_DERIVE_1.md`). As erratas E1/E2 foram commitadas antes em `b28e100`; a preservação literal do v0, em `e58e8c4`. Nenhum parâmetro ou gate foi alterado após o congelamento.

O inventário histórico contém dez resultados reais v4. Todos os dez streams históricos e os seis streams alternativos permitidos foram lidos localmente, verificados contra os hashes pré-registrados e passados pelo filtro v4. **Todos os 16 falharam o gate temporal de velocidade máxima de 120 m/s**. Portanto, zero pistas históricas ficaram estruturalmente elegíveis para o LOO e nenhum fold pôde ser formado. Não há holdout independente por pista: os dez deltas históricos eram públicos e os seis alternativos são outros pilotos em quatro dessas pistas. A árvore do S6 leva a Ramo 2; não se propõe um limiar global e o comprimento permanece report-only.

## Execução offline

Execução reproduzível por `backend/scripts/audit_gate_re_derive_1.py`; dados resumidos em `backend/experiments/gate-re-derive-1/audit.json`. O script lê apenas os streams hash-pinned e `backend/f1db.db`; não tem caminho de fallback para API. A saída foi gerada duas vezes bit a bit, SHA-256 `67353f413e499b1dacb19d5933266516248d893ef5f6ae112ddfd22132e04091`.

| Grupo | Streams tentados | Extrações v4 | Passaram todos os gates | Deltas novos reportados |
|---|---:|---:|---:|---:|
| Dez históricos | 10 | 10 | 0 | Não aplicável; resultados já públicos |
| Seis alternativos | 6 | 6 | 0 | 0 |

Não houve chamada de rede, escrita em path frozen, alteração de pool/cache FastF1 ou simulação de treino/corrida. A execução da suíte de regressão abaixo foi a única atividade de testes/simulação.

## Camada estrutural

A conversão de `x/y` de decímetros para metros (`×0,1`) foi verificada contra o v4 e a documentação do FONTE-2. `z` não é usado. Os 16 streams tinham campos `x/y/date` completos, coordenadas finitas e datas parseáveis, únicas e compatíveis entre ordenação lexical do v4 e UTC. O resultado de cada stream segue; `min/max segmento` inclui o fechamento. A faixa bbox/comp. oficial exigida é `[0,05;0,50]`; espaçamento e fechamento exigem `[5;15] m`; topologia reprova se a distância mínima entre segmentos não adjacentes for `≤0,1 m`.

| Pista | Piloto | Velocidade máxima (m/s) | bbox / oficial | wp | min–max segmento (m) | distância topológica mínima (m) | Resultado estrutural |
|---|---:|---:|---:|---:|---:|---:|---|
| Bahrain | 11 | 626,588 | 0,2647 | 530 | 8,083–10,006 | 8,083 | Reprovada: velocidade |
| Hungaroring | 81 | 1689,704 | 0,3667 | 432 | 9,760–10,010 | 9,760 | Reprovada: velocidade |
| LasVegas | 63 | 313,104 | 0,3659 | 614 | 6,147–10,011 | 6,147 | Reprovada: velocidade |
| Mexico | 55 | 1014,436 | 0,4125 | 423 | 9,493–10,023 | 9,493 | Reprovada: velocidade |
| Miami | 1 | 699,803 | 0,2974 | 533 | 8,657–10,011 | 8,657 | Reprovada: velocidade |
| Montreal | 1 | 252,452 | 0,4594 | 430 | 6,584–10,006 | 6,584 | Reprovada: velocidade |
| Monza | 44 | 1050,771 | 0,4325 | 575 | 8,984–10,014 | 8,984 | Reprovada: velocidade |
| Silverstone | 44 | 687,981 | 0,3389 | 581 | 8,726–10,009 | 8,726 | Reprovada: velocidade |
| Suzuka | 1 | 2355,559 | 0,3824 | 576 | 9,713–10,010 | 0,000 | Reprovada: velocidade e auto-interseção |
| Zandvoort | 4 | 1269,308 | 0,3000 | 417 | 7,741–10,023 | 7,741 | Reprovada: velocidade |
| Bahrain | 1 | 2061,922 | 0,2648 | 530 | 8,039–10,008 | 8,039 | Reprovada: velocidade |
| Miami | 4 | 640,613 | 0,2972 | 533 | 8,725–10,011 | 8,725 | Reprovada: velocidade |
| Suzuka | 11 | 1665,190 | 0,3822 | 576 | 9,852–10,006 | 0,000 | Reprovada: velocidade e auto-interseção |
| Suzuka | 55 | 1241,415 | 0,3824 | 576 | 9,799–10,012 | 0,000 | Reprovada: velocidade e auto-interseção |
| Zandvoort | 1 | 2422,140 | 0,2994 | 417 | 8,167–10,019 | 8,167 | Reprovada: velocidade |
| Zandvoort | 16 | 1969,923 | 0,3000 | 417 | 7,791–10,023 | 7,791 | Reprovada: velocidade |

Em todas as linhas, a plausibilidade de escala, número mínimo de waypoints, espaçamento e fechamento passaram. A falha de velocidade, que ocorreu nos 16 streams, é decisiva; Suzuka também falhou topologia nas três linhas avaliadas. As velocidades máximas variaram de 252,452 a 2355,559 m/s no inventário histórico e de 640,613 a 2422,140 m/s nos alternativos. O achado mostra que o limite temporal congelado não é utilizável nesses streams tal como estão; ele não demonstra, por si só, defeito físico da geometria.

Os comprimentos históricos reextraídos concordaram com os valores registrados dentro do arredondamento publicado: diferença absoluta máxima de 0,394 m (Monza, cujo valor histórico foi publicado ao metro); para as outras nove pistas, diferença máxima de 0,025 m. Esses valores reproduzem o histórico, mas não foram usados para contornar a reprovação estrutural.

## Calibração, holdout e escopo

- **LOO:** zero pistas elegíveis depois da camada estrutural; zero folds calculáveis; `all_folds_valid = false`. Nenhum limiar foi ajustado ou escolhido.
- **Holdout:** zero. Não houve circuito inédito entre os streams locais disponíveis; não se buscou stream pela rede.
- **Alternativos:** 6/6 extraídos em ordem pré-registrada; 0/6 estruturalmente aprovados; nenhum delta alternativo calculado/reportado, conforme regra de elegibilidade.
- **Promoções e adoção:** nenhuma. LasVegas continua no estado anterior. Suzuka permanece sem flip de default. Pools, loader, checkpoints, geometria frozen e dados FastF1 ficaram intocados.
- **Limites:** resultado de diagnóstico exploratório sobre estes streams. Não prova generalização para outras pistas, correspondência à linha central, qualidade de bordas/largura, segurança do piloto, desempenho de modelo ou adequação para treino/avaliação.

## Suíte de regressão

Comparação serial com o baseline registrado em `1a228b8`: baseline `20F/345P/3S`; run final `20F/349P/3S` (200,38 s). As mesmas 20 falhas conhecidas permaneceram; quatro testes adicionais passam. Rótulo obrigatório: **“349 testes, com 20 falhas bit a bit estáveis ('regressão estável conhecida') e 3 skips”**.

Falhas atuais, iguais às registradas no baseline/dossiê anterior:

1. `test_kappa_sign::TestKappaSignProcedural::test_local_sign_correct`
2. `test_kappa_sign::TestKappaSignProcedural::test_no_spurious_flip`
3. `test_mixed_race::TestHoldAt::test_hold_car_stays_at_s`
4. `test_procedural_track::TestDeterminism::test_same_seed_same_track`
5. `test_procedural_track::TestDeterminism::test_different_seed_different_track`
6. `test_procedural_track::TestGeometry::test_closure`
7. `test_procedural_track::TestGeometry::test_spacing_le_4m`
8. `test_procedural_track::TestGeometry::test_length_range`
9. `test_procedural_track::TestGeometry::test_kappa_in_range`
10. `test_procedural_track::TestWidth::test_custom_width`
11. `test_procedural_track::TestWidth::test_width_range`
12. `test_procedural_track::TestEnvIntegration::test_env_with_procedural`
13. `test_procedural_track::TestEnvIntegration::test_start_zones_auto`
14. `test_procedural_track::TestEnvIntegration::test_race_layer_compatible`
15. `test_procedural_track::TestFeatures::test_hairpin_produces_tight_corner`
16. `test_procedural_track::TestFeatures::test_esse_track_variety`
17. `test_race_layer::TestSplineGeometry::test_subdivision_preserves_length_exactly`
18. `test_race_neural_60d::TestDeployProfiles::test_profiles_exist_default_race_obs_correct`
19. `test_rl_v2::test_reference_controller_completes_lap`
20. `test_rl_v2::test_skidpad_radius_close_to_bicycle`

O primeiro run desta tarefa detectou, além dessas falhas, um `test_state_files_doc_integrity` por falta do parêntese final na linha histórica PISTA-IDENT de `backend/PROJECT_STATE.md`. A mesma linha passava no baseline `1a228b8`; corrigi apenas o fechamento tipográfico no estado vivo e o teste direcionado passou. O run completo final voltou a 20 falhas, 349 passes e 3 skips.
