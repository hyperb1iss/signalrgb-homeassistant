"""Test real config-entry setup, recovery, and unload."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.signalrgb.api import NotFoundError, SignalRGBConnectionError
from custom_components.signalrgb.coordinator import SignalRGBConfigEntry

from .conftest import entity_id


async def test_setup_and_unload(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """All six entities share one snapshot and retain their registry IDs."""
    assert setup_entry.state is ConfigEntryState.LOADED
    for platform, key in (
        ("light", "light"),
        ("select", "layout"),
        ("select", "preset"),
        ("button", "next_effect"),
        ("button", "previous_effect"),
        ("button", "random_effect"),
    ):
        assert hass.states.get(entity_id(hass, setup_entry, platform, key)) is not None
    mock_client.get_current_state.assert_awaited_once()
    session = async_get_clientsession(hass)
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.NOT_LOADED
    assert not session.closed


async def test_setup_retries_offline_host(
    hass: HomeAssistant, config_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """An offline PC causes a retry rather than a broken loaded entry."""
    mock_client.get_current_state.side_effect = SignalRGBConnectionError("offline")
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_all_entities_recover_together(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """A failed poll marks entities unavailable, and the next success restores them."""
    coordinator = setup_entry.runtime_data
    mock_client.get_current_state.side_effect = SignalRGBConnectionError("offline")
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    for platform, key in (("light", "light"), ("button", "next_effect"), ("select", "layout")):
        state = hass.states.get(entity_id(hass, setup_entry, platform, key))
        assert state is not None
        assert state.state == "unavailable"
    mock_client.get_current_state.side_effect = None
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get(entity_id(hass, setup_entry, "light", "light"))
    assert state is not None
    assert state.state == "on"


async def test_optional_resources_do_not_block_lighting(
    hass: HomeAssistant, config_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """Missing layout and preset resources leave global lighting usable."""
    mock_client.get_layouts.side_effect = NotFoundError("404", "missing")
    mock_client.get_effect_presets.side_effect = NotFoundError("404", "missing")
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    light = hass.states.get(entity_id(hass, config_entry, "light", "light"))
    layout = hass.states.get(entity_id(hass, config_entry, "select", "layout"))
    assert light is not None and light.state == "on"
    assert layout is not None and layout.state == "unavailable"
