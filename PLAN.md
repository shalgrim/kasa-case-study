# Implementation Plan — Kasa Reputation Dashboard

## Current State (for future Claude sessions)

**Phase 5 is DONE — verified locally.** Next up is Phase 6 (Documentation).

**The live Render database has 422 hotels including junk summary/aggregate rows** (e.g., "AC" with City="4" State="2%", "Albuquerque" with City="1" State="0%"). These came from summary rows in the original CSV (`Example_Review_Comparison.csv`). A clean CSV (`hotel_rows_to_import.csv`) has been created with only real hotel rows. Phase 5's admin reset endpoint will let us wipe the DB and re-import with the clean file.

**Known issues to fix later:**
- "Needs Attention" dashboard card shows hotels with no review data (weighted avg 0) instead of genuinely low-scoring hotels → Phase 7
- CSV upload reports "426 rows imported" but hotel count unchanged (upsert — count is misleading) → Phase 8
- CORS required setting `FRONTEND_URL` env var on Render (no trailing slash) — fixed during verification

**Important conventions** (see also CLAUDE.md):
- User pushes to GitHub manually (don't use `git push`)
- Commits tell a story — at least one per phase, meaningful messages
- Dev script: `backend/dev.sh` wraps venv commands (run, test, compile-install, etc.)
- Smoke test: `backend/verify_live.sh [BASE_URL]` for post-deploy verification
- Frontend type-check: `cd frontend && npx tsc -b --noEmit`
- Frontend build: `cd frontend && npx vite build`

## Deployed URLs
- Backend: https://kasa-case-study.onrender.com (`/api/health` for health check)
- Frontend: https://kasa-case-study.vercel.app
- Render may cold-start (30-60s on first request after inactivity)

## Phases

0. ~~**Scaffolding** — FastAPI + React + DB setup (hello world endpoints)~~ **DONE**
1. ~~**Deploy the Skeleton** — Render (backend + Postgres), Vercel (frontend)~~ **DONE**
2. ~~**Backend Core + CSV Import** — Models, CSV parsing, scoring, auth, hotel CRUD~~ **DONE**
   - 10 unit tests passing (pytest): auth flow, CSV import, scoring normalization, weighted averages, hotel CRUD
   - Verified live on Render: 422 hotels imported, Sea Crest weighted avg = 7.58 (correct)
   - Bugs found & fixed: passlib→bcrypt (Python 3.14 compat), JWT sub must be string, pydantic v2 deprecations
3. ~~**Frontend MVP** — Auth pages, dashboard, hotel list/detail with charts~~ **DONE**
   - Login/register with JWT, protected routes
   - Dashboard: summary stats, CSV upload button
   - Hotel list: sortable, searchable, color-coded scores (green >=8, yellow 6-8, red <6), CSV export
   - Hotel detail: score cards, bar chart + radar chart (recharts), snapshot history, live collection button
   - Groups placeholder (links to /groups, shows "coming in Phase 4")
   - Verified live: register, hotel list, search/filter, Sea Crest detail page (scores, charts, history all correct)
   - Bug found & fixed: CORS preflight failing (FRONTEND_URL env var on Render needed to be set without trailing slash)
4. ~~**Groups + Export** — Group CRUD API + UI, CSV export~~ **DONE**
   - Groups list page: create with searchable hotel multi-select, delete with confirm
   - Group detail page: score table (same color coding as hotel list), CSV export, inline edit (rename + membership)
   - 8 new backend tests (18 total): group CRUD, export endpoints, user isolation
   - Minor bugs deferred to Phase 7: export filename doesn't reflect group name; no "back to groups" breadcrumb from hotel detail
5. ~~**Live Data Collection + Admin** — Admin reset, hotel deletion, mocked collection tests~~ **DONE**
   - `POST /api/admin/reset` — wipes all data and re-imports from clean CSV
   - `DELETE /api/hotels/{id}` — cascading delete (snapshots + group memberships)
   - Frontend "Delete Hotel" button with confirm dialog
   - 6 new tests (24 total): mocked collection (single + group), admin reset, hotel deletion, group membership cleanup
   - Booking/Expedia scraping deferred — no public APIs available; Google (SerpAPI) and TripAdvisor (Content API) collectors already implemented in Phase 2
6. **Documentation** — README.md with architecture, data strategy, scoring, AI usage, trade-offs
7. **Cleanup** — Fix "Needs Attention" card to exclude hotels with no review data (weighted avg 0); remove CSV upload button from dashboard UI; group CSV export filename should reflect group name; hotel detail page should show "Back to groups" breadcrumb when navigated from a group
8. **CSV Upload Polish** (stretch, likely won't reach) — Fix misleading "imported" count to distinguish new vs updated hotels; improve error handling for bad CSV files

### Cost philosophy
Prefer free options. Consider responsible scraping if paid APIs are needed. Keep costs well under budget.

### Workflow per phase
1. Implement and test locally
2. Commit with meaningful message
3. User pushes to GitHub
4. Verify live (Render auto-deploys backend, Vercel auto-deploys frontend)
5. Update PLAN.md to mark phase DONE with verification notes
6. Commit the PLAN.md update

## API Endpoints
```
POST /api/auth/register        POST /api/auth/login
POST /api/hotels/import-csv    GET  /api/hotels
GET  /api/hotels/{id}          GET  /api/hotels/{id}/history
POST /api/reviews/hotels/{id}/collect
POST /api/groups               GET  /api/groups
GET  /api/groups/{id}          PUT  /api/groups/{id}
DELETE /api/groups/{id}        POST /api/reviews/groups/{id}/collect
GET  /api/export/hotels        GET  /api/export/groups/{id}
DELETE /api/hotels/{id}        POST /api/admin/reset
```

## Database Models
- **User**: id, email, hashed_password
- **Hotel**: id, name, city, state, keys, kind, brand, parent, booking_name, expedia_name, tripadvisor_name
- **ReviewSnapshot**: id, hotel_id, collected_at, source, scores/counts per channel (google/booking/expedia/tripadvisor), normalized scores (4), weighted_average
- **HotelGroup**: id, name, user_id, created_at
- **HotelGroupMembership**: group_id, hotel_id

## Frontend Pages
- `/login`, `/register` — auth (done)
- `/dashboard` — summary stats, CSV upload (done)
- `/hotels` — sortable/filterable/color-coded table (done)
- `/hotels/:id` — detail with charts and history (done)
- `/groups` — list/create groups (done)
- `/groups/:id` — group detail with scores (done)

## Key Technical Notes
- Python 3.14 — passlib doesn't work, we use bcrypt directly
- JWT sub claim must be a string (python-jose enforces the spec)
- SQLAlchemy uses psycopg v3 (`psycopg[binary]`), not psycopg2
- DB connection string: Render gives `postgres://`, we rewrite to `postgresql+psycopg://`
- Test setup uses in-memory SQLite with StaticPool + dependency override (see `tests/conftest.py`)
- CSV parsing uses hardcoded column indices (see CLAUDE.md for positions)
- Scoring: Google/TripAdvisor (1-5) * 2 = normalized. Booking/Expedia (1-10) as-is. Weighted avg = sum(norm * count) / sum(count)
