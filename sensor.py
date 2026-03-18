"""Support for Allnet sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfTemperature
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
    """Set up Allnet sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    device = hass.data[DOMAIN][config_entry.entry_id]["device"]

    entities: list[AllnetSensor] = []

    if coordinator.data and "sensors" in coordinator.data:
        for sensor_data in coordinator.data["sensors"]:
            if _is_binary_like_sensor(sensor_data):
                continue

            try:
                entities.append(AllnetSensor(coordinator, device, sensor_data))
            except Exception as err:
                _LOGGER.error(
                    "Fehler beim Erzeugen des Sensors %s (%s): %s",
                    sensor_data.get("id"),
                    sensor_data.get("name"),
                    err,
                )

    async_add_entities(entities)


class AllnetSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Allnet sensor."""

    _attr_device_class = None
    _attr_state_class = None

    def __init__(self, coordinator, device, sensor_data: dict[str, Any]) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device = device
        self._sensor_id = sensor_data["id"]
        self._attr_name = f"Allnet {sensor_data['name']}"
        self._attr_unique_id = f"{device.host}_sensor_{self._sensor_id}"

        unit = str(sensor_data.get("unit", "")).lower()
        sensor_name = str(sensor_data.get("name", "")).lower()

        if "°c" in unit or unit == "c":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif "°f" in unit or unit == "f":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        elif "%" in unit or "rh" in unit or "feucht" in sensor_name:
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif "hpa" in unit or "mbar" in unit or "druck" in sensor_name:
            self._attr_device_class = SensorDeviceClass.PRESSURE
            self._attr_native_unit_of_measurement = UnitOfPressure.HPA
        elif unit == "pa":
            self._attr_device_class = SensorDeviceClass.PRESSURE
            self._attr_native_unit_of_measurement = UnitOfPressure.PA
        else:
            self._attr_native_unit_of_measurement = sensor_data.get("unit", "")

        if self._attr_device_class is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data or "sensors" not in self.coordinator.data:
            return None

        for sensor in self.coordinator.data["sensors"]:
            if sensor["id"] == self._sensor_id:
                try:
                    return float(sensor["value"])
                except (ValueError, TypeError):
                    return sensor["value"]

        return None

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._device.host)},
            "name": f"Allnet Device {self._device.host}",
            "manufacturer": "Allnet",
            "model": "ALL3500",
        }
