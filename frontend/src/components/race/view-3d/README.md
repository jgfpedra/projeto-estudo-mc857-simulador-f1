# Visualização 3D da corrida (`view-3d/`)

O modo **3D** da tela de corrida (`pages/race-simulation.tsx`). Mostra a mesma
corrida ao vivo que o mapa 2D, ~150 ms atrás dele (reprodução com buffer, para
o movimento não tremer com a chegada irregular dos ticks), com os carros
posicionados pela pose da engine.

O 3D de produção fica aqui. `viz3d/` continua sendo o laboratório (verificações
de pista, gravações, replay, `npm run snapshot`) e não é importado: o build do
Docker do frontend usa `./frontend` como contexto e não enxerga `../viz3d`. Por
isso o código foi **copiado e adaptado**, não importado.

## Arquivos

| Arquivo | O que faz | Portado de (`viz3d/`, commit do arquivo) |
|---|---|---|
| `race-view-3d.tsx` | Contrato de props do Luiz (inalterado) + `React.lazy`/`Suspense` e um *error boundary*. É o único módulo do 3D no bundle principal. | — |
| `race-scene.tsx` | `<Canvas>`, luzes, pista, carros, câmera; botões Perseguição/A bordo; seletor de cenário (por portal na barra da página); sair do seguimento por arrasto, rolagem ou Esc. Chunk preguiçoso. | `src/live/LiveRace.tsx` (`aa32ad2`), só a parte da cena |
| `toolbar-slot.ts` | Contexto com o lugar da barra de cima onde a cena põe o seletor de cenário. | — |
| `scene/track-frame.ts` | Referencial `(s, d)` → mundo, `wrapS`, `toWorld`, curvatura; `nearestS` (novo). | `src/track/frame.ts` (`3fb91fa`) |
| `scene/race-track.ts` | Waypoints do backend → Three.js, rotação para `startFinishWaypoint` = s 0, via dos boxes, extremos da linha de chegada, enquadramento da visão geral. | `src/live/track.ts` (`aa32ad2`) |
| `scene/geometry.ts` | Faixa da pista, superfície e contorno da via dos boxes, linha de chegada. | `src/track/ribbon.ts` (`3fb91fa`), `src/live/pitRibbon.ts` (`aa32ad2`), `src/live/StartFinishLine.tsx` (`35baba2`) |
| `scene/track-meshes.tsx` | `TrackRibbon`, `PitLaneRibbon`, `StartFinishLine`. | `src/track/TrackRibbon.tsx` (`3fb91fa`, sem a verificação I), `src/live/PitLaneRibbon.tsx` (`aa32ad2`), `src/live/StartFinishLine.tsx` (`35baba2`) |
| `scene/car-model.ts` | Correção de eixos/escala do glTF, geometria para instâncias, matrizes de pose e de roda, posição da faixa do composto no flanco. | `src/cars/model.ts` (`a7763c5`), `src/cars/instance.ts` (`2d25e8a`) |
| `scene/cars.tsx` | Um `InstancedMesh` por primitiva, rodas pelo hodômetro, faixas de composto (um `InstancedMesh` com cor por instância), marcadores clicáveis que só aparecem com a câmera longe dos carros. | `src/cars/Grid.tsx` (`a7763c5`), sem a verificação J e sem as marcas de roda |
| `scene/live-pose.ts` | Interpolação igual à do 2D, direção pelo arco mais curto, mapeamento de eixos, hodômetro, desembrulho de `s`. | `src/live/buffer.ts` (`a7763c5`), `src/cars/odometry.ts` (`a7763c5`), `engineYaw` de `src/engine/source.ts` (`a7763c5`) |
| `scene/camera-math.ts` | Perseguição atrás do carro pela direção dele suavizada (sem pose: o rig antigo, pela pista, com o limite de 8°), T-cam (a bordo), amortecimento e inclinação. | `src/cameras/rig.ts` (`39b2589`), perseguição reescrita |
| `scene/camera-jitter.ts` | Tremor de um ângulo quadro a quadro (taxa menos a média de ±0,25 s), para a direção da câmera e o carro na tela. | — |
| `scene/camera-rig.tsx` | Órbita (visão geral), perseguição e a bordo. | `src/cameras/CameraRig.tsx` (`f6c843d`) |
| `scene/tyre-compound.ts` | Composto do frame → cor da faixa no pneu (ou nenhuma). | — |
| `scene/car-colors.ts` | Cor de equipe ou, se nula/"unknown", uma cor distinta da paleta. | — |
| `scene/dev-probe.ts` | `window.__race3d`, só em desenvolvimento, para a verificação headless; `sample()`, `freeze()`/`unfreeze()`, `view()`, `bench()`, `playback()`, `smoothness()`, `chaseRig()`, `cameraJitter()`, `shadowOffset()`, `tyreBands()`, `tyreView()` e `weather()`. | — |
| `scene/playback.ts` | Reprodução com buffer: frames por `simTs`, instante desenhado ~150 ms atrás do mais novo, taxa ajustada em ±5%, sem extrapolação, ressincronização. | — |
| `scene/live-clock.ts` | Liga a store ao relógio de `playback.ts` enquanto o 3D está montado e entrega a cada quadro o par de frames e o `alpha`; o gancho de desenvolvimento pode congelar a vista ou voltar ao caminho antigo. | — |
| `scene/smoothness.ts` | Medida do passo do carro seguido quadro a quadro (dispersão, paradas, saltos, ré). | — |
| `scene/pin-fade.ts` | Opacidade dos marcadores pela distância ao carro mais próximo. | — |
| `scene/environment/curvature.ts` | Curvatura em metros (Menger com vizinhos a ≥ 12 m, suavização de ±16 m), trechos acima de um limiar, ápices. | — |
| `scene/environment/layout.ts` | Regras de posicionamento do cenário (função pura, com semente), caixas dos modelos, folgas, `propMatrix`. | protótipo de cenário (`env-prototype/main.js`), reescrito |
| `scene/environment/surfaces.ts` | Faixas do chão: asfalto, linhas, zebras, brita, gramado aparado, via dos boxes; alturas das camadas. | idem |
| `scene/environment/textures.ts` | Texturas de grão em canvas, com semente; paleta do kit. | idem |
| `scene/environment/environment.tsx` | Céu, neblina, luzes e sombra que segue o alvo da câmera; chão; modelos instanciados; o clima aplicado a eles e os riscos de chuva. | idem |
| `scene/environment/weather.ts` | Clima do frame → `cloud`/`wet`/`rain`, mistura de 5 s, parâmetros da cena, neblina, quantidade de riscos de chuva. | — |
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
                 │                         │ subscribe (só com o 3D montado)
        track-2d.tsx (d3)          live-clock.ts ─► playback.ts: últimos ~3 s de frames, por simTs
        (borda ao vivo)                    │
                     useFrame: readLive() ─┘  t = instante de simulação ~150 ms atrás do mais novo
                     prev ≤ t < cur do buffer, alpha = (t - prev.simTs) / (cur.simTs - prev.simTs)
                     (x, y) = interpolateCars(prev, cur, alpha)              (mesma função do 2D)
                     direção: heading_deg interpolado pelo arco mais curto
                     three.x = x, three.z = -y, yaw = heading - 90°
                     ─► matrizes de instância (corpo, rodas, marcador) ─► câmera
