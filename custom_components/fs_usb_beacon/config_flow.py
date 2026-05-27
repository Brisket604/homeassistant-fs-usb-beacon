"""Config flow for FS USB Beacon."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    BEACON_PID,
    BEACON_VID,
    CONF_DEFAULT_EFFECT,
    CONF_KEEPALIVE_INTERVAL,
    DEFAULT_EFFECT,
    DOMAIN,
    EFFECTS,
    KEEPALIVE_INTERVAL,
)
from .transport import open_beacon_transport

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeassistant.components.usb import UsbServiceInfo


@config_entries.HANDLERS.register(DOMAIN)
class FsUsbBeaconConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for the FS USB Beacon."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return FsUsbBeaconOptionsFlow(config_entry)

    def __init__(self) -> None:
        """Initialise flow state."""
        self._vid: int = BEACON_VID
        self._pid: int = BEACON_PID

    # ------------------------------------------------------------------
    # USB auto-discovery path
    # ------------------------------------------------------------------

    async def async_step_usb(
        self, discovery_info: UsbServiceInfo
    ) -> FlowResult:
        """Handle USB auto-discovery triggered by the manifest usb table."""
        _LOGGER.debug("USB discovery received: %s", discovery_info)
        self._vid = int(str(discovery_info.vid), 16)
        self._pid = int(str(discovery_info.pid), 16)

        # Prefer the serial number as unique_id so entries survive port changes.
        unique_id = (
            discovery_info.serial_number
            if discovery_info.serial_number
            else f"{str(discovery_info.vid).lower()}:{str(discovery_info.pid).lower()}"
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        _LOGGER.debug(
            "USB discovery accepted for %04x:%04x unique_id=%s",
            self._vid,
            self._pid,
            unique_id,
        )

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask the user to confirm a discovered device before creating an entry."""
        if user_input is not None:
            _LOGGER.debug(
                "Discovery confirmed by user for %04x:%04x",
                self._vid,
                self._pid,
            )
            return self.async_create_entry(
                title=f"FS USB Beacon {self._vid:04x}:{self._pid:04x}",
                data={"vid": self._vid, "pid": self._pid},
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "vid": f"{self._vid:04x}",
                "pid": f"{self._pid:04x}",
            },
        )

    # ------------------------------------------------------------------
    # Manual setup path
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual setup initiated from the UI."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                vid = int(user_input["vid"].strip(), 16)
                pid = int(user_input["pid"].strip(), 16)
            except ValueError:
                _LOGGER.debug("Manual setup rejected due to invalid VID/PID input")
                errors["base"] = "invalid_vid_pid"
            else:
                _LOGGER.debug("Manual setup test for %04x:%04x", vid, pid)
                try:
                    await self.hass.async_add_executor_job(_test_device, vid, pid)
                except OSError:
                    _LOGGER.debug("Manual setup connection failed for %04x:%04x", vid, pid)
                    errors["base"] = "cannot_connect"
                else:
                    vid_str = f"{vid:04x}"
                    pid_str = f"{pid:04x}"
                    await self.async_set_unique_id(f"{vid_str}:{pid_str}")
                    self._abort_if_unique_id_configured()
                    _LOGGER.debug("Manual setup succeeded for %s:%s", vid_str, pid_str)
                    return self.async_create_entry(
                        title=f"FS USB Beacon {vid_str}:{pid_str}",
                        data={"vid": vid, "pid": pid},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("vid", default="340d"): str,
                    vol.Required("pid", default="1710"): str,
                }
            ),
            errors=errors,
        )


def _test_device(vid: int, pid: int) -> None:
    """Attempt to open and immediately close the HID device. Blocking."""
    transport = open_beacon_transport(vid, pid)
    transport.close()


class FsUsbBeaconOptionsFlow(config_entries.OptionsFlow):
    """Handle options for FS USB Beacon."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage FS USB Beacon options."""
        if user_input is not None:
            keepalive = int(user_input[CONF_KEEPALIVE_INTERVAL])
            default_effect = str(user_input[CONF_DEFAULT_EFFECT])

            _LOGGER.debug(
                "Saving options for entry_id=%s: default_effect=%s keepalive_interval=%s",
                self._config_entry.entry_id,
                default_effect,
                keepalive,
            )
            return self.async_create_entry(
                title="",
                data={
                    CONF_DEFAULT_EFFECT: default_effect,
                    CONF_KEEPALIVE_INTERVAL: keepalive,
                },
            )

        current_effect = self._config_entry.options.get(CONF_DEFAULT_EFFECT, DEFAULT_EFFECT)
        current_keepalive = int(
            self._config_entry.options.get(CONF_KEEPALIVE_INTERVAL, KEEPALIVE_INTERVAL)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEFAULT_EFFECT,
                        default=current_effect,
                    ): vol.In(EFFECTS),
                    vol.Required(
                        CONF_KEEPALIVE_INTERVAL,
                        default=current_keepalive,
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=9)),
                }
            ),
        )
