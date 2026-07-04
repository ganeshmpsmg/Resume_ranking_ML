# Deployment Guide — Resume Ranking System

## Architecture

```
┌─────────────────────┐        HTTP / REST        ┌──────────────────────┐
│  Streamlit Frontend │  ────────────────────────▶ │  FastAPI Backend     │
│  (port 8501)        │                            │  (port 8000)         │
└─────────────────────┘                            └──────────┬───────────┘
                                                              │
                          ┌───────────────────────────────────┼───────────────────────────────┐
                          │                                   │                               │
                   ┌──────▼──────┐                   ┌───────▼──────┐              ┌─────────▼──────┐
                   │  PostgreSQL │                   │   Redis      │              │  ChromaDB      │
                   │  (port 5432)│                   │  (port 6379) │              │  (on-disk)     │
                   └─────────────┘                   └──────────────┘              └────────────────┘
```

---

## Option 1 — Docker Compose (Recommended)

### Prerequisites
- Docker ≥ 24.x
- Docker Compose ≥ 2.x
- 4 GB RAM minimum (SBERT model loads ~500 MB)

### Steps

```bash
# 1. Clone / enter project
cd ResumeRankingSystem

# 2. Copy env and set OpenAI key (optional — only for LLM feedback feature)
cp backend/.env.example backend/.env
# edit backend/.env and set OPENAI_API_KEY=sk-... if needed

# 3. Build and start all services
docker compose up --build -d

# 4. Verify all services healthy
docker compose ps
curl http://localhost:8000/health

# 5. Open the dashboard
open http://localhost:8501
```

### Useful Commands

```bash
# View backend logs
docker compose logs -f backend

# Run DB migrations (Alembic)
docker compose exec backend alembic upgrade head

# Rebuild after code changes
docker compose up --build backend

# Stop everything
docker compose down

# Full reset (wipes all data)
docker compose down -v
```

---

## Option 2 — Local Development (No Docker)

### Prerequisites
- Python 3.12.10
- PostgreSQL 16 running locally
- Redis 7 running locally

### Backend setup

```bash
cd backend

# Create virtualenv
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# Edit .env — set your Postgres/Redis credentials

# Run DB migrations
alembic upgrade head

# Start backend (with hot-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend setup (new terminal)

```bash
cd frontend

pip install -r requirements.txt

# Point frontend at the backend
export API_BASE_URL=http://localhost:8000   # Windows: set API_BASE_URL=...

streamlit run app.py
```

Backend API docs: http://localhost:8000/docs
Frontend:         http://localhost:8501

---

## Option 3 — Streamlit Cloud + Render

### Backend → Render (FastAPI)

1. Push `backend/` to a GitHub repo.
2. Create a new **Web Service** on [render.com](https://render.com).
3. Set **Build command:** `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
4. Set **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add all env vars from `.env.example` in the Render Environment tab.
6. Provision a **Render Postgres** and **Render Redis** add-on; paste their URLs as `DATABASE_URL` and `REDIS_URL`.

### Frontend → Streamlit Cloud

1. Push `frontend/` to a GitHub repo (or a subfolder of the same repo).
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app.
3. Set **Main file path:** `frontend/app.py`
4. Add secret: `API_BASE_URL = https://your-render-service.onrender.com`

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | Postgres host |
| `POSTGRES_PORT` | `5432` | Postgres port |
| `POSTGRES_USER` | `resume_user` | Postgres user |
| `POSTGRES_PASSWORD` | `resume_pass` | Postgres password |
| `POSTGRES_DB` | `resume_ranking` | Database name |
| `DATABASE_URL` | _(auto-built)_ | Full SQLAlchemy URL (overrides above) |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_URL` | _(auto-built)_ | Full Redis URL (overrides above) |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | ChromaDB persistence path |
| `SBERT_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence-BERT model |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI key — enables `/feedback/llm` |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `HYBRID_VECTOR_WEIGHT` | `0.7` | Weight for vector search in RRF fusion |
| `HYBRID_BM25_WEIGHT` | `0.3` | Weight for BM25 in RRF fusion |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache TTL |
| `MAX_UPLOAD_MB` | `10` | Max resume file size |

---

## Production Checklist

- [ ] Set `APP_ENV=production` and `DEBUG=false`
- [ ] Use strong Postgres and Redis passwords
- [ ] Run `alembic upgrade head` before first deploy
- [ ] Set `OPENAI_API_KEY` only if using the LLM feedback endpoint
- [ ] Mount a persistent volume for `CHROMA_PERSIST_DIR`
- [ ] Add HTTPS termination (Nginx / Render / Cloudflare) in front of both services
- [ ] Enable Postgres connection pooling (PgBouncer) for high traffic
