#!/bin/bash
/bin/git config --global --add safe.directory /app/repository
/usr/local/bin/python3 webhook_server.py