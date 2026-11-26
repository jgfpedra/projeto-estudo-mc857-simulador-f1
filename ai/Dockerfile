# AI race engineer listener.
#
# Runs the Python listener that subscribes to the engine's Redis pub/sub and
# publishes `ai_suggestion` events back on `race:<id>:events`. The Ollama model
# server lives in the `llama` service; this container only talks to it over
# HTTP (see OLLAMA_URL in docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/app

# Wheels for numpy/pandas are available for this platform, so no compiler is
# needed. Keep the image small and reproducible.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["python", "app/redis_listener.py"]
