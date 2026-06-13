# Agentic RAG Pipeline

A production-ready Retrieval-Augmented Generation (RAG) system with an agentic loop. The LLM autonomously decides when to search the knowledge base, how many times, and with what queries — then synthesizes a grounded answer. Documents are ingested asynchronously into a pgvector-backed PostgreSQL store.

**Stack:** FastAPI · AsyncOpenAI · SQLAlchemy async · asyncpg · pgvector · React 19 · TypeScript · Redux Toolkit · Vite

---

## Architecture

```
frontend/           React + TypeScript SPA (Vite, RTK Query, React Router)
  Dockerfile.dev    Hot-reload dev server (Vite, port 5174)
  Dockerfile.prod   Multi-stage nginx build (port 80)

backend/            FastAPI async API
  Dockerfile.dev    uvicorn --reload (port 8002)
  Dockerfile.prod   uvicorn --workers 2, non-root user (port 8002)
  app/
    config.py       pydantic-settings, @lru_cache
    db/             Async SQLAlchemy engine + migrations
    models/         Pydantic request/response schemas
    services/
      chunker.py    File reading, PDF extraction, text chunking
      embeddings.py Async OpenAI embedding calls (batched)
      retrieval.py  pgvector similarity search + CRUD
      generation.py Async LLM completion + SSE streaming
      agent.py      Agentic loop — vector_search + list_documents tools
    routers/
      ingest.py     POST /ingest/local  (background task + job status)
      chat.py       POST /chat  |  POST /chat/stream (SSE)
      documents.py  GET/DELETE /documents

compose.yaml              Development (hot reload, volume mounts)
docker-compose.prod.yml   Production (compiled builds, persistent DB volume)
```

---

## Prerequisites

- Docker ≥ 24
- Node.js ≥ 20 + npm (for local-without-Docker frontend dev)
- Python ≥ 3.12 (for local-without-Docker backend dev)
- An OpenAI API key

---

## Quick start (development)

```bash
cp backend/.env.example backend/.env   # first time only — add your OPENAI_API_KEY
```

### Port conflicts

If any default port is already in use, override it with an environment variable (or add it to a root `.env` file):

```bash
BACKEND_PORT=8003 FRONTEND_PORT=5175 docker compose up --build

# Or create a root .env and uncomment the relevant lines (see .env.example)
```

---

## Production

```bash
cp backend/.env.example backend/.env   # if not done already
docker compose -f docker-compose.prod.yml up --build -d
```

| Service | URL |
|---------|-----|
| Frontend (nginx) | http://localhost:80 |
| Backend (uvicorn) | http://localhost:8002 |

Differences from dev:
- Frontend compiled to a static bundle served by nginx
- Backend runs with `--workers 2`, no `--reload`, non-root user
- Postgres data persisted in a named Docker volume (`postgres_data`)

---

## Run locally without Docker

### 1. Start Postgres

```bash
docker compose up postgres -d
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
uvicorn app.main:app --reload --port 8002
# Swagger UI: http://localhost:8002/docs
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# App: http://localhost:5173
```

The Vite dev server proxies `/api/*` → `http://localhost:8002` automatically.

---

## Docker — Backend only

```bash
cd backend

# Development (hot reload)
docker build -f Dockerfile.dev -t rag-backend:dev .
docker run -it --rm \
  -p 8002:8002 \
  -v "$(pwd)/app:/app/app" \
  --env-file .env \
  rag-backend:dev

# Production
docker build -f Dockerfile.prod -t rag-backend:prod .
docker run -d --rm \
  -p 8002:8002 \
  --env-file .env \
  rag-backend:prod
```

## Docker — Frontend only

```bash
cd frontend

# Development (hot reload)
docker build -f Dockerfile.dev -t rag-frontend:dev .
docker run -it --rm \
  -p 5174:5174 \
  -v "$(pwd)/src:/app/src" \
  rag-frontend:dev
# → http://localhost:5174
# The dev server expects the backend at http://localhost:8002.
# To override: docker run -e VITE_BACKEND_URL=http://myhost:8002 ...

# Production
docker build -f Dockerfile.prod -t rag-frontend:prod .
docker run -d --rm \
  -p 80:80 \
  -e NGINX_BACKEND_URL=http://localhost:8002 \
  rag-frontend:prod
# → http://localhost
```

---

## Environment variables

### `backend/.env`

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/ragdemo` | PostgreSQL connection string (overridden in compose) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `CHAT_MODEL` | `gpt-4o-mini` | OpenAI chat model |

### Root `.env` — compose port overrides (all optional)

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PORT` | `5432` | Host port for Postgres |
| `BACKEND_PORT` | `8002` | Host port for the backend |
| `FRONTEND_PORT` | `5174` | Host port for the dev frontend |
| `FRONTEND_PROD_PORT` | `80` | Host port for the prod frontend |

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest/local` | Start async ingestion job — returns `job_id` |
| `GET` | `/ingest/jobs/{job_id}` | Poll ingestion job status |
| `POST` | `/chat` | Agentic RAG chat (full JSON response) |
| `POST` | `/chat/stream` | Server-Sent Events streaming chat |
| `GET` | `/documents` | List indexed document paths |
| `DELETE` | `/documents/{path}` | Remove all chunks for a document |
| `GET` | `/health` | Health check |

### Ingest example

```bash
curl -X POST http://localhost:8002/ingest/local \
  -H "Content-Type: application/json" \
  -d '{"directory": "/path/to/docs", "patterns": ["*.md", "*.txt", "*.pdf"]}'
# → {"status": "accepted", "job_id": "abc123..."}

curl http://localhost:8002/ingest/jobs/abc123...
# → {"status": "complete", "files_indexed": 5, "chunks_stored": 42}
```

### Chat example

```bash
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What does this project do?", "top_k": 5}'
# → {"answer": "...", "sources": [...], "tool_calls": [...]}
```

---

## Production deployment (cloud)

Frontend and backend are **independently deployable** — neither references the other at build time.

```bash
# Build and push
docker build -f backend/Dockerfile.prod  -t ghcr.io/<org>/rag-backend:latest  ./backend
docker build -f frontend/Dockerfile.prod -t ghcr.io/<org>/rag-frontend:latest ./frontend
docker push ghcr.io/<org>/rag-backend:latest
docker push ghcr.io/<org>/rag-frontend:latest
```

- **Backend** — deploy to ECS, Cloud Run, Fly.io, or Kubernetes. Set `OPENAI_API_KEY` and `DATABASE_URL` as secrets.
- **Frontend** — deploy the nginx container, setting `NGINX_BACKEND_URL` to the backend's public URL; or build with `VITE_API_URL=https://api.yourdomain.com npm run build` and host the `dist/` folder on any static CDN.
- Add your frontend domain to the `allow_origins` list in `backend/app/main.py` if deploying them on different domains.

---

## License

MIT
