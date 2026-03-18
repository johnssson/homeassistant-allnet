"""The Allnet integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .allnet_api import AllnetDevice
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Allnet from a config entry."""
    host = entry.data["host"]
    username = entry.data["username"]
    password = entry.data["password"]

    device = AllnetDevice(host, username, password)

    try:
        await hass.async_add_executor_job(device.get_device_info)
    except Exception as err:
        _LOGGER.error("Could not connect to Allnet device: %s", err)
        raise ConfigEntryNotReady from err

    async def async_update_data():
        """Fetch data from Allnet device."""
        try:
            sensors = await hass.async_add_executor_job(device.get_all_sensors)
            actors = await hass.async_add_executor_job(device.get_all_actors)
            return {"sensors": sensors, "actors": actors}
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Allnet device: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"allnet_{host}",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "device": device,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
