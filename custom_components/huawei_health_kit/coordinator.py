"""Polling, local daily history and long-term statistics import."""

from __future__ import annotations

import asyncio
import re
from datetime import date, timedelta

from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import HealthKitApi
from .const import (
    BACKFILL_EMPTY_WINDOWS,
    CONF_CATEGORIES,
    DOMAIN,
    LOGGER,
    RECENT_DAYS,
    UPDATE_MINUTES,
)
from .healthkit import (
    MAX_DATA_TYPES,
    MIN_DAY,
    HealthKitAuthError,
    HealthKitError,
    HealthKitScopeError,
    Metric,
    data_types,
    latest,
    metrics_for,
    parse_daily,
    statistic_rows,
    windows,
)

STORE_VERSION = 1

type Daily = dict[str, dict[str, float | list[float]]]


class HealthKitCoordinator(DataUpdateCoordinator[dict[str, tuple[str, float]]]):
    """Reads the last days every 30 minutes, backfills the history once, writes statistics.

    The whole daily history is kept in .storage/huawei_health_kit.<entry_id> so the running
    totals of the sum statistics can always be recomputed from the first day.
    Coordinator data: {metric key: (YYYYMMDD, value)} for the most recent day with data.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: HealthKitApi) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_MINUTES),
        )
        self.api = api
        self.metrics: list[Metric] = metrics_for(entry.data[CONF_CATEGORIES])
        self.denied: set[str] = set()  # data types refused by Huawei (scope not granted)
        self.daily: Daily = {}
        self.backfilled = False
        self._store: Store[dict] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        uid = re.sub(r"[^a-z0-9_]", "_", (entry.unique_id or entry.entry_id).lower())
        self._stat_prefix = f"{DOMAIN}:{uid}_"

    @property
    def active_metrics(self) -> list[Metric]:
        return [m for m in self.metrics if m.data_type not in self.denied]

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.daily = data.get("daily", {})
        self.backfilled = data.get("backfilled", False)

    async def _async_save(self) -> None:
        await self._store.async_save({"daily": self.daily, "backfilled": self.backfilled})

    async def _fetch(self, start: date, end: date) -> Daily:
        """dailyPolymerize for the active data types; a type refused alone is dropped for good."""
        metrics = self.active_metrics
        types = data_types(metrics)
        tz = dt_util.get_default_time_zone()
        out: Daily = {}
        for i in range(0, len(types), MAX_DATA_TYPES):
            chunk = types[i : i + MAX_DATA_TYPES]
            try:
                resp = await self.api.daily_polymerize(chunk, start, end, tz)
            except HealthKitScopeError:
                resp = {"group": []}
                for data_type in chunk:  # find which types are refused
                    try:
                        one = await self.api.daily_polymerize([data_type], start, end, tz)
                    except HealthKitScopeError as err:
                        LOGGER.warning("Huawei refused %s (scope not granted?), ignored: %s", data_type, err)
                        self.denied.add(data_type)
                        continue
                    resp["group"] += one.get("group") or []
            for key, days in parse_daily(resp, metrics, tz).items():
                out.setdefault(key, {}).update(days)
        return out

    def _merge(self, new: Daily) -> set[str]:
        changed = set()
        for key, days in new.items():
            stored = self.daily.setdefault(key, {})
            for day, value in days.items():
                if stored.get(day) != value:
                    stored[day] = value
                    changed.add(key)
        return changed

    def _import_statistics(self, keys: set[str], since: str | None = None) -> None:
        tz = dt_util.get_default_time_zone()
        title = self.config_entry.title
        for metric in self.metrics:
            if metric.key not in keys or not self.daily.get(metric.key):
                continue
            rows = statistic_rows(metric, self.daily[metric.key], tz, since)
            if not rows:
                continue
            is_sum = metric.kind == "sum"
            async_add_external_statistics(
                self.hass,
                {
                    "statistic_id": self._stat_prefix + metric.key,
                    "source": DOMAIN,
                    "name": f"{title} {metric.key.replace('_', ' ')}",
                    "unit_of_measurement": metric.unit,
                    "unit_class": metric.unit_class,
                    "has_sum": is_sum,
                    "mean_type": StatisticMeanType.NONE if is_sum else StatisticMeanType.ARITHMETIC,
                },
                rows,
            )

    async def _async_update_data(self) -> dict[str, tuple[str, float]]:
        end = dt_util.now().date()
        start = end - timedelta(days=RECENT_DAYS - 1)
        try:
            new = await self._fetch(start, end)
        except HealthKitAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except HealthKitError as err:
            raise UpdateFailed(str(err)) from err
        if self.api.health_app_privacy == "2":
            LOGGER.warning(
                "Data sharing with this app is not enabled in the HUAWEI Health app "
                "(Me > Privacy management > Data sharing and authorization): no data is returned"
            )
        changed = self._merge(new)
        if changed:
            await self._async_save()
            self._import_statistics(changed, since=start.strftime("%Y%m%d"))
        return {
            m.key: value
            for m in self.metrics
            if (value := latest(m, self.daily.get(m.key, {}))) is not None
        }

    def start_backfill(self) -> None:
        if not self.backfilled:
            self.config_entry.async_create_background_task(
                self.hass, self._backfill(), f"{DOMAIN} history backfill"
            )

    async def _backfill(self) -> None:
        """Whole history, 30 days per request, newest first, until a year without data."""
        end = dt_util.now().date() - timedelta(days=RECENT_DAYS)
        empty = 0
        count = 0
        for lo, hi in windows(MIN_DAY, end):
            try:
                new = await self._fetch(lo, hi)
            except HealthKitError as err:
                LOGGER.warning("History backfill stopped at %s: %s (retried at next start)", hi, err)
                await self._async_save()
                return
            empty = 0 if any(new.values()) else empty + 1
            self._merge(new)
            count += 1
            if count % 10 == 0:
                await self._async_save()
            if empty >= BACKFILL_EMPTY_WINDOWS:
                break
            await asyncio.sleep(1)
        self.backfilled = True
        await self._async_save()
        # Running totals change when older days are added: rewrite every row.
        self._import_statistics({m.key for m in self.metrics})
        LOGGER.info("History backfill done (%d requests, from %s)", count, lo)
