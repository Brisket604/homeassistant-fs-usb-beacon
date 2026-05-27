"""Transport layer for talking to the FS USB Beacon."""
from __future__ import annotations

from dataclasses import dataclass
import glob
import logging
import os


_LOGGER = logging.getLogger(__name__)


class BeaconTransport:
    """Minimal transport interface used by the integration."""

    def write(self, payload: bytes) -> None:
        """Write one HID payload to the device."""

    def close(self) -> None:
        """Close transport resources."""


@dataclass(slots=True)
class LinuxHidrawTransport(BeaconTransport):
    """Native Linux hidraw transport using only the Python standard library."""

    fd: int

    def write(self, payload: bytes) -> None:
        os.write(self.fd, payload)

    def close(self) -> None:
        os.close(self.fd)


@dataclass(slots=True)
class PyHidTransport(BeaconTransport):
    """Fallback transport backed by the optional ``hid`` package."""

    device: object

    def write(self, payload: bytes) -> None:
        # pyhid accepts a list of ints for report bytes.
        self.device.write(list(payload))

    def close(self) -> None:
        self.device.close()


def open_beacon_transport(vid: int, pid: int) -> BeaconTransport:
    """Open a beacon transport.

    Strategy:
    1) Linux hidraw (no external Python dependency)
    2) Optional ``hid`` package fallback
    """
    first_error: OSError | None = None
    _LOGGER.debug("Opening beacon transport for %04x:%04x", vid, pid)

    if os.name == "posix":
        try:
            _LOGGER.debug("Trying Linux hidraw transport")
            return _open_linux_hidraw_transport(vid, pid)
        except OSError as err:
            first_error = err
            _LOGGER.debug("Linux hidraw transport failed: %s", err)

    try:
        _LOGGER.debug("Trying optional pyhid transport")
        return _open_pyhid_transport(vid, pid)
    except OSError as err:
        if first_error is not None:
            raise OSError(f"{first_error}; fallback via hid failed: {err}") from err
        raise


def _open_linux_hidraw_transport(vid: int, pid: int) -> LinuxHidrawTransport:
    """Find and open a matching Linux ``/dev/hidrawX`` node."""
    expected = f"{vid:04X}:{pid:04X}"
    for sys_node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        uevent_path = os.path.join(sys_node, "device", "uevent")
        if not os.path.exists(uevent_path):
            continue

        with open(uevent_path, encoding="utf-8") as file_obj:
            uevent = file_obj.read()

        hid_id_prefix = "HID_ID="
        hid_id_line = next(
            (line for line in uevent.splitlines() if line.startswith(hid_id_prefix)),
            None,
        )
        if hid_id_line is None:
            continue

        # HID_ID format: BUS:VID:PID (all hex), example 0003:0000340D:00001710
        parts = hid_id_line.removeprefix(hid_id_prefix).split(":")
        if len(parts) != 3:
            continue
        candidate = f"{parts[1][-4:]}:{parts[2][-4:]}".upper()
        if candidate != expected:
            continue

        dev_name = os.path.basename(sys_node)
        dev_path = os.path.join("/dev", dev_name)
        _LOGGER.debug("Matched beacon hidraw node at %s", dev_path)
        fd = os.open(dev_path, os.O_WRONLY | os.O_CLOEXEC)
        return LinuxHidrawTransport(fd=fd)

    raise OSError(
        f"No matching hidraw device found for {vid:#06x}:{pid:#06x}; "
        "check udev permissions and container device mapping"
    )


def _open_pyhid_transport(vid: int, pid: int) -> PyHidTransport:
    """Open optional ``hid``-based transport."""
    try:
        import hid  # noqa: PLC0415
    except ImportError as err:  # pragma: no cover - depends on runtime environment
        raise OSError(
            "The optional 'hid' package is not installed. "
            "Install it or run on Linux with hidraw access."
        ) from err

    device = hid.device()
    device.open(vid, pid)
    device.set_nonblocking(True)
    _LOGGER.debug("Opened pyhid transport for %04x:%04x", vid, pid)
    return PyHidTransport(device=device)