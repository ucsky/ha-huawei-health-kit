"""Config flow: pick the data categories, then OAuth2 with the user's Huawei Developers app."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import CONF_CATEGORIES, DOMAIN, LOGGER
from .healthkit import CATEGORIES, DEFAULT_CATEGORIES, scopes_for


def _id_token_subject(token: dict) -> str | None:
    """User id (sub) from the OpenID id_token; only used as unique id, so not verified."""
    id_token = token.get("id_token")
    if not id_token or id_token.count(".") != 2:
        return None
    payload = id_token.split(".")[1]
    try:
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("sub")
    except ValueError:
        return None


class OAuth2FlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Huawei ID OAuth2 (authorization code, offline access for a refresh token)."""

    DOMAIN = DOMAIN
    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._categories: list[str] = list(DEFAULT_CATEGORIES)

    @property
    def logger(self):
        return LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        return {"scope": " ".join(scopes_for(self._categories)), "access_type": "offline"}

    def _categories_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_CATEGORIES, default=self._categories): SelectSelector(
                    SelectSelectorConfig(
                        options=list(CATEGORIES),
                        multiple=True,
                        translation_key=CONF_CATEGORIES,
                    )
                )
            }
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=self._categories_schema())
        self._categories = user_input[CONF_CATEGORIES]
        return await self.async_step_pick_implementation()

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._categories = list(entry_data.get(CONF_CATEGORIES, DEFAULT_CATEGORIES))
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_pick_implementation()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        uid = _id_token_subject(data["token"])
        if uid is None:
            return self.async_abort(reason="no_user_id")
        await self.async_set_unique_id(uid)
        data[CONF_CATEGORIES] = self._categories
        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates=data)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Huawei Health", data=data)
