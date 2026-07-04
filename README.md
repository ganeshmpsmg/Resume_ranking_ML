# 📋 AI-Powered Resume Ranking System

> Production-grade, internship-ready resume screening system using **Sentence-BERT semantic embeddings**, **hybrid BM25 + ChromaDB vector search**, **PostgreSQL persistence**, **Redis caching**, and a **LangChain/OpenAI bonus feedback feature** — served via **FastAPI** with a **Streamlit** dashboard frontend.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend (8501)                    │
│  Home | Rank & Dashboard | Candidate Profile | Evaluation |      │
│  Compare | AI Feedback (LLM)                                     │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP REST
┌───────────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend (8000)                         │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  /resumes  │  │     /jds     │  │  /ranking    │             │
│  └────────────┘  └──────────────┘  └──────────────┘             │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ /feedback  │  │ /evaluation  │  │   /health    │             │
│  └────────────┘  └──────────────┘  └──────────────┘             │
│                                                                  │
│  Services:  Parser · SkillExtractor · JDProcessor               │
│             EmbeddingService (SBERT) · HybridSearch             │
│             RankingEngine · RecommendationEngine                │
│             LLMService (LangChain+OpenAI) · CacheService        │
└───────┬──────────────────┬────────────────────┬─────────────────┘
        │                  │                    │
 ┌──────▼──────┐   ┌───────▼──────┐   ┌────────▼───────┐
 │ PostgreSQL  │   │    Redis     │   │   ChromaDB     │
 │  (ORM data) │   │   (cache)    │   │ (embeddings)   │
 └─────────────┘   └──────────────┘   └────────────────┘
```

---

## 🚀 Ranking Formula

```
Final Score = 0.40 × Semantic Similarity   (SBERT + Chroma/BM25 hybrid)
            + 0.25 × Skill Match            (taxonomy dictionary overlap)
            + 0.20 × Experience Match       (years vs JD requirement)
            + 0.10 × Education Match        (degree level rank)
            + 0.05 × Project Relevance      (projects section vs JD embedding)
```

Weights are user-adjustable in the UI. Hybrid search uses **Reciprocal Rank Fusion (RRF)** to merge ChromaDB vector results and BM25 keyword results.

---

## 📁 Folder Structure

```
ResumeRankingSystem/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI route handlers
│   │   │   ├── health.py        # GET /health
│   │   │   ├── resumes.py       # POST /resumes/upload, GET/DELETE /resumes
│   │   │   ├── job_descriptions.py  # POST /jds, GET/DELETE /jds
│   │   │   ├── ranking.py       # POST /ranking/rank, GET /ranking/{id}
│   │   │   ├── feedback.py      # GET /feedback/{rid}/{jdid}, POST /feedback/llm
│   │   │   └── evaluation.py    # POST /evaluation/metrics, /evaluation/compare
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings — all env vars
│   │   │   ├── logging_config.py # Structured JSON logging
│   │   │   └── taxonomy.py      # Skill taxonomy + education ranks
│   │   ├── db/
│   │   │   └── session.py       # SQLAlchemy engine + get_db() dependency
│   │   ├── models/
│   │   │   └── orm_models.py    # Resume, JobDescription, RankingJob, RankingResult, Feedback
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic v2 request/response models
│   │   ├── services/
│   │   │   ├── parser_service.py       # PDF/DOCX/TXT text extraction + field detection
│   │   │   ├── skill_service.py        # Regex+taxonomy skill extraction + match scoring
│   │   │   ├── jd_service.py           # Job description processor
│   │   │   ├── embedding_service.py    # SBERT singleton + batch encode
│   │   │   ├── search_service.py       # ChromaDB + BM25 + RRF hybrid search
│   │   │   ├── cache_service.py        # Redis cache (ranking + feedback)
│   │   │   ├── ranking_service.py      # Multi-factor weighted ranking engine
│   │   │   ├── recommendation_service.py  # ATS score + rule-based feedback
│   │   │   ├── llm_service.py          # LangChain + OpenAI feedback (bonus)
│   │   │   └── evaluation_service.py   # Precision@K, Recall@K, MRR
│   │   ├── utils/
│   │   │   └── text_utils.py    # Regex patterns, text cleaning helpers
│   │   └── main.py              # FastAPI app factory + lifespan startup
│   ├── alembic/                 # DB migrations
│   ├── data/
│   │   ├── sample_resumes/      # 5 sample resume .txt files
│   │   └── sample_jds/          # 2 sample job description .txt files
│   ├── tests/
│   │   └── test_services.py     # 45 unit tests (parser, skills, ranking, eval)
│   ├── Dockerfile
│   ├── requirements.txt         # Python 3.12.10 pinned deps
│   ├── alembic.ini
│   └── .env.example
├── frontend/
│   ├── app.py                   # Main Streamlit entry point + navigation
│   ├── pages/
│   │   ├── home.py              # Upload resumes & JDs
│   │   ├── dashboard.py         # Rank, view results, analytics charts
│   │   ├── profile.py           # Candidate deep-dive + ATS feedback
│   │   ├── evaluation.py        # Precision@K / Recall@K / MRR evaluation
│   │   ├── compare.py           # Resume vs Resume comparison
│   │   └── llm_feedback.py      # LangChain/OpenAI AI feedback (bonus)
│   ├── components/
│   │   └── ui_components.py     # Reusable HTML components, CSS injection
│   ├── services/
│   │   └── api_client.py        # Typed HTTP client for all backend calls
│   ├── utils/
│   │   └── charts.py            # Plotly chart builders
│   ├── Dockerfile
│   └── requirements.txt
├── docs/
│   └── DEPLOYMENT.md            # Full deployment guide (Docker, Render, Streamlit Cloud)
├── docker-compose.yml           # Postgres + Redis + Backend + Frontend
└── README.md
```

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/yourname/ResumeRankingSystem.git
cd ResumeRankingSystem

# 2. Configure
cp backend/.env.example backend/.env
# Optionally add OPENAI_API_KEY for LLM feedback

# 3. Start everything
docker compose up --build -d

# 4. Check health
curl http://localhost:8000/health

# 5. Open dashboard
open http://localhost:8501
```