```

- **Reprodução com buffer.** O 2D desenha na borda ao vivo (`prevFrame ->
  frame`, `alpha` desde a chegada do tick). Os ticks chegam com 87-112 ms de
  intervalo mesmo no localhost, então ali o carro para quando um tick atrasa e
  salta quando um adianta; na perseguição isso tremia nas curvas (as direções
  da engine são lisas: 2ª diferença p95 de 0,16°). O 3D guarda os frames
  (`playback.ts`, por `simTs`; mesmo `simTs` substitui, como na mudança de
  clima) e desenha um instante `t` que avança pelo tempo de parede do quadro
  de animação (`document.timeline.currentTime`) vezes a taxa da simulação, com
  um ajuste de no máximo ±5% para manter o atraso médio de 150 ms atrás do
  frame mais novo. A taxa começa em 1 (a engine roda em tempo real) e é
  medida pelo contorno inferior das chegadas nos últimos 20 s: atrasos só
  empurram uma chegada para depois, então as mais adiantadas dão o ritmo.
  Um mínimos-quadrados sobre todas as chegadas lia o lote de ticks entregue
  depois de uma parada da página (ao montar o 3D com SwiftShader, por
  exemplo) como simulação acelerada, e o 3D ficava parado no frame mais novo
  por ~10 s; lotes (chegadas a < 30 ms) e a primeira chegada depois de uma
  pausa de > 0,5 s ficam fora da medida. Com a engine mais lenta que o tempo
  real, os primeiros ~3 s podem parar no frame mais novo enquanto a taxa é
  aprendida. No primeiro quadro desde que o relógio começou, `t` parte do
  atraso alvo (a cena pode levar ~0,7 s para carregar com 20 carros e
  cenário alto; sem isso o 3D começava esse tempo atrás). Isso absorve um
  tick até ~100 ms atrasado; se `t` alcança o frame mais novo, ele para ali
  (nunca extrapola) e o ajuste reconstrói o atraso. Uma engine que oscila
  muito abaixo do tempo real (medido: 0,55-0,8x com quatro corridas ao mesmo
  tempo no WSL) não cabe no ajuste de ±5% e faz o 3D parar às vezes.
  Ressincroniza na hora (e a câmera corta) depois de um snapshot (carga,
  reconexão: a store zera `prevFrame`), de um salto de mais de 1 s no tempo de
  simulação, de tempo voltando, ou se ficar mais de 1 s atrás. Carros, direção,
  progresso, rodas, marcadores e câmera saem desse instante; o 2D, o painel de
  tempos e o cartão do piloto continuam na borda ao vivo. O React não
  re-renderiza a cena a cada tick (`RaceScene` é `memo` e não recebe `frame`).

  Medido ao vivo (24/11/2026): corrida de 20 carros em Interlagos (OpenF1),
  Chrome headless na GTX 1660 SUPER, cenário alto, seguindo o líder por uma
  volta em cada modo (`playback("live")` e depois o padrão), com
  `smoothness()` no S do Senna (s 200-600 m) e na Junção (s 3000-3350 m).
  Sem vsync, o headless desenhou ~300-400 quadros/s, então as contagens
  absolutas não se comparam às de uma tela de 60 Hz; o antes e o depois sim.

  | Modo | Trecho | Quadros | Dispersão | Paradas | Saltos | Parado no mais novo | Atraso médio |
  |---|---|---|---|---|---|---|---|
  | antes (borda ao vivo) | S do Senna | 4068 | 0,519 | 291 | 194 | 71 | 48 ms |
  | antes (borda ao vivo) | Junção | 2813 | 0,598 | 248 | 135 | 23 | 48 ms |
  | antes (borda ao vivo) | volta | 26859 | 0,530 | 1857 | 1287 | 298 | 48 ms |
  | depois (com buffer) | S do Senna | 4078 | 0,001 | 0 | 0 | 0 | 148 ms |
  | depois (com buffer) | Junção | 2868 | 0,001 | 0 | 0 | 0 | 148 ms |
  | depois (com buffer) | volta | 31109 | 0,001 | 0 | 0 | 0 | 148 ms |

  Nos dois modos, 3D e interpolação do 2D no instante desenhado diferem
  < 0,0001 m. Nenhum passo de ré em nenhum dos dois.
- **Pista.** Exatamente os waypoints servidos (`GET /races/{id}`), rotacionados
  para que `startFinishWaypoint` seja s = 0, com largura `widthM` (12 m se
  nula) e a via dos boxes `track.pitLane`. Sem suavização: desenhamos o que a
  engine simulou.
- **Carros.** Pela pose (`position_xy`, `heading_deg`), não por `(s, d)`.
  Tamanho da caixa do chassi (`carGeometry`) quando o backend envia; senão o
  modelo é escalado para 2,0 m de largura. Rodas giram pelo deslocamento no
  chão entre ticks.
- **Câmera.** `selectedDriverId` definido → perseguição desse carro (ou
  *a bordo*, pelo botão no canto). `null` → visão geral ajustada à pista e ao
  formato do elemento. Clicar num carro (ou no marcador acima dele na visão
  geral) chama `onSelectDriver(id)`; arrastar, rolar ou Esc durante o
  seguimento chamam `onSelectDriver(null)`, como o botão "Visão geral".

  A perseguição fica atrás do carro, pela direção desenhada dele (a mesma do
  modelo) suavizada com um amortecimento independente da taxa de quadros
  (`yawTauS` = 0,25 s): posição = carro − 9 m na direção + 3,2 m de altura,
  alvo = carro + 25 m na direção (0,8 m de altura). Não lê a pista nem o
  `progressM`, e o carro fica sempre no eixo da câmera na horizontal. Corta
  (sem amortecer) ao trocar de carro e numa ressincronização. O passo do
  amortecimento sai do carimbo do quadro da reprodução, o mesmo que moveu o
  carro, e não do `delta` do R3F (`performance.now()` na hora do callback):
  com os dois relógios a câmera girava em passos desiguais em relação ao carro
  (medido: 8-9 graus/s de tremor só por isso). Congelado, usa o `delta` para
  assentar.

  O rig antigo, portado do viz3d, mirava por pontos da pista (`u` = s − 9 m
  atrás, s + 25 m à frente, pelo `progressM`). Nas curvas essa mira ficava a
  mais de 8° do carro, o limite de 8° a prendia, e a direção da câmera passava
  a seguir as cordas da polilinha servida, que nas pistas do OpenF1 dobra a
  cada 14-42 m: a câmera balançava nas curvas. Ele ficou só para o carro sem
  pose (com o limite de 8°) e, em desenvolvimento, atrás de
  `__race3d.chaseRig("track")`, para comparar.

  Medido ao vivo (24/11/2026), na mesma configuração da tabela da reprodução
  (20 carros, Interlagos do OpenF1 com 280 pontos, GTX 1660 SUPER, cenário
  alto, ~240 quadros/s no headless), seguindo o líder por ~95 s com cada rig
  (antigo e depois o novo), `cameraJitter()` (graus/s; `carHeading` é a mesma
  medida na direção do próprio carro, a referência):

  | Rig | Trecho | Quadros | Câmera | Carro na tela | Direção do carro | Carro fora do eixo (máx.) |
  |---|---|---|---|---|---|---|
  | antigo (pela pista) | S do Senna | 1803 | 7,63 | 7,43 | 2,87 | 8,0° |
  | antigo (pela pista) | Junção* | 281 | 0,41 | 0,78 | 0,65 | 0,8° |
  | antigo (pela pista) | volta | 20635 | 7,31 | 5,58 | 2,27 | 8,0° |
  | novo (atrás do carro) | S do Senna | 3824 | 1,28 | 0 | 3,03 | 0° |
  | novo (atrás do carro) | Junção | 2278 | 0,86 | 0 | 2,10 | 0° |
  | novo (atrás do carro) | volta | 20541 | 0,98 | 0 | 2,24 | 0° |

  \* Só o fim da Junção caiu na janela do rig antigo, já na reta. O que sobra
  no rig novo (~1 grau/s) não é tremor: num S rápido a média de ±0,25 s não
  acompanha toda a rotação real (uma direção lisa, sem ruído, também lê ~2
  graus/s no teste sintético), e a câmera fica abaixo da direção do próprio
  carro. Fora do teste ao vivo, num percurso sintético com pontos a 14-42 m
  (`tests/view-3d.test.mjs`): antigo 3,5 graus/s na câmera e 11,9 no carro na
  tela; novo 0,07 e 0.
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
- **Qualidade.** Um seletor "Cenário" na barra de cima, logo depois da chave
  2D/3D (embaixo do canvas o cartão do piloto selecionado o cobria):
  *Alta* (sombras, 2600 árvores), *Baixa* (sem sombras, 35% das árvores), *Sem
  cenário* (o visual antigo: fundo liso, só a faixa da pista e o renderizador
  sem mapa de sombras). A escolha fica no `localStorage`. O seletor fica fora
  do canvas de propósito: com um elemento HTML sempre por cima dele, o Chrome
  com WebGL por software às vezes avisava "glBlitFramebuffer: Blit feedback
  loop" ao montar ou desmontar o 3D (3 em 300 alternâncias; 0 em 300 sem o
  elemento e 0 em 300 no `origin/dev`). É um `<select>` nativo: a lista abre
  fora do documento. A página monta a barra como uma linha flexível (chave
  2D/3D, um lugar para os controles do 3D, a faixa de eventos no que sobra)
  e passa o lugar por contexto (`toolbar-slot.ts`); a cena põe o seletor ali
  por portal, sem mudar as props de `RaceView3D`. Assim a faixa de eventos
  começa depois do seletor no 3D e onde sempre esteve no 2D (o lugar vazio
  some). Medido a 1440×900 com uma mensagem na faixa e o cartão do piloto
  aberto: chave x 145-245, seletor 253-436, faixa 448-911; nada se sobrepõe.
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

  Sem a faixa de qualidade embaixo, o canvas voltou a ter a altura toda da área (750×541 nessa janela).

  A verificação ao vivo (`viz3d/scripts/check-3d-frontend.mjs`) usa
  SwiftShader por padrão, então roda sem cenário; `--gpu --quality high` roda
  na GPU com o cenário. Em ambos os casos ela congela o relógio do 3D
  (`__race3d.freeze()`) antes de cada captura e da leitura de posições que vai
  com ela, então o resultado não depende da velocidade de renderização.
- **Sombra em velocidade.** A sombra do carro não fica para trás: o three
  0.169 avança o contador de quadros antes de desenhar as sombras, então o
  passo da sombra já envia as matrizes de instância do quadro. Medido com
  `shadowOffset()` (centro da superfície do carro no mapa de sombra, no
  referencial do carro): na mesma pose, desenhada andando e depois congelada,
  12 pares a 22-31 m/s diferem de −0,018 a +0,014 m (meio texel de 0,037 m),
  quando um quadro de atraso daria 0,09-0,13 m (0,53 m no único quadro de
  16,7 ms). A "cópia escura" vista em velocidade não veio do mapa de sombra
  atrasado; não foi reproduzida aqui.
- **Sombra no primeiro quadro.** O three desenha as sombras antes de montar as
  luzes do quadro; no primeiro quadro de um renderizador as luzes estão vazias
  e os modelos já em cache compilariam uma variante extra do material de
  profundidade (2 programas a mais a partir da 2ª montagem). A sombra fica
  desligada nesse quadro e liga no seguinte.

Modelos: [Racing Kit](https://kenney.nl/assets/racing-kit) de
[Kenney](https://www.kenney.nl), CC0 (licença em `public/models/License.txt`).

## Clima e pneus

### Faixa do composto

Cada pneu tem um anel colorido no flanco externo, no ombro (toro de raio 0,86
e tubo 0,14 do raio da roda, com o centro do tubo na face externa: de trás e
de cima ele aparece como uma faixa na borda do pneu). O anel usa a matriz da
roda, então anda e gira com ela. Todos os anéis de todos os carros são um só
`InstancedMesh` (carro k, roda w → instância k·4 + w), com a cor por
instância; o material não tem luz nem tone mapping, para a cor sair exata em
qualquer clima (a neblina ainda vale). A cor vem do `tyre` do mesmo frame
amostrado que dá a pose (`CarFrame.tyre`, o `tyre_compound` que o parser
guarda como veio, em qualquer caixa) e é trocada quando ele muda, como depois
de um pit stop:

| Composto | Cor |
|---|---|
| SOFT | `#E10600` (vermelho) |
| MEDIUM | `#FFD12E` (amarelo) |
| HARD | `#F0F0F0` (branco) |
| INTERMEDIATE | `#43B02A` (verde) |
| WET | `#0067AD` (azul) |

