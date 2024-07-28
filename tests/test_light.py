"""Unit tests for the SignalRGB component."""

import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.signalrgb import async_setup_entry, async_unload_entry
from homeassistant.components.signalrgb.const import (
    ALL_OFF_EFFECT,
    DEFAULT_EFFECT,
    DEFAULT_PORT,
    DOMAIN,
)
from homeassistant.components.signalrgb.light import SignalRGBLight
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

PLATFORMS = ["light"]


@pytest.fixture
def mock_signalrgb_client():
    """Mock SignalRGB client."""
    with patch("homeassistant.components.signalrgb.SignalRGBClient") as mock_client:
        yield mock_client


@pytest.fixture
def mock_config_entry():
    """Mock configuration entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="SignalRGB",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: DEFAULT_PORT,
        },
        source="user",
        entry_id="test",
        options={},
        unique_id=f"192.168.1.100:{DEFAULT_PORT}",
    )


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.async_add_executor_job = AsyncMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.loop_thread_id = threading.get_ident()

    # Mock the states attribute
    mock_states = MagicMock()
    mock_states.async_set_internal = AsyncMock()
    hass.states = mock_states

    return hass


@pytest.fixture
def mock_coordinator():
    """Mock DataUpdateCoordinator."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.data = None
    return coordinator


