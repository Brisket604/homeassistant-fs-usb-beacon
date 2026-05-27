# FS USB Beacon — Home Assistant Custom Integration

Control the **Giants Software FS22 USB Beacon** (included in the Farming Simulator 22 Collector's Edition) directly from Home Assistant as a **light entity** with Spin and Strobe effects.

## Hardware

| Property | Value |
|---|---|
| Device | Giants Software FS22 USB Beacon |
| USB Vendor ID | `0x340D` |
| USB Product ID | `0x1710` |
| Colour | Fixed orange |
| Modes | Spin, Strobe |
| Protocol | USB HID (Human Interface Device) |

The beacon communicates via raw 10-byte USB HID output reports. Because the hardware auto-offs after approximately 10 seconds without a command, the integration maintains a background keepalive loop that resends the active mode every 4 seconds.

## Features

- Exposes the beacon as a **light** entity
- Two **effects**: `Spin` (rotating beacon) and `Strobe` (rapid blinking)
- USB auto-discovery — HA detects the beacon when it is plugged in
- Keepalive loop keeps the beacon active without manual intervention
- Native Linux `hidraw` transport (no extra Python package required)
- HACS-compatible

## Requirements

### Out-of-box mode (recommended)

On Linux, this integration works **without any external Python dependency** by writing directly to `/dev/hidrawX`.

- **Home Assistant OS / Supervised**: works out of the box once USB access is available.
- **Home Assistant Container (Docker)**: pass through the beacon `hidraw` device (see below).
- **Home Assistant Core (venv)**: no extra pip package required; ensure `hidraw` permissions are configured.

### Optional fallback (`hid` package)

If native `hidraw` is unavailable in your environment, the integration can fall back to the optional [`hid`](https://pypi.org/project/hid/) package if you install it manually.

```bash
pip install hid
```

### Linux udev rule (HA Core / Container only)

By default Linux restricts raw HID access to root. Add a udev rule to grant the `homeassistant` user access to the beacon:

1. Create `/etc/udev/rules.d/99-fs-usb-beacon.rules`:

   ```
   SUBSYSTEM=="hidraw", ATTRS{idVendor}=="340d", ATTRS{idProduct}=="1710", MODE="0660", GROUP="homeassistant"
   ```

2. Reload rules and re-plug the beacon:

   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

### Docker / Home Assistant Container

Pass the beacon's `/dev/hidrawX` device through to the container:

```yaml
# docker-compose.yml
devices:
  - /dev/hidraw0:/dev/hidraw0   # adjust as needed
```

Or use `--device /dev/hidraw0` with `docker run`.

## Installation

### Via HACS (recommended)

#### 1. Prerequisite: HACS installed

If HACS is not installed yet, install it first from the official guide:
https://hacs.xyz/docs/setup/download

#### 2. Add this repository to HACS

1. Open Home Assistant.
2. Go to **HACS** → **Integrations**.
3. Click the menu (⋮) in the top-right corner.
4. Click **Custom repositories**.
5. In **Repository**, paste:
  `https://github.com/Brisket604/homeassistant-fs-usb-beacon`
6. In **Category**, select **Integration**.
7. Click **Add**.

#### 3. Install the integration

1. Stay in **HACS** → **Integrations**.
2. Search for **FS USB Beacon**.
3. Open the integration card and click **Download**.
4. Keep the default version (or choose a specific tag) and confirm.

#### 4. Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**.
2. Wait for Home Assistant to come back online.

#### 5. Add integration in Home Assistant

1. Go to **Settings** → **Devices & Services**.
2. Click **Add Integration**.
3. Search for **FS USB Beacon**.
4. Complete the flow.

After this, the entity `light.fs_usb_beacon` should appear.

#### Updating through HACS

1. Open **HACS** → **Integrations**.
2. If an update is available for **FS USB Beacon**, click **Update**.
3. Restart Home Assistant after updating.

#### If it does not appear in HACS search

1. Confirm the repository URL is exactly:
  `https://github.com/Brisket604/homeassistant-fs-usb-beacon`
2. Confirm **Category** is set to **Integration**.
3. Click **HACS** → **⋮** → **Reload data**.
4. Restart Home Assistant and search again.

### Manual

1. Download or clone this repository
2. Copy `custom_components/fs_usb_beacon/` to `<config>/custom_components/fs_usb_beacon/`
3. Restart Home Assistant

## Setup

1. Plug in the beacon **before** (or after) starting Home Assistant
2. If auto-discovery is enabled, a notification will appear — click **Configure** to confirm
3. Otherwise go to **Settings → Devices & Services → Add Integration** → search for **FS USB Beacon** and enter the VID/PID if prompted
4. The entity `light.fs_usb_beacon` will appear

## Usage

## Options

After setup, open the integration card and click **Configure** to change:

- **Default effect**: `Spin` or `Strobe` when `light.turn_on` is called without an `effect`
- **Keepalive interval**: resend interval in seconds (allowed range: 2-9)

## Debug logging

Add this to your Home Assistant `configuration.yaml` to enable verbose diagnostics:

```yaml
logger:
  default: info
  logs:
    custom_components.fs_usb_beacon: debug
```

Then restart Home Assistant. The integration will log transport selection, setup flow decisions, option updates, turn_on/turn_off actions, and keepalive activity.

### Turn on (default Spin effect)

```yaml
service: light.turn_on
target:
  entity_id: light.fs_usb_beacon
```

### Turn on with Strobe effect

```yaml
service: light.turn_on
target:
  entity_id: light.fs_usb_beacon
data:
  effect: Strobe
```

### Switch to Spin

```yaml
service: light.turn_on
target:
  entity_id: light.fs_usb_beacon
data:
  effect: Spin
```

### Turn off

```yaml
service: light.turn_off
target:
  entity_id: light.fs_usb_beacon
```

## References

- Protocol payloads: [steve228uk's Gist](https://gist.github.com/steve228uk/873d653f1ecec0456ea3f475b6e54f68)
- Go implementation: [duckfullstop/blinkybeacon](https://github.com/duckfullstop/blinkybeacon)
- Python library: [Microgenital/Giants_Software_USB_Beacon](https://github.com/Microgenital/Giants_Software_USB_Beacon)
- Windows launcher: [M5trBl5tr/LS22-Beacon-Win](https://github.com/M5trBl5tr/LS22-Beacon-Win)

## License

This project is released under the MIT License.

See [LICENSE.md](LICENSE.md).

The repository references external protocol research and implementations in the
References section. At this stage, those references are used as documentation
and interoperability guidance, while this integration code is distributed under MIT.
