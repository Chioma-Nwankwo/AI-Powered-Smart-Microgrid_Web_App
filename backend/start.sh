#!/usr/bin/env bash
# Render start script — explicit flags override any gunicorn.conf.py ambiguity.
# Set in Render dashboard: Start Command = bash backend/start.sh
exec gunicorn app:app \
  --chdir backend \
  --timeout 120 \
  --workers 1 \
  --bind "0.0.0.0:${PORT:-10000}"
