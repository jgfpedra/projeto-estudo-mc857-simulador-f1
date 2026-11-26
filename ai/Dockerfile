FROM ollama/ollama:latest

# Porta padrão da API do Ollama
EXPOSE 11434

# Sobe o servidor e, na primeira execução, baixa o modelo
ENTRYPOINT ["/bin/sh", "-c", "\
  ollama serve & \
  sleep 3 && \
  ollama pull llama3.2 && \
  wait"]
