# WindWatch

A small web app for a GB power desk that buys electricity on the day-ahead market. For any delivery day in January 2026 it shows the newest national wind forecast that existed at the moment the buy had to be decided, and it measures how accurate those forecasts were against metered wind output.

Live app: **LIVE_URL_PLACEHOLDER**

## What it does

1. **Decision view.** Pick a delivery day. For each hour, the app picks the latest WINDFOR forecast published at or before the decision time on the previous day (default 09:00 UK, adjustable in the UI). It shows the hourly forecast, a likely range for the real output, and the forecast runs that were used. A switch reveals the actual generation afterwards, so a day can be replayed fairly.
2. **Forecast accuracy.** For all delivery hours in January 2026: mean absolute error, root mean square error, bias, 90th percentile miss, error by day, by lead time, by hour of day, and the spread of errors.

Findings for January 2026 at the 09:00 decision point (744 scored hours): mean absolute error about 2,130 MW (22% of actual output), bias about +1,850 MW (forecasts too high), and a 90th percentile miss of about 4,300 MW. Error grows with lead time, from about 1,770 MW for forecasts under 6 hours old to about 2,400 MW beyond 42 hours.

## Method and assumptions

- **Data.** Actuals: Elexon FUELHH, fuel type WIND. Forecasts: Elexon WINDFOR. National level only, nothing else.
- **Decision time.** A purchase for delivery day D is decided at `cutoff_hour` UK time on D-1. The default of 09:00 is an approximation of the day-ahead auction gate closure. It is a parameter, not a hard-coded constant.
- **Forecast choice.** For each target hour, the forecast with the latest `publishTime` that is not after the decision time. Forecasts published later, including those published after the target hour, are never used.
- **Matching.** WINDFOR has one value per hour, while FUELHH is half-hourly. Hours are matched on the exact `startTime`, so the half-hours that fall between forecast points are not scored. This leaves 24 scored points per day.
- **Error sign.** `error = forecast - actual`. Positive means the forecast was too optimistic.
- **Likely range.** The shaded band uses the 10th and 90th percentile of forecast errors from earlier delivery days only, so it never uses the outcome of the day being planned. It is hidden when fewer than 24 earlier hours exist (the first day of the month).
- **Bias-removed MAE.** Reported as an upper bound on the gain from a bias correction, because it is measured on the same data.
- **Time zone.** Day boundaries use Europe/London. The code handles 23 and 25 hour days even though January has none.
- **What is not covered.** Demand, prices and the gap to be bought from thermal plants are outside the given data scope. The app deals only with the wind side of that sum.

One open question worth checking with the data owner: the persistent positive bias at every lead time could be a definition mismatch between the forecast series and the metered actuals, rather than pure forecast skill.

## Repository layout

```
backend/
  app/
    analysis.py     pure functions: forecast selection, metrics, bands, histograms
    store.py        loads the data snapshot into memory once
    service.py      builds API payloads, caches computed ranges
    main.py         FastAPI routes, request logging, optional static hosting
  data/             January 2026 snapshot (actuals and forecasts, JSON)
  scripts/
    fetch_data.py   re-downloads the snapshot from the Elexon API
  tests/            pytest: unit tests for analysis, API tests on real data
  requirements-dev.txt
frontend/
  src/
    components/     ForecastView, AccuracyView, Kpi, Status
    api.ts          typed fetch helpers
    useAsync.ts     data loading hook with request cancellation
    format.ts       number, time and wording helpers
    test/           Vitest and Testing Library tests
api/index.py        Vercel entry point, re-exports the FastAPI app
vercel.json         Vercel build and routing config
Dockerfile          multi-stage build: React build, then Python image serving both
docker-compose.yml
.github/workflows/ci.yml
requirements.txt    runtime dependencies
```

## Run it

### With Docker

```
docker compose up --build
```

Open http://localhost:8000. The container serves the React app and the API together. API docs are at http://localhost:8000/api/docs.

### Locally for development

Backend (Python 3.11 or newer):

```
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --reload --port 8000
```

Frontend (Node 20 or newer), in a second terminal:

```
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to port 8000.

### Tests and checks

```
pytest                                  # backend
ruff check backend && ruff format --check backend
cd frontend && npm test && npm run lint && npm run build
```

### Refreshing the data

The app reads a snapshot from `backend/data/` and does not call Elexon while serving requests. This keeps the demo fast and independent of the upstream API. To pull the data again:

```
python backend/scripts/fetch_data.py
```

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness and row counts |
| `GET /api/meta` | Available date range and defaults |
| `GET /api/forecast?delivery_day=2026-01-15&cutoff_hour=9` | Hourly forecast as of the decision time, with range and actuals |
| `GET /api/accuracy?first_day=...&last_day=...&cutoff_hour=9` | Metrics and breakdowns over a range |

Out of range dates return 404 with a readable message, and bad input returns 422. Every request is logged with a request id, also returned in the `x-request-id` header.

## CI and deployment

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and pull request:

1. Backend: ruff lint and format check, pytest.
2. Frontend: eslint, type check, Vitest, production build.
3. Docker: builds the image, starts it, and smoke tests `/api/health`, `/api/forecast` and the served UI.
4. On pushes to `main`, deploys to Vercel when `VERCEL_TOKEN`, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` secrets are set. Without them the step is skipped, and Vercel's own Git integration can deploy instead.

On Vercel the React build is served as static files and the FastAPI app runs as a Python function at `/api/*` (see `vercel.json`).

## Tools

Built with the help of Claude Code, used for implementation, testing and documentation.
