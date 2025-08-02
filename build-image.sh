#!/bin/bash

docker build \
  --no-cache \
  -t git_webhook:latest .

# docker login
docker tag git_webhook:latest zmutclik/git_webhook:latest
docker push zmutclik/git_webhook:latest