# Pendências — IA, interfaces e recuperação

**Última atualização:** 2026-11-27

Este é o único documento de acompanhamento em `ai/report/`. Ele contém somente trabalho ainda aberto; o histórico das implementações e validações concluídas permanece no Git.

## 1. Validar os ajustes da UI do 3D no navegador

**Escopo:** `frontend/src/pages/race-simulation.tsx`, `frontend/src/components/race/driver-follow-card.tsx`, `frontend/src/components/race/timing-panel.tsx` e `frontend/src/components/race/ai/ai-floating-panel.tsx`.

- [ ] Confirmar que o card **MONITORANDO** só aparece após clicar no olho de acompanhar, fica abaixo dos dados do piloto e desaparece junto com esse card ao fechá-lo.
- [ ] Confirmar que o card de estatísticas fica dentro da área do visual 3D, abaixo do header 2D/3D, cenário e último evento, sem cobrir esses controles.
- [ ] Confirmar que posição, nome, telemetria e diferença fazem parte da área clicável do piloto na classificação ao vivo e no resultado final.
- [ ] Confirmar que clicar no card seleciona/desseleciona o piloto e aplica/remove o highlight vermelho, sem acionar o botão separado de acompanhar.
- [ ] Verificar a disposição e a rolagem dos painéis na view 3D e ao alternar 2D/3D, sem sobreposição com a cena ou os controles.

## 2. Validar o debrief com Ollama real

**Arquivos principais:** `ai/app/debrief.py`, `ai/app/client.py`, `ai/app/redis_listener.py`, `backend/api/main.py`, `viz3d/src/live/DebriefPanel.tsx` e `viz3d/src/live/LiveRace.tsx`.

- [ ] Subir Ollama e Redis e confirmar que o modelo configurado está carregado.
- [ ] Medir uma chamada fria e pelo menos três chamadas quentes com dados reais, registrando latência, tokens, validade do JSON, `fallback` e `fallback_motivo`.
- [ ] Ajustar prompt, `DEBRIEF_NUM_PREDICT`, `DEBRIEF_NUM_CTX` ou timeout somente se as medições indicarem necessidade, sem mudar os parâmetros das sugestões ao vivo.
- [ ] Obter JSON aceito por `validate_debrief_output()` e persistido com `fallback: false`.
- [ ] Confirmar geração em menos de 30 segundos ou revisar explicitamente essa meta com base nas medições.
- [ ] Validar o fluxo integral `race_end` → geração → `race:{race_id}:debrief` → `GET /races/{race_id}/debrief`, incluindo timeout e fallback factual.
- [ ] Validar visualmente abertura/fechamento do painel, todas as seções, polling enquanto o conteúdo não existe, estado de erro e apresentação do fallback.

## 3. Validar TTS em navegadores

**Arquivos principais:** `viz3d/src/ai/SpeechSynthesis.ts`, `viz3d/src/ai/AiPanel.tsx`, `viz3d/src/ai/AiEngineer.tsx`, `frontend/src/services/speech-synthesis.ts` e `frontend/src/components/race/ai/`.

- [ ] Testar em Chrome e Firefox disponíveis a voz `pt-BR` e os fallbacks instalados.
- [ ] Confirmar que a seleção de voz permanece coerente entre os painéis durante uma corrida real.
- [ ] Confirmar reprodução audível das mensagens, fila sem sobreposição e prioridade por urgência.
- [ ] Desligar o TTS durante a fala e reativá-lo, verificando interrupção imediata e ausência de backlog atrasado.
- [ ] Registrar navegador, voz utilizada, comportamento ouvido e resultado; não substituir essa validação por testes com mocks.

## 4. Fechar dependências e code-splitting do `viz3d`

**Arquivos principais:** `viz3d/package.json`, `viz3d/package-lock.json`, `viz3d/vite.config.ts`, `viz3d/src/main.tsx`, `viz3d/src/App.tsx` e `viz3d/src/live/LiveRace.tsx`.

- [ ] Executar `npm ci` no `viz3d` e alinhar o ambiente local aos manifestos; confirmar Vite 8.2.2 em vez da instalação local divergente 5.4.21.
- [ ] Separar React, Three e R3F, mantendo `App` e `LiveRace` sob carregamento lazy.
- [ ] Eliminar o chunk combinado de aplicação + Three de 925,80 kB; isolar e justificar explicitamente qualquer vendor que ainda ultrapasse 500 kB.
- [ ] Rodar build e testes de `frontend` e `viz3d` com as dependências alinhadas.
- [ ] Verificar navegação entre rotas e alternância 2D/3D após o lazy loading.

## 5. Concluir a validação da recuperação de corridas

**Arquivos principais:** `backend/engine/checkpoint.py`, `backend/api/race_manager.py`, `frontend/src/stores/live-race-store.ts`, `docker-compose.yml` e `compose.ha.yml`.

- [ ] Verificar se existem checkpoints v2 no Redis e removê-los de forma controlada ou implementar migração v2 → v3; não apagar checkpoints ativos indiscriminadamente.
- [ ] Executar o teste manual criar corrida → derrubar backend → reiniciar backend e confirmar que a engine volta a publicar ticks.
- [ ] Confirmar no frontend que os carros voltam a se mover e que as sugestões/comandos da IA continuam após o recovery.
- [ ] Testar recovery com viewers conectados e sem viewers, incluindo cancelamento após o grace period quando aplicável.
- [ ] Testar o modo HA com múltiplos backends: derrubar o owner e confirmar que outro assume sem duplicar a corrida.
- [ ] Em produção, definir um `F1_CHECKPOINT_SECRET` fixo por secrets manager/variável de ambiente e confirmar que ele não muda entre restarts.

## 6. Validação integrada final

- [ ] Executar uma corrida curta completa com Ollama, Redis, backend e frontends.
- [ ] Confirmar TTS durante a corrida e debrief real após `race_end` na mesma execução.
- [ ] Repetir a validação Docker integrada após as correções da UI do 3D e das demais frentes.
- [ ] Rodar as suítes de IA, os testes backend relacionados e os testes/builds dos dois frontends.
- [ ] Confirmar o pipeline completo no GitHub Actions, sem tratar avisos não bloqueantes como falhas.
- [ ] Registrar as evidências no handoff da sessão e remover deste arquivo apenas as pendências efetivamente concluídas.
