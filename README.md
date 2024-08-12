<div align="center">

# 🌈✨ SignalRGB Home Assistant Integration

[<img src="https://img.shields.io/github/actions/workflow/status/hyperb1iss/signalrgb-homeassistant/validate.yml?style=for-the-badge&logo=github&label=CI%2FCD" alt="CI/CD">](https://github.com/hyperb1iss/signalrgb-homeassistant/actions)
[<img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge">](https://github.com/custom-components/hacs)
[<img src="https://img.shields.io/github/license/hyperb1iss/signalrgb-homeassistant?style=for-the-badge" alt="License">](https://opensource.org/licenses/Apache-2.0)

Transform your smart home lighting with the power of SignalRGB, now integrated directly into Home Assistant!

[Features](#-features) • [Requirements](#-requirements) • [Installation](#%EF%B8%8F-installation) • [Configuration](#%EF%B8%8F-configuration) • [Usage](#-usage) • [Development](#-development) • [Contributing](#-contributing) • [Support](#-support)

</div>

## 🌟 Features

- 💡 Control SignalRGB as a light entity in Home Assistant
- 🔌 Seamless on/off control
- 🎨 Apply a wide range of lighting effects
- 🔆 Adjust brightness of your entire SignalRGB setup
- 📊 View current effect and available effects list
- 🔄 Automatic effect image and color extraction
- 🎛️ Effect parameter control (coming soon!)

Want more features? Vote for this [SignalRGB feature request](https://forum.signalrgb.com/t/rest-api-features/2635)!

## 📋 Requirements

- Home Assistant 2024.2.0 or newer
- SignalRGB software installed and running on a Windows PC on your network
- SignalRGB HTTP API enabled (default port: 16038)

## 🛠️ Installation

### HACS Installation (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. In the HACS panel, go to "Integrations".
3. Click the "+" button in the bottom right corner.
4. Search for "SignalRGB" and select it.
5. Click "Install" and wait for the installation to complete.
6. Restart Home Assistant.

> **Note**: This component isn't in the official HACS repository yet. You can add it as a custom repository:
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

Once configured, SignalRGB will appear as a light entity in Home Assistant. You can:

- 💡 Turn it on/off
- 🎨 Select different effects from the effect list
- 🔆 Adjust the brightness of your entire SignalRGB setup
- 🏠 Include it in automations, scripts, and scenes
- 👁️ View effect details and parameters

Example automation:

```yaml
automation:
  - alias: "Gaming Time"
    trigger:
      platform: state
      entity_id: binary_sensor.gaming_pc_status
      to: 'on'
    action:
      - service: light.turn_on
        target:
          entity_id: light.signalrgb
        data:
          effect: "Cyberpunk 2077"
          brightness: 255
```

You can also control the brightness using slider controls in the Home Assistant UI or by calling the `light.turn_on` service with a brightness value:

```yaml
service: light.turn_on
target:
  entity_id: light.signalrgb
data:
  brightness: 128  # Values range from 0 (off) to 255 (full brightness)
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

## 🛠 Development

This project uses Poetry for dependency management and packaging. To set up the development environment:

1. Install [Poetry](https://python-poetry.org/docs/#installation)
2. Clone the repository:
   ```bash
   git clone https://github.com/hyperb1iss/signalrgb-homeassistant.git
   ```
3. Navigate to the project directory:
   ```bash
   cd signalrgb-homeassistant
   ```
4. Install dependencies:
   ```bash
   poetry install
   ```
5. Activate the virtual environment:
   ```bash
   poetry shell
   ```
6. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Useful Commands

- Run tests: `make test`
- Lint code: `make lint`
- Format code: `make format`
- Run all checks: `make check`

## 🤝 Contributing

We welcome contributions to the SignalRGB Home Assistant Integration! Here's how you can help:

1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit them using [Gitmoji](https://gitmoji.dev/): `git commit -m ":sparkles: Add amazing feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Submit a pull request

Please ensure your code adheres to our style guidelines and passes all tests.

## 🆘 Support

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