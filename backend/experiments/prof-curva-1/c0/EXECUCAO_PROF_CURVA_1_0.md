# EXECUÇÃO PROF-CURVA-1 — estágio 0

Data: 2026-11-06
Modo: referência OFF, professor solo, sem `--prof-curva`
Escopo: 10 corridas de 600 s (`N=0..4` em Interlagos e Monaco) e 20 leituras do instrumento.

## Fronteira física v2

A grade foi executada duas vezes em processos separados, com 250 medições por leitura:

- velocidades: 4, 6, 8, 10, 13, 16, 18, 20, 22 e 25 m/s;
- raios: 4, 6, 8, 10, 13, 16, 20, 25, 30, 40, 50, 65 e 80 m;
- grips: 0,788 (`real`) e 0,842 (`soft`);
- saída canônica: `physics_frontier_v2_canonical.json`;
- SHA-256 das duas saídas: `fd8b9d2881f5e0f5741180b8d73945d603e1c5a9959cb56ec508f11ca202fa81`;
- `cmp`: **0**;
- `metrics_sha256`: `6425b5d9895ff4b57f9cb4a3f27ef18c31e9e43c1d19afae2642896fc46404f6`.

Na resolução declarada do instrumento, a fronteira de círculo estável foi:

| velocidade (m/s) | real (m) | soft (m) |
|---:|---:|---:|
| 4 | 4 | 4 |
| 6 | 4 | 4 |
| 8 | 4 | 4 |
| 10 | 4 | 4 |
| 13 | 4 | 4 |
| 16 | 4 | 4 |
| 18 | 6 | 6 |
| 20 | 6 | 6 |
| 22 | 6 | 6 |
| 25 | 8 | 8 |

O critério antigo (`LIMPO`) produziu uma fronteira muito mais esparsa: real 4 m/s → 16 m e 6 m/s → 40 m; soft 4 m/s → 16 m e 6 m/s → 30 m; demais pontos sem `LIMPO` na grade. A saída v2 é isolada em `experiments/` e não altera `model_train/physics_frontier.json`.

## Matriz OFF

Comando canônico, repetido em série:

```text
.venv/bin/python model_train/race_diagnostic.py --controller professor --n-cars 1 --ticks 6000 --laps 99 --track interlagos|Monaco --seed N --weather seeded --variance off --grid f1 --rejoin bearing --variedade N --out <arquivo>.csv
```

Todos os CSVs têm 3.002 linhas (3.000 amostras), sidecar presente e `--prof-curva` desligado.

| realização | fora (%) | excursões | voltas (s) |
|---|---:|---:|---|
| Interlagos N0 | 24,567 | 20 | 138,572; 130,498; 127,441; 129,891 |
| Interlagos N1 | 25,333 | 21 | 139,753; 131,217; 128,498; 131,022 |
| Interlagos N2 | 24,900 | 21 | 139,011; 130,431; 128,682; 129,948 |
| Interlagos N3 | 25,333 | 20 | 139,527; 131,485; 128,874; 130,741 |
| Interlagos N4 | 24,500 | 20 | 137,911; 130,227; 127,885; 130,016 |
| Monaco N0 | 56,933 | 41 | 212,067; 211,505 |
| Monaco N1 | 56,733 | 41 | 215,223; 212,898 |
| Monaco N2 | 56,733 | 41 | 213,773; 214,295 |
| Monaco N3 | 57,167 | 41 | 213,606; 217,546 |
| Monaco N4 | 56,400 | 42 | 211,604; 212,903 |

Em Interlagos, o instrumento encontrou as quatro regiões-alvo em todas as cinco realizações: C01/Descida do Lago (`s≈31–37`), C06/Bico de Pato (`s≈1945–1949`), C07/Mergulho (`s≈2056–2058`) e C08/Junção (`s≈2317–2319`). A Reta também apresentou quatro excursões em cada realização, com `|lat|` máximo agregado de aproximadamente 26,7–28,4 m. C07, C08 e Reta exibiram saturação de esterço no segundo anterior na maioria ou totalidade dos eventos; C01 e C06 foram predominantemente não saturados.

Em Monaco, as 41–42 excursões concentram-se em C03, C04, C05, C06, C07, C11, C12 e Reta, com saturação de esterço presente em praticamente todos os eventos de curva. O valor N0 reproduz o golden anterior (`56,933%` fora e `41` excursões).

As dez leituras foram repetidas com o mesmo CSV/log/sidecar; todos os pares `*_metrics.json` versus `*_metrics_rep.json` passaram `cmp=0`. Cada leitura conferiu o SHA da pista, a variedade, o log `tempos=`, as 3.002 linhas e a presença do sidecar.

## Gates e decisão

- Gate Primário, medido na referência OFF: **FAIL informativo**, como esperado para a linha de base; as saídas crônicas não são zero.
- Gate Monaco: ainda não é um gate de tratamento; a referência OFF fica registrada em 56,4–57,2% fora para comparação posterior.
- Guarda de ritmo: a referência histórica fixada no prereg continua sendo o comparador; a baseline OFF observada fica registrada acima de 123,05 s nas voltas rolantes de ambas as pistas.
- Nenhuma corrida ON, matriz de 10 carros, alteração de governor de produção ou promoção foi realizada nesta etapa.

**PARE formal:** o estágio 0 está fechado para revisão do Dono. A próxima ação autorizável é a Task 5 (mapa de viabilidade e prereg do mecanismo); não iniciar a implementação/ligação do teto nem novas corridas antes do Freeze/closing do Dono.
