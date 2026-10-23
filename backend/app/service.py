"""Builds the payloads the API returns. Sits between the HTTP layer and analysis."""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from . import analysis
from .store import FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY, get_dataset


def _iso(dt) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


@lru_cache(maxsize=64)
def _rows_for_range(first: date, last: date, cutoff_hour: int):
    ds = get_dataset()
    return {d: analysis.decision_rows(ds.forecasts_by_target, ds.actuals, d, cutoff_hour) for d in _days(first, last)}


def meta() -> dict:
    ds = get_dataset()
    return {
        "first_delivery_day": FIRST_DELIVERY_DAY.isoformat(),
        "last_delivery_day": LAST_DELIVERY_DAY.isoformat(),
        "default_cutoff_hour": 9,
        "timezone": "Europe/London",
        "actual_points": len(ds.actuals),
        "forecast_points": ds.forecast_count,
    }


def forecast_for_day(delivery_day: date, cutoff_hour: int) -> dict:
    rows = _rows_for_range(delivery_day, delivery_day, cutoff_hour)[delivery_day]

    # Planning band from errors of earlier delivery days only, so it never
    # peeks at the outcome of the day being planned.
    past_errors: list[float] = []
    if delivery_day > FIRST_DELIVERY_DAY:
        past = _rows_for_range(FIRST_DELIVERY_DAY, delivery_day - timedelta(days=1), cutoff_hour)
        past_errors = [r.error_mw for day_rows in past.values() for r in day_rows if r.error_mw is not None]
    band = analysis.planning_band(past_errors)

    points = []
    for r in rows:
        point = {
            "target": _iso(r.target),
            "forecast_mw": r.forecast_mw,
            "published": _iso(r.published),
            "horizon_h": round(r.horizon_h, 2),
            "actual_mw": r.actual_mw,
            "error_mw": r.error_mw,
            "low_mw": None,
            "high_mw": None,
        }
        if band:
            point["low_mw"] = max(0.0, r.forecast_mw - band["p90_error_mw"])
            point["high_mw"] = max(0.0, r.forecast_mw - band["p10_error_mw"])
        points.append(point)

    forecasts = [r.forecast_mw for r in rows]
    published = sorted({r.published for r in rows})
    return {
        "delivery_day": delivery_day.isoformat(),
        "cutoff": _iso(analysis.decision_cutoff(delivery_day, cutoff_hour)),
        "cutoff_hour": cutoff_hour,
        "forecast_runs_used": [_iso(p) for p in published],
        "summary": {
            "hours": len(rows),
            "mean_forecast_mw": sum(forecasts) / len(forecasts) if forecasts else None,
            "min_forecast_mw": min(forecasts) if forecasts else None,
            "max_forecast_mw": max(forecasts) if forecasts else None,
            "total_forecast_mwh": sum(forecasts) if forecasts else None,
        },
        "band": band,
        "points": points,
    }


def accuracy(first: date, last: date, cutoff_hour: int) -> dict:
    ds = get_dataset()
    rows_by_day = _rows_for_range(first, last, cutoff_hour)
    all_rows = [r for rows in rows_by_day.values() for r in rows]
    errors = [r.error_mw for r in all_rows if r.error_mw is not None]
    return {
        "first_day": first.isoformat(),
        "last_day": last.isoformat(),
        "cutoff_hour": cutoff_hour,
        "overall": analysis.summarize(all_rows),
        "by_day": analysis.by_day(rows_by_day),
        "by_hour": analysis.by_hour_of_day(all_rows),
        "histogram": analysis.error_histogram(errors),
        "by_horizon": analysis.horizon_profile(ds.forecasts_by_target, ds.actuals, first, last),
    }
