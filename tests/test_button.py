"""Test effect navigation through Home Assistant services."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
import pytest

from custom_components.signalrgb.coordinator import SignalRGBConfigEntry

from .conftest import entity_id


@pytest.mark.parametrize(
    ("key", "method"),
    [
        ("next_effect", "apply_next_effect"),
        ("previous_effect", "apply_previous_effect"),
        ("random_effect", "apply_random_effect"),
    ],
)
async def test_navigation_refreshes_shared_snapshot(
    hass: HomeAssistant,
    setup_entry: SignalRGBConfigEntry,
    mock_client: AsyncMock,
    key: str,
    method: str,
) -> None:
    """Each button invokes its typed command and refreshes all entities."""
    mock_client.get_current_state.reset_mock()
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id(hass, setup_entry, "button", key)}, blocking=True
    )
    getattr(mock_client, method).assert_awaited_once()
    mock_client.get_current_state.assert_awaited_once()
