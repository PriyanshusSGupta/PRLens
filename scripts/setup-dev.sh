#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Generate keys if .env missing
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "=== IMPORTANT: Generate encryption keys ==="
    scripts/generate-keys.sh
    echo ""
    echo "=== IMPORTANT: Register a GitHub OAuth App ==="
    echo "1. Go to https://github.com/settings/developers"
    echo "2. Click 'New OAuth App'"
    echo "3. Set Homepage URL: http://localhost:5173"
    echo "4. Set Authorization callback URL: http://localhost:8000/api/auth/github/callback"
    echo "5. Copy Client ID and Client Secret into .env"
    echo ""
fi

# Backend
echo "Installing backend dependencies..."
cd backend
uv sync
cd ..

# Frontend
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "Setup complete. Start services with:"
echo "  docker compose -f infra/docker-compose.yml up --build"
echo "  # or manually:"
echo "  scripts/run-backend.sh"
echo "  scripts/run-frontend.sh"
