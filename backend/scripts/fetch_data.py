"""Download January 2026 wind data from the Elexon BMRS API and store a slim snapshot.

Usage (from the repo root):
    python backend/scripts/fetch_data.py

Two files are written to backend/data/:
    fuelhh_wind_2026-01.json   actual wind generation, half-hourly
    windfor_2026-01.json       wind forecasts, one row per (target hour, publish time)

Only the fields the app needs are kept, which keeps the snapshot small enough
to ship with the deployment. The app never calls Elexon at request time.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT_DIR = Path(__file__).resolve().parents[1] / "data"

# Decisions for delivery days in January 2026 are taken on the day before, so
# forecasts published from the last days of December are relevant too.
ACTUALS_FROM, ACTUALS_TO = "2026-01-01", "2026-01-31"
FORECAST_PUBLISHED_FROM = "2025-12-29T00:00:00Z"
FORECAST_PUBLISHED_TO = "2026-02-01T00:00:00Z"


def get_json(dataset: str, params: dict[str, str]) -> list[dict]:
    url = f"{BASE}/{dataset}/stream?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    actuals = get_json(
        "FUELHH",
        {
            "settlementDateFrom": ACTUALS_FROM,
            "settlementDateTo": ACTUALS_TO,
            "fuelType": "WIND",
        },
    )
    forecasts = get_json(
        "WINDFOR",
        {
            "publishDateTimeFrom": FORECAST_PUBLISHED_FROM,
            "publishDateTimeTo": FORECAST_PUBLISHED_TO,
        },
    )

    slim_actuals = sorted(
        ({"startTime": r["startTime"], "generation": r["generation"]} for r in actuals if r["fuelType"] == "WIND"),
        key=lambda r: r["startTime"],
    )
    slim_forecasts = sorted(
        (
            {
                "startTime": r["startTime"],
                "publishTime": r["publishTime"],
                "generation": r["generation"],
            }
            for r in forecasts
        ),
        key=lambda r: (r["startTime"], r["publishTime"]),
    )

    (OUT_DIR / "fuelhh_wind_2026-01.json").write_text(json.dumps(slim_actuals, separators=(",", ":")))
    (OUT_DIR / "windfor_2026-01.json").write_text(json.dumps(slim_forecasts, separators=(",", ":")))
    print(f"actuals: {len(slim_actuals)} rows, forecasts: {len(slim_forecasts)} rows -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
