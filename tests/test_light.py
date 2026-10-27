"""Test global lighting through Home Assistant services."""

import asyncio
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import pytest

from custom_components.signalrgb.api import CurrentState, Effect, SignalRGBConnectionError
from custom_components.signalrgb.coordinator import SignalRGBConfigEntry

from .conftest import entity_id


async def test_state_and_brightness_conversion(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry
) -> None:
    """The initial state reflects the server, including brightness scaling."""
    state = hass.states.get(entity_id(hass, setup_entry, "light", "light"))
    assert state is not None
    assert state.state == "on"
    assert state.attributes["brightness"] == 128
    assert state.attributes["effect"] == "Rainbow"
    assert state.attributes["effect_list"] == ["Rainbow", "Solid"]


async def test_turn_on_updates_shared_state(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """A brightness/effect command refreshes the shared snapshot once."""
    mock_client.get_current_state.return_value = CurrentState("solid", "Solid", True, 100)
    mock_client.get_current_state.reset_mock()
    await hass.services.async_call(
        "light",
        "turn_on",
        {
            "entity_id": entity_id(hass, setup_entry, "light", "light"),
            "brightness": 255,
            "effect": "Solid",
        },
        blocking=True,
    )
    mock_client.set_brightness.assert_awaited_once_with(100)
    mock_client.apply_effect.assert_awaited_once_with("solid")
    mock_client.get_current_state.assert_awaited_once()
    assert setup_entry.runtime_data.data.state.effect_name == "Solid"


async def test_turn_off_observes_server(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """An accepted command does not overwrite contradictory server state."""
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": entity_id(hass, setup_entry, "light", "light")},
        blocking=True,
    )
    mock_client.set_enabled.assert_awaited_once_with(False)
    state = hass.states.get(entity_id(hass, setup_entry, "light", "light"))
    assert state is not None
    assert state.state == "on"


async def test_failed_command_becomes_ha_error(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """Command failures propagate through the service API."""
    mock_client.set_enabled.side_effect = SignalRGBConnectionError("offline")
    with pytest.raises(HomeAssistantError, match="SignalRGB command failed"):
        await hass.services.async_call(
            "light",
            "turn_off",
            {"entity_id": entity_id(hass, setup_entry, "light", "light")},
            blocking=True,
        )


async def test_ambiguous_effect_does_not_pick_arbitrary_device(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """Duplicate display names cannot silently select the wrong effect."""
    mock_client.get_effects.return_value = [Effect("one", "Same"), Effect("two", "Same")]
    await setup_entry.runtime_data.async_refresh()
    with pytest.raises(ServiceValidationError, match="ambiguous"):
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_id(hass, setup_entry, "light", "light"), "effect": "Same"},
            blocking=True,
        )
    mock_client.apply_effect.assert_not_awaited()


async def test_cancelled_command_does_not_start_refresh(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """Cancelling a command must not start more network work during shutdown."""
    mock_client.set_enabled.side_effect = asyncio.CancelledError
    mock_client.get_current_state.reset_mock()
    with pytest.raises(asyncio.CancelledError):
        await hass.services.async_call(
            "light",
            "turn_off",
            {"entity_id": entity_id(hass, setup_entry, "light", "light")},
            blocking=True,
        )
    mock_client.get_current_state.assert_not_awaited()


async def test_partial_command_failure_refreshes_actual_state(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """A successful brightness write remains visible if applying an effect fails."""
    mock_client.apply_effect.side_effect = SignalRGBConnectionError("effect failed")
    mock_client.get_current_state.return_value = CurrentState("rainbow", "Rainbow", True, 100)
    with pytest.raises(HomeAssistantError, match="effect failed"):
        await hass.services.async_call(
            "light",
            "turn_on",
            {
                "entity_id": entity_id(hass, setup_entry, "light", "light"),
                "brightness": 255,
                "effect": "Solid",
            },
            blocking=True,
        )
    state = hass.states.get(entity_id(hass, setup_entry, "light", "light"))
    assert state is not None
    assert state.attributes["brightness"] == 255
    assert state.attributes["effect"] == "Rainbow"


async def test_turn_on_ignores_stale_cached_enabled_state(
    hass: HomeAssistant, setup_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """A desktop-side power change cannot turn a service call into a no-op."""
    assert setup_entry.runtime_data.data.state.enabled
    mock_client.get_current_state.return_value = CurrentState("rainbow", "Rainbow", False, 50)
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id(hass, setup_entry, "light", "light")},
        blocking=True,
    )
    mock_client.set_enabled.assert_awaited_once_with(True)
