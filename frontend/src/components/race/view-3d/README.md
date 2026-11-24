# Visualização 3D da corrida (`view-3d/`)

O modo **3D** da tela de corrida (`pages/race-simulation.tsx`). Mostra a mesma
corrida ao vivo que o mapa 2D, no mesmo instante, com os carros posicionados
pela pose da engine.

O 3D de produção fica aqui. `viz3d/` continua sendo o laboratório (verificações
de pista, gravações, replay, `npm run snapshot`) e não é importado: o build do
Docker do frontend usa `./frontend` como contexto e não enxerga `../viz3d`. Por
isso o código foi **copiado e adaptado**, não importado.

## Arquivos

| Arquivo | O que faz | Portado de (`viz3d/`, commit do arquivo) |
|---|---|---|
| `race-view-3d.tsx` | Contrato de props do Luiz (inalterado) + `React.lazy`/`Suspense` e um *error boundary*. É o único módulo do 3D no bundle principal. | — |
| `race-scene.tsx` | `<Canvas>`, luzes, pista, carros, câmera; botões Perseguição/A bordo; sair do seguimento por arrasto, rolagem ou Esc. Chunk preguiçoso. | `src/live/LiveRace.tsx` (`aa32ad2`), só a parte da cena |
| `scene/track-frame.ts` | Referencial `(s, d)` → mundo, `wrapS`, `toWorld`, curvatura; `nearestS` (novo). | `src/track/frame.ts` (`3fb91fa`) |
| `scene/race-track.ts` | Waypoints do backend → Three.js, rotação para `startFinishWaypoint` = s 0, via dos boxes, extremos da linha de chegada, enquadramento da visão geral. | `src/live/track.ts` (`aa32ad2`) |
| `scene/geometry.ts` | Faixa da pista, superfície e contorno da via dos boxes, linha de chegada. | `src/track/ribbon.ts` (`3fb91fa`), `src/live/pitRibbon.ts` (`aa32ad2`), `src/live/StartFinishLine.tsx` (`35baba2`) |
| `scene/track-meshes.tsx` | `TrackRibbon`, `PitLaneRibbon`, `StartFinishLine`. | `src/track/TrackRibbon.tsx` (`3fb91fa`, sem a verificação I), `src/live/PitLaneRibbon.tsx` (`aa32ad2`), `src/live/StartFinishLine.tsx` (`35baba2`) |
| `scene/car-model.ts` | Correção de eixos/escala do glTF, geometria para instâncias, matrizes de pose e de roda. | `src/cars/model.ts` (`a7763c5`), `src/cars/instance.ts` (`2d25e8a`) |
| `scene/cars.tsx` | Um `InstancedMesh` por primitiva, rodas pelo hodômetro, marcadores clicáveis na visão geral. | `src/cars/Grid.tsx` (`a7763c5`), sem a verificação J e sem as marcas de roda |
| `scene/live-pose.ts` | Interpolação igual à do 2D, direção pelo arco mais curto, mapeamento de eixos, hodômetro, desembrulho de `s`. | `src/live/buffer.ts` (`a7763c5`), `src/cars/odometry.ts` (`a7763c5`), `engineYaw` de `src/engine/source.ts` (`a7763c5`) |
| `scene/camera-math.ts` | Perseguição, T-cam (a bordo), amortecimento e inclinação. | `src/cameras/rig.ts` (`39b2589`) |
| `scene/camera-rig.tsx` | Órbita (visão geral), perseguição e a bordo. | `src/cameras/CameraRig.tsx` (`f6c843d`) |
| `scene/car-colors.ts` | Cor de equipe ou, se nula/"unknown", uma cor distinta da paleta. | — |
| `scene/dev-probe.ts` | `window.__race3d`, só em desenvolvimento, para a verificação headless. | — |
| `public/models/raceCarRed.glb` | Kenney Racing Kit, CC0 (`viz3d/ASSETS.md`), cópia byte a byte. | `public/models/raceCarRed.glb` (`3fb91fa`) |

Ficaram de fora (só servem ao laboratório): verificações de pista e de
espelhamento (`verify.ts`, checks I e J), gravações e replay (`src/engine/`,
`src/replay/`, timeline), o `?probe`, o posicionamento por `(s, d)` do campo
sintético, as marcas de roda e os painéis. A cópia foi feita a partir de
`origin/dev` em `5c76c9d` (23/11/2026).

Versões fixadas exatamente como no viz3d: `three` 0.169.0,
`@react-three/fiber` 9.8.2, `@react-three/drei` 10.7.9, `@types/three` 0.169.0.
Não atualize o three ou o R3F separadamente: o par de versões quebra fácil.

## Fluxo de dados

```
WebSocket ─► live-race-store (frame, prevFrame, frameAt, tickIntervalMs, selectedDriverId)
                 │                                   │
        track-2d.tsx (d3)                    race-view-3d.tsx ─lazy─► race-scene.tsx
                                                                      │
                     useFrame: useLiveRaceStore.getState()  ◄─────────┘
                     alpha = clamp((now - frameAt) / tickIntervalMs, 0, 1)   (igual ao 2D)
                     (x, y) = interpolateCars(prevFrame, frame, alpha)       (mesma função)
                     direção: heading_deg interpolado pelo arco mais curto
                     three.x = x, three.z = -y, yaw = heading - 90°
                     ─► matrizes de instância (corpo, rodas, marcador) ─► câmera
```

- **Um relógio.** Nenhum buffer próprio: o 3D usa os mesmos `prevFrame`,
  `frame`, `frameAt` e `tickIntervalMs` que o 2D, lidos com `getState()` dentro
  do `useFrame`. O React não re-renderiza a cena a cada tick (`RaceScene` é
  `memo` e não recebe `frame`).
- **Pista.** Exatamente os waypoints servidos (`GET /races/{id}`), rotacionados
  para que `startFinishWaypoint` seja s = 0, com largura `widthM` (12 m se
  nula) e a via dos boxes `track.pitLane`. Sem suavização: desenhamos o que a
  engine simulou.
- **Carros.** Pela pose (`position_xy`, `heading_deg`), não por `(s, d)`.
  Tamanho da caixa do chassi (`carGeometry`) quando o backend envia; senão o
  modelo é escalado para 2,0 m de largura. Rodas giram pelo deslocamento no
  chão entre ticks.
- **Câmera.** `selectedDriverId` definido → perseguição desse carro (ou
  *a bordo*, pelo botão no canto). A direção da perseguição e o ponto à frente
  usam `progressM` quando existe (senão `sM` desembrulhado, senão a projeção
  na pista); a âncora fica sobre a pose. `null` → visão geral ajustada à pista
  e ao formato do elemento. Clicar num carro (ou no marcador acima dele na
  visão geral) chama `onSelectDriver(id)`; arrastar, rolar ou Esc durante o
  seguimento chamam `onSelectDriver(null)`, como o botão "Visão geral".
- **Cores.** `teamColor`, exceto quando nula ou `teamColorSource === "unknown"`
  (o cinza de emergência do backend); aí cada piloto recebe uma cor própria da
  paleta do 2D (sem os tons cinza), diferente das cores de equipe em uso. O 2D
  continua mostrando o cinza nesses casos.
- **Recursos.** O `<Canvas>` preenche o elemento pai e acompanha o tamanho
  dele. Ao voltar para o 2D, o R3F descarta o renderizador e força a perda do
  contexto WebGL; geometrias e materiais clonados são descartados nos efeitos.

## Como rodar

```bash
# Backend (WSL; o pybullet não tem wheel para Windows)
redis-server --daemonize yes
cd backend && ~/venvs/sim/bin/python -m uvicorn api.main:app --port 8000

# Frontend (Windows)
cd frontend && npm ci && npm run dev
```

Crie uma corrida pelo fluxo normal (Iniciar → circuito → pilotos → clima/pneus)
e, na tela da corrida, escolha **3D**.

Testes: `npm test` (inclui `tests/view-3d.test.mjs`: direção através de
±180°, rotação dos waypoints, cores, pose igual à interpolação 2D),
`npm run lint`, `npm run build`. Em desenvolvimento, `window.__race3d.sample()`
devolve as posições desenhadas pelo 3D (lidas das matrizes de instância) e as
do 2D para o mesmo `performance.now()`.
