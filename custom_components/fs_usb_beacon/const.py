"""Constants for the FS USB Beacon integration."""

DOMAIN = "fs_usb_beacon"

CONF_DEFAULT_EFFECT = "default_effect"
CONF_KEEPALIVE_INTERVAL = "keepalive_interval"

# Giants Software FS22 USB Beacon — USB identifiers
BEACON_VID = 0x340D
BEACON_PID = 0x1710

# Light effect names exposed to Home Assistant
EFFECT_SPIN = "Spin"
EFFECT_STROBE = "Strobe"
EFFECTS: list[str] = [EFFECT_SPIN, EFFECT_STROBE]
DEFAULT_EFFECT = EFFECT_SPIN

# Keepalive interval in seconds.
# The beacon auto-offs after ~10 s without a command; re-send every 4 s.
KEEPALIVE_INTERVAL = 4

# Raw 10-byte HID output reports, reverse-engineered from USB sniff traffic.
# Credit: https://gist.github.com/steve228uk/873d653f1ecec0456ea3f475b6e54f68
# and https://github.com/duckfullstop/blinkybeacon
PAYLOAD_OFF = bytes([0x00, 0xFF, 0x00, 0x00, 0x64, 0x00, 0x32, 0x9E, 0xD7, 0x0D])
PAYLOAD_STROBE = bytes([0x00, 0xFF, 0x07, 0xFF, 0x64, 0xFF, 0xEB, 0x7D, 0x9A, 0x03])
PAYLOAD_SPIN = bytes([0x00, 0xFF, 0x01, 0x66, 0xC8, 0xFF, 0xAD, 0x52, 0x81, 0xD6])
