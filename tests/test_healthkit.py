"""Unit tests of the pure Health Kit module (no Home Assistant needed)."""

import importlib.util
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_spec = importlib.util.spec_from_file_location(
    "healthkit", Path(__file__).parents[1] / "custom_components/huawei_health_kit/healthkit.py"
)
hk = importlib.util.module_from_spec(_spec)
sys.modules["healthkit"] = hk
_spec.loader.exec_module(hk)

PARIS = ZoneInfo("Europe/Paris")


def ms(y, m, d, h=0):
    return int(datetime(y, m, d, h, tzinfo=PARIS).timestamp() * 1000)


def group(day, data_type, values, original=None):
    point = {"dataTypeName": data_type, "value": [{"fieldName": k, **v} for k, v in values.items()]}
    if original:
        point["originalDataCollectorId"] = original
    return {"startTime": ms(*day), "endTime": ms(*day) + 86400000,
            "sampleSet": [{"dataCollectorId": f"derived:{data_type}:x:polymerized", "samplePoints": [point]}]}


def test_scopes():
    assert hk.scopes_for(["activity", "weight"]) == [
        "openid",
        "https://www.huawei.com/healthkit/step.read",
        "https://www.huawei.com/healthkit/distance.read",
        "https://www.huawei.com/healthkit/calories.read",
        "https://www.huawei.com/healthkit/heightweight.read",
    ]


def test_data_types_distinct():
    types = hk.data_types(hk.metrics_for(["sleep"]))
    assert types == ["com.huawei.continuous.sleep.fragment"]


def test_utc_offset_dst():
    assert hk.utc_offset(PARIS, date(2026, 1, 15)) == "+0100"
    assert hk.utc_offset(PARIS, date(2026, 7, 15)) == "+0200"
    assert hk.utc_offset(ZoneInfo("America/St_Johns"), date(2026, 1, 15)) == "-0330"


def test_windows():
    w = list(hk.windows(date(2026, 1, 1), date(2026, 3, 1)))
    assert w[0] == (date(2026, 1, 31), date(2026, 3, 1))
    assert w[-1][0] == date(2026, 1, 1)
    assert all((hi - lo).days < 30 for lo, hi in w)


def test_daily_body():
    body = hk.daily_body(["a"], date(2026, 10, 1), date(2026, 10, 30), PARIS)
    assert body == {"dataTypes": ["a"], "startDay": "20261001", "endDay": "20261030", "timeZone": "+0100"}


def test_parse_daily():
    resp = {"group": [
        group((2026, 11, 1), "com.huawei.continuous.steps.total", {"steps": {"integerValue": 9000}}),
        group((2026, 11, 1), "com.huawei.continuous.body_weight.statistics",
              {"avg": {"floatValue": 80.2}, "min": {"floatValue": 80.0}, "max": {"floatValue": 80.4}}),
        group((2026, 11, 2), "com.huawei.continuous.sleep.statistics",
              {"all_sleep_time": {"integerValue": 420}, "deep_sleep_time": {"integerValue": 90},
               "fall_asleep_time": {"longValue": 1}}),
        group((2026, 11, 2), "com.huawei.continuous.steps.total", {"steps": {"integerValue": 0}}),
    ]}
    out = hk.parse_daily(resp, hk.metrics_for(["activity", "weight", "sleep"]), PARIS)
    assert out["steps"] == {"20261101": 9000.0}
    assert out["weight"] == {"20261101": [80.2, 80.0, 80.4]}
    assert out["sleep_total"] == {"20261102": [420.0, 420.0, 420.0]}
    assert out["sleep_deep"] == {"20261102": [90.0, 90.0, 90.0]}


def test_parse_daily_by_original_collector():
    resp = {"group": [group((2026, 11, 1), "unknown", {"steps": {"integerValue": 5}},
                            original="raw:com.huawei.continuous.steps.delta:app:huawei:watch:1")]}
    assert hk.parse_daily(resp, hk.metrics_for(["activity"]), PARIS)["steps"] == {"20261101": 5.0}


def test_statistic_rows_sum_running_total():
    steps = next(m for m in hk.METRICS if m.key == "steps")
    rows = hk.statistic_rows(steps, {"20261102": 200.0, "20261101": 100.0, "20261103": 50.0}, PARIS, since="20261102")
    assert [(r["start"].day, r["start"].hour, r["state"], r["sum"]) for r in rows] == [(2, 23, 200.0, 300.0), (3, 23, 50.0, 350.0)]


def test_statistic_rows_mean_and_latest():
    weight = next(m for m in hk.METRICS if m.key == "weight")
    days = {"20261101": [80.2, 80.0, 80.4], "20261103": [79.9, 79.9, 79.9]}
    rows = hk.statistic_rows(weight, days, PARIS)
    assert rows[0] == {"start": datetime(2026, 11, 1, 12, tzinfo=PARIS), "mean": 80.2, "min": 80.0, "max": 80.4}
    assert hk.latest(weight, days) == ("20261103", 79.9)
    assert hk.latest(weight, {}) is None
