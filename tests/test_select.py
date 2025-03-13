"""Unit tests for the SignalRGB select components."""

# pylint: disable=protected-access, redefined-outer-name

from unittest.mock import MagicMock

from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.signalrgb.const import DOMAIN
from custom_components.signalrgb.select import (
    LAYOUT_SELECT,
    PRESET_SELECT,
    SignalRGBLayoutSelect,
    SignalRGBPresetSelect,
    async_setup_entry,
)

# Import fixtures from conftest.py


async def test_async_setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test setting up the entry with layouts and presets."""
    # Prepare hass.data for the entry
    mock_hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {"client": mock_signalrgb_client}
    }

    # Mock get_layouts and current_layout for layout coordinator
    mock_layout = MagicMock()
    mock_layout.id = "test_layout"

    # Mock get_current_effect and get_effects for effect coordinator
    mock_effect = MagicMock()
    mock_effect.id = "test_effect_id"
    mock_effect.attributes.name = "Test Effect"

    # Mock get_effect_presets for preset selector
    mock_preset = MagicMock()
    mock_preset.id = "test_preset"

    # Set up side effects for all the calls in the setup method
    mock_hass.async_add_executor_job.side_effect = [
        [mock_layout],  # get_layouts
        mock_layout,  # current_layout
        mock_effect,  # get_current_effect
        [mock_effect],  # get_effects
        [mock_preset],  # get_effect_presets
    ]

    # Call async_setup_entry
    entities = []
    def async_add_entities(added_entities):
        return entities.extend(added_entities)

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Check that both entities were added
    assert len(entities) == 2
    assert isinstance(entities[0], SignalRGBLayoutSelect)
    assert isinstance(entities[1], SignalRGBPresetSelect)


class TestSignalRGBLayoutSelect:
    """Unit tests for the SignalRGBLayoutSelect class."""

    @pytest.fixture
    def mock_layout_select(
        self, mock_hass, mock_signalrgb_client, mock_config_entry, mock_coordinator
    ):
        """Create a mock layout select entity."""
        layout_select = SignalRGBLayoutSelect(
            mock_coordinator,
            mock_signalrgb_client,
            mock_config_entry,
        )
        layout_select.hass = mock_hass
        layout_select.entity_id = f"select.signalrgb_{LAYOUT_SELECT}"
        layout_select.async_write_ha_state = MagicMock()
        return layout_select

    @pytest.fixture
    def mock_layout_data(self, mock_coordinator):
        """Create mock layout data for the coordinator."""
        mock_layout1 = MagicMock()
        mock_layout1.id = "layout1"
        mock_layout2 = MagicMock()
        mock_layout2.id = "layout2"
        current_layout = MagicMock()
        current_layout.id = "layout1"

        mock_coordinator.data = {
            "layouts": [mock_layout1, mock_layout2],
            "current_layout": current_layout,
        }

        return mock_coordinator.data

    async def test_layout_select_properties(self, mock_layout_select, mock_layout_data):
        """Test the layout selector properties."""
        # Update the data from coordinator
        mock_layout_select._update_data()

        # Since we're mocking, manually set up the layouts dictionary
        mock_layout_select._layouts = {
            "layout1": mock_layout_data["layouts"][0],
            "layout2": mock_layout_data["layouts"][1],
        }
        mock_layout_select._current_layout_id = "layout1"

        # Test properties
        assert mock_layout_select.available is True
        assert sorted(mock_layout_select.options) == ["layout1", "layout2"]
        assert mock_layout_select.current_option == "layout1"

    async def test_layout_select_option(self, mock_layout_select):
        """Test selecting a layout option."""
        # Set up the entity's state
        mock_layout1 = MagicMock()
        mock_layout1.id = "layout1"
        mock_layout2 = MagicMock()
        mock_layout2.id = "layout2"

        mock_layout_select._layouts = {
            "layout1": mock_layout1,
            "layout2": mock_layout2,
        }

        # Test selecting a valid option
        await mock_layout_select.async_select_option("layout2")

        # Verify the client was called to set the layout
        mock_layout_select.hass.async_add_executor_job.assert_called_with(
            setattr, mock_layout_select._client, "current_layout", "layout2"
        )
        assert mock_layout_select._current_layout_id == "layout2"
        mock_layout_select.async_write_ha_state.assert_called_once()
        mock_layout_select.coordinator.async_request_refresh.assert_called_once()

        # Test selecting an invalid option
        with pytest.raises(HomeAssistantError):
            await mock_layout_select.async_select_option("nonexistent_layout")


class TestSignalRGBPresetSelect:
    """Unit tests for the SignalRGBPresetSelect class."""

    @pytest.fixture
    def mock_preset_select(
        self, mock_hass, mock_signalrgb_client, mock_config_entry, mock_coordinator
    ):
        """Create a mock preset select entity."""
        preset_select = SignalRGBPresetSelect(
            mock_coordinator,
            mock_signalrgb_client,
            mock_config_entry,
        )
        preset_select.hass = mock_hass
        preset_select.entity_id = f"select.signalrgb_{PRESET_SELECT}"
        preset_select.async_write_ha_state = MagicMock()
        return preset_select

    @pytest.fixture
    def mock_preset_data(self, mock_coordinator):
        """Create mock preset data for the coordinator."""
        mock_effect = MagicMock()
        mock_effect.id = "effect_id"
        mock_effect.attributes.name = "Test Effect"

        mock_preset1 = MagicMock()
        mock_preset1.id = "preset1"
        mock_preset2 = MagicMock()
        mock_preset2.id = "preset2"

        mock_coordinator.data = {
            "current_effect": mock_effect,
            "presets": [mock_preset1, mock_preset2],
        }

        return mock_coordinator.data

    async def test_preset_select_properties(self, mock_preset_select, mock_preset_data):
        """Test the preset selector properties."""
        # Update the data from coordinator
        mock_preset_select._update_data()

        # Test properties
        assert mock_preset_select.available is True
        assert mock_preset_select.options == ["preset1", "preset2"]
        assert (
            mock_preset_select.current_option is None
        )  # Current preset is not tracked by API

    async def test_preset_select_option(self, mock_preset_select, mock_preset_data):
        """Test selecting a preset option."""
        # Set up the entity's state
        mock_preset_select._current_effect = mock_preset_data["current_effect"]
        mock_preset_select._presets = ["preset1", "preset2"]

        # Test selecting a valid option
        await mock_preset_select.async_select_option("preset1")

        # Verify the client was called to apply the preset
        mock_preset_select.hass.async_add_executor_job.assert_called_with(
            mock_preset_select._client.apply_effect_preset,
            mock_preset_data["current_effect"].id,
            "preset1",
        )
        assert mock_preset_select._current_preset == "preset1"
        mock_preset_select.async_write_ha_state.assert_called_once()
        mock_preset_select.coordinator.async_request_refresh.assert_called_once()

        # Test selecting an invalid option
        with pytest.raises(HomeAssistantError):
            await mock_preset_select.async_select_option("nonexistent_preset")

        # Test without active effect
        mock_preset_select._current_effect = None
        with pytest.raises(HomeAssistantError):
            await mock_preset_select.async_select_option("preset1")
