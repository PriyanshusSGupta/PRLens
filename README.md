# PRLens

**PRLens is a GitHub pull request reviewer that combines rule-based checks, LLM reasoning, and risk scoring to surface the most important issues before human review.**

## Quick Start

```
# 1. Clone and set up
git clone https://github.com/your-org/prlens
cd prlens
cp .env.example .env
scripts/generate-keys.sh     # generates JWT_SECRET and ENCRYPTION_KEY

# 2. Register a GitHub OAuth App
#    Go to: https://github.com/settings/developers
#    Set callback URL: http://localhost:8000/api/auth/github/callback
#    Copy Client ID → GITHUB_CLIENT_ID and Client Secret → GITHUB_CLIENT_SECRET in .env

# 3. Start the stack
docker compose -f infra/docker-compose.yml up --build

# 4. Open http://localhost:3000 and connect GitHub
```

## What It Does

- **Connects to GitHub** via OAuth — reads PR diffs and posts review comments
- **Runs rule-based analyzers** for security, reliability, performance, and testing gaps
- **Optionally uses your own AI key** (OpenAI, Claude, Grok, Grok, DeepSeek, Kimi, Gemini, or custom) for semantic review
- **Computes a risk score** per PR (0–100%) from severity-weighted findings
- **Persists everything** — PRs, findings, review runs — in PostgreSQL
- **Evaluates accuracy** against ground-truth annotations to measure precision and false positive rate

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌────────────┐
│  Browser │────▶│   Frontend   │────▶│  Backend   │
│ (React)  │     │  (nginx)     │     │ (FastAPI)  │
└──────────┘     └──────────────┘     └─────┬──────┘
                                            │
                         ┌──────────────────┼──────────────────┐
                         ▼                  ▼                  ▼
                  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
                  │  GitHub API │   │  PostgreSQL │   │  LLM (your  │
                  │  (PRs/diff) │   │  (storage)  │   │  API key)   │
                  └─────────────┘   └─────────────┘   └─────────────┘
```

## Security

- **Tokens encrypted at rest** with AES-256-GCM (key from ENCRYPTION_KEY env var, never in code)
- **Sessions signed** with HS256 JWT stored in httpOnly cookies
- **OAuth CSRF protection** via state parameter
- **Minimal GitHub scopes**: `repo:status` (read PR metadata), `pull_requests:read` (read diffs)
- **Revoke anytime**: GitHub Settings → Applications → Authorized OAuth Apps → Revoke
- **Your data lives on your machine** — PostgreSQL instance you control

For full details, see [docs/SECURITY.md](docs/SECURITY.md).

## AI Provider Integration

PRLens **does not ship with an AI key**. You bring your own:

| Provider | Setup Time | Model Examples |
|---|---|---|
| **OpenAI** | [Get key](https://platform.openai.com/api-keys) | gpt-4o, gpt-4-turbo |
| **Anthropic (Claude)** | [Get key](https://console.anthropic.com/settings/keys) | claude-3-5-sonnet-latest |
| **Groq** | [Get key](https://console.groq.com/keys) | llama-3.3-70b |
| **xAI (Grok)** | [Get key](https://x.ai/api) | grok-2-latest |
| **DeepSeek** | [Get key](https://platform.deepseek.com/api_keys) | deepseek-chat |
| **Moonshot (Kimi)** | [Get key](https://platform.moonshot.cn/console/api-keys) | moonshot-v1-8k |
| **Google (Gemini)** | [Get key](https://aistudio.google.com/apikey) | gemini-2.0-flash |
| **Custom** | Any OpenAI-compatible endpoint | any |

Go to **AI Settings** (gear icon in navbar) after signing in. Your API key is encrypted in the database and never leaves your server except to call the provider's API.

## Evaluation

PRLens can evaluate review quality against ground-truth annotations:

- **Precision**: what fraction of flagged issues are real problems
- **False Positive Rate**: what fraction of flags are noise
- **Coverage**: what fraction of known issues were caught

Create ground-truth datasets by annotating PRs with expected findings, then run evaluations via the `/evaluations` page.

## Configuration

All settings via environment variables:

| Variable | Default | Description |
|---|---|---|
| `GITHUB_CLIENT_ID` | — | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | — | GitHub OAuth App client secret |
| `JWT_SECRET` | — | Session token signing key (64 random chars) |
| `ENCRYPTION_KEY` | — | AES-256 key for token encryption (base64 32 bytes) |
| `DATABASE_URL` | postgresql://... | PostgreSQL connection string |
| `LLM_API_KEY` | — | Global fallback AI key (users can set their own) |
| `LLM_MODEL` | gpt-4o | Global fallback model |
| `APP_BASE_URL` | http://localhost:8000 | Backend URL for OAuth redirects |
| `FRONTEND_URL` | http://localhost:5173 | Frontend URL for CORS |
| `ENABLE_LLM` | false | Enable LLM-based review |
| `SEVERITY_THRESHOLD_BLOCK` | critical | Minimum severity to report |
| `MIN_CONFIDENCE` | 0.3 | Minimum confidence to report a finding |

## Contributing

1. Fork, create a feature branch
2. Follow existing code style
3. Add tests for new functionality
4. Open a PR with a clear description

## License

MIT — see [LICENSE](LICENSE).
