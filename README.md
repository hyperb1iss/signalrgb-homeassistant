# SignalRGB Home Assistant Integration

[![CI/CD](https://github.com/hyperb1iss/signalrgb-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/hyperb1iss/signalrgb-homeassistant/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Transform your smart home lighting with the power of SignalRGB, now integrated directly into Home Assistant!

## 🌟 Features

- 💡 Control SignalRGB as a light entity in Home Assistant
- 🔌 Seamless on/off control
- 🎨 Apply a wide range of lighting effects
- 📊 View current effect and available effects list

Want more features? Vote for this [SignalRGB feature request!](https://forum.signalrgb.com/t/rest-api-features/2635)

## 📋 Requirements

- Home Assistant instance
- SignalRGB software installed and running on a Windows PC on your network
- SignalRGB HTTP API enabled

## 🛠️ Installation

### HACS Installation (Recommended)

1. Ensure that [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. In the HACS panel, go to "Integrations".
3. Click the "+" button in the bottom right corner.
4. Search for "SignalRGB" and select it.
5. Click "Install" and wait for the installation to complete.
6. Restart Home Assistant.

### Manual Installation

1. Download the `signalrgb` folder from this repository.
2. Copy the folder to your `custom_components` directory in your Home Assistant config directory.
   - If the `custom_components` directory doesn't exist, you'll need to create it.
3. Restart Home Assistant.

### Enable SignalRGB HTTP API

1. Open SignalRGB on your Windows PC.
2. Go to Settings > App Settings.
3. Enable the "Enable HTTP API" option.
4. Note down the port number (default is 16068).

## ⚙️ Configuration

After installation, you can add the SignalRGB integration through the Home Assistant UI:

1. Go to Configuration > Integrations.
2. Click the "+" button to add a new integration.
3. Search for "SignalRGB" and select it.
4. Enter the hostname or IP address of the PC running SignalRGB and the port number.
5. Click "Submit" to add the integration.

## 🚀 Usage

Once configured, SignalRGB will appear as a light entity in Home Assistant. You can control it like any other light entity:

- Turn it on/off
- Select different effects from the effect list
- Include it in automations, scripts, and scenes

## 🔍 Troubleshooting

If you encounter any issues:

1. Ensure that SignalRGB is running and the HTTP API is enabled.
2. Check that the IP address and port are correct in the integration configuration.
3. Verify that your Home Assistant instance can reach the PC running SignalRGB on your network.
4. Check the Home Assistant logs for any error messages related to SignalRGB.

## 🤝 Contributing

Contributions to this component are welcome! Please feel free to submit pull requests or open issues on the GitHub repository.

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This component is not officially affiliated with or endorsed by WhirlwindFX or SignalRGB. Use at your own risk.

## 🆘 Support

For support, please open an issue on the GitHub repository. For general discussion or questions, you can use the Home Assistant community forums.

---

<div align="center">

Created by [Stefanie Jane 🌠](https://github.com/hyperb1iss)

If you find this project useful, consider [buying me a Monster Ultra Violet!](https://ko-fi.com/hyperb1iss)! ⚡️

</div>

