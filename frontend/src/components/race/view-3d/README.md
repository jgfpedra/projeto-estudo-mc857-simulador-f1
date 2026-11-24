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
| `scene/cars.tsx` | Um `InstancedMesh` por primitiva, rodas pelo hodômetro, marcadores clicáveis que só aparecem com a câmera longe dos carros. | `src/cars/Grid.tsx` (`a7763c5`), sem a verificação J e sem as marcas de roda |
| `scene/live-pose.ts` | Interpolação igual à do 2D, direção pelo arco mais curto, mapeamento de eixos, hodômetro, desembrulho de `s`. | `src/live/buffer.ts` (`a7763c5`), `src/cars/odometry.ts` (`a7763c5`), `engineYaw` de `src/engine/source.ts` (`a7763c5`) |
| `scene/camera-math.ts` | Perseguição (direção a no máximo 8° do carro na horizontal), T-cam (a bordo), amortecimento e inclinação. | `src/cameras/rig.ts` (`39b2589`) |
| `scene/camera-rig.tsx` | Órbita (visão geral), perseguição e a bordo. | `src/cameras/CameraRig.tsx` (`f6c843d`) |
| `scene/car-colors.ts` | Cor de equipe ou, se nula/"unknown", uma cor distinta da paleta. | — |
| `scene/dev-probe.ts` | `window.__race3d`, só em desenvolvimento, para a verificação headless; `freeze()`/`unfreeze()`, `view()` e `bench()`. | — |
| `scene/live-clock.ts` | Relógio e store como o 3D os lê a cada quadro; o gancho de desenvolvimento pode congelá-los. | — |
| `scene/pin-fade.ts` | Opacidade dos marcadores pela distância ao carro mais próximo. | — |
| `scene/environment/curvature.ts` | Curvatura em metros (Menger com vizinhos a ≥ 12 m, suavização de ±16 m), trechos acima de um limiar, ápices. | — |
| `scene/environment/layout.ts` | Regras de posicionamento do cenário (função pura, com semente), caixas dos modelos, folgas, `propMatrix`. | protótipo de cenário (`env-prototype/main.js`), reescrito |
| `scene/environment/surfaces.ts` | Faixas do chão: asfalto, linhas, zebras, brita, gramado aparado, via dos boxes; alturas das camadas. | idem |
| `scene/environment/textures.ts` | Texturas de grão em canvas, com semente; paleta do kit. | idem |
| `scene/environment/environment.tsx` | Céu, neblina, luzes e sombra que segue o alvo da câmera; chão; modelos instanciados. | idem |
| `scene/environment/quality.ts` | Chave Alta / Baixa / Sem cenário, guardada no `localStorage`. | — |
| `scene/environment/views.ts` | Visão geral, grid e curva para as capturas (só o gancho de desenvolvimento usa). | — |
| `public/models/raceCarRed.glb` | Kenney Racing Kit, CC0 (`viz3d/ASSETS.md`), cópia byte a byte. | `public/models/raceCarRed.glb` (`3fb91fa`) |
| `public/models/*.glb` (12 do cenário) | Kenney Racing Kit 2.0, CC0, cópia byte a byte: `treeLarge`, `treeSmall`, `grandStandCovered`, `grandStandCoveredRound`, `pitsGarage`, `pitsOffice`, `overheadLights`, `billboard`, `lightPostLarge`, `tentLong`, `bannerTowerRed`, `flagCheckers`. | pacote do kit, pasta `GLTF format` |
| `public/models/License.txt` | Licença do kit (CC0), do mesmo pacote. | idem |

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
  Na perseguição, a direção não se afasta mais de 8° do carro na horizontal:
  num grampo de 25 m, mirar 25 m à frente pela pista poria o carro a ~29° do
  eixo, na borda da tela.
- **Marcadores.** Só com a câmera longe dos carros: a opacidade vai de 0 a 1
  entre 25% e 40% da distância da visão geral, medida até o carro mais
  próximo (`pin-fade.ts`). Na visão geral o carro mais próximo fica a pelo
  menos ~63% dessa distância, então lá eles estão sempre opacos (e com a cor
  exata: o material só fica transparente durante o esmaecimento); no grid,
  numa curva, com zoom de perto, na perseguição e a bordo, somem.
- **Cores.** `teamColor`, exceto quando nula ou `teamColorSource === "unknown"`
  (o cinza de emergência do backend); aí cada piloto recebe uma cor própria da
  paleta do 2D (sem os tons cinza), diferente das cores de equipe em uso. O 2D
  continua mostrando o cinza nesses casos.
- **Recursos.** O `<Canvas>` preenche o elemento pai e acompanha o tamanho
  dele. Ao voltar para o 2D, o R3F descarta o renderizador e força a perda do
  contexto WebGL; geometrias e materiais clonados são descartados nos efeitos.

## Cenário

Tudo é gerado a partir dos waypoints servidos (e da via dos boxes), então
qualquer pista ganha cenário, inclusive as do OpenF1 com pontos a 14–42 m.

- **Céu e luz.** `Sky` do three com o sol a 32° de elevação, neblina da cor do
  horizonte escalada pela distância da visão geral, luz hemisférica +
  direcional com sombras suaves (PCF soft, mapa 2048). O volume da sombra segue
  o alvo da câmera (o carro seguido ou o alvo da órbita), cresce com a
  distância e é alinhado aos texels para não tremer. Tone mapping ACES,
  exposição 0,8. Os marcadores dos carros ignoram neblina e tone mapping (a
  verificação ao vivo mede a cor deles).
