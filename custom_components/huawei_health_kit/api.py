"""Authenticated Health Kit cloud client (token handled by Home Assistant's OAuth2Session)."""

from __future__ import annotations

from datetime import date, tzinfo
from uuid import uuid4

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import X_VERSION
from .healthkit import (
    API_BASE,
    DAILY_POLYMERIZE,
    HealthKitAuthError,
    HealthKitError,
    HealthKitScopeError,
    daily_body,
)


class HealthKitApi:
    """Calls to https://health-api.cloud.huawei.com/healthkit/v1."""

    def __init__(self, session: OAuth2Session, client_id: str | None) -> None:
        self._session = session
        self._client_id = client_id
        # x-health-app-privacy of the last response: 1 granted in the Health app, 2 not granted,
        # 3 not a Health app user.
        self.health_app_privacy: str | None = None

    async def _post(self, path: str, body: dict) -> dict:
        await self._session.async_ensure_token_valid()
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "x-version": X_VERSION,
            "x-caller-trace-id": uuid4().hex,
        }
        if self._client_id:
            headers["x-client-id"] = str(self._client_id)
        resp = await self._session.async_request("post", API_BASE + path, json=body, headers=headers)
        self.health_app_privacy = resp.headers.get("x-health-app-privacy", self.health_app_privacy)
        if resp.status == 401:
            raise HealthKitAuthError(await resp.text())
        if resp.status == 403:
            raise HealthKitScopeError(await resp.text())
        if resp.status >= 400:
            raise HealthKitError(f"HTTP {resp.status}: {await resp.text()}")
        return await resp.json(content_type=None)

    async def daily_polymerize(self, types: list[str], start: date, end: date, tz: tzinfo) -> dict:
        """One aggregated value per day and data type, start..end (at most 30 days)."""
        return await self._post(DAILY_POLYMERIZE, daily_body(types, start, end, tz))
