# Kasa Reputation Dashboard — Project Context

## What This Is
Case study for Kasa's AI Solutions Engineer role. A web-based "Reputation Dashboard" that aggregates hotel review data across Google, TripAdvisor, Expedia, and Booking.com.

## Tech Stack
- **Backend**: Python / FastAPI, SQLAlchemy, python-jose (JWT), passlib
- **Frontend**: React (TypeScript), Vite, Tailwind CSS, Recharts
- **Database**: SQLite (dev), PostgreSQL on Render (prod)
- **Deployment**: Render (backend + DB), Vercel (frontend)

## Coding Conventions
- Python: pytest for tests, venv in `.venv`
- TypeScript: strict mode, functional components with hooks
- API prefix: `/api/`
- Auth: JWT bearer tokens

## Scoring Assumptions
- **Normalization to 0-10**: Google/TripAdvisor (1-5 scale) multiply by 2. Booking/Expedia (1-10 scale) use as-is.
- **Weighted average**: `sum(normalized_score_i * review_count_i) / sum(review_count_i)` across channels with data.
- Channels with no data (n/a) are excluded from the weighted average.

## CSV Format Notes (`Example_Review_Comparison.csv`)
- Two header rows (row 1 = category labels, row 2 = column names)
- Key columns by 0-indexed position: Name(5), City(6), State(7), Keys(8), Kind(9), Brand(10), Parent(11), Google Score(16), Booking Score(17), Expedia Score(18), TripAdvisor Score(19), Google Count(22), Booking Count(23), Expedia Count(24), TripAdvisor Count(25), Booking Name(37), Expedia Name(38), TripAdvisor Name(39)
- Comma-separated numbers in quotes (e.g., `"1,596 "`)
- Trailing spaces in numeric fields
- `n/a` for missing data

## Git Strategy
- Commit at least once per phase — the commit history should tell the story of our work and thought process
- Meaningful commit messages that explain the "why" of each phase

## Key Decisions
- CSV parsing uses hardcoded column indices (more reliable than header matching given messy format)
- Live collection only for Google (SerpAPI) and TripAdvisor (Content API); Booking/Expedia lack public APIs.
  - We can revisit doing a scraping solution if time permits
- Each collection creates a new ReviewSnapshot to preserve history
