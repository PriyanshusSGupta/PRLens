#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ -d .venv ]; then
    source .venv/bin/activate
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
