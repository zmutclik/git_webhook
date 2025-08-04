FROM python:3.11-slim
ENV BRANCH=main
ENV REPO_PATH="/app/repository"
WORKDIR /app
COPY webhook_func.py .
COPY requirements.txt .
COPY webhook_server.py .
COPY webhook_models.py .
COPY setup_ssh_keys.sh .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get update \
    && apt-get install -y git curl jq nano \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p secrets \
    && chmod -R 600 secrets \
    && mkdir -p repository \
    && chmod -R 700 repository \
    && mkdir -p /root/.ssh \
    && chmod 700 /root/.ssh 
COPY ssh-config/config /root/.ssh/config
RUN chmod 600 /root/.ssh/config 
EXPOSE 7000
CMD [ "python3","webhook_server.py" ]