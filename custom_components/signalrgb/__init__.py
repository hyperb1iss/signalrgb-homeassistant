"""The SignalRGB integration."""

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .api import AsyncSignalRGBClient
from .const import DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import SignalRGBConfigEntry, SignalRGBCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: SignalRGBConfigEntry) -> bool:
    """Set up SignalRGB after its first successful lighting snapshot."""
    client = AsyncSignalRGBClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
    )
    coordinator = SignalRGBCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SignalRGBConfigEntry) -> bool:
    """Unload entities; Home Assistant owns the shared HTTP session."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
