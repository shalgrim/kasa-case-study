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

## Didn't Find What You Were Looking For?

Try [README-LONG.md](./README-LONG.md)
