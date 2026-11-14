"""Application credentials: the user's own Huawei Developers app (client id / secret)."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .healthkit import OAUTH2_AUTHORIZE, OAUTH2_TOKEN


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    return AuthorizationServer(authorize_url=OAUTH2_AUTHORIZE, token_url=OAUTH2_TOKEN)


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    return {
        "console_url": "https://developer.huawei.com/consumer/en/console",
        "redirect_url": "https://my.home-assistant.io/redirect/oauth",
        "docs_url": "https://github.com/ucsky/ha-activity-bridge#setup",
    }
