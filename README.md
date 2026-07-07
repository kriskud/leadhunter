# LeadHunter

Automated lead search and qualification pipeline for web development, CRM, and automation services.

## Stack

- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0
- Alembic
- Playwright
- Docker Compose

## Project Structure

```
leadhunter/
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── app/
│   ├── api/
│   │   ├── health.py
│   │   └── leads.py
│   ├── collector/
│   ├── config/
│   │   ├── scoring_rules.json
│   │   └── settings.py
│   ├── database/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── session.py
│   ├── enricher/
│   ├── message_builder/
│   ├── qualifier/
│   ├── scorer/
│   ├── services/
│   │   └── openrouter.py
│   ├── workers/
│   └── main.py
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── pyproject.toml
├── requirements.txt
└── .env.example
```

## Quick Start

### 1. Clone and configure

```bash
cd leadhunter
cp .env.example .env
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs  
Health: http://localhost:8000/api/v1/health

### 3. Local development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Start PostgreSQL locally or via Docker:
docker compose up db -d

cp .env.example .env
# Set POSTGRES_HOST=localhost in .env

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Alembic Commands

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration (after model changes)
alembic revision --autogenerate -m "describe change"

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

Via Docker:

```bash
docker compose run --rm migrate
docker compose exec api alembic current
```

## Pipeline Modules

| Module | Function | Status |
|--------|----------|--------|
| `collector` | `collect_leads()` | Stub |
| `enricher` | `enrich_lead()` | Stub |
| `qualifier` | `qualify_lead()` | Stub |
| `scorer` | `score_lead()` | Stub |
| `message_builder` | `generate_message()` | Stub |
| `workers` | Pipeline workers | Stub |

## API Endpoints

- `GET /api/v1/health` — health check with DB status
- `GET /api/v1/leads` — list leads
- `GET /api/v1/leads/{id}` — get lead by ID

## Configuration

- `.env` — environment variables (see `.env.example`)
- `app/config/scoring_rules.json` — scoring weights for future implementation
- OpenRouter settings prepared in `.env` and `app/services/openrouter.py` (not implemented)

## Lead Status Flow

```
NEW → ENRICHED → QUALIFIED → SCORED → MESSAGE_GENERATED
                                      ↘ REJECTED
```
