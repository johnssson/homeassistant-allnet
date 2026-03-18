"""Support for Allnet binary sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _is_binary_like_sensor(sensor_data: dict[str, Any]) -> bool:
    """Return True if the sensor should be represented as binary_sensor."""
    unit = str(sensor_data.get("unit", "")).strip()
    value = str(sensor_data.get("value", "")).strip()

    if unit:
        return False

    return value in {"0", "1", "0.0", "1.0", "0.00", "1.00"}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Allnet binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device = hass.data[DOMAIN][config_entry.entry_id]["device"]

    entities: list[AllnetBinarySensor] = []

    if coordinator.data and "sensors" in coordinator.data:
        for sensor_data in coordinator.data["sensors"]:
            if not _is_binary_like_sensor(sensor_data):
                continue

            try:
                entities.append(AllnetBinarySensor(coordinator, device, sensor_data))
            except Exception as err:
                _LOGGER.error(
                    "Fehler beim Erzeugen des Binärsensors %s (%s): %s",
                    sensor_data.get("id"),
                    sensor_data.get("name"),
                    err,
                )

    async_add_entities(entities)


class AllnetBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an Allnet binary sensor."""

    def __init__(self, coordinator, device, sensor_data: dict[str, Any]) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._device = device
        self._sensor_id = sensor_data["id"]
        self._attr_name = f"Allnet {sensor_data['name']}"
        self._attr_unique_id = f"{device.host}_binary_sensor_{self._sensor_id}"

        sensor_name = str(sensor_data.get("name", "")).lower()

        if "schalteingang" in sensor_name or "anschluss" in sensor_name:
            self._attr_device_class = BinarySensorDeviceClass.OPENING

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data or "sensors" not in self.coordinator.data:
            return None

        for sensor in self.coordinator.data["sensors"]:
            if sensor["id"] == self._sensor_id:
                value = str(sensor.get("value", "")).strip().lower()
                return value in {"1", "1.0", "1.00", "true", "on"}

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data or "sensors" not in self.coordinator.data:
            return {}

        for sensor in self.coordinator.data["sensors"]:
            if sensor["id"] == self._sensor_id:
                return {
                    "sensor_id": sensor["id"],
                    "original_name": sensor["name"],
                    "raw_value": sensor["value"],
                    "unit": sensor.get("unit", ""),
                }

        return {}

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device.host)},
            "name": f"Allnet Device {self._device.host}",
            "manufacturer": "Allnet",
            "model": "ALL3500",
        }
