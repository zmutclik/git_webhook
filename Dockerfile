FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY webhook_server.py .
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
EXPOSE 8000
CMD ["python3", "webhook_server.py"]