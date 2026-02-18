# Implementation Plan

See the full plan in the Claude session transcript. Key phases:

## Phases
0. **Scaffolding** — FastAPI + React + DB setup (hello world endpoints)
1. **Deploy the Skeleton** — Render (backend + Postgres), Vercel (frontend). Pave the deploy path before adding real functionality
2. **Backend Core + CSV Import** — Models, CSV parsing, scoring, auth, hotel CRUD
3. **Frontend MVP** — Auth pages, dashboard, hotel list/detail with charts
4. **Groups + Export** — Group CRUD, group UI, CSV export
5. **Live Data Collection** — SerpAPI (Google), TripAdvisor Content API; consider responsible scraping for Booking/Expedia if free API options aren't available
6. **Documentation** — README.md

### Cost philosophy
Prefer free options. If a paid API is needed, consider responsible scraping as an alternative. Keep API costs well under budget.

## API Endpoints
```
POST /api/auth/register        POST /api/auth/login
POST /api/hotels/import-csv    GET  /api/hotels
GET  /api/hotels/{id}          GET  /api/hotels/{id}/history
POST /api/hotels/{id}/collect
POST /api/groups               GET  /api/groups
GET  /api/groups/{id}          PUT  /api/groups/{id}
DELETE /api/groups/{id}        POST /api/groups/{id}/collect
GET  /api/export/hotels?format=csv
GET  /api/export/groups/{id}?format=csv
```

## Database Models
- **User**: id, email, hashed_password
- **Hotel**: id, name, city, state, keys, kind, brand, parent, booking_name, expedia_name, tripadvisor_name
- **ReviewSnapshot**: id, hotel_id, collected_at, source, scores/counts per channel, normalized scores, weighted_average
- **HotelGroup**: id, name, user_id, created_at
- **HotelGroupMembership**: group_id, hotel_id

## Frontend Pages
`/login` `/register` `/dashboard` `/hotels` `/hotels/:id` `/groups` `/groups/:id`
