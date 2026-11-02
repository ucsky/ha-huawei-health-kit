"""Huawei Health through the official Health Kit cloud API."""

from __future__ import annotations

from aiohttp import ClientError, ClientResponseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow

from .api import HealthKitApi
from .coordinator import HealthKitCoordinator

PLATFORMS = [Platform.SENSOR]

type HealthKitConfigEntry = ConfigEntry[HealthKitCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HealthKitConfigEntry) -> bool:
    try:
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)
    except config_entry_oauth2_flow.ImplementationUnavailableError as err:
        raise ConfigEntryNotReady("OAuth implementation not available") from err
    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    try:
        await session.async_ensure_token_valid()
    except ClientResponseError as err:
        if 400 <= err.status < 500:
            raise ConfigEntryAuthFailed("Huawei refused the refresh token") from err
        raise ConfigEntryNotReady from err
    except ClientError as err:
        raise ConfigEntryNotReady from err

    coordinator = HealthKitCoordinator(hass, entry, HealthKitApi(session, getattr(implementation, "client_id", None)))
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_backfill()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HealthKitConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
