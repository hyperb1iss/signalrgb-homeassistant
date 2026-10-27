"""Test layouts and presets through Home Assistant services."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from custom_components.signalrgb.api import CurrentState, Layout, Preset
from custom_components.signalrgb.coordinator import SignalRGBConfigEntry

from .conftest import entity_id


async def test_layout_reads_actual_state(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """Layout option IDs stay compatible and update after the command."""
    select_id = entity_id(hass, setup_entry, "select", "layout")
    state = hass.states.get(select_id)
    assert state is not None
    assert state.state == "Desk"
    assert state.attributes["options"] == ["Desk", "Room"]
    mock_client.get_current_layout.return_value = Layout("Room")
    await hass.services.async_call(
        "select", "select_option", {"entity_id": select_id, "option": "Room"}, blocking=True
    )
    mock_client.set_current_layout.assert_awaited_once_with("Room")
    state = hass.states.get(select_id)
    assert state is not None
    assert state.state == "Room"


async def test_presets_never_guess_default_and_reset_on_effect_change(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """A newly loaded effect has no invented first-preset selection."""
    select_id = entity_id(hass, setup_entry, "select", "preset")
    state = hass.states.get(select_id)
    assert state is not None
    assert state.state == "unknown"
    await hass.services.async_call(
        "select", "select_option", {"entity_id": select_id, "option": "Soft"}, blocking=True
    )
    mock_client.apply_effect_preset.assert_awaited_once_with("rainbow", "Soft")
    state = hass.states.get(select_id)
    assert state is not None
    assert state.state == "Soft"
    mock_client.get_current_state.return_value = CurrentState("solid", "Solid", True, 50)
    await setup_entry.runtime_data.async_refresh()
    state = hass.states.get(select_id)
    assert state is not None
    assert state.state == "unknown"
    mock_client.get_current_state.return_value = CurrentState("rainbow", "Rainbow", True, 50)
    await setup_entry.runtime_data.async_refresh()
    state = hass.states.get(select_id)
    assert state is not None
    assert state.state == "unknown"


async def test_preset_list_updates_and_empty_list_is_unavailable(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """Preset options follow the current server catalog."""
    mock_client.get_effect_presets.return_value = [Preset("New")]
    await setup_entry.runtime_data.async_refresh()
    state = hass.states.get(entity_id(hass, setup_entry, "select", "preset"))
    assert state is not None
    assert state.attributes["options"] == ["New"]
    mock_client.get_effect_presets.return_value = []
    await setup_entry.runtime_data.async_refresh()
    state = hass.states.get(entity_id(hass, setup_entry, "select", "preset"))
    assert state is not None
    assert state.state == "unavailable"
