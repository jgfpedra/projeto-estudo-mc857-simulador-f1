# pybullet não publica wheel no PyPI: usa a imagem full (buildpack-deps, com
# g++) para compilar o sdist. A slim não tem compilador e quebra o build.
FROM python:3.11
WORKDIR /app/backend
ENV PYTHONPATH=/app/backend:/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
ENTRYPOINT ["sh", "/app/backend/docker-entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
