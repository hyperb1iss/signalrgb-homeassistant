"""The SignalRGB integration."""

from __future__ import annotations

from signalrgb.client import SignalRGBClient, SignalRGBException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, LOGGER

PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SignalRGB from a config entry."""
    LOGGER.debug("Setting up SignalRGB integration for %s", entry.data[CONF_HOST])

    client = SignalRGBClient(entry.data[CONF_HOST], entry.data[CONF_PORT])

    try:
        await hass.async_add_executor_job(client.get_current_effect)
    except SignalRGBException as err:
        LOGGER.error(
            "Failed to connect to SignalRGB at %s:%s: %s",
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            err,
        )
        raise ConfigEntryNotReady from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    LOGGER.info("SignalRGB integration setup completed for %s", entry.data[CONF_HOST])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading SignalRGB integration for %s", entry.data[CONF_HOST])

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        LOGGER.info("SignalRGB integration unloaded for %s", entry.data[CONF_HOST])
    else:
        LOGGER.warning(
            "Failed to unload SignalRGB integration for %s", entry.data[CONF_HOST]
        )

    return unload_ok