Desconhecido ou ausente (`"UNKNOWN"` do parser): sem anel. Lê-se na
perseguição, a bordo e no grid; na visão geral é pequeno demais, de propósito.
As faixas existem nas três qualidades, inclusive em *Sem cenário* (não são
clima).

### Clima

O `weather` do frame que os carros desenharam (`kind`, `rainfall`,
`trackTemp`) vira três números entre 0 e 1 (`environment/weather.ts`):
`cloud` (céu encoberto), `wet` (asfalto molhado) e `rain` (intensidade da
chuva, `1 − exp(−rainfall / 3 mm/h)`: 0,5 mm/h → 0,15, 2,5 → 0,57, 8 →
0,93). Esses três são misturados no tempo e só então viram cores e
intensidades, então a cena nunca salta:

- **Seco** (`DRY`, sem clima ou um `kind` desconhecido): exatamente a cena de
  antes (sol 2,4, hemisférica 0,9, neblina `#b9cfe0` de 1x a 3x a distância da
  visão geral, asfalto sem mudança).
- **Nublado** (`CLOUDY`): o shader do `Sky` com um cinza por cima (85% do céu;
  `overcast` = 0 devolve o céu de antes, o mesmo programa em qualquer clima),
  turbidez 10, sol 0,9 e sem o tom quente, luz ambiente cinza-azulada, neblina
  cinza e mais perto (×0,75 / ×0,85).
