#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== PRLens Key Generator ==="
echo ""
echo "Copy these into your .env file:"
echo ""

JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
ENCRYPTION_KEY=$(python3 -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())")

echo "JWT_SECRET=$JWT_SECRET"
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"
echo ""
echo "Security: JWT_SECRET signs session tokens. ENCRYPTION_KEY encrypts OAuth tokens at rest."
echo "Keep these values secret. Do not commit them to version control."
