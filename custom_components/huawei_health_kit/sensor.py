"""Sensors: latest daily value of each metric.

The history lives in the integration's external statistics (huawei_health_kit:<user>_<metric>),
so these sensors have no state_class: the recorder does not build a second, partial history.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfMass, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HealthKitConfigEntry
from .const import DOMAIN
from .coordinator import HealthKitCoordinator
from .healthkit import Metric

UNITS = {
    "m": (UnitOfLength.METERS, SensorDeviceClass.DISTANCE),
    "kg": (UnitOfMass.KILOGRAMS, SensorDeviceClass.WEIGHT),
    "°C": (UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    "min": (UnitOfTime.MINUTES, SensorDeviceClass.DURATION),
    "%": (PERCENTAGE, None),
}
ICONS = {
    "steps": "mdi:shoe-print",
    "calories": "mdi:fire",
    "heart_rate": "mdi:heart-pulse",
    "resting_heart_rate": "mdi:heart",
    "stress": "mdi:head-alert",
    "spo2": "mdi:water-percent",
    "sleep_wakeup_count": "mdi:sleep-off",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HealthKitConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(HealthKitSensor(coordinator, metric) for metric in coordinator.metrics)


class HealthKitSensor(CoordinatorEntity[HealthKitCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HealthKitCoordinator, metric: Metric) -> None:
        super().__init__(coordinator)
        self.metric = metric
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.unique_id}_{metric.key}"
        self._attr_translation_key = metric.key
        unit, device_class = UNITS.get(metric.unit or "", (metric.unit, None))
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_icon = ICONS.get(metric.key, "mdi:sleep" if metric.category == "sleep" else None)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="Huawei",
            model="Health Kit",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        return super().available and self.metric.data_type not in self.coordinator.denied

    @property
    def native_value(self) -> float | None:
        value = (self.coordinator.data or {}).get(self.metric.key)
        return value[1] if value else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        value = (self.coordinator.data or {}).get(self.metric.key)
        if not value:
            return {}
        day = value[0]
        return {"date": f"{day[:4]}-{day[4:6]}-{day[6:]}"}
