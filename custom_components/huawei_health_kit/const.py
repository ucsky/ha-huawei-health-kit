"""Constants of the HA Activity Bridge integration."""

import logging

DOMAIN = "huawei_health_kit"
LOGGER = logging.getLogger(__package__)

CONF_CATEGORIES = "categories"

VERSION = "0.1.0"
# x-version header: "OS_App type_Version" (Health Kit common parameters).
X_VERSION = f"ha_activity_bridge_{VERSION}"

UPDATE_MINUTES = 30
RECENT_DAYS = 7  # days re-read at every update (late syncs from the watch)
BACKFILL_EMPTY_WINDOWS = 12  # stop the history backfill after this many empty 30-day windows
