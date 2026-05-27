"""FS USB Beacon light platform."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BEACON_PID,
    BEACON_VID,
    CONF_DEFAULT_EFFECT,
    CONF_KEEPALIVE_INTERVAL,
    DEFAULT_EFFECT,
    DOMAIN,
    EFFECT_STROBE,
    EFFECTS,
    KEEPALIVE_INTERVAL,
    PAYLOAD_OFF,
    PAYLOAD_SPIN,
    PAYLOAD_STROBE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the FS USB Beacon light entity."""
    device = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FsUsbBeaconLight(device, entry)])


class FsUsbBeaconLight(LightEntity):
    """Representation of the Giants Software FS22 USB Beacon as a light.

    The beacon is a fixed-orange LED light with two animation modes:
    - Spin  : rotating beacon effect
    - Strobe: rapid blinking effect

    The device auto-offs after ~10 s without a command, so a keepalive
    task re-sends the active HID report every KEEPALIVE_INTERVAL seconds.
    """

    _attr_has_entity_name = True
    _attr_name = None  # entity name == device name
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes: set[ColorMode] = {ColorMode.ONOFF}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECTS
    _attr_should_poll = False

    def __init__(self, device: Any, entry: ConfigEntry) -> None:
        """Initialise the light entity."""
        self._device = device
        self._entry = entry
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_is_on = False
        self._attr_effect: str | None = str(
            entry.options.get(CONF_DEFAULT_EFFECT, DEFAULT_EFFECT)
        )
        self._keepalive_interval: int = int(
            entry.options.get(CONF_KEEPALIVE_INTERVAL, KEEPALIVE_INTERVAL)
        )
        self._keepalive_task: asyncio.Task | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name="FS USB Beacon",
            manufacturer="Giants Software",
            model="FS22 USB Beacon",
            configuration_url="https://github.com/Brisket604/homeassistant-fs-usb-beacon",
        )
        _LOGGER.debug(
            "Light entity initialised entry_id=%s default_effect=%s keepalive_interval=%ss",
            entry.entry_id,
            self._attr_effect,
            self._keepalive_interval,
        )

    # ------------------------------------------------------------------
    # HA light interface
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the beacon on, optionally switching to the requested effect."""
        self._attr_is_on = True

        if ATTR_EFFECT in kwargs:
            requested = str(kwargs[ATTR_EFFECT])
            if requested in EFFECTS:
                self._attr_effect = requested
            else:
                _LOGGER.debug("Ignoring unsupported effect request: %s", requested)
        elif self._attr_effect is None:
            self._attr_effect = str(self._entry.options.get(CONF_DEFAULT_EFFECT, DEFAULT_EFFECT))

        _LOGGER.debug("Turning beacon on with effect=%s", self._attr_effect)

        payload = self._current_payload()
        try:
            await self.hass.async_add_executor_job(self._write_payload, payload)
        except OSError:
            _LOGGER.error("Failed to send command to FS USB Beacon")

        self._start_keepalive()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the beacon off."""
        self._attr_is_on = False
        _LOGGER.debug("Turning beacon off")
        self._stop_keepalive()
        try:
            await self.hass.async_add_executor_job(self._write_payload, PAYLOAD_OFF)
        except OSError:
            _LOGGER.error("Failed to send off command to FS USB Beacon")
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Keepalive loop
    # ------------------------------------------------------------------

    def _start_keepalive(self) -> None:
        """Start (or restart) the keepalive background task."""
        self._stop_keepalive()
        _LOGGER.debug("Starting keepalive task interval=%ss", self._keepalive_interval)
        self._keepalive_task = self.hass.loop.create_task(self._keepalive_loop())

    def _stop_keepalive(self) -> None:
        """Cancel the keepalive task if it is running."""
        if self._keepalive_task and not self._keepalive_task.done():
            _LOGGER.debug("Stopping keepalive task")
            self._keepalive_task.cancel()
        self._keepalive_task = None

    async def _keepalive_loop(self) -> None:
        """Re-send the current HID report every KEEPALIVE_INTERVAL seconds.

        The beacon hardware auto-offs after ~10 s without a command; this loop
        keeps it alive while ``_attr_is_on`` is True.
        """
        try:
            while True:
                await asyncio.sleep(self._keepalive_interval)
                if self._attr_is_on:
                    try:
                        _LOGGER.debug("Sending keepalive payload for effect=%s", self._attr_effect)
                        await self.hass.async_add_executor_job(
                            self._write_payload, self._current_payload()
                        )
                    except OSError:
                        _LOGGER.warning(
                            "FS USB Beacon keepalive write failed — "
                            "the device may have been unplugged"
                        )
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # HA entity lifecycle
    # ------------------------------------------------------------------

    async def async_will_remove_from_hass(self) -> None:
        """Stop the keepalive task when the entity is removed."""
        self._stop_keepalive()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current_payload(self) -> bytes:
        """Return the HID payload that matches the currently selected effect."""
        if self._attr_effect == EFFECT_STROBE:
            return PAYLOAD_STROBE
        return PAYLOAD_SPIN  # default / EFFECT_SPIN

    def _write_payload(self, payload: bytes) -> None:
        """Write a HID output report to the device.

        This is a blocking call and must always be dispatched via
        ``hass.async_add_executor_job``.
        """
        _LOGGER.debug("Writing HID payload length=%s", len(payload))
        self._device.write(payload)
