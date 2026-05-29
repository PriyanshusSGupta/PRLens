#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ -d .venv ]; then
    source .venv/bin/activate
fi

alembic upgrade head
