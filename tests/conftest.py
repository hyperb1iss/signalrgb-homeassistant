"""Fixtures exercising the integration through Home Assistant."""

from collections.abc import Generator
from typing import cast
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.signalrgb.api import (
    AsyncSignalRGBClient,
    CurrentState,
    Effect,
    Layout,
    Preset,
)
from custom_components.signalrgb.const import DOMAIN
from custom_components.signalrgb.coordinator import SignalRGBConfigEntry

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load this custom integration."""


@pytest.fixture
def mock_client() -> Generator[AsyncMock]:
    """Mock only the HTTP client, leaving HA lifecycle and services real."""
    client = AsyncMock(spec=AsyncSignalRGBClient)
    client.get_current_state.return_value = CurrentState("rainbow", "Rainbow", True, 50)
    client.get_effect.return_value = Effect("rainbow", "Rainbow")
    client.get_effects.return_value = [Effect("rainbow", "Rainbow"), Effect("solid", "Solid")]
    client.get_layouts.return_value = [Layout("Desk"), Layout("Room")]
    client.get_current_layout.return_value = Layout("Desk")
    client.get_effect_presets.return_value = [Preset("Default"), Preset("Soft")]
    with (
        patch("custom_components.signalrgb.AsyncSignalRGBClient", return_value=client),
        patch("custom_components.signalrgb.config_flow.AsyncSignalRGBClient", return_value=client),
    ):
        yield client


@pytest.fixture
def config_entry(hass: HomeAssistant) -> SignalRGBConfigEntry:
    """Add a configuration entry with existing stable identity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="192.168.1.100",
        data={"host": "192.168.1.100", "port": 16038},
        unique_id="192.168.1.100:16038",
    )
    entry.add_to_hass(hass)
    return cast(SignalRGBConfigEntry, entry)


@pytest.fixture
async def setup_entry(
    hass: HomeAssistant, config_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> SignalRGBConfigEntry:
    """Load real platforms and their entities."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def entity_id(hass: HomeAssistant, entry: SignalRGBConfigEntry, platform: str, key: str) -> str:
    """Find entities by their stable registry IDs rather than generated names."""
    result = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert result is not None
    return result
