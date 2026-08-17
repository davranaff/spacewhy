#!/bin/sh
set -eu

python scripts/prestart.py
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers
