"""Test real config-entry setup, recovery, and unload."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.signalrgb.api import (
    APIError,
    AuthenticationError,
    NotFoundError,
    SignalRGBConnectionError,
    SignalRGBError,
)
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


@pytest.mark.parametrize(
    "method", ["get_layouts", "get_current_layout", "get_effect_presets", "get_effect"]
)
@pytest.mark.parametrize(
    "error",
    [
        APIError("500", "resource failed"),
        AuthenticationError("403", "resource denied"),
        SignalRGBConnectionError("resource offline"),
    ],
)
async def test_optional_resource_failure_and_recovery(
    hass: HomeAssistant,
    config_entry: SignalRGBConfigEntry,
    mock_client: AsyncMock,
    method: str,
    error: SignalRGBError,
) -> None:
    """Optional errors affect only their resource and are retried on the next poll."""
    getattr(mock_client, method).side_effect = error
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    light_id = entity_id(hass, config_entry, "light", "light")
    light = hass.states.get(light_id)
    assert light is not None and light.state == "on"
    if method in {"get_layouts", "get_current_layout", "get_effect_presets"}:
        key = "preset" if method == "get_effect_presets" else "layout"
        state = hass.states.get(entity_id(hass, config_entry, "select", key))
        assert state is not None and state.state == "unavailable"
    else:
        assert config_entry.runtime_data.data.current_effect is None
        assert "effect_description" not in light.attributes
    getattr(mock_client, method).side_effect = None
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    if method in {"get_layouts", "get_current_layout", "get_effect_presets"}:
        key = "preset" if method == "get_effect_presets" else "layout"
        state = hass.states.get(entity_id(hass, config_entry, "select", key))
        assert state is not None and state.state != "unavailable"
    else:
        assert config_entry.runtime_data.data.current_effect is not None
        light = hass.states.get(light_id)
        assert light is not None and "effect_description" in light.attributes


@pytest.mark.parametrize("method", ["get_current_state", "get_effects"])
@pytest.mark.parametrize(
    "error",
    [
        APIError("500", "core failed"),
        AuthenticationError("403", "core denied"),
        SignalRGBConnectionError("core offline"),
    ],
)
async def test_core_failures_still_prevent_setup(
    hass: HomeAssistant,
    config_entry: SignalRGBConfigEntry,
    mock_client: AsyncMock,
    method: str,
    error: SignalRGBError,
) -> None:
    """The required lighting and effect catalogs never become silently optional."""
    getattr(mock_client, method).side_effect = error
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
