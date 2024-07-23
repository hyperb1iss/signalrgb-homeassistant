"""Constants for the SignalRGB integration."""

from logging import getLogger

DOMAIN = "signalrgb"

LOGGER = getLogger(__package__)

# Configuration constants
DEFAULT_PORT = 16038
DEFAULT_NAME = "SignalRGB"

# Update interval for data coordinator (in seconds)
UPDATE_INTERVAL = 300

# Effect constants
ALL_OFF_EFFECT = "Good Night!"
DEFAULT_EFFECT = "Falling Stars"

# Device info
MANUFACTURER = "WhirlwindFX"
MODEL = "SignalRGB"

# Icon
ICON = "mdi:led-strip-variant"
