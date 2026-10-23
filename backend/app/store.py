"""Loads the Elexon snapshot once and exposes it in the shapes the analysis needs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

from .analysis import Forecast, parse_ts

log = logging.getLogger("windwatch.store")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ACTUALS_FILE = "fuelhh_wind_2026-01.json"
FORECASTS_FILE = "windfor_2026-01.json"

# Purchase decisions are in scope for delivery days in January 2026 only.
FIRST_DELIVERY_DAY = date(2026, 1, 1)
LAST_DELIVERY_DAY = date(2026, 1, 31)


@dataclass(frozen=True)
class Dataset:
    actuals: dict[datetime, float]
    forecasts_by_target: dict[datetime, list[Forecast]]

    @property
    def forecast_count(self) -> int:
        return sum(len(v) for v in self.forecasts_by_target.values())


def load_dataset(data_dir: Path = DATA_DIR) -> Dataset:
    actual_rows = json.loads((data_dir / ACTUALS_FILE).read_text())
    forecast_rows = json.loads((data_dir / FORECASTS_FILE).read_text())

    actuals = {parse_ts(r["startTime"]): float(r["generation"]) for r in actual_rows}

    by_target: dict[datetime, list[Forecast]] = {}
    for r in forecast_rows:
        f = Forecast(
            target=parse_ts(r["startTime"]),
            published=parse_ts(r["publishTime"]),
            mw=float(r["generation"]),
        )
        by_target.setdefault(f.target, []).append(f)
    for fcs in by_target.values():
        fcs.sort(key=lambda f: f.published)

    log.info("dataset loaded actuals=%d forecasts=%d", len(actuals), sum(len(v) for v in by_target.values()))
    return Dataset(actuals=actuals, forecasts_by_target=by_target)


@lru_cache(maxsize=1)
def get_dataset() -> Dataset:
    return load_dataset()
