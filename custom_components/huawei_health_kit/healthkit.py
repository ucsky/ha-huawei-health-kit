"""Huawei Health Kit cloud API: metric catalogue and response parsing.

Pure Python (no Home Assistant import) so it can be unit tested on its own.

Reference: HMS Core Health Kit, "Accessing Health Kit via the HTTP RESTful API" and
"Querying Sampling Data by Day" (POST /healthkit/v1/sampleSet:dailyPolymerize).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

OAUTH2_AUTHORIZE = "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize"
OAUTH2_TOKEN = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
API_BASE = "https://health-api.cloud.huawei.com/healthkit/v1"
DAILY_POLYMERIZE = "/sampleSet:dailyPolymerize"

# dailyPolymerize limits: startDay >= 20140101, endDay - startDay <= 30 days, <= 20 data types.
MIN_DAY = date(2014, 1, 1)
MAX_WINDOW_DAYS = 30
MAX_DATA_TYPES = 20

SCOPE_PREFIX = "https://www.huawei.com/healthkit/"

# Data categories the user can pick at setup -> Health Kit read scopes.
# Huawei refuses every category except "activity" to individual developer accounts: health data
# (height/weight, heart rate, sleep, stress, SpO2, body temperature) is only granted to
# enterprise accounts (Health Kit application rejected for this reason on 2026-11-09).
CATEGORIES: dict[str, tuple[str, ...]] = {
    "activity": ("step.read", "distance.read", "calories.read"),
    "weight": ("heightweight.read",),
    "heart_rate": ("heartrate.read",),
    "sleep": ("sleep.read",),
    "stress": ("stress.read",),
    "spo2": ("oxygensaturation.read",),
    "body_temperature": ("bodytemperature.read",),
}
ENTERPRISE_ONLY_CATEGORIES = frozenset(CATEGORIES) - {"activity"}
DEFAULT_CATEGORIES = ("activity",)


@dataclass(frozen=True, slots=True)
class Metric:
    """One value per day extracted from a dailyPolymerize group."""

    key: str
    category: str
    data_type: str  # atomic data type sent in the request
    field: str  # field of the statistical data type in the response (the daily value)
    kind: str  # "sum" (daily total) or "mean" (daily average)
    unit: str | None
    unit_class: str | None = None
    min_field: str | None = None
    max_field: str | None = None


METRICS: tuple[Metric, ...] = (
    Metric("steps", "activity", "com.huawei.continuous.steps.delta", "steps", "sum", "steps"),
    Metric("distance", "activity", "com.huawei.continuous.distance.delta", "distance", "sum", "m", "distance"),
    Metric("calories", "activity", "com.huawei.continuous.calories.burnt", "calories_total", "sum", "kcal"),
    Metric("weight", "weight", "com.huawei.instantaneous.body_weight", "avg", "mean", "kg", "mass", "min", "max"),
    Metric("heart_rate", "heart_rate", "com.huawei.instantaneous.heart_rate", "avg", "mean", "bpm", None, "min", "max"),
    Metric("resting_heart_rate", "heart_rate", "com.huawei.instantaneous.resting_heart_rate", "avg", "mean", "bpm"),
    Metric("stress", "stress", "com.huawei.instantaneous.stress", "avg", "mean", None),
    Metric("spo2", "spo2", "com.huawei.instantaneous.spo2", "saturation_avg", "mean", "%"),
    Metric("body_temperature", "body_temperature", "com.huawei.instantaneous.body.temperature", "avg", "mean", "°C", "temperature"),
    # Sleep: com.huawei.continuous.sleep.statistics, durations in minutes.
    Metric("sleep_total", "sleep", "com.huawei.continuous.sleep.fragment", "all_sleep_time", "mean", "min", "duration"),
    Metric("sleep_deep", "sleep", "com.huawei.continuous.sleep.fragment", "deep_sleep_time", "mean", "min", "duration"),
    Metric("sleep_light", "sleep", "com.huawei.continuous.sleep.fragment", "light_sleep_time", "mean", "min", "duration"),
    Metric("sleep_rem", "sleep", "com.huawei.continuous.sleep.fragment", "dream_time", "mean", "min", "duration"),
    Metric("sleep_awake", "sleep", "com.huawei.continuous.sleep.fragment", "awake_time", "mean", "min", "duration"),
    Metric("sleep_wakeup_count", "sleep", "com.huawei.continuous.sleep.fragment", "wakeup_count", "mean", None),
)


class HealthKitError(Exception):
    """Base error of the Health Kit API."""


class HealthKitAuthError(HealthKitError):
    """The access token is invalid or revoked (HTTP 401)."""


class HealthKitScopeError(HealthKitError):
    """A data type is not covered by the granted scopes (HTTP 403)."""


def scopes_for(categories: Iterable[str]) -> list[str]:
    """OAuth scopes for the chosen categories (openid gives the user id in the id_token)."""
    scopes = ["openid"]
    for category in categories:
        scopes += [SCOPE_PREFIX + s for s in CATEGORIES[category] if SCOPE_PREFIX + s not in scopes]
    return scopes


def metrics_for(categories: Iterable[str]) -> list[Metric]:
    chosen = set(categories)
    return [m for m in METRICS if m.category in chosen]


def data_types(metrics: Iterable[Metric]) -> list[str]:
    """Distinct atomic data types of the metrics, in catalogue order."""
    return list(dict.fromkeys(m.data_type for m in metrics))


def utc_offset(tz: tzinfo, day: date) -> str:
    """Huawei time zone format (+0100) of `tz` at noon of `day`."""
    offset = datetime(day.year, day.month, day.day, 12, tzinfo=tz).utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    return f"{sign}{abs(minutes) // 60:02d}{abs(minutes) % 60:02d}"


def windows(start: date, end: date, size: int = MAX_WINDOW_DAYS) -> Iterator[tuple[date, date]]:
    """[start, end] split in windows of at most `size` days, most recent first."""
    hi = end
    while hi >= start:
        lo = max(start, hi - timedelta(days=size - 1))
        yield lo, hi
        hi = lo - timedelta(days=1)


def daily_body(types: list[str], start: date, end: date, tz: tzinfo) -> dict:
    return {
        "dataTypes": types,
        "startDay": start.strftime("%Y%m%d"),
        "endDay": end.strftime("%Y%m%d"),
        "timeZone": utc_offset(tz, end),
    }


def _field_values(point: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for value in point.get("value") or []:
        for kind in ("integerValue", "floatValue", "longValue"):
            if value.get(kind) is not None:
                out[value["fieldName"]] = float(value[kind])
                break
    return out


def parse_daily(response: dict, metrics: Iterable[Metric], tz: tzinfo) -> dict[str, dict[str, float | list[float]]]:
    """dailyPolymerize response -> {metric key: {"YYYYMMDD": value}}.

    Sum metrics store the day total; mean metrics store [mean, min, max]. Several sample points
    in the same day (several devices) keep the largest total, and the last point for means.
    Missing or non-positive values mean "not measured" and are skipped.
    """
    by_type: dict[str, list[Metric]] = {}
    for metric in metrics:
        by_type.setdefault(metric.data_type, []).append(metric)
    out: dict[str, dict[str, float | list[float]]] = {}
    for group in response.get("group") or []:
        day = datetime.fromtimestamp(group["startTime"] / 1000, tz).strftime("%Y%m%d")
        for sample_set in group.get("sampleSet") or []:
            for point in sample_set.get("samplePoints") or []:
                atomic = _atomic_of(sample_set, point)
                fields = _field_values(point)
                for metric in by_type.get(atomic, []):
                    value = fields.get(metric.field)
                    if value is None or value <= 0:
                        continue
                    days = out.setdefault(metric.key, {})
                    if metric.kind == "sum":
                        days[day] = max(value, float(days.get(day, 0)))
                    else:
                        low = fields.get(metric.min_field, value) if metric.min_field else value
                        high = fields.get(metric.max_field, value) if metric.max_field else value
                        days[day] = [value, low, high]
    return out


# Statistical data type returned for each atomic data type (Health Kit "Mapping Between
# Statistical Data Types and Atomic Data Types").
STATISTICAL_TO_ATOMIC = {
    "com.huawei.continuous.steps.total": "com.huawei.continuous.steps.delta",
    "com.huawei.continuous.distance.total": "com.huawei.continuous.distance.delta",
    "com.huawei.continuous.calories.burnt.total": "com.huawei.continuous.calories.burnt",
    "com.huawei.continuous.heart_rate.statistics": "com.huawei.instantaneous.heart_rate",
    "com.huawei.continuous.body_weight.statistics": "com.huawei.instantaneous.body_weight",
    "com.huawei.continuous.sleep.statistics": "com.huawei.continuous.sleep.fragment",
    "com.huawei.continuous.spo2.statistics": "com.huawei.instantaneous.spo2",
    "com.huawei.instantaneous.stress.statistics": "com.huawei.instantaneous.stress",
    "com.huawei.continuous.resting_heart_rate.statistics": "com.huawei.instantaneous.resting_heart_rate",
    "com.huawei.continuous.body.temperature.statistics": "com.huawei.instantaneous.body.temperature",
}


def _atomic_of(sample_set: dict, point: dict) -> str:
    name = point.get("dataTypeName", "")
    if name in STATISTICAL_TO_ATOMIC:
        return STATISTICAL_TO_ATOMIC[name]
    # originalDataCollectorId "raw:<atomic type>:...", dataCollectorId "derived:<statistical type>:..."
    parts = (point.get("originalDataCollectorId") or "").split(":")
    if len(parts) > 1:
        return parts[1]
    parts = (sample_set.get("dataCollectorId") or "").split(":")
    return STATISTICAL_TO_ATOMIC.get(parts[1], parts[1]) if len(parts) > 1 else name


def statistic_rows(metric: Metric, days: dict[str, float | list[float]], tz: tzinfo, since: str | None = None) -> list[dict]:
    """Long-term statistics rows for one metric, from its whole daily history.

    Sums: one row per day at 23:00 local time, state = day total, sum = running total (so the
    running total must be computed from the first day, even if only rows >= `since` are returned).
    Means: one row per day at 12:00 local time with mean/min/max.
    """
    rows = []
    running = 0.0
    for day in sorted(days):
        d = datetime.strptime(day, "%Y%m%d")
        if metric.kind == "sum":
            running += float(days[day])
            start = datetime(d.year, d.month, d.day, 23, tzinfo=tz)
            row = {"start": start, "state": float(days[day]), "sum": round(running, 3)}
        else:
            mean, low, high = days[day]
            start = datetime(d.year, d.month, d.day, 12, tzinfo=tz)
            row = {"start": start, "mean": mean, "min": low, "max": high}
        if since is None or day >= since:
            rows.append(row)
    return rows


def latest(metric: Metric, days: dict[str, float | list[float]]) -> tuple[str, float] | None:
    """Most recent day with a value, and that value (the mean for mean metrics)."""
    if not days:
        return None
    day = max(days)
    value = days[day]
    return day, float(value[0] if isinstance(value, list) else value)
