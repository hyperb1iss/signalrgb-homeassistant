"""The SignalRGB integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv

from signalrgb import AsyncSignalRGBClient, SignalRGBException

from .const import DOMAIN, LOGGER, PLATFORMS

# This integration only supports configuration via config entries
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: dict[str, Any]) -> bool:
    """Set up the SignalRGB component."""
    hass.data.setdefault(DOMAIN, {})
    return True


def _create_client(host: str, port: int) -> AsyncSignalRGBClient:
    """Create client in executor to avoid blocking SSL operations."""
    return AsyncSignalRGBClient(host, port)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SignalRGB from a config entry."""
    LOGGER.debug("Setting up SignalRGB integration for %s", entry.data[CONF_HOST])

    # Initialize client in a thread executor to avoid blocking SSL certificate loading
    client = await hass.async_add_executor_job(
        _create_client, entry.data[CONF_HOST], entry.data[CONF_PORT]
    )

    try:
        # Test the connection by getting the current effect
        await client.get_current_effect()
    except SignalRGBException as err:
        LOGGER.error(
            "Failed to connect to SignalRGB at %s:%s: %s",
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            err,
        )
        # Make sure to close the client on error
        await client.aclose()
        raise ConfigEntryNotReady from err

    # Store client in hass.data - coordinators will be added by platform setup
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    LOGGER.info("SignalRGB integration setup completed for %s", entry.data[CONF_HOST])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading SignalRGB integration for %s", entry.data[CONF_HOST])

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Close the client when unloading
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        await client.aclose()

        hass.data[DOMAIN].pop(entry.entry_id)
        LOGGER.info("SignalRGB integration unloaded for %s", entry.data[CONF_HOST])
    else:
        LOGGER.warning("Failed to unload SignalRGB integration for %s", entry.data[CONF_HOST])

    return bool(unload_ok)