- **Chuva** (`WET`, e `DAMP` com `rainfall` > 0, que é a "chuva fraca" do
  backend): nublado, mais o céu mais escuro com a chuva, sol e ambiente
  menores (sol 0,58 na chuva forte), riscos de chuva em volta da câmera em
  número proporcional a `rain`, asfalto e via dos boxes mais escuros (×0,58)
  e mais lisos (rugosidade 0,92 → 0,55), e uma neblina que fecha com a chuva
  numa escala que acompanha a câmera (25x a distância até o alvo, entre 250 m
  e a da visão geral): na perseguição em chuva forte ela vai de ~160 m a
  ~730 m; na visão geral a pista continua legível. `DAMP` sem chuva: só o
  céu nublado e a pista úmida (0,7 de `wet` até 24 °C, 0,4 a partir de 40 °C:
  a única coisa que a temperatura da pista muda). `WET` sem `rainfall` usa os
  2,5 mm/h do backend.

Os riscos são um `LineSegments` com todos os riscos da qualidade (alta 9000,
baixa 1500), animados no vertex shader (queda de 12 m/s com um pouco de
vento, numa caixa de 40 m que acompanha a câmera e dá a volta); a intensidade
só muda o `drawRange`, e sem chuva nada é desenhado. Na visão geral a caixa
cresce com a distância (até 25x) e os riscos ficam mais transparentes. O
tempo é o do quadro desenhado: congelado (`freeze()`), a chuva para.