async def test_setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test setting up the SignalRGB integration."""
    mock_client = mock_signalrgb_client.return_value
    mock_client.get_current_effect = MagicMock()

    assert await async_setup_entry(mock_hass, mock_config_entry)
    assert DOMAIN in mock_hass.data
    assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
    assert isinstance(mock_hass.data[DOMAIN][mock_config_entry.entry_id], MagicMock)
    assert len(mock_hass.config_entries.async_forward_entry_setups.mock_calls) == 1
    assert (
        mock_hass.config_entries.async_forward_entry_setups.mock_calls[0][1][1]
        == PLATFORMS
    )


async def test_unload_entry(mock_hass, mock_config_entry):
    """Test unloading the SignalRGB integration."""
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: MagicMock()}

    assert await async_unload_entry(mock_hass, mock_config_entry)
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]


class TestSignalRGBLight:
    """Unit tests for the SignalRGBLight class."""

    @pytest.fixture
    def mock_light(
        self, mock_hass, mock_signalrgb_client, mock_config_entry, mock_coordinator
    ):
        """Mock SignalRGBLight instance."""
        client = mock_signalrgb_client.return_value
        light = SignalRGBLight(mock_coordinator, client, mock_config_entry)
        light.hass = mock_hass
        light.entity_id = "light.signalrgb"
        light.async_write_ha_state = MagicMock()
        return light

    async def test_turn_on(self, mock_light, mock_coordinator):
        """Test turning on the light."""
        mock_effect = MagicMock()
        mock_effect.id = "test_effect_id"
        mock_effect.attributes.name = DEFAULT_EFFECT

        mock_light.hass.async_add_executor_job = AsyncMock(
            side_effect=[
                mock_effect,  # For get_effect_by_name
                None,  # For apply_effect
            ]
        )
        mock_coordinator.async_request_refresh = AsyncMock()

        await mock_light.async_turn_on()
        assert mock_light.is_on
        assert mock_light._current_effect == mock_effect
        mock_light.hass.async_add_executor_job.assert_any_await(
            mock_light._client.get_effect_by_name, DEFAULT_EFFECT
        )
        mock_light.hass.async_add_executor_job.assert_any_await(
            mock_light._client.apply_effect, "test_effect_id"
        )
        mock_coordinator.async_request_refresh.assert_called_once()
        mock_light.async_write_ha_state.assert_called_once()

    async def test_turn_off(self, mock_light, mock_coordinator):
        """Test turning off the light."""
        mock_effect = MagicMock()
        mock_effect.id = "all_off_effect_id"
        mock_effect.attributes.name = ALL_OFF_EFFECT

        mock_light.hass.async_add_executor_job = AsyncMock(
            side_effect=[
                mock_effect,  # For get_effect_by_name
                None,  # For apply_effect
            ]
        )
        mock_coordinator.async_request_refresh = AsyncMock()

        await mock_light.async_turn_off()
        assert not mock_light.is_on
        mock_light.hass.async_add_executor_job.assert_any_await(
            mock_light._client.get_effect_by_name, ALL_OFF_EFFECT
        )
        mock_light.hass.async_add_executor_job.assert_any_await(
            mock_light._client.apply_effect, "all_off_effect_id"
        )
        mock_coordinator.async_request_refresh.assert_called_once()
        mock_light.async_write_ha_state.assert_called_once()

    async def test_effect_list(self, mock_light):
        """Test getting the effect list."""
        mock_effect = MagicMock()
        mock_effect.attributes.name = "Test Effect"
        mock_light.hass.async_add_executor_job = AsyncMock(return_value=[mock_effect])

        await mock_light.async_update_effect_list()
        assert mock_light.effect_list == ["Test Effect"]

    async def test_apply_effect(self, mock_light, mock_coordinator):
        """Test applying an effect."""
        mock_effect = MagicMock()
        mock_effect.id = "test_effect_id"
        mock_effect.attributes.name = "Test Effect"
        mock_effect.attributes.description = "Test Description"
        mock_effect.attributes.developer_effect = False
        mock_effect.attributes.publisher = "Test Publisher"
        mock_effect.attributes.uses_audio = True
        mock_effect.attributes.uses_input = False
        mock_effect.attributes.uses_meters = True
        mock_effect.attributes.uses_video = False
        mock_effect.attributes.parameters = {"speed": 50, "brightness": 100}
        mock_effect.attributes.image = "test_image_url"

        mock_light.hass.async_add_executor_job = AsyncMock(
            side_effect=[
                mock_effect,  # For get_effect_by_name
                None,  # For apply_effect
            ]
        )
        mock_coordinator.async_request_refresh = AsyncMock()

        await mock_light._apply_effect("Test Effect")

        mock_light.hass.async_add_executor_job.assert_any_await(
            mock_light._client.get_effect_by_name, "Test Effect"
        )
        mock_light.hass.async_add_executor_job.assert_any_await(
            mock_light._client.apply_effect, "test_effect_id"
        )
        mock_coordinator.async_request_refresh.assert_called_once()

        assert mock_light.effect == "Test Effect"
        assert mock_light.extra_state_attributes == {
            "effect_name": "Test Effect",
            "effect_description": "Test Description",
            "effect_developer": False,
            "effect_publisher": "Test Publisher",
            "effect_uses_audio": True,
            "effect_uses_input": False,
            "effect_uses_meters": True,
            "effect_uses_video": False,
            "effect_parameters": {"speed": 50, "brightness": 100},
            "effect_image": "test_image_url",
        }
        mock_light.async_write_ha_state.assert_called_once()

    async def test_update(self, mock_light, mock_coordinator):
        """Test updating the light state."""
        mock_effect = MagicMock()
        mock_effect.attributes.name = "Current Effect"
        mock_effect.attributes.description = "Current Description"
        mock_effect.attributes.developer_effect = True
        mock_effect.attributes.publisher = "Current Publisher"
        mock_effect.attributes.uses_audio = False
        mock_effect.attributes.uses_input = True
        mock_effect.attributes.uses_meters = False
        mock_effect.attributes.uses_video = True
        mock_effect.attributes.parameters = {"color": "red", "intensity": 75}
        mock_effect.attributes.image = "effect_image_url"

        mock_coordinator.data = mock_effect
        mock_light._current_effect = mock_effect  # Set the current effect

        mock_light._handle_coordinator_update()

        assert mock_light.is_on
        assert mock_light.effect == "Current Effect"
        assert mock_light.extra_state_attributes == {
            "effect_name": "Current Effect",
            "effect_description": "Current Description",
            "effect_developer": True,
            "effect_publisher": "Current Publisher",
            "effect_uses_audio": False,
            "effect_uses_input": True,
            "effect_uses_meters": False,
            "effect_uses_video": True,
            "effect_parameters": {"color": "red", "intensity": 75},
            "effect_image": "effect_image_url",
        }

        # Test with ALL_OFF_EFFECT
        mock_effect.attributes.name = ALL_OFF_EFFECT
        mock_coordinator.data = mock_effect
        mock_light._current_effect = mock_effect  # Set the current effect
        mock_light._handle_coordinator_update()

        assert not mock_light.is_on
        assert mock_light.extra_state_attributes == {}

    async def test_extra_state_attributes(self, mock_light):
        """Test extra state attributes."""
        mock_light._current_effect = MagicMock()
        mock_light._current_effect.attributes.name = "Test Effect"
        mock_light._current_effect.attributes.description = "Test Description"
        mock_light._current_effect.attributes.developer_effect = False
        mock_light._current_effect.attributes.publisher = "Test Publisher"
        mock_light._current_effect.attributes.uses_audio = True
        mock_light._current_effect.attributes.uses_input = False
        mock_light._current_effect.attributes.uses_meters = True
        mock_light._current_effect.attributes.uses_video = False
        mock_light._current_effect.attributes.parameters = {
            "speed": 50,
            "brightness": 100,
        }
        mock_light._current_effect.attributes.image = "test_image_url"

        assert mock_light.extra_state_attributes == {
            "effect_name": "Test Effect",
            "effect_description": "Test Description",
            "effect_developer": False,
            "effect_publisher": "Test Publisher",
            "effect_uses_audio": True,
            "effect_uses_input": False,
            "effect_uses_meters": True,
            "effect_uses_video": False,
            "effect_parameters": {"speed": 50, "brightness": 100},
            "effect_image": "test_image_url",
        }

        # Test when light is off
        mock_light._current_effect.attributes.name = ALL_OFF_EFFECT
        assert mock_light.extra_state_attributes == {}
