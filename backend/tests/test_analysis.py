from datetime import UTC, date, datetime, timedelta

import pytest

from backend.app import analysis
from backend.app.analysis import Forecast, Row

UTC = UTC


def fc(target, published, mw):
    return Forecast(target=target, published=published, mw=mw)


def test_cutoff_is_previous_day_at_given_uk_hour_winter():
    # In January the UK is on GMT, so local and UTC agree.
    cutoff = analysis.decision_cutoff(date(2026, 1, 15), 9)
    assert cutoff == datetime(2026, 1, 14, 9, 0, tzinfo=UTC)


def test_cutoff_respects_british_summer_time():
    cutoff = analysis.decision_cutoff(date(2026, 7, 15), 9)
    assert cutoff == datetime(2026, 7, 14, 8, 0, tzinfo=UTC)


def test_cutoff_rejects_bad_hour():
    with pytest.raises(ValueError):
        analysis.decision_cutoff(date(2026, 1, 15), 24)


def test_delivery_hours_normal_and_dst_days():
    assert len(analysis.delivery_hours(date(2026, 1, 15))) == 24
    assert len(analysis.delivery_hours(date(2026, 3, 29))) == 23
    assert len(analysis.delivery_hours(date(2026, 10, 25))) == 25


def test_latest_before_picks_most_recent_not_after_cutoff():
    t = datetime(2026, 1, 15, 12, tzinfo=UTC)
    fcs = [
        fc(t, datetime(2026, 1, 13, 22, 30, tzinfo=UTC), 100),
        fc(t, datetime(2026, 1, 14, 7, 30, tzinfo=UTC), 200),
        fc(t, datetime(2026, 1, 14, 9, 30, tzinfo=UTC), 300),
    ]
    chosen = analysis.latest_before(fcs, datetime(2026, 1, 14, 9, 0, tzinfo=UTC))
    assert chosen.mw == 200


def test_latest_before_includes_forecast_published_exactly_at_cutoff():
    t = datetime(2026, 1, 15, 12, tzinfo=UTC)
    cutoff = datetime(2026, 1, 14, 9, 0, tzinfo=UTC)
    assert analysis.latest_before([fc(t, cutoff, 5)], cutoff).mw == 5


def test_latest_before_returns_none_when_nothing_available():
    t = datetime(2026, 1, 15, 12, tzinfo=UTC)
    fcs = [fc(t, datetime(2026, 1, 14, 9, 30, tzinfo=UTC), 300)]
    assert analysis.latest_before(fcs, datetime(2026, 1, 14, 9, 0, tzinfo=UTC)) is None
    assert analysis.latest_before([], datetime(2026, 1, 14, 9, 0, tzinfo=UTC)) is None


def test_decision_rows_ignores_forecasts_published_after_cutoff_and_skips_uncovered_hours():
    day = date(2026, 1, 15)
    t0 = datetime(2026, 1, 15, 0, tzinfo=UTC)
    t1 = t0 + timedelta(hours=1)
    by_target = {
        t0: [
            fc(t0, datetime(2026, 1, 14, 7, 30, tzinfo=UTC), 1000),
            fc(t0, datetime(2026, 1, 14, 11, 30, tzinfo=UTC), 9999),
        ],
        t1: [fc(t1, datetime(2026, 1, 14, 11, 30, tzinfo=UTC), 5555)],  # only after cutoff
    }
    rows = analysis.decision_rows(by_target, {t0: 900.0}, day, 9)
    assert len(rows) == 1
    assert rows[0].forecast_mw == 1000
    assert rows[0].actual_mw == 900
    assert rows[0].error_mw == 100
    assert rows[0].horizon_h == pytest.approx(16.5)


def _row(forecast, actual, hour=0):
    t = datetime(2026, 1, 15, hour, tzinfo=UTC)
    return Row(target=t, forecast_mw=forecast, published=t - timedelta(hours=20), horizon_h=20, actual_mw=actual)


def test_summarize_basic_metrics():
    rows = [_row(110, 100), _row(90, 100), _row(130, 100), _row(100, 100)]
    s = analysis.summarize(rows)
    assert s["n"] == 4
    assert s["mae_mw"] == pytest.approx((10 + 10 + 30 + 0) / 4)
    assert s["bias_mw"] == pytest.approx((10 - 10 + 30 + 0) / 4)
    assert s["rmse_mw"] == pytest.approx(((100 + 100 + 900 + 0) / 4) ** 0.5)
    assert s["mape_pct"] == pytest.approx((10 + 10 + 30 + 0) / 4)


def test_summarize_skips_rows_without_actual_and_handles_empty():
    assert analysis.summarize([]) == {"n": 0}
    assert analysis.summarize([_row(100, None)]) == {"n": 0}
    s = analysis.summarize([_row(100, None), _row(120, 100)])
    assert s["n"] == 1 and s["mae_mw"] == 20


def test_summarize_mape_ignores_zero_actuals():
    s = analysis.summarize([_row(50, 0), _row(110, 100)])
    assert s["mape_pct"] == pytest.approx(10)


def test_quantile_interpolates():
    assert analysis.quantile([0, 10], 0.5) == 5
    assert analysis.quantile([1, 2, 3, 4, 5], 0.9) == pytest.approx(4.6)
    assert analysis.quantile([7], 0.9) == 7
    with pytest.raises(ValueError):
        analysis.quantile([], 0.5)


def test_planning_band_needs_enough_history():
    assert analysis.planning_band([1.0] * (analysis.MIN_SAMPLES_FOR_BAND - 1)) is None
    band = analysis.planning_band(list(range(-50, 50)))
    assert band["samples"] == 100
    assert band["p10_error_mw"] < 0 < band["p90_error_mw"]


def test_error_histogram_counts_every_value():
    errors = [-1500, -200, 0, 300, 1200, 2999]
    bins = analysis.error_histogram(errors, 1000)
    assert sum(b["count"] for b in bins) == len(errors)
    assert bins[0]["from_mw"] == -2000
    assert analysis.error_histogram([]) == []


def test_horizon_profile_buckets_and_drops_negative_horizons():
    target = datetime(2026, 1, 15, 12, tzinfo=UTC)
    by_target = {
        target: [
            fc(target, target - timedelta(hours=30), 110),  # horizon 30 -> bin 24-30? 30//6 = 5 -> 30-36
            fc(target, target - timedelta(hours=2), 105),  # bin 0-6
            fc(target, target + timedelta(hours=1), 100),  # published after target, dropped
        ]
    }
    out = analysis.horizon_profile(by_target, {target: 100.0}, date(2026, 1, 15), date(2026, 1, 15))
    assert [b["from_h"] for b in out] == [0, 30]
    assert out[0]["mae_mw"] == 5
    assert out[1]["mae_mw"] == 10
    assert sum(b["n"] for b in out) == 2


def test_bias_removed_mae_is_smaller_when_errors_share_a_sign():
    rows = [_row(1100, 1000), _row(1120, 1000), _row(1090, 1000)]
    s = analysis.summarize(rows)
    assert s["mae_bias_removed_mw"] < s["mae_mw"]
    # errors 100, 120, 90 -> mean 103.33, absolute deviations 3.33, 16.67, 13.33
    assert s["mae_bias_removed_mw"] == pytest.approx(11.11, abs=0.01)
