FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir 'redis>=5,<7' 'requests>=2.32,<3'
COPY app/ /app/
ENV PYTHONUNBUFFERED=1
CMD ["python", "consumer.py"]
