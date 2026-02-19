# Implementation Plan — Kasa Reputation Dashboard

## Current State (for future Claude sessions)

**Phase 3 is code-complete but not yet verified live.** The frontend MVP has been built and compiles cleanly. The next step is:
1. Commit the staged frontend changes (already staged in git)
2. Push to GitHub (user pushes manually to save tokens)
3. Vercel auto-deploys the frontend
4. Verify live: register a user, upload the CSV, check the hotel list and detail pages
5. Only then mark Phase 3 as DONE and update this file

**The live Render database currently has 422 hotels from a test CSV import.** We plan to add an admin reset endpoint in Phase 5 to clean this up. For now it's fine — the frontend will display this data.

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
3. **Frontend MVP** — Auth pages, dashboard, hotel list/detail with charts — **CODE COMPLETE, NEEDS LIVE VERIFICATION**
   - Login/register with JWT, protected routes
   - Dashboard: summary stats, CSV upload button
   - Hotel list: sortable, searchable, color-coded scores (green >=8, yellow 6-8, red <6), CSV export
   - Hotel detail: score cards, bar chart + radar chart (recharts), snapshot history, live collection button
   - Groups placeholder (links to /groups, shows "coming in Phase 4")
4. **Groups + Export** — Group CRUD API + UI, CSV export (backend endpoints already exist)
5. **Live Data Collection + Admin** — SerpAPI (Google), TripAdvisor Content API; responsible scraping for Booking/Expedia if free APIs unavailable. Admin reset endpoint to wipe hotel/snapshot data
6. **Documentation** — README.md with architecture, data strategy, scoring, AI usage, trade-offs

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
- `/groups` — list/create groups (Phase 4)
- `/groups/:id` — group detail with scores (Phase 4)

## Key Technical Notes
- Python 3.14 — passlib doesn't work, we use bcrypt directly
- JWT sub claim must be a string (python-jose enforces the spec)
- SQLAlchemy uses psycopg v3 (`psycopg[binary]`), not psycopg2
- DB connection string: Render gives `postgres://`, we rewrite to `postgresql+psycopg://`
- Test setup uses in-memory SQLite with StaticPool + dependency override (see `tests/conftest.py`)
- CSV parsing uses hardcoded column indices (see CLAUDE.md for positions)
- Scoring: Google/TripAdvisor (1-5) * 2 = normalized. Booking/Expedia (1-10) as-is. Weighted avg = sum(norm * count) / sum(count)
