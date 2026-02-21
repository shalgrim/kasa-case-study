# Kasa Reputation Dashboard

> Case study submission for Kasa's AI Solutions Engineer role.

## Start Here: Demo and Links

- **Recorded demo:** [Watch Me First](https://photos.google.com/share/AF1QipPoAF6GTJyOCaB8kZ62j1bG5fYR8lVua3QDP7IkwN2-MRu67TIcdbA8qVJ6EdMESA/photo/AF1QipPl5jP104DeV9Qy8X6B0kSM39-Jeq6aXiN3WIln?key=ZFZUYTJWWDIzbWhXQUxyUjFwNXdERkFOenpLN2t3)
- **Live demo:** [kasa-case-study.vercel.app](https://kasa-case-study.vercel.app) (register with any email/password)
- **Source code:** This repo
- **Backend API:** [kasa-case-study.onrender.com](https://kasa-case-study.onrender.com/api/health) *(free tier — first request may take 30-60s to cold-start)*

## Summary

A full-stack web application that aggregates hotel review data across Google, TripAdvisor, Expedia, and Booking.com. Users can log in, import hotels from CSV or create them manually, organize them into named groups, view normalized scores with visualizations, collect live review data, and export results to CSV.

The system normalizes scores to a common 0-10 scale, computes review-count-weighted averages, and preserves full snapshot history so scores can be tracked over time.

- **Built with:** Python/FastAPI, React/TypeScript, PostgreSQL, Tailwind CSS, Recharts
- **Tested with:** 54 backend tests (pytest) covering auth, CRUD, scoring, collection, groups, export, admin, and hardening
- **Built using:** Claude (Anthropic) — see [AI Usage](#ai-usage) below

## Quick Tour for Evaluators

1. **Open the [live demo](https://kasa-case-study.vercel.app)** and register (any email/password, no verification)
2. **Browse the hotel list** — ~100 hotels pre-loaded from the provided CSV with scores across all four channels. The table is sortable, searchable, and color-coded (green >= 8, yellow 6-8, red < 6)
3. **Click any hotel** to see score cards, bar/radar charts, and snapshot history
4. **Create a group** from the Groups page to organize hotels into a portfolio with a comparison table
5. **Export to CSV** from either the hotel list or a group detail page
6. **Try live collection** — click "Collect Live Reviews" on any hotel detail page. Google and TripAdvisor are the most reliable channels; Booking.com and Expedia work but have accuracy issues (see [Known Limitations](#known-limitations) below)

### What to look at in the code

| Area | File(s) | Why it's interesting |
|------|---------|---------------------|
| Scoring model | `backend/app/services/scoring.py` | Normalization, weighted average, count imputation for missing data |
| Live collectors | `backend/app/services/collectors/` | Four collectors with different API patterns, each returning `(score, count)` with graceful fallback |
| CSV parsing | `backend/app/services/csv_import.py` | Handles the messy two-header-row CSV format with comma-formatted numbers and `n/a` values |
| Test suite | `backend/tests/` | 54 tests including N+1 query regression test, LIKE-wildcard injection test, and collector unit tests |
| Hardening commits | Git log, Phase 7 | Self-evaluation identified 12 weaknesses; 9 addressed with TDD |

## Known Limitations

### Scraper reliability (Booking.com and Expedia)

The two Apify-backed collectors (Booking.com and Expedia) are the weakest part of the system. Specific issues:

- **Booking.com frequently returns no match** — even for well-known hotels like Stoweflake Mountain Resort & Spa. The actor searches by geographic query and returns the top 5 results, but the target hotel often isn't among them. The collector does name-matching to pick the right property from results, but if the hotel doesn't appear in the top 5, it returns nothing.
- **Expedia scores are inaccurate** — the Apify actor returns text labels ("Very Good", "Excellent") that I map to numeric midpoint values, but the mapped scores often don't match what's shown on Expedia's actual website. The scraper may be pulling data from a stale or different view of the listing. This means Expedia scores in the dashboard should be treated as approximate at best.
- **Google and TripAdvisor are reliable** — SerpAPI (knowledge graph) and the TripAdvisor Content API return accurate, current data consistently.

In a production system, I would address this by:
1. Accepting direct OTA URLs per hotel (Booking.com URL, Expedia URL) and using Apify's `startUrls` mode for targeted scraping instead of geographic search
2. Cross-validating scraped scores against the CSV baseline to flag suspicious deltas
3. Evaluating paid data aggregation services (e.g., ReviewPro, TrustYou) that have direct integrations with OTA platforms

The architecture already handles partial collection gracefully — if a channel fails, it's excluded from the weighted average, and the API response reports exactly which channels succeeded and which failed.

## Architecture

```
┌─────────────┐       ┌──────────────────────────────────┐
│   Vercel    │       │         Render                   │
│   (React)   │──────>│  FastAPI  ──>  PostgreSQL        │
│             │  JWT  │     │                            │
└─────────────┘       │     ├──> SerpAPI (Google)        │
                      │     ├──> TripAdvisor Content API │
                      │     └──> Apify (Booking/Expedia) │
                      └──────────────────────────────────┘
```

The frontend is a static React SPA on Vercel. All API calls go through the FastAPI backend on Render, which handles auth (JWT), hotel/group CRUD, CSV import, live review collection (4 channels in parallel via ThreadPoolExecutor), and CSV export.

## Scoring Model

| Channel | Native Scale | Normalization |
|---------|-------------|---------------|
| Google | 1-5 | multiply by 2 |
| TripAdvisor | 1-5 | multiply by 2 |
| Booking.com | 1-10 | as-is |
| Expedia | text labels | mapped to 1-10 (see below) |

**Weighted average** = `sum(normalized_score * review_count) / sum(review_count)` across channels with data. Channels returning `n/a` are excluded.

**Count imputation**: If a channel returns a score but no review count (which happens with some scraper responses), the missing count is imputed as the average of the known counts from other channels. This avoids discarding valid score data.

**Expedia label mapping**: The Expedia scraper returns text labels instead of numeric scores. These are mapped to midpoint values: Exceptional (9.5), Wonderful (9.0), Excellent (8.5), Very Good (7.5), Good (6.5), OK (5.5). Unknown labels are treated as missing data. As noted above, these mapped values often don't match what Expedia actually shows — this mapping is a best-effort approximation.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, SQLAlchemy, python-jose (JWT), bcrypt |
| Frontend | React 19 (TypeScript), Vite, Tailwind CSS, Recharts |
| Database | SQLite (dev), PostgreSQL (prod via Render) |
| Deployment | Render (backend + DB), Vercel (frontend) |
| Live collection | SerpAPI (Google), TripAdvisor Content API, Apify (Booking/Expedia) |
| Testing | pytest (54 tests), in-memory SQLite with StaticPool |

## Key Trade-offs

- **Apify for Booking/Expedia** — Neither offers a public API. Apify hosted scrapers avoid maintaining custom scrapers but add latency (30-120s per actor run), cost compute units, and — as documented above — have reliability and accuracy issues. This is the area with the most room for improvement.
- **Hardcoded CSV column indices** — The source CSV has two header rows, merged cells, and inconsistent formatting. Index-based parsing is more reliable than header-name matching for this specific format.
- **Shared hotel model** — Hotels are global (not per-user) since they represent real properties. Groups provide per-user organization on top of the shared dataset.
- **Snapshot-per-collection** — Each import or live collection creates a new `ReviewSnapshot` row rather than overwriting. This preserves history but means the database grows over time. A retention policy would be needed at scale.

## Future Work

- **Booking.com collector** — The third-party Apify actor (`voyager/booking-scraper`) has become unreliable, failing with "Failed to extract destination" errors on Booking's autocomplete API. A custom scraper (e.g., Playwright-based) that navigates directly to a hotel's Booking.com URL and extracts the aggregate score/count would be far more reliable than depending on a third-party actor's search resolution.
- **Expedia collector reliability** — The Expedia Apify actor works but geographic search can return wrong matches. Direct-URL scraping or score cross-validation against known baselines would improve accuracy.
- **Hotel-group integration on detail page** — The hotel detail page should show which groups a hotel belongs to and offer an "Add to Group" action, so users don't have to navigate away to manage membership.
- **Interactive snapshot history** — Clicking a row in the snapshot history table should update the score cards and charts to reflect that point-in-time snapshot, not just the latest one. Currently the charts always show the most recent data.
- **Frontend tests** — The backend has 54 tests; the frontend has none. React Testing Library or Playwright E2E tests would close this gap.
- **Background collection** — Live collection runs synchronously in the request cycle. For group collection across many hotels, a background task system (Celery, ARQ) would prevent timeout issues.
- **Admin-only hotel deletion** — Currently any authenticated user can delete any hotel (with confirmation). Should be restricted to admin role.
- **"Needs Attention" dashboard card** — Should highlight genuinely low-scoring hotels rather than those with missing data.
- **Group export filename** — Should include the group name.

## AI Usage

This project was built collaboratively with Claude (Anthropic). Claude was used for:

- **Architecture and planning** — Phase breakdown, API design, scoring model decisions
- **Implementation** — Backend routes, frontend components, CSV parsing, test writing
- **Code review and hardening** — A self-evaluation pass identified 12 weaknesses; 9 were addressed with TDD (tests written first, then fixed)
- **Debugging** — Python 3.14 compatibility (passlib/bcrypt), CORS configuration, Apify actor schemas, SQLAlchemy N+1 queries

The commit history is intentionally structured to show the progression of work across 9 phases.

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

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

bash dev.sh run       # Start server
bash dev.sh test      # Run 54 tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev           # Dev server on :5173
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

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app + CORS + router registration
    auth.py              # JWT auth (bcrypt, python-jose)
    models.py            # SQLAlchemy models (User, Hotel, ReviewSnapshot, HotelGroup)
    database.py          # Engine + session setup
    routers/             # hotels, groups, reviews, export, admin, auth
    services/
      csv_import.py      # CSV parser (column-index based)
      scoring.py         # Normalization + weighted average + count imputation
      collectors/        # Google (SerpAPI), TripAdvisor, Booking (Apify), Expedia (Apify)
  tests/
    test_api.py          # 33 integration tests
    test_collectors.py   # 15 collector unit tests
    test_scoring.py      # 6 scoring unit tests
frontend/
  src/
    pages/               # Login, Register, Dashboard, HotelList,
                         #   HotelDetail, Groups, GroupDetail
    api/                 # Axios client, auth context, groups service
CLAUDE.md                # AI assistant context (conventions, scoring rules)
PLAN.md                  # Phase plan with status and verification notes
```
