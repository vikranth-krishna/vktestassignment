"""FastAPI entry point.

Routes live under /api so the same app works behind the Vite dev proxy,
inside Docker, and as a Vercel function.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import service
from .store import FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY, get_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("windwatch.api")

app = FastAPI(
    title="WindWatch API",
    version="1.0.0",
    description="Day-ahead wind generation forecasts and their measured accuracy for GB (Elexon data).",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["x-request-id"] = request_id
    log.info(
        "request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def _check_day(d: date, name: str) -> date:
    if not FIRST_DELIVERY_DAY <= d <= LAST_DELIVERY_DAY:
        raise HTTPException(
            status_code=404,
            detail=f"{name} {d} is outside the available range {FIRST_DELIVERY_DAY} to {LAST_DELIVERY_DAY}",
        )
    return d


@app.get("/api/health")
def health() -> dict:
    ds = get_dataset()
    return {"status": "ok", "actual_points": len(ds.actuals), "forecast_points": ds.forecast_count}


@app.get("/api/meta")
def meta() -> dict:
    return service.meta()


@app.get("/api/forecast")
def forecast(
    delivery_day: date = Query(..., description="Delivery day (UK local date)"),
    cutoff_hour: int = Query(9, ge=0, le=23, description="UK clock hour on the previous day when the buy is decided"),
) -> dict:
    return service.forecast_for_day(_check_day(delivery_day, "delivery_day"), cutoff_hour)


@app.get("/api/accuracy")
def accuracy(
    first_day: date = Query(FIRST_DELIVERY_DAY),
    last_day: date = Query(LAST_DELIVERY_DAY),
    cutoff_hour: int = Query(9, ge=0, le=23),
) -> dict:
    _check_day(first_day, "first_day")
    _check_day(last_day, "last_day")
    if first_day > last_day:
        raise HTTPException(status_code=422, detail="first_day must not be after last_day")
    return service.accuracy(first_day, last_day, cutoff_hour)


# In Docker the API also serves the built React app. On Vercel the static files
# are served by the platform and this directory is not part of the function.
_dist = Path(os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
