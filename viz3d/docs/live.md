# Corrida ao vivo

Inicie Redis (`redis://localhost:6379/0` por padrão) e a API com `cd backend && uvicorn api.main:app --port 8000`. Em outro terminal, execute `cd viz3d && npm ci && npm run dev`, abra o endereço do Vite e selecione **Corrida ao vivo**. Em Docker Compose, execute `docker compose up --build redis backend frontend viz3d`; a API fica na porta 8000, o menu principal na 3000 e o visualizador na 3001. O menu tem o acesso **Corrida 3D ao vivo**; `VITE_VIZ3D_URL` pode apontá-lo para outra origem no build do frontend.

A tela cria corridas pelo `POST /races` e também permite abrir uma corrida existente com `?race=<id>`. A geometria e a lista de carros vêm de `GET /races/{id}`. A engine publica ticks no canal Redis `race:{id}:events` e mantém o último tick em `race:{id}:state`; o WebSocket `/ws/races/{id}` entrega o estado salvo e acompanha o canal. A chave expira após 24 horas. `VITE_API_URL` configura a origem da API no build do visualizador; `REDIS_URL` configura o Redis no backend.

O eixo do backend `(x, y)` corresponde a `(x, 0, -y)` no Three.js; a direção vem do ângulo do solver. O visualizador interpola posições, direção e velocidade entre os ticks lógicos de 10 Hz, com um buffer de cerca de 150 ms, sem simulação de colisões no navegador. Se a conexão atrasar, ele mantém a última posição recebida; após uma reconexão ou perda longa de ticks, retoma do novo estado recebido. Os contatos carro-carro coletados pelo solver aparecem no campo `collisions` do tick; os deslocamentos após o impacto vêm das posições seguintes. Os movimentos entre ticks são aproximações lineares e os contatos continuam vindos do solver. A tela inicia a configuração padrão do backend, atualmente com dois pilotos; o formulário de seleção de pilotos, clima e pneus do frontend principal continua usando dados simulados e não inicia esta corrida ao vivo.

## Comparar com a janela do PyBullet

Na sessão gráfica Linux, execute na raiz do projeto:

```bash
backend/scripts/visualization/run-live-compare.sh --laps 3 --camera follow
```

O script cria uma única corrida, abre a janela do PyBullet e abre no navegador o visualizador conectado à mesma engine. Pressione `Ctrl+C` no terminal para encerrar os processos iniciados pelo script. A visualização no navegador usa um buffer de cerca de 150 ms, de modo que fica um pouco atrás do PyBullet.

É necessário ter `backend/.venv` com `backend/requirements.txt` instalado, Node/npm e uma sessão gráfica com `DISPLAY`. Sem `REDIS_URL`, o script usa Docker para criar um Redis temporário; se `viz3d/node_modules` não existir, instala as dependências com `npm ci`. Use `--no-browser` para abrir o endereço manualmente, `--camera overview` para a câmera geral ou `--help` para as demais opções. As portas padrão podem ser alteradas com `F1_API_PORT` e `F1_VIZ_PORT`.

## Geometria e largada

As corridas ao vivo usam por padrão as linhas derivadas da telemetria de Interlagos 2023 e Monza 2024, em `backend/config/tracks/`. A linha de chegada é o waypoint 0 e o grid é montado atrás dela. Em Interlagos, a linha foi estimada a partir de 980 voltas cronometradas (dispersão MAD de cerca de 3 m); em Monza, a estimativa fica a aproximadamente 1 m da referência de cronometragem. Os traçados representam linhas médias de telemetria, não um levantamento cadastral das bordas da pista. As larguras de 12 m são valores de simulação, não medições de cada ponto do autódromo.

A API envia os próprios waypoints, largura, índice da linha, hash da geometria e dimensões do chassi. A pista do navegador é construída desses dados, com os mesmos pontos e a mesma largura que o PyBullet usa. A linha branca do navegador e a vermelha do PyBullet marcam a mesma posição. A caixa de colisão do backend mede 5,0 × 1,8 × 0,7 m; para a corrida ao vivo, o modelo 3D estilizado é ajustado a essas mesmas dimensões externas. O formato detalhado ainda difere da caixa de colisão e as poses entre ticks são interpoladas.

Para conferir a proveniência das cópias usadas pelo backend, execute `backend/.venv/bin/python scripts/sync_live_tracks.py`. O relatório geométrico e os limites das comparações estão em [phase0-geometry-report.md](phase0-geometry-report.md); os arquivos congelados antigos permanecem disponíveis para reproduzir experimentos anteriores.

Na corrida ao vivo, **Marcar rodas** mostra uma faixa para inspecionar o giro. Os pneus do modelo são mantidos circulares mesmo quando o corpo é ajustado às dimensões do chassi, e o giro acompanha o deslocamento longitudinal entre poses da engine; em lacunas de conexão a fase é preservada até chegar o próximo estado. Em velocidades altas, a taxa de quadros pode produzir o efeito de roda aparentemente parada ou invertida (aliasing), mesmo com o cálculo de giro correto.
