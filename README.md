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

<p>
  <a href="https://github.com/hacs/integration">
    <img src="https://img.shields.io/badge/HACS-Default-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white" alt="HACS Default">
  </a>
  <a href="https://www.home-assistant.io">
    <img src="https://img.shields.io/badge/Home%20Assistant-2026.4+-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white" alt="Home Assistant 2026.4+">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.14+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.14+">
  </a>
</p>

<strong>Transform your smart home lighting with the power of SignalRGB, integrated directly into Home Assistant.</strong>

<a href="#-features">Features</a> •
<a href="#-requirements">Requirements</a> •
<a href="#-installation">Installation</a> •
<a href="#%EF%B8%8F-configuration">Configuration</a> •
<a href="#-usage">Usage</a> •
<a href="#-development">Development</a> •
<a href="#-contributing">Contributing</a>

</div>

---

## 🔮 Features

- 🌐 Control SignalRGB as a light entity in Home Assistant
- 💡 Seamless on/off control with brightness adjustment
- 🎭 Apply lighting effects from SignalRGB's full effect library
- 🧬 Automatic effect image and color extraction
- 🧩 Select and apply per-effect presets
- 📐 Change device layouts with the layout selector
- 🪄 Navigate effects with next / previous / random buttons
- ⚡ Single-shot state polling (one API call per coordinator cycle)

