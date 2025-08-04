FROM python:3.11-slim
ENV BRANCH=main
ENV REPO_PATH="/app/repository"
WORKDIR /app
COPY requirements.txt .
COPY webhook_server.py .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update \
    && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*
EXPOSE 8000
CMD [ "python3","webhook_server.py" ]