FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir piper-tts==1.4.1 fastapi uvicorn
RUN mkdir /voices && python -m piper.download_voices --data-dir /voices pt_BR-faber-medium
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
