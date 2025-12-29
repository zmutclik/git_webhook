#!/bin/bash

docker build \
  --no-cache \
  -t zmutclik/git_webhook:latest .

# docker login
docker push zmutclik/git_webhook:latest