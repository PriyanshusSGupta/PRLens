#!/usr/bin/env bash
set -euo pipefail

# Render build script for PRLens backend
cd backend
uv pip install --system -r pyproject.toml
