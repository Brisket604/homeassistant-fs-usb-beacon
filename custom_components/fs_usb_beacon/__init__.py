"""FS USB Beacon integration setup."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .transport import open_beacon_transport

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["light"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FS USB Beacon from a config entry."""
    vid: int = entry.data["vid"]
    pid: int = entry.data["pid"]

    _LOGGER.debug(
        "Setting up FS USB Beacon entry_id=%s for %04x:%04x with options=%s",
        entry.entry_id,
        vid,
        pid,
        entry.options,
    )

    try:
        device = await hass.async_add_executor_job(open_beacon_transport, vid, pid)
    except OSError as err:
        _LOGGER.debug(
            "Transport open failed for %04x:%04x: %s",
            vid,
            pid,
            err,
        )
        raise ConfigEntryNotReady(
            f"Cannot open USB HID device {vid:#06x}:{pid:#06x} — "
            "check the beacon is plugged in and you have HID access permissions"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = device
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("FS USB Beacon setup complete for entry_id=%s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and close the HID device."""
    _LOGGER.debug("Unloading FS USB Beacon entry_id=%s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        device = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(device.close)
        _LOGGER.debug("Closed transport for entry_id=%s", entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry options updates by reloading the entry."""
    _LOGGER.debug(
        "Options updated for entry_id=%s, reloading integration with options=%s",
        entry.entry_id,
        entry.options,
    )
    await hass.config_entries.async_reload(entry.entry_id)