Want more features? Vote for this [SignalRGB feature request](https://forum.signalrgb.com/t/rest-api-features/2635)!

## 📡 Requirements

- **Home Assistant** 2026.4.0 or newer
- **Python** 3.14.2 or newer (matches Home Assistant's floor)
- **SignalRGB** installed and running on a Windows PC reachable from your HA instance
- **SignalRGB HTTP API** enabled (default port: `16038`)
- **SignalRGB [Pro subscription](https://signalrgb.com/pricing/)** — the HTTP API requires Pro

## 💎 Installation

### HACS (Recommended)

This integration is in the [HACS](https://hacs.xyz/) default repository:

1. Open **HACS** in Home Assistant
2. Go to **Integrations** and click the **+** button
3. Search for **SignalRGB** and select it
4. Click **Download** and restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/hyperb1iss/signalrgb-homeassistant/releases)
2. Copy the `custom_components/signalrgb/` folder into your Home Assistant `custom_components/` directory
3. Restart Home Assistant

### Enable the SignalRGB HTTP API

1. Open SignalRGB on your Windows PC
2. Go to **Settings → General → Enable HTTP API**
3. Note the port number (default: `16038`)
4. If needed, allow incoming connections on that port in Windows Firewall

## ⚙️ Configuration

After installation, add the integration from the Home Assistant UI:

1. Navigate to **Settings → Devices & Services**
2. Click **Add Integration** and search for **SignalRGB**
3. Enter the hostname or IP address of the PC running SignalRGB and the port number
4. Click **Submit**

## 🎭 Usage

Once configured, SignalRGB exposes several entities:

- 💡 **Light Entity** — power, brightness, and effect selection
- 📐 **Layout Selector** — switch between SignalRGB device layouts
- 🧩 **Effect Preset Selector** — apply presets for the current effect
- 🪄 **Button Entities** — navigate effects (next, previous, random)

### 💡 Light Entity

The main light entity lets you turn SignalRGB on/off, select effects, and adjust brightness — all from automations, scripts, and scenes.

```yaml
automation:
  - alias: "Gaming Time"
    trigger:
      platform: state
      entity_id: binary_sensor.gaming_pc_status
      to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.signalrgb
        data:
          effect: "Cyberpunk 2077"
          brightness: 255
```

### 📐 Layout Selector

Switch between SignalRGB device layouts:

```yaml
service: select.select_option
target:
  entity_id: select.signalrgb_layout
data:
  option: "My Gaming Setup"
```

Automation example — switch layout in the evening:

```yaml
automation:
  - alias: "Evening Gaming Setup"
    trigger:
      platform: time
      at: "20:00:00"
    action:
      - service: select.select_option
        target:
          entity_id: select.signalrgb_layout
        data:
          option: "Gaming Setup"
      - service: light.turn_on
        target:
          entity_id: light.signalrgb
        data:
          effect: "Ambient Waves"
          brightness: 200
```

### 🧩 Effect Preset Selector

Apply presets for the current effect:

```yaml
service: select.select_option
target:
  entity_id: select.signalrgb_effect_preset
data:
  option: "Rainbow"
```

Movie-night script example:

```yaml
script:
  movie_night:
    alias: "Movie Night Lighting"
    sequence:
      - service: light.turn_on
        target:
          entity_id: light.signalrgb
        data:
          effect: "Audio Visualizer"
      - delay: 00:00:02
      - service: select.select_option
        target:
          entity_id: select.signalrgb_effect_preset
        data:
          option: "Subtle Pulse"
      - service: light.turn_on
        target:
          entity_id: light.signalrgb
        data:
          brightness: 128
```

### 🪄 Effect Navigation Buttons

```yaml
# Next effect
service: button.press
target:
  entity_id: button.signalrgb_next_effect
```

```yaml
# Random effect
service: button.press
target:
  entity_id: button.signalrgb_random_effect
```

Cycle effects every hour while the light is on:

```yaml
automation:
  - alias: "Hourly Effect Change"
    trigger:
      platform: time_pattern
      hours: "*"
    condition:
      - condition: state
        entity_id: light.signalrgb
        state: "on"
    action:
      - service: button.press
        target:
          entity_id: button.signalrgb_next_effect
```

Dashboard button card:

```yaml
type: button
name: Next Effect
icon: mdi:skip-next
tap_action:
  action: call-service
  service: button.press
  target:
    entity_id: button.signalrgb_next_effect
```

## 🪄 Enhance Your UI with hyper-light-card

Take your SignalRGB control to the next level with [hyper-light-card](https://github.com/hyperb1iss/hyper-light-card) — a custom Lovelace card featuring:

- 🌈 Dynamic color adaptation based on the current effect
- 📊 Detailed effect information display
- 🖼️ Effect preview images
- 🎛️ Easy effect switching and parameter control

Install via HACS as a custom repository in the **Frontend** category.

## 🧪 Development

This project uses the **[Astral](https://astral.sh)** stack — [uv](https://docs.astral.sh/uv/) for packaging, [ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [ty](https://docs.astral.sh/ty/) for type checking.

```bash
# Install uv (one-time)
curl --proto '=https' --tlsv1.2 -sSf https://astral.sh/uv/install.sh | sh

# Clone and set up
git clone https://github.com/hyperb1iss/signalrgb-homeassistant.git
cd signalrgb-homeassistant
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Common Commands

| Command | What it does |
|---|---|
| `make test` | Run the test suite |
| `make coverage` | Tests with coverage (HTML report in `htmlcov/`) |
| `make lint` | `ruff check` + `ruff format --check` |
| `make typecheck` | `ty check` |
| `make check` | lint → typecheck → test (the full gauntlet) |
| `make format` | Format with ruff |
| `make fix` | Auto-fix lint issues + format |

All commands run through `uv run` — no virtualenv activation needed.

## 🦋 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a branch: `git checkout -b your-feature-name`
3. Make your changes, commit using [Gitmoji](https://gitmoji.dev/) conventions
4. Run `make check` to verify lint, types, and tests all pass
5. Open a pull request

## 🐛 Support

- 📚 [Documentation & Wiki](https://github.com/hyperb1iss/signalrgb-homeassistant/wiki)
- 🐛 [Report a bug](https://github.com/hyperb1iss/signalrgb-homeassistant/issues/new?assignees=&labels=bug&template=bug_report.md&title=)
- 💎 [Request a feature](https://github.com/hyperb1iss/signalrgb-homeassistant/issues/new?assignees=&labels=enhancement&template=feature_request.md&title=)

## 📄 License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

This integration is not officially affiliated with or endorsed by WhirlwindFX or SignalRGB. Use at your own risk.

---

<div align="center">

Created by [Stefanie Jane 🌠](https://github.com/hyperb1iss)

If you find this project useful, [buy me a Monster Ultra Violet](https://ko-fi.com/hyperb1iss) 💜

</div>