**Mistura.** O primeiro clima entra na hora (abrir o 3D com chuva mostra
chuva); cada mudança depois parte do valor do instante e chega ao alvo em 5 s
por uma `smoothstep`, e um alvo novo no meio recomeça dali. A mistura usa o
mesmo relógio dos carros: congelada, ela para também.

**Qualidade.** *Alta*: tudo. *Baixa*: 1500 riscos em vez de 9000 e nada mais
(as mudanças de céu, luz, neblina e asfalto são só valores de uniforms). *Sem
cenário*: nenhum clima (o cenário inteiro não é montado; o visual de antes).
Os marcadores continuam com `fog: false` e `toneMapped: false`: cor exata com
qualquer neblina.

**Verificado ao vivo** (24/11/2026, GTX 1660 SUPER, Chrome headless,
Interlagos do OpenF1, 10 carros, capturas em `viz3d/.cache/weather-tyres/`,
fora do git): corrida criada com chuva forte (`weather: heavy_rain`, 8 mm/h,
pneus de chuva) na perseguição, a bordo e na visão geral, nas três qualidades;
corrida seca; pit stop pedido no carro seguido
(`POST /races/{id}/drivers/{driver}/pit-stop`, `soft`) com a faixa amarela
antes e vermelha depois, ao lado e na perseguição. Uma mudança de clima ao
vivo com `weather_change` a 1,0 por volta não pôde ser capturada: o backend
sorteia o clima na largada (a corrida "seca" já abriu em chuva, 2,5 mm/h) e,
nas duas tentativas, não trocou de novo na virada da volta 1 para a 2; a
mistura está coberta pelos testes. Tempo de quadro com `bench(150)` (mediana,
canvas de 750×541; perseguição atrás do líder; p90 entre parênteses):

