"""Unit tests for the SignalRGB component."""

# pylint: disable=protected-access, redefined-outer-name

import asyncio
from unittest.mock import MagicMock, patch

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntityFeature,
)
import pytest

from custom_components.signalrgb.const import (
    DEFAULT_PORT,
    DOMAIN,
)
from custom_components.signalrgb.light import SignalRGBLight

# Import fixtures from conftest.py (they're auto-loaded by pytest)

# Test data
TEST_HOST = "192.168.1.100"
TEST_PORT = DEFAULT_PORT
TEST_CONFIG = {
    "host": TEST_HOST,
    "port": TEST_PORT,
}


async def test_async_setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test setting up the entry."""
    from custom_components.signalrgb.light import async_setup_entry

    # Prepare hass.data for the entry
    mock_hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {"client": mock_signalrgb_client}
    }

    # Mock the async client method results for update
    mock_effect = MagicMock()
    mock_effect.attributes.name = "Test Effect"

    # Set return values for direct async calls
    mock_signalrgb_client.get_current_effect.return_value = mock_effect
    mock_signalrgb_client.get_enabled.return_value = True
    mock_signalrgb_client.get_brightness.return_value = 75

    # Call async_setup_entry and wait for the coordinator's first refresh
    entities = []

    def async_add_entities(added_entities, **kwargs):
        return entities.extend(added_entities)

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Check that the entity was added
    assert len(entities) == 1
    assert isinstance(entities[0], SignalRGBLight)

    # Verify the coordinator was stored in hass.data
    assert "coordinator" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]


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
        # Mock the _schedule_delayed_refresh method to prevent actual waiting
        with patch.object(mock_light, "_schedule_delayed_refresh") as mock_refresh:
            await mock_light.async_turn_on()

        # Verify set_enabled was called directly (no executor job)
        mock_light._client.set_enabled.assert_called_with(True)

        assert mock_light._is_on is True
        assert mock_light.async_write_ha_state.call_count == 1  # Once for turning on

        # Verify refresh was scheduled
        mock_refresh.assert_called_once()

    async def test_turn_on_with_brightness(self, mock_light, mock_coordinator):
        """Test turning on the light with brightness."""
        # Mock the _schedule_delayed_refresh method to prevent actual waiting
        with patch.object(mock_light, "_schedule_delayed_refresh") as mock_refresh:
            await mock_light.async_turn_on(**{ATTR_BRIGHTNESS: 128})

        # Verify direct client calls
        mock_light._client.set_enabled.assert_called_with(True)
        mock_light._client.set_brightness.assert_called_with(50)

        assert mock_light._is_on is True
        assert mock_light._brightness == 50
        assert (
            mock_light.async_write_ha_state.call_count == 2
        )  # Once for on, once for brightness

        # Verify refresh was scheduled
        mock_refresh.assert_called_once()

    async def test_turn_on_with_effect(self, mock_light, mock_coordinator):
        """Test turning on the light with an effect."""
        mock_effect = "Rainbow Wave"
        mock_effect_obj = MagicMock()
        mock_effect_obj.id = "test_effect_id"
        mock_effect_obj.attributes.name = mock_effect

        # Set up the client method return values
        mock_light._client.get_effect_by_name.return_value = mock_effect_obj
        mock_light._client.apply_effect_by_name.return_value = None

        # Mock the _schedule_delayed_refresh method
        with patch.object(mock_light, "_schedule_delayed_refresh") as mock_refresh:
            await mock_light.async_turn_on(**{ATTR_EFFECT: mock_effect})

        # Verify direct client calls
        mock_light._client.set_enabled.assert_called_with(True)
        mock_light._client.get_effect_by_name.assert_called_with(mock_effect)
        mock_light._client.apply_effect_by_name.assert_called_with(mock_effect)

        assert mock_light._is_on is True
        assert mock_light._current_effect == mock_effect_obj
        assert (
            mock_light.async_write_ha_state.call_count == 2
        )  # Once for on, once for effect

        # Verify refresh was scheduled
        mock_refresh.assert_called_once()

    async def test_turn_off(self, mock_light, mock_coordinator):
        """Test turning off the light."""
        await mock_light.async_turn_off()

        # Verify direct client call
        mock_light._client.set_enabled.assert_called_with(False)

        assert mock_light._is_on is False
        mock_light.async_write_ha_state.assert_called_once()
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_effect_list(self, mock_light):
        """Test getting the effect list."""
        mock_effect1 = MagicMock()
        mock_effect1.attributes.name = "Effect 1"
        mock_effect2 = MagicMock()
        mock_effect2.attributes.name = "Effect 2"

        # Set up the client method return values
        mock_light._client.refresh_effects.return_value = None
        mock_light._client.get_effects.return_value = [mock_effect1, mock_effect2]

        await mock_light.async_update_effect_list()
        assert mock_light.effect_list == ["Effect 1", "Effect 2"]

    async def test_apply_effect(self, mock_light):
        """Test applying an effect."""
        mock_effect = "Test Effect"
        mock_effect_obj = MagicMock()
        mock_effect_obj.id = "test_effect_id"
        mock_effect_obj.attributes.name = mock_effect

        # Set up the client method return values
        mock_light._client.get_effect_by_name.return_value = mock_effect_obj
        mock_light._client.apply_effect_by_name.return_value = None

        await mock_light._apply_effect(mock_effect)

        # Verify direct client calls
        mock_light._client.get_effect_by_name.assert_called_with(mock_effect)
        mock_light._client.apply_effect_by_name.assert_called_with(mock_effect)

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

    async def test_async_will_remove_from_hass(self, mock_light):
        """Test the async_will_remove_from_hass method."""

        # Create a real asyncio.Task for _refresh_task
        async def mock_refresh():
            await asyncio.sleep(10)  # Simulate a long-running task

        mock_light._refresh_task = asyncio.create_task(mock_refresh())

        # Call the method we're testing
        await mock_light.async_will_remove_from_hass()

        # Assert that the task was cancelled
        assert mock_light._refresh_task.cancelled()


@pytest.fixture
def mock_light(mock_hass, mock_signalrgb_client, mock_config_entry, mock_coordinator):
    """Mock SignalRGBLight instance."""
    light = SignalRGBLight(mock_coordinator, mock_signalrgb_client, mock_config_entry)
    light.hass = mock_hass
    light.entity_id = "light.signalrgb"
    light.async_write_ha_state = MagicMock()
    return light
