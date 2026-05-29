# Technology Stack

**Analysis Date:** 2026-05-29

## Languages

**Primary:**
- **Python 3.11+** - Backend (FastAPI app, async SQLAlchemy, LLM client, GitHub client)
- **TypeScript 5.7** - Frontend (React 18, strict mode enabled)

**Secondary:**
- **CSS** - Design tokens via `tokens.css`, Tailwind utility classes for layout only
- **Shell** - Dev setup scripts (`scripts/setup-dev.sh`, `scripts/run-backend.sh`, `scripts/run-frontend.sh`)

## Runtime

**Backend Environment:**
- **Python 3.11+** via `python:3.11-slim` Docker image
- Package manager: **uv** (Rust-based Python package manager)
- Lockfile: `backend/uv.lock` present
- ASGI server: **uvicorn** (`uvicorn[standard]>=0.34.0`)

**Frontend Environment:**
- **Node.js 18** via `node:18-alpine` Docker image (build only)
- Package manager: **npm** with `package-lock.json` (lockfile committed)
- Bundler: **Vite 6** with `@vitejs/plugin-react`
- Production: Served via **nginx:alpine** (static files)

## Frameworks

**Core Backend:**
- **FastAPI 0.115+** - Async web framework with automatic OpenAPI docs at `/docs` and `/redoc`
- **SQLAlchemy 2.0.36+** (async) - ORM with `asyncio` extension, `DeclarativeBase`
- **Pydantic 2.10+** / **pydantic-settings 2.7+** - Data validation and settings management via `BaseSettings`
- **Alembic 1.14+** - Migrations (installed but not used in dev — `create_all` on startup)

**Testing:**
- Backend: Not detected (no test framework in `pyproject.toml` dependencies)
- Frontend: Not detected (no test libraries in `package.json`)

**Build/Dev:**
- **uvicorn** with hot-reload for backend development
- **Vite 6** dev server on port 5173 with proxy to backend at `localhost:8000`
- **Tailwind CSS 3.4** with PostCSS and Autoprefixer for frontend styling

## Key Dependencies

**Backend Critical:**
| Package | Version | Why It Matters |
|---|---|---|
| `fastapi` | >=0.115.0 | Core web framework, route handling, middleware |
| `sqlalchemy[asyncio]` | >=2.0.36 | Async ORM with `async_sessionmaker` |
| `aiosqlite` | >=0.22.0 | SQLite async driver (dev default) |
| `asyncpg` | >=0.30.0 | PostgreSQL async driver (production) |
| `httpx` | >=0.28.0 | Async HTTP client for GitHub API, LLM APIs, OAuth flows |
| `pyjwt` | >=2.13.0 | JWT session token encoding/decoding (HS256) |
| `cryptography` | >=44.0.0 | AES-256-GCM encryption for stored OAuth tokens and AI keys |
| `passlib[bcrypt]` | >=1.7.0 | Password hashing with bcrypt |
| `slowapi` | >=0.1.9 | Rate limiting middleware (200 req/min default) |
| `cachetools` | >=5.5.0 | In-memory TTL caches for OAuth states and exchange tokens |
| `pydantic[email]` | >=2.10.0 | Validation including EmailStr type |
| `python-dotenv` | >=1.0.0 | `.env` file loading |

**Frontend Critical:**
| Package | Version | Why It Matters |
|---|---|---|
| `react` | ^18.3.1 | UI rendering |
| `react-dom` | ^18.3.1 | DOM bindings |
| `react-router-dom` | ^6.28.0 | Client-side routing (7 routes) |
| `axios` | ^1.7.9 | HTTP client with `withCredentials: true` for cookie-based auth |
| `typescript` | ^5.7.2 | Type checking (`strict: true`) |
| `vite` | ^6.0.3 | Build tool and dev server |
| `tailwindcss` | ^3.4.16 | Utility CSS framework (layout only, no color classes) |

## Configuration

**Environment:**
- Single `.env` file at project root, loaded by `pydantic-settings` (`backend/app/core/config.py`)
- Frontend uses Vite proxy to backend — no frontend env vars needed
- Backend config class: `Settings` in `backend/app/core/config.py` with typed fields and defaults

**Required env vars:**
```
JWT_SECRET, ENCRYPTION_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
```
(All others have sensible defaults or are optional)

**Build:**
- `backend/pyproject.toml` — Python project definition and dependencies
- `frontend/package.json` — Node project definition and dependencies
- `frontend/tsconfig.json` — TypeScript strict mode config
- `frontend/vite.config.ts` — Vite bundler config with proxy to backend
- `frontend/tailwind.config.js` — Tailwind design token mapping
- `frontend/postcss.config.js` — PostCSS with Tailwind and Autoprefixer
- `infra/docker-compose.yml` — Production/CI container orchestration
- `infra/docker/Dockerfile.backend` — Python 3.11-slim + uv multi-stage
- `infra/docker/Dockerfile.frontend` — Node 18 build + nginx serve

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js 18+
- uv (`pip install uv`)
- SQLite (default) or PostgreSQL 16
- Run `. scripts/setup-dev.sh` for first-time setup

**Production:**
- Docker and Docker Compose
- PostgreSQL 16 (production only)
- Reverse proxy / TLS termination for `https://`

---

*Stack analysis: 2026-05-29*
