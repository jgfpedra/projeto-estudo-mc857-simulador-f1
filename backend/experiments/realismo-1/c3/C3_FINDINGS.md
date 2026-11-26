# REALISMO-1 · C3-A — verificação offline da mordida da rampa P2

**Estado:** report-only, zero simulação, zero edição de produção. Esta saída aguarda revisão do dono.

## Pergunta e método

A pergunta congelada foi se a rampa P2 ultrapassaria o teto em pelo menos 30% das reentradas que têm uma nova saída do mesmo carro em até 10 s.

- Reentrada: transição imediata `offtrack=1 -> 0` para o mesmo `drv` no CSV 5 Hz.
- Reentrada crítica: primeira linha futura `offtrack=1` em `(reentrada, reentrada+10 s]`.
- O `v_plan` é calculado pela implementação frozen `VelocityProfile` e congelado no `s` da reentrada.
- Teto da rampa: `min(0,8·v_plan, 8 + max(0,8·v_plan−8, 0)·elapsed/5)` m/s, com `elapsed` de 0 a 5 s.
- Mordida: alguma velocidade observada estritamente acima do teto (`excesso > 0`). A janela usa ticks inteiros e inclui os extremos.

## Parâmetros e proveniência

- Parâmetros da rampa: `v0=8.0 m/s`, `hold=5.0 s`, `target=0.8·v_plan`.
- Perfil: `grip_mult=0.788`, `sf=0.8`, `ds_target=4.0 m`, `smooth_window_m=20.0 m`.
- SHA dos parâmetros: `d6402d1873ec435cd331e56abb628a21b70055ada38f1f54b7b44f8502b9c0b8`.
- SHA do script: `d94f6f3608c641ee83ba01ccd8e39571bc2eaf3bbb59633104c02cb698b2ee5b`.
- SHA do JSON: `cf2ebe12dd20e258651aaf048b38cf6fa928db210b27e49645bf70f5065ebd29`.

## Resultado

| Pista | Reentradas | Críticas | Avaliáveis 5 s | Mordidas | Fração | Veredito |
|---|---:|---:|---:|---:|---:|---|
| interlagos | 217 | 119 | 119 | 115 | 96.6% | C3_MORDE |
| monaco | 378 | 274 | 274 | 263 | 96.0% | C3_MORDE |

A decisão é por pista. `C3_MORDE` exige todas as janelas críticas completas e fração avaliável maior ou igual a 30%.

## Decisão operacional

- **interlagos: C3_MORDE** — autorizar a redação de um prereg C3-B antes de qualquer produção/simulação.
- **monaco: C3_MORDE** — autorizar a redação de um prereg C3-B antes de qualquer produção/simulação.

## Caveats

- N=0 é uma realização determinística e não representa a distribuição N=0..4. O resultado é uma triagem offline, não uma homologação comportamental.
- Episódios são contados por reentrada, portanto um mesmo `drv` pode contribuir com vários episódios. O JSON registra `drivers` separadamente.
- O teste mede se a telemetria frozen excede um teto hipotético. Não demonstra que uma implementação P2 causaria ou evitaria esse excesso.
- Nenhum sidecar de eventos, log de runner, controller, peso ou simulador foi lido; a análise usa apenas os CSVs principais e as geometrias frozen.
- A evidência completa por reentrada, incluindo cada amostra da janela de 5 s, está em `C3_RAMP_CHECK.json`.

## Disposição

C3-A permanece offline-only. Não implementar C3-B, não ajustar seus parâmetros e não executar simulação antes da revisão e autorização do dono.
