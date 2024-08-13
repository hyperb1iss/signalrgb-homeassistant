"""Unit tests for the SignalRGB component."""

# pylint: disable=protected-access, redefined-outer-name

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.signalrgb.const import (
    DEFAULT_PORT,
    DOMAIN,
)
from custom_components.signalrgb.light import SignalRGBLight

PLATFORMS = ["light"]


@pytest.fixture
def mock_signalrgb_client():
    """Mock SignalRGB client."""
    with patch("custom_components.signalrgb.SignalRGBClient") as mock_client:
        yield mock_client


@pytest.fixture
def mock_config_entry():
    """Mock configuration entry."""
    return MagicMock(
        version=1,
        domain=DOMAIN,
        title="SignalRGB",
        data={
            "host": "192.168.1.100",
            "port": DEFAULT_PORT,
        },
        source="user",
        entry_id="test",
        unique_id="192.168.1.100:16038",
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
    return hass


@pytest.fixture
def mock_coordinator():
    """Mock DataUpdateCoordinator."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.data = None
    return coordinator


@pytest.fixture
def mock_light(mock_hass, mock_signalrgb_client, mock_config_entry, mock_coordinator):
    """Mock SignalRGBLight instance."""
    client = mock_signalrgb_client.return_value
    light = SignalRGBLight(mock_coordinator, client, mock_config_entry)
    light.hass = mock_hass
    light.entity_id = "light.signalrgb"
    light.async_write_ha_state = MagicMock()
    return light


class TestSignalRGBLight:
    """Unit tests for the SignalRGBLight class."""

    async def test_light_properties(self, mock_light):
        """Test SignalRGBLight properties."""
        assert mock_light.supported_color_modes == {ColorMode.BRIGHTNESS}
        assert mock_light.color_mode == ColorMode.BRIGHTNESS
        assert mock_light.supported_features == LightEntityFeature.EFFECT

    async def test_is_on(self, mock_light):
        """Test is_on property."""
        mock_light._is_on = True
        assert mock_light.is_on is True
        mock_light._is_on = False
        assert mock_light.is_on is False

    async def test_brightness(self, mock_light):
        """Test brightness property."""
        mock_light._brightness = 50
        assert mock_light.brightness == 128  # 50% of 255
        mock_light._brightness = 100
        assert mock_light.brightness == 255  # 100% of 255

    async def test_turn_on(self, mock_light, mock_coordinator):
        """Test turning on the light."""
        await mock_light.async_turn_on()
        mock_light.hass.async_add_executor_job.assert_any_call(
            setattr, mock_light._client, "enabled", True
        )
        assert mock_light._is_on is True
        assert mock_light.async_write_ha_state.call_count == 1  # Once for turning on
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_turn_on_with_brightness(self, mock_light, mock_coordinator):
        """Test turning on the light with brightness."""
        await mock_light.async_turn_on(**{ATTR_BRIGHTNESS: 128})
        mock_light.hass.async_add_executor_job.assert_any_call(
            setattr, mock_light._client, "enabled", True
        )
        mock_light.hass.async_add_executor_job.assert_any_call(
            setattr, mock_light._client, "brightness", 50
        )
        assert mock_light._is_on is True
        assert mock_light._brightness == 50
        assert (
            mock_light.async_write_ha_state.call_count == 2
        )  # Once for on, once for brightness
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_turn_on_with_effect(self, mock_light, mock_coordinator):
        """Test turning on the light with an effect."""
        mock_effect = "Rainbow Wave"
        mock_effect_obj = MagicMock()
        mock_effect_obj.id = "test_effect_id"
        mock_effect_obj.attributes.name = mock_effect

        mock_light.hass.async_add_executor_job.side_effect = [
            True,  # For setting enabled
            mock_effect_obj,  # For get_effect_by_name
            None,  # For apply_effect
        ]

        await mock_light.async_turn_on(**{ATTR_EFFECT: mock_effect})
        assert mock_light._is_on is True
        assert mock_light._current_effect == mock_effect_obj
        assert (
            mock_light.async_write_ha_state.call_count == 2
        )  # Once for on, once for effect
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_turn_off(self, mock_light, mock_coordinator):
        """Test turning off the light."""
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await mock_light.async_turn_off()
        mock_light.hass.async_add_executor_job.assert_called_with(
            setattr, mock_light._client, "enabled", False
        )
        assert mock_light._is_on is False
        mock_light.async_write_ha_state.assert_called_once()
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_effect_list(self, mock_light):
        """Test getting the effect list."""
        mock_effect1 = MagicMock()
        mock_effect1.attributes.name = "Effect 1"
        mock_effect2 = MagicMock()
        mock_effect2.attributes.name = "Effect 2"
        mock_light.hass.async_add_executor_job.return_value = [
            mock_effect1,
            mock_effect2,
        ]

        await mock_light.async_update_effect_list()
        assert mock_light.effect_list == ["Effect 1", "Effect 2"]

    async def test_apply_effect(self, mock_light):
        """Test applying an effect."""
        mock_effect = "Test Effect"
        mock_effect_obj = MagicMock()
        mock_effect_obj.id = "test_effect_id"
        mock_effect_obj.attributes.name = mock_effect

        mock_light.hass.async_add_executor_job.side_effect = [
            mock_effect_obj,  # For get_effect_by_name
            None,  # For apply_effect
        ]

        await mock_light._apply_effect(mock_effect)
        assert mock_light._current_effect == mock_effect_obj
        mock_light.async_write_ha_state.assert_called_once()

    async def test_update(self, mock_light):
        """Test updating the light state."""
        mock_effect = MagicMock()
        mock_effect.attributes.name = "Current Effect"
        mock_light.coordinator.data = {
            "current_effect": mock_effect,
            "is_on": True,
            "brightness": 75,
        }

        mock_light._handle_coordinator_update()

        assert mock_light.effect == "Current Effect"
        assert mock_light._is_on is True
        assert mock_light._brightness == 75
        mock_light.async_write_ha_state.assert_called_once()

    async def test_extra_state_attributes(self, mock_light):
        """Test extra state attributes."""
        mock_effect = MagicMock()
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

        mock_light._current_effect = mock_effect
        mock_light._is_on = True

        expected_attributes = {
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

        assert mock_light.extra_state_attributes == expected_attributes

        # Test when light is off
        mock_light._is_on = False
        assert mock_light.extra_state_attributes == {}