| Clima | Alta | Baixa | Sem cenário | Visão geral, alta |
|---|---|---|---|---|
| seco | 1,2 ms (1,5) | 0,7 ms (0,8) | 0,4 ms (0,5) | 1,4 ms (1,7) |
| chuva forte | 1,3 ms (1,7) | 0,7 ms (1,1) | 0,5 ms (0,8) | 1,6 ms (2,1) |

A chuva custa uma chamada de desenho (42 contra 41 na perseguição) e ~0,1-0,2
ms na alta; na baixa, nada mensurável.

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
Interlagos do OpenF1, orientação dos boxes e arquibancadas, semente; a
perseguição num percurso com pontos a 14-42 m (tremor da câmera < 1 grau/s,
carro no eixo, o rig antigo como referência), ruído no `progressM` sem mover
a câmera, amortecimento independente da taxa de quadros e corte; limite de 8°
do caminho sem pose num grampo, esmaecimento dos marcadores; a reprodução
com buffer com tremor sintético de ±30 ms e rajadas de 3 ticks, uma parada de
250 ms da página, ticks atrasados demais, simulação a 0,9x e as
ressincronizações; composto → cor, clima → parâmetros da cena em seco, nublado,
chuva fraca e forte, a mistura contínua que termina em 5 s e os riscos de
chuva por qualidade, zero em *Sem cenário*), `npm run lint`, `npm run build`. Em desenvolvimento,
`window.__race3d.sample()` devolve as posições desenhadas pelo 3D (lidas das
matrizes de instância) e as da interpolação do 2D no instante de simulação
que o 3D desenhou (de uma cópia própria dos frames da store), mais o atraso
atrás do frame mais novo; `view("overview" | "grid" | "corner")` põe a câmera
nos pontos de vista das capturas, `bench(n)` mede o tempo de quadro (n
renderizações, cada uma esperando a GPU) e `freeze()` / `unfreeze()`
congelam e soltam a vista do 3D (os carros param na pose do último quadro; o
WebSocket, o buffer e o 2D seguem; ao sair do 3D o congelamento é desfeito).
`traceReset()` e `smoothness({ sRanges, playback })` medem o carro seguido
quadro a quadro (`smoothness.ts`: `r` = velocidade aparente do quadro / mediana
de ±15 quadros; `spread` = desvio-padrão de `r`, paradas `r` < 0,5, saltos `r`
> 1,5, passos de ré), e `playback("live")` volta ao caminho antigo (borda ao
vivo, como o 2D) para comparar; `playback("buffered")` é o padrão. `cameraJitter({ sRanges, chaseRig })`
mede a câmera de perseguição desde o `traceReset()` (`camera-jitter.ts`:
taxa de giro de cada quadro menos a média de ±0,25 s, RMS; para a direção da
câmera, para o ângulo do carro em relação ao eixo e, como referência, para a
direção do carro), `chaseRig("track")` volta ao rig antigo para comparar
(`"heading"` é o padrão), `tyreBands()` lê a cor e a visibilidade das faixas de
composto do buffer de instâncias, `tyreView(id)` põe a câmera parada ao lado de um
carro (fora do seguimento, com `freeze()`), `weather()` devolve o clima misturado,
o alvo, o andamento da mistura, a neblina e os riscos, e `shadowOffset()` lê o mapa de sombra do último
quadro em volta do carro seguido.
