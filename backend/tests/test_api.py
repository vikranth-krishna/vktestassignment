from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["actual_points"] == 1488
    assert body["forecast_points"] > 10000
    assert "x-request-id" in r.headers


def test_meta_describes_scope():
    body = client.get("/api/meta").json()
    assert body["first_delivery_day"] == "2026-01-01"
    assert body["last_delivery_day"] == "2026-01-31"
    assert body["default_cutoff_hour"] == 9


def test_forecast_for_a_day_uses_only_forecasts_available_at_cutoff():
    body = client.get("/api/forecast", params={"delivery_day": "2026-01-15"}).json()
    assert body["cutoff"] == "2026-01-14T09:00:00Z"
    assert body["summary"]["hours"] == 24
    for p in body["points"]:
        assert p["published"] <= body["cutoff"]
        assert p["horizon_h"] > 0
        assert p["error_mw"] == p["forecast_mw"] - p["actual_mw"]


def test_forecast_band_is_absent_on_first_day_and_present_later():
    first = client.get("/api/forecast", params={"delivery_day": "2026-01-01"}).json()
    assert first["band"] is None
    assert all(p["low_mw"] is None for p in first["points"])

    later = client.get("/api/forecast", params={"delivery_day": "2026-01-20"}).json()
    assert later["band"]["samples"] >= 24
    for p in later["points"]:
        assert p["low_mw"] <= p["high_mw"]


def test_later_cutoff_can_only_move_to_a_newer_forecast_run():
    early = client.get("/api/forecast", params={"delivery_day": "2026-01-15", "cutoff_hour": 6}).json()
    late = client.get("/api/forecast", params={"delivery_day": "2026-01-15", "cutoff_hour": 20}).json()
    assert max(early["forecast_runs_used"]) <= max(late["forecast_runs_used"])


def test_forecast_out_of_range_is_404():
    assert client.get("/api/forecast", params={"delivery_day": "2026-02-01"}).status_code == 404
    assert client.get("/api/forecast", params={"delivery_day": "2025-12-31"}).status_code == 404


def test_forecast_validates_input():
    assert client.get("/api/forecast").status_code == 422
    assert client.get("/api/forecast", params={"delivery_day": "nonsense"}).status_code == 422
    assert client.get("/api/forecast", params={"delivery_day": "2026-01-15", "cutoff_hour": 30}).status_code == 422


def test_accuracy_full_month():
    body = client.get("/api/accuracy").json()
    o = body["overall"]
    assert o["n"] > 600
    assert o["mae_mw"] > 0
    assert o["rmse_mw"] >= o["mae_mw"]
    assert len(body["by_day"]) == 31
    assert len(body["by_hour"]) == 24
    assert sum(b["count"] for b in body["histogram"]) == o["n"]
    assert body["by_horizon"][0]["from_h"] == 0


def test_accuracy_single_day_and_bad_range():
    one = client.get("/api/accuracy", params={"first_day": "2026-01-10", "last_day": "2026-01-10"}).json()
    assert one["overall"]["n"] == 24
    bad = client.get("/api/accuracy", params={"first_day": "2026-01-10", "last_day": "2026-01-05"})
    assert bad.status_code == 422


def test_openapi_docs_are_served():
    assert client.get("/api/openapi.json").status_code == 200