- **Chão.** Grama, faixa de grama aparada (±6 m além da borda), asfalto com
  grão, linhas brancas nas bordas, zebras vermelhas e brancas e brita por fora
  das curvas onde |curvatura| > 1/140 1/m (alargadas 40 m), via dos boxes com
  linhas brancas só onde ela já saiu do asfalto. Paleta do kit (grama
  `#4d8f6d`, asfalto `#444444`, brita `#c7b795`, vermelho `#e85452`). Cada
  camada tem altura e `polygonOffset` próprios (`LAYERS` em `surfaces.ts`),
  então nada fica coplanar, nem na visão geral.
- **Curvatura.** `frame.curvature` usa os vizinhos imediatos, o que não serve
  para pistas grossas. `curvature.ts` mede o círculo por três pontos com
  vizinhos a pelo menos 12 m de arco e suaviza em ±16 m de arco: dá 1/R com
  qualquer espaçamento. Testado: Monza de 4 m e reamostrada a 14–42 m acham as
  mesmas curvas (posição < 30 m, raio ±25%); o Interlagos real do OpenF1 (280
  pontos) acha as curvas do Interlagos de 4 m.
- **Modelos** (`layout.ts`). Pórtico em s = 0 com um pé de cada lado (vão de
  W + 2 m; se a via dos boxes estiver colada à pista ali, ele estica na largura
  e passa por cima dela também). Boxes e escritórios ao longo da via, do lado
  oposto à pista, de frente para ela. Arquibancadas cobertas do outro lado da
  reta principal; arquibancada curva, torre de faixa e (em ápices alternados)
  tenda por fora de cada ápice com |curvatura| > 1/70 1/m. Placas e postes
  nas retas. Árvores a ≥ 55 m da linha central, mais raras depois de 140 m.
  Escalas do protótipo: árvores 6–11, arquibancadas 14, boxes 9, tenda 8,
  torre 6, placa 7, poste 9, bandeira 5. Toda colocação passa por uma checagem
  de folga contra o asfalto, a via dos boxes e o que já foi colocado; o que
  não cabe é descartado. Cada modelo repetido é um `InstancedMesh` por
  primitiva, com a geometria e o material do cache do `useGLTF`. A semente
  vem dos próprios pontos: a mesma pista sempre tem o mesmo cenário.
- **Qualidade.** Botões na faixa abaixo do canvas: *Alta* (sombras, 2600
  árvores), *Baixa* (sem sombras, 35% das árvores), *Sem cenário* (o visual
  antigo: fundo liso, só a faixa da pista e o renderizador sem mapa de
  sombras). A escolha fica no `localStorage`. A faixa fica fora do canvas de
  propósito: com um elemento HTML sempre por cima dele, o Chrome com WebGL por
  software às vezes avisava "glBlitFramebuffer: Blit feedback loop" ao montar
  ou desmontar o 3D (3 em 300 alternâncias; 0 em 300 sem o elemento e 0 em
  300 no `origin/dev`).
  Sem escolha guardada, o padrão é *Alta*, exceto com WebGL por software
  (SwiftShader, llvmpipe, sem GPU: `softwareRendering()` em `quality.ts`),
  onde o padrão é *Sem cenário*. A detecção cria um contexto descartável uma
  vez por página e o libera na hora (o canvas fica referenciado até o evento
  de perda chegar). Tempo de quadro medido com `bench()`
  (renderização + espera da GPU, mediana):

  | Canvas | Renderizador | Alta | Baixa | Sem cenário |
  |---|---|---|---|---|
  | 750×541 | GTX 1660 SUPER | 1,5 ms | 1,0 ms | 0,4 ms |
  | 1006×1081 | GTX 1660 SUPER | 2,0 ms | 1,1 ms | 0,5 ms |
  | 750×541 | SwiftShader | 225 ms | 77 ms | 9 ms |

  Medido com o canvas ainda sem a faixa de qualidade embaixo (hoje 750×513, 28 px a menos de altura).

  A verificação ao vivo (`viz3d/scripts/check-3d-frontend.mjs`) usa
  SwiftShader por padrão, então roda sem cenário; `--gpu --quality high` roda
  na GPU com o cenário. Em ambos os casos ela congela o relógio do 3D
  (`__race3d.freeze()`) antes de cada captura e da leitura de posições que vai
  com ela, então o resultado não depende da velocidade de renderização.
- **Sombra no primeiro quadro.** O three desenha as sombras antes de montar as
  luzes do quadro; no primeiro quadro de um renderizador as luzes estão vazias
  e os modelos já em cache compilariam uma variante extra do material de
  profundidade (2 programas a mais a partir da 2ª montagem). A sombra fica
  desligada nesse quadro e liga no seguinte.

Modelos: [Racing Kit](https://kenney.nl/assets/racing-kit) de
[Kenney](https://www.kenney.nl), CC0 (licença em `public/models/License.txt`).

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
±180°, rotação dos waypoints, cores, pose igual à interpolação 2D; e o
cenário: caixas dos modelos iguais às dos GLBs, curvatura em pista grossa,
nenhum modelo sobre o asfalto ou a via dos boxes em Interlagos, Monza e no
Interlagos do OpenF1, orientação dos boxes e arquibancadas, semente; limite
de 8° da perseguição num grampo, esmaecimento dos marcadores),
`npm run lint`, `npm run build`. Em desenvolvimento, `window.__race3d.sample()`
devolve as posições desenhadas pelo 3D (lidas das matrizes de instância) e as
do 2D para o mesmo `performance.now()`; `view("overview" | "grid" | "corner")`
põe a câmera nos pontos de vista das capturas, `bench(n)` mede o tempo de
quadro (n renderizações, cada uma esperando a GPU) e `freeze()` /
`unfreeze()` congelam e soltam o relógio do 3D (os carros param na pose do
instante; o WebSocket e o 2D seguem; ao sair do 3D o congelamento é desfeito).
