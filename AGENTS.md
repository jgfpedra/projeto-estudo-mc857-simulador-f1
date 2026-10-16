# Regras de Memória (ai-memory)

Este projeto utiliza o servidor ai-memory via MCP para persistência de contexto e handoffs entre sessões.

## Protocolo de Uso

1. **Início da Sessão / Tarefa:**
   - Antes de assumir premissas sobre a arquitetura ou decisões passadas, consulte o histórico via `memory_search` ou reivindique handoffs pendentes.
2. **Durante a Execução:**
   - Armazene fatos duráveis (decisões de design, convenções de código adotadas, dependências alteradas). Não salve logs brutos ou segredos.
3. **Fim da Sessão / Transição:**
   - Execute o registro de encerramento (`memory_handoff_begin`) descrevendo:
     - O que foi concluído.
     - O que falhou ou permaneceu aberto.
     - Próximos passos recomendados.
