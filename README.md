<div align="center">

# 🌌 SignalRGB Home Assistant Integration

<p>
  <a href="https://github.com/hyperb1iss/signalrgb-homeassistant/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/hyperb1iss/signalrgb-homeassistant/ci.yml?branch=main&style=for-the-badge&logo=github&logoColor=white&label=CI" alt="CI Status">
  </a>
  <a href="https://github.com/hyperb1iss/signalrgb-homeassistant/releases">
    <img src="https://img.shields.io/github/v/release/hyperb1iss/signalrgb-homeassistant?style=for-the-badge&logo=github&logoColor=white" alt="Latest Release">
  </a>
  <a href="https://github.com/hyperb1iss/signalrgb-homeassistant/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/hyperb1iss/signalrgb-homeassistant?style=for-the-badge&logo=apache&logoColor=white" alt="License">
  </a>
</p>

Control your SignalRGB lighting from Home Assistant over your local network.

[Features](#features) · [Setup](#setup) · [Usage](#usage) · [Troubleshooting](#troubleshooting) · [Development](#development)

</div>

## Features

| Entity | Controls |
| --- | --- |
| Light | Canvas on/off, global brightness, installed effects |
| Layout selector | The active SignalRGB device layout |
| Effect preset selector | Presets belonging to the current effect |
| Buttons | Next, previous, and random effects |

The integration uses SignalRGB's [local API v1](https://docs.signalrgb.com/developer/signalrgb-api/introduction/). Home Assistant polls SignalRGB every five minutes and refreshes after commands. Existing entity unique IDs are preserved when upgrading.

## Requirements

- Home Assistant 2026.10.4 or newer (Python 3.14.2 or newer).
- SignalRGB running on a Windows PC reachable from Home Assistant.
- A working SignalRGB API v1 endpoint, normally on TCP port `16038`.
- A SignalRGB account with the required API access. SignalRGB's [API documentation](https://docs.signalrgb.com/developer/signalrgb-api/introduction/) says most endpoints require Pro and return HTTP 403 when the user is signed out or lacks Pro.

## Setup

### Install

In [HACS](https://hacs.xyz/), search for **SignalRGB**, download the integration, and restart Home Assistant.

For a manual installation, download a [release](https://github.com/hyperb1iss/signalrgb-homeassistant/releases), copy `custom_components/signalrgb/` into your Home Assistant `custom_components/` directory, and restart Home Assistant.

### Check the connection

Start SignalRGB and sign in on the Windows PC. Open this address in a browser on that PC:

```text
http://127.0.0.1:16038/api/v1/lighting
```

A working endpoint returns JSON with `status: "ok"` and the current lighting state. The old instructions pointing to **Settings → General → Enable HTTP API** were incorrect for current versions. Use the endpoint check to establish whether your installation is serving the API.

Next, check the same endpoint from Home Assistant's host or another machine on its network, replacing `192.168.1.100` with the Windows PC's address:

```bash
curl --max-time 10 http://192.168.1.100:16038/api/v1/lighting
```

If the local check works but the network check fails, allow inbound TCP connections to port `16038` through Windows Firewall for your trusted network. Check any routing or firewall rules between Home Assistant and the PC. Keep the API on your local network; it uses plain HTTP.

### Add to Home Assistant

1. Open **Settings → Devices & services → Add integration**.
2. Search for **SignalRGB**.
3. Enter the PC's hostname or IP address and the API port (default `16038`). Enter only the hostname or IP, without `http://` or a path.
4. Submit the form.

If the PC's address or API port changes, use **Reconfigure** on the integration entry to update it without recreating the entities.

## Usage

Find the integration's entities on its device page. The entity IDs below are examples; replace them with your actual IDs. Effect, layout, and preset names must match the options shown in Home Assistant.

### Apply an effect and brightness

```yaml
action: light.turn_on
target:
  entity_id: light.signalrgb
data:
  effect: "Neon Shift"
  brightness: 200
```

### Change layout or preset

```yaml
action: select.select_option
target:
  entity_id: select.signalrgb_layout
data:
  option: "My Gaming Setup"
```

```yaml
action: select.select_option
target:
  entity_id: select.signalrgb_effect_preset
data:
  option: "My Fancy Preset 1"
```

The preset selector reports an unknown selection until you apply a preset through Home Assistant. SignalRGB's documented API does not identify the active preset. Changing effects clears the remembered selection.

### Change effects on a schedule

Paste this into an automation's YAML editor:

```yaml
alias: Hourly SignalRGB effect
triggers:
  - trigger: time_pattern
    hours: "*"
conditions:
  - condition: state
    entity_id: light.signalrgb
    state: "on"
actions:
  - action: button.press
    target:
      entity_id: button.signalrgb_next_effect
mode: single
```

The Previous Effect button follows SignalRGB's effect history. SignalRGB can reject the command when there is no previous effect.

For effect previews and lighting controls on a dashboard, see [hyper-light-card](https://github.com/hyperb1iss/hyper-light-card).

## Scope and alternatives

### Individual devices

The integration exposes one light for the SignalRGB canvas. Individual keyboards, fans, and strips are not separate Home Assistant lights. The documented [lighting API](https://docs.signalrgb.com/developer/signalrgb-api/lighting/) provides global canvas controls; it does not document individual-device RGB control. Configure device-specific behavior in SignalRGB.

### Sending SignalRGB colors to Home Assistant lights

The integration controls SignalRGB from Home Assistant. It does not stream SignalRGB's rendered colors to arbitrary Home Assistant lights. For supported hardware, connect the lights directly to SignalRGB; its [network device guide](https://docs.signalrgb.com/guides/device-configuration/supported-wifi-devices/) covers supported brands, including Philips Hue through a Hue Bridge. Generic Zigbee lights exposed only through Home Assistant need a separate bridge implementation.

### Application URLs

SignalRGB also supports [application URLs](https://docs.signalrgb.com/developer/application-urls/) for applying effects from another program on the Windows PC. For example, run this in Command Prompt:

```bat
start "" "signalrgb://effect/apply/Gradient%20Wave"
```

In a `.bat` file, double the percent sign (`Gradient%%20Wave`). A Windows automation agent can launch the URL on the PC. Application URLs are a separate control mechanism and do not provide this integration's state reporting. Check SignalRGB's current licensing for the feature you intend to use.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused or timed out | Confirm SignalRGB is running, then compare the local and network endpoint checks above. Verify the host, port, and Windows Firewall rule. |
| HTTP 403 | Sign in to SignalRGB and check the account's API entitlement. |
| HTTP 404 or an unexpected response | Check the full `/api/v1/lighting` URL and update SignalRGB. A response from `/` alone does not verify API compatibility. |
| Entities unavailable after the PC sleeps | Wake the PC and start SignalRGB. Home Assistant's next successful refresh restores availability. |
| Effect or preset missing | Confirm the effect is installed and that the preset belongs to the active effect. |
| Windows certificate errors or SignalRGB crashes | Contact [SignalRGB support](https://docs.signalrgb.com/guides/community-support/contact-support/); include the Windows event and desktop app version. |

For integration bugs, [open an issue](https://github.com/hyperb1iss/signalrgb-homeassistant/issues/new) with the Home Assistant, integration, and SignalRGB versions, relevant Home Assistant logs, and the result of the API check. Remove private addresses and personal data from anything you post.

## Development

The project uses [uv](https://docs.astral.sh/uv/) for dependencies, [Ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [ty](https://docs.astral.sh/ty/) for type checking.

```bash
git clone https://github.com/hyperb1iss/signalrgb-homeassistant.git
cd signalrgb-homeassistant
uv sync --locked
uv run pre-commit install
make check
```

| Command | Purpose |
| --- | --- |
| `make test` | Run the tests |
| `make coverage` | Run tests with terminal and HTML coverage reports |
| `make lint` | Check lint and formatting |
| `make typecheck` | Run ty |
| `make check` | Run lint, type checking, and tests |
| `make format` | Format Python files |
| `make fix` | Apply Ruff fixes and formatting |
| `make build` | Build the distribution |
| `make update HASS_CONFIG_DIR=/path/to/config` | Copy the integration to an explicit local Home Assistant config directory |

Tests simulate SignalRGB responses and exercise Home Assistant behavior. They do not replace a live test against the Windows application. Changes to API handling should include response fixtures and a test for the reported failure.

Contributions should use [Conventional Commits](https://www.conventionalcommits.org/), pass `make check`, and describe the behavior changed and how it was verified. Include the tested SignalRGB version when reporting a live test.

### Release preparation

Prepare a version locally with `uv run scripts/release.py prepare VERSION`, replacing `VERSION` with the intended version. Review the version changes and changelog, then run the checks and build. Preparation does not commit, tag, or push. The release workflow validates version tags, builds the integration archive, and publishes the GitHub release when a maintainer pushes a release tag.

## License

[Apache License 2.0](LICENSE). This project is independent of WhirlwindFX and SignalRGB.

Created by [Stefanie Jane](https://github.com/hyperb1iss). If the integration is useful to you, [buy me a Monster Ultra Violet](https://ko-fi.com/hyperb1iss) 💜