---

## 🧪 Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
# 45 tests covering: Parser, Skill Extraction, JD Processing,
# Ranking Components, Evaluation Metrics, Recommendation Engine
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health — DB, Redis, Chroma, SBERT |
| `POST` | `/api/v1/resumes/upload` | Upload PDF/DOCX/TXT resumes |
| `GET` | `/api/v1/resumes` | List all stored resumes |
| `GET` | `/api/v1/resumes/{id}` | Get full resume detail |
| `DELETE` | `/api/v1/resumes/{id}` | Delete a resume |
| `POST` | `/api/v1/jds` | Create JD from pasted text |
| `POST` | `/api/v1/jds/upload` | Create JD from file upload |
| `GET` | `/api/v1/jds` | List all JDs |
| `POST` | `/api/v1/ranking/rank` | **Rank resumes against a JD** |
| `GET` | `/api/v1/ranking/{id}` | Retrieve past ranking result |
| `GET` | `/api/v1/feedback/{rid}/{jdid}` | Rule-based ATS feedback |
| `POST` | `/api/v1/feedback/llm` | LLM-enhanced feedback (bonus) |
| `POST` | `/api/v1/evaluation/metrics` | Precision@K / Recall@K / MRR |
| `POST` | `/api/v1/evaluation/compare` | Side-by-side resume comparison |

Full interactive docs: **http://localhost:8000/docs**

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Semantic Search** | Sentence-BERT `all-MiniLM-L6-v2` |
| **Vector DB** | ChromaDB 0.5.23 (persistent, cosine similarity) |
| **Keyword Search** | BM25Okapi (rank-bm25) |
| **Search Fusion** | Reciprocal Rank Fusion (RRF) |
| **Backend Framework** | FastAPI 0.115+ with async lifespan |
| **Data Validation** | Pydantic v2 + pydantic-settings |
| **ORM** | SQLAlchemy 2.0 + Alembic migrations |
| **Database** | PostgreSQL 16 |
| **Cache** | Redis 7 |
| **LLM (bonus)** | LangChain + OpenAI GPT-4o-mini |
| **Resume Parsing** | PyMuPDF + pdfplumber + python-docx |
| **NLP** | spaCy + custom skill taxonomy (5 categories, 100+ skills) |
| **Frontend** | Streamlit 1.45+ |
| **Charts** | Plotly |
| **Containerization** | Docker + Docker Compose |
| **Python** | 3.12.10 |

---

## 📊 Evaluation Metrics

- **Precision@K** — fraction of top-K ranked resumes that are truly relevant
- **Recall@K** — fraction of all relevant resumes captured in top-K
- **MRR** — Mean Reciprocal Rank of first relevant result
- **Avg Cosine Similarity** — mean semantic similarity across all candidates

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Multi-format parsing** | PDF (PyMuPDF + pdfplumber fallback), DOCX (table-aware), TXT |
| **Hybrid search** | ChromaDB vector + BM25 keyword, fused via RRF |
| **Adjustable weights** | All 5 scoring components tunable in the UI |
| **Redis caching** | Ranking results and feedback cached with configurable TTL |
| **Postgres persistence** | All resumes, JDs, ranking jobs, and results persisted |
| **ATS score prediction** | Rule-based heuristic score (0–100) with breakdown |
| **LLM feedback (bonus)** | LangChain + OpenAI GPT for AI-generated resume suggestions |
| **Resume comparison** | Side-by-side skill and score comparison between any two candidates |
| **Skill gap analysis** | JD required skills vs candidate pool coverage visualization |
| **Export** | Download full ranking report as CSV |

---

## 🔑 Skills Taxonomy (5 Categories)

- **Programming Languages** — Python, Java, C++, JavaScript, TypeScript, Go, Rust, R, SQL, ...
- **Machine Learning / AI** — PyTorch, TensorFlow, BERT, Hugging Face, LangChain, RAG, spaCy, ...
- **Cloud / DevOps** — AWS, GCP, Azure, Docker, Kubernetes, Terraform, CI/CD, ...
- **Databases** — PostgreSQL, MongoDB, Redis, ChromaDB, Elasticsearch, Snowflake, ...
- **Tools / Frameworks** — FastAPI, Streamlit, Flask, Pandas, NumPy, Plotly, Airflow, ...

---

## 👨‍💻 Author

Built as an internship-ready, production-level ML portfolio project.  
Suitable for showcasing at **ML / NLP / Data Science** interviews.

**GitHub** | **LinkedIn** | **Resume**
