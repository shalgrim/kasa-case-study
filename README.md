# Kasa Reputation Dashboard

A web-based dashboard that aggregates hotel review data across Google, TripAdvisor, Expedia, and Booking.com — built as a case study for Kasa's AI Solutions Engineer role.

**Live demo:** [Frontend](https://kasa-case-study.vercel.app) · [API health check](https://kasa-case-study.onrender.com/api/health)
*(Render backend may cold-start on first request — allow 30-60s)*

## What It Does

- **Import hotel data** from a multi-source CSV with scores and review counts across four OTA channels
- **Normalize scores** to a common 0-10 scale and compute weighted averages
- **Browse and search** hotels in a sortable, color-coded table (green ≥8, yellow 6-8, red <6)
- **Drill into hotel detail** with bar charts, radar charts, and snapshot history
- **Organize hotels into groups** for portfolio comparison and CSV export
- **Collect live reviews** from Google (SerpAPI), TripAdvisor (Content API), Booking.com (Apify), and Expedia (Apify)
- **Create hotels manually** when they aren't in the CSV

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, SQLAlchemy, python-jose (JWT), bcrypt |
| Frontend | React (TypeScript), Vite, Tailwind CSS, Recharts |
| Database | SQLite (dev), PostgreSQL (prod via Render) |
| Deployment | Render (backend + DB), Vercel (frontend) |
| Scraping | Apify (apify-client) for Booking.com + Expedia |
| Testing | pytest (43 backend tests), in-memory SQLite with StaticPool |

## Architecture

```
┌─────────────┐       ┌────────────────────────-──────────┐
│   Vercel    │       │         Render                    │
│   (React)   │──────▶│  FastAPI  ──▶  PostgreSQL         │
│             │  JWT  │     │                             │
└─────────────┘       │     ├──▶ SerpAPI (Google)         │
                      │     ├──▶ TripAdvisor Content API  │
                      │     └──▶ Apify (Booking/Expedia)  │
                      └────────────────────────-──────────┘
```

The frontend is a static React SPA deployed on Vercel. All API calls go to the FastAPI backend on Render, which manages auth (JWT bearer tokens), hotel/group CRUD, CSV import, live review collection, and data export.

## Scoring Model

Review scores arrive on different scales per channel:

| Channel | Native Scale | Normalization |
|---------|-------------|---------------|
| Google | 1-5 | × 2 |
| TripAdvisor | 1-5 | × 2 |
| Booking.com | 1-10 | as-is |
| Expedia | 1-10 | as-is |

**Weighted average** = `Σ(normalized_score × review_count) / Σ(review_count)` across channels with data. Channels with no data (`n/a`) are excluded.

## Data Strategy

1. **CSV import** — The primary data source is a multi-format CSV with two header rows, comma-formatted numbers, and mixed `n/a` values. Parsing uses hardcoded column indices (more reliable than header matching given the messy format).

2. **Live collection** — Google reviews via SerpAPI (knowledge graph → local results fallback), TripAdvisor via their Content API (location search → detail lookup), and Booking.com/Expedia via Apify hosted scrapers (apify-client). Apify actors run on-demand and return scores + review counts.

3. **Snapshot history** — Each import or live collection creates a new `ReviewSnapshot` rather than overwriting, preserving the full history of score changes over time.

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run server
bash dev.sh run

# Run tests
bash dev.sh test

# Type-check + compile deps
bash dev.sh compile-install
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # dev server
npx tsc -b --noEmit  # type-check
npx vite build       # production build
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes (prod) | JWT signing key (defaults to dev key locally) |
| `DATABASE_URL` | Yes (prod) | PostgreSQL connection string |
| `FRONTEND_URL` | Yes (prod) | CORS origin (no trailing slash) |
| `SERPAPI_KEY` | No | Enables Google live collection |
| `TRIPADVISOR_KEY` | No | Enables TripAdvisor live collection |
| `APIFY_TOKEN` | No | Enables Booking.com + Expedia live collection |

## API Endpoints

```
Auth:        POST /api/auth/register    POST /api/auth/login
Hotels:      POST /api/hotels           GET  /api/hotels (paginated)
             GET  /api/hotels/{id}      DELETE /api/hotels/{id}?confirm=true
             GET  /api/hotels/{id}/history
Import:      POST /api/hotels/import-csv
Collection:  POST /api/reviews/hotels/{id}/collect
             POST /api/reviews/groups/{id}/collect
Groups:      POST /api/groups           GET  /api/groups
             GET  /api/groups/{id}      PUT  /api/groups/{id}
             DELETE /api/groups/{id}
Export:      GET  /api/export/hotels     GET  /api/export/groups/{id}
Admin:       POST /api/admin/reset (admin-only)
```

## Key Trade-offs

- **Booking/Expedia via Apify** — Neither offers a free public API. We use Apify hosted scrapers which add latency (30-120s per actor run) and cost compute units, but avoid maintaining custom scrapers.
- **Shared hotel model** — Hotels are global (not per-user) since they represent real properties. Groups provide per-user organization on top of the shared dataset.
- **SQLite for dev, PostgreSQL for prod** — Keeps local development simple while using a production-grade database on Render. Tests use in-memory SQLite for speed and isolation.
- **CSV parsing with column indices** — The source CSV has two header rows, merged cells, and inconsistent formatting. Hardcoded indices are more reliable than header-name matching for this specific file format.

## AI Usage

This project was built collaboratively with Claude (Anthropic). Claude was used for:

- **Architecture and planning** — Phase breakdown, API design, scoring model decisions
- **Implementation** — Backend routes, frontend components, CSV parsing, test writing
- **Code review and hardening** — An evaluation pass identified 12 weaknesses; 9 were addressed with TDD (tests written first, verified red, then fixed and verified green)
- **Debugging** — Python 3.14 compatibility issues (passlib/bcrypt), CORS configuration, SQLAlchemy N+1 queries

The commit history is intentionally structured to show the progression of work across phases. All code was reviewed and understood by the developer before committing.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + router registration
│   │   ├── auth.py              # JWT auth (bcrypt, python-jose)
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── database.py          # Engine + session setup
│   │   ├── routers/             # hotels, groups, reviews, export, admin, auth
│   │   └── services/
│   │       ├── csv_import.py    # CSV parser (column-index based)
│   │       ├── scoring.py       # Normalization + weighted average
│   │       └── collectors/      # Google (SerpAPI), TripAdvisor, Booking, Expedia (Apify)
│   ├── tests/
│   │   ├── conftest.py          # In-memory SQLite, fixtures, query counter
│   │   ├── test_api.py          # 33 integration tests
│   │   └── test_collectors.py  # 10 unit tests (Booking + Expedia)
│   └── dev.sh                   # Dev helper (run, test, compile, etc.)
├── frontend/
│   └── src/
│       ├── pages/               # Login, Register, Dashboard, HotelList,
│       │                        #   HotelDetail, Groups, GroupDetail
│       └── api/                 # Axios client, auth context, groups service
├── CLAUDE.md                    # AI assistant context (conventions, CSV format)
└── PLAN.md                      # Phase plan with status and notes
```
