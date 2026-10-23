"""Forecast selection and error metrics.

Everything in here is a pure function over plain data, so it can be tested
without the web layer or the data files.

Sign convention: error = forecast - actual. A positive error means the
forecast was higher than what the wind farms really produced, so a buyer who
trusted it would have bought too little from the market.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")
UTC = UTC

# Minimum number of past errors needed before a planning band is shown.
MIN_SAMPLES_FOR_BAND = 24


@dataclass(frozen=True)
class Forecast:
    target: datetime  # start of the delivery hour, UTC
    published: datetime  # when this forecast was created, UTC
    mw: float


@dataclass(frozen=True)
class Row:
    """One delivery hour as seen from the decision point."""

    target: datetime
    forecast_mw: float
    published: datetime
    horizon_h: float
    actual_mw: float | None

    @property
    def error_mw(self) -> float | None:
        if self.actual_mw is None:
            return None
        return self.forecast_mw - self.actual_mw


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def decision_cutoff(delivery_day: date, cutoff_hour: int) -> datetime:
    """The moment the buyer has to commit: cutoff_hour UK time on the day before."""
    if not 0 <= cutoff_hour <= 23:
        raise ValueError("cutoff_hour must be between 0 and 23")
    prior = delivery_day - timedelta(days=1)
    local = datetime.combine(prior, time(cutoff_hour), tzinfo=UK)
    return local.astimezone(UTC)


def delivery_hours(delivery_day: date) -> list[datetime]:
    """Hourly UTC start times for a UK delivery day (handles 23h and 25h days)."""
    start = datetime.combine(delivery_day, time(0), tzinfo=UK).astimezone(UTC)
    end = datetime.combine(delivery_day + timedelta(days=1), time(0), tzinfo=UK).astimezone(UTC)
    hours = []
    t = start
    while t < end:
        hours.append(t)
        t += timedelta(hours=1)
    return hours


def latest_before(forecasts: list[Forecast], cutoff: datetime) -> Forecast | None:
    """Most recent forecast published at or before the cutoff.

    `forecasts` must be sorted by publish time.
    """
    keys = [f.published for f in forecasts]
    idx = bisect_right(keys, cutoff)
    if idx == 0:
        return None
    return forecasts[idx - 1]


def decision_rows(
    forecasts_by_target: dict[datetime, list[Forecast]],
    actuals: dict[datetime, float],
    delivery_day: date,
    cutoff_hour: int,
) -> list[Row]:
    """Latest available forecast for every hour of a delivery day, as of the cutoff."""
    cutoff = decision_cutoff(delivery_day, cutoff_hour)
    rows: list[Row] = []
    for target in delivery_hours(delivery_day):
        chosen = latest_before(forecasts_by_target.get(target, []), cutoff)
        if chosen is None:
            continue
        rows.append(
            Row(
                target=target,
                forecast_mw=chosen.mw,
                published=chosen.published,
                horizon_h=(target - chosen.published).total_seconds() / 3600,
                actual_mw=actuals.get(target),
            )
        )
    return rows


def quantile(sorted_values: list[float], q: float) -> float:
    """Linear interpolation quantile on an already sorted list."""
    if not sorted_values:
        raise ValueError("no values")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    frac = pos - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def summarize(rows: list[Row]) -> dict:
    """Accuracy metrics over rows that have both a forecast and an actual."""
    scored = [r for r in rows if r.actual_mw is not None]
    n = len(scored)
    if n == 0:
        return {"n": 0}
    errors = [r.forecast_mw - r.actual_mw for r in scored]  # type: ignore[operator]
    abs_errors = sorted(abs(e) for e in errors)
    sorted_errors = sorted(errors)
    pct = [abs(e) / r.actual_mw * 100 for e, r in zip(errors, scored, strict=True) if r.actual_mw and r.actual_mw > 0]
    return {
        "n": n,
        "mae_mw": sum(abs_errors) / n,
        "rmse_mw": math.sqrt(sum(e * e for e in errors) / n),
        "bias_mw": sum(errors) / n,
        # In-sample figure: MAE if the average bias were subtracted from every forecast.
        "mae_bias_removed_mw": sum(abs(e - sum(errors) / n) for e in errors) / n,
        "mape_pct": (sum(pct) / len(pct)) if pct else None,
        "median_abs_error_mw": quantile(abs_errors, 0.5),
        "p90_abs_error_mw": quantile(abs_errors, 0.9),
        "error_p10_mw": quantile(sorted_errors, 0.1),
        "error_p50_mw": quantile(sorted_errors, 0.5),
        "error_p90_mw": quantile(sorted_errors, 0.9),
        "mean_actual_mw": sum(r.actual_mw for r in scored) / n,  # type: ignore[misc]
    }


def planning_band(past_errors: list[float]) -> dict | None:
    """Range the real generation is likely to fall in, given past forecast errors.

    actual = forecast - error, so a high error quantile gives the low end.
    Returns offsets to subtract from a forecast: low = f - p90, high = f - p10.
    """
    if len(past_errors) < MIN_SAMPLES_FOR_BAND:
        return None
    ordered = sorted(past_errors)
    return {
        "p10_error_mw": quantile(ordered, 0.1),
        "p90_error_mw": quantile(ordered, 0.9),
        "samples": len(ordered),
    }


def by_day(rows_by_day: dict[date, list[Row]]) -> list[dict]:
    out = []
    for day in sorted(rows_by_day):
        s = summarize(rows_by_day[day])
        if s["n"]:
            out.append({"date": day.isoformat(), **s})
    return out


def by_hour_of_day(rows: list[Row]) -> list[dict]:
    """Accuracy per UK clock hour, to show whether some hours are harder to call."""
    buckets: dict[int, list[Row]] = {}
    for r in rows:
        buckets.setdefault(r.target.astimezone(UK).hour, []).append(r)
    out = []
    for hour in sorted(buckets):
        s = summarize(buckets[hour])
        if s["n"]:
            out.append({"hour": hour, "n": s["n"], "mae_mw": s["mae_mw"], "bias_mw": s["bias_mw"]})
    return out


def error_histogram(errors: list[float], width_mw: float = 1000.0) -> list[dict]:
    if not errors:
        return []
    lo = math.floor(min(errors) / width_mw) * width_mw
    hi = math.ceil((max(errors) + 1e-9) / width_mw) * width_mw
    n_bins = max(1, int(round((hi - lo) / width_mw)))
    counts = [0] * n_bins
    for e in errors:
        idx = min(int((e - lo) // width_mw), n_bins - 1)
        counts[idx] += 1
    return [{"from_mw": lo + i * width_mw, "to_mw": lo + (i + 1) * width_mw, "count": c} for i, c in enumerate(counts)]


def horizon_profile(
    forecasts_by_target: dict[datetime, list[Forecast]],
    actuals: dict[datetime, float],
    first_day: date,
    last_day: date,
    bin_hours: int = 6,
    max_hours: int = 72,
) -> list[dict]:
    """How error grows with forecast lead time.

    Uses every forecast published before its target hour, not just the one a
    buyer would have picked, so the sample is much larger. Forecasts published
    after the target time are not decision-relevant and are left out.
    """
    window_start = datetime.combine(first_day, time(0), tzinfo=UK).astimezone(UTC)
    window_end = datetime.combine(last_day + timedelta(days=1), time(0), tzinfo=UK).astimezone(UTC)
    bins: dict[int, list[float]] = {}
    for target, fcs in forecasts_by_target.items():
        if not (window_start <= target < window_end) or target not in actuals:
            continue
        for f in fcs:
            horizon = (target - f.published).total_seconds() / 3600
            if horizon < 0 or horizon >= max_hours:
                continue
            bins.setdefault(int(horizon // bin_hours), []).append(f.mw - actuals[target])
    out = []
    for b in sorted(bins):
        errs = bins[b]
        out.append(
            {
                "from_h": b * bin_hours,
                "to_h": (b + 1) * bin_hours,
                "n": len(errs),
                "mae_mw": sum(abs(e) for e in errs) / len(errs),
                "bias_mw": sum(errs) / len(errs),
            }
        )
    return out
