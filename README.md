<div align="center">

# 🌌✨ SignalRGB Home Assistant Integration

[![CI/CD](https://img.shields.io/github/actions/workflow/status/hyperb1iss/signalrgb-homeassistant/ci-cd.yml?style=flat-square&logo=github&logoColor=white&label=CI%2FCD)](https://github.com/hyperb1iss/signalrgb-homeassistant/actions)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square&logo=homeassistant&logoColor=white)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/hyperb1iss/signalrgb-homeassistant?style=flat-square&logo=apache&logoColor=white)](https://opensource.org/licenses/Apache-2.0)
[![GitHub Release](https://img.shields.io/github/v/release/hyperb1iss/signalrgb-homeassistant?style=flat-square&logo=github&logoColor=white)](https://github.com/hyperb1iss/signalrgb-homeassistant/releases)
[![GitHub Stars](https://img.shields.io/github/stars/hyperb1iss/signalrgb-homeassistant?style=flat-square&logo=github&logoColor=white)](https://github.com/hyperb1iss/signalrgb-homeassistant/stargazers)

Transform your smart home lighting with the power of SignalRGB, now integrated directly into Home Assistant!

[Features](#-features) • [Requirements](#-requirements) • [Installation](#-installation) • [Configuration](#%EF%B8%8F-configuration) • [Usage](#-usage) • [Development](#-development) • [Contributing](#-contributing) • [Support](#-support)

</div>

## 🔮 Features

- 🌐 Control SignalRGB as a light entity in Home Assistant
- ⚡ Seamless on/off control
- 🎭 Apply a wide range of lighting effects
- 🔆 Adjust brightness of your entire SignalRGB setup
- 📊 View current effect and available effects list
- 🧬 Automatic effect image and color extraction
- 🧩 Select and apply effect presets
- 📐 Change layouts with the layout selector
- 🔄 Navigate effects with next/previous/random buttons

Want more features? Vote for this [SignalRGB feature request](https://forum.signalrgb.com/t/rest-api-features/2635)!

## 📡 Requirements

- Home Assistant 2025.3.0 or newer
- SignalRGB software installed and running on a Windows PC on your network
- SignalRGB HTTP API enabled (default port: 16038)
- SignalRGB [Pro subscription](https://signalrgb.com/pricing/) (required for API)

## 🔧 Installation

### HACS Installation (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. In the HACS panel, go to "Integrations".
3. Click the "+" button in the bottom right corner.
4. Search for "SignalRGB" and select it.
5. Click "Install" and wait for the installation to complete.
6. Restart Home Assistant.

> **Note**: This component isn't in the official HACS repository yet. You can add it as a custom repository:
>
> 1. Go to HACS
> 2. Click on the three dots in the top right corner
> 3. Select "Custom repositories"
> 4. Enter "hyperb1iss/signalrgb-homeassistant" for the repository
> 5. Select "Integration" for the category
> 6. Click "Add"

### Manual Installation

1. Download the `signalrgb` folder from this repository.
2. Copy the folder to your `custom_components` directory in your Home Assistant config directory.
   - If the `custom_components` directory doesn't exist, you'll need to create it.
3. Restart Home Assistant.

### Enable SignalRGB API

Ensure that the SignalRGB API is enabled and accessible:

1. Open SignalRGB on your Windows PC.
2. Go to Settings > General > Enable HTTP API.
3. Note the port number (default is 16038).
4. If necessary, configure your Windows firewall to allow incoming connections on this port.

## ⚙️ Configuration

After installation, add the SignalRGB integration through the Home Assistant UI:

1. Navigate to **Configuration** > **Integrations**.
2. Click the "+" button to add a new integration.
3. Search for "SignalRGB" and select it.
4. Enter the hostname or IP address of the PC running SignalRGB and the port number.
5. Click "Submit" to add the integration.

## 🚀 Usage

Once configured, SignalRGB will appear as several entities in Home Assistant:

- 💠 **Light Entity**: Control power, brightness, and effects
- 📐 **Layout Selector**: Change between different layouts
- ⚙️ **Effect Preset Selector**: Apply presets for the current effect
- ⏯️ **Button Entities**: Navigate through effects (next, previous, random)

### 💠 Light Entity

The main light entity allows you to:

- 💡 Turn it on/off
- 🎨 Select different effects from the effect list
- 🔆 Adjust the brightness of your entire SignalRGB setup
- 🏠 Include it in automations, scripts, and scenes

Example automation:

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

The layout selector allows you to switch between different device layouts in SignalRGB:

```yaml
# Example service call to change layout
service: select.select_option
target:
  entity_id: select.signalrgb_layout
data:
  option: "My Gaming Setup"
```

Example automation to switch layouts based on time of day:

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

### ⚙️ Effect Preset Selector

Apply different presets for the current effect:

```yaml
# Example service call to apply a preset
service: select.select_option
target:
  entity_id: select.signalrgb_effect_preset
data:
  option: "Rainbow"
```

Example script to set up a movie night ambiance:

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
      - delay: 00:00:02 # Wait for effect to load
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

### ⏯️ Effect Navigation Buttons

Use the button entities to navigate through effects:

```yaml
# Example service call to go to the next effect
service: button.press
target:
  entity_id: button.signalrgb_next_effect
```

```yaml
# Example service call to go to a random effect
service: button.press
target:
  entity_id: button.signalrgb_random_effect
```

Example automation to cycle through effects every hour:

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

Example dashboard button card configuration:

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

## 🎨 Enhance Your UI with hyper-light-card

To take your SignalRGB control to the next level, check out the [hyper-light-card](https://github.com/hyperb1iss/hyper-light-card) for Home Assistant! This custom card provides a beautiful, intuitive interface for controlling your SignalRGB setup, featuring:

- 🌈 Dynamic color adaptation based on the current effect
- 📊 Detailed effect information display
- 🖼️ Effect preview images
- 🔧 Easy effect switching and parameter control

To install hyper-light-card:

1. Add it to HACS as a custom repository (Frontend category)
2. Install it through HACS
3. Add a new card to your dashboard and select "Hyper Light Card"
4. Choose your SignalRGB entity

Experience the perfect blend of functionality and aesthetics with hyper-light-card and SignalRGB!

## 🧠 Development

This project uses UV for dependency management and packaging. To set up the development environment:

1. Install [UV](https://github.com/astral-sh/uv)
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://astral.sh/uv/install.sh | sh
   ```
2. Clone the repository:
   ```bash
   git clone https://github.com/hyperb1iss/signalrgb-homeassistant.git
   ```
3. Navigate to the project directory:
   ```bash
   cd signalrgb-homeassistant
   ```
4. Create a virtual environment and install dependencies:
   ```bash
   uv venv .venv
   . .venv/bin/activate
   uv sync
   ```
5. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Useful Commands

- Run tests: `python -m pytest`
- Run tests with coverage: `python -m pytest --cov=custom_components.signalrgb`
- Lint code: `ruff check .`
- Format code: `ruff format .`
- Type check: `mypy custom_components/signalrgb/`

## 🧪 Contributing

We welcome contributions to the SignalRGB Home Assistant Integration! Here's how you can help:

1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit them using [Gitmoji](https://gitmoji.dev/): `git commit -m ":sparkles: Add amazing feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Submit a pull request

Please ensure your code adheres to our style guidelines and passes all tests.

## 🔍 Support

- 📚 For documentation and general questions, check out our [Wiki](https://github.com/hyperb1iss/signalrgb-homeassistant/wiki).
- 🐛 Found a bug? [Open an issue](https://github.com/hyperb1iss/signalrgb-homeassistant/issues/new?assignees=&labels=bug&template=bug_report.md&title=).
- 💡 Have a feature idea? [Submit a feature request](https://github.com/hyperb1iss/signalrgb-homeassistant/issues/new?assignees=&labels=enhancement&template=feature_request.md&title=).
- 💬 For general discussion, join our [Discord community](https://discord.gg/your-discord-invite).

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This integration is not officially affiliated with or endorsed by WhirlwindFX or SignalRGB. Use at your own risk.

---

<div align="center">

Created by [Stefanie Jane 🌠](https://github.com/hyperb1iss)

If you find this project useful, [buy me a Monster Ultra Violet](https://ko-fi.com/hyperb1iss)! ⚡️

</div>
