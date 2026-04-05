"""Unit tests for the SignalRGB button components."""

# pylint: disable=redefined-outer-name

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.signalrgb.button import (
    NEXT_EFFECT_BUTTON,
    PREVIOUS_EFFECT_BUTTON,
    RANDOM_EFFECT_BUTTON,
    SignalRGBButton,
    SignalRGBButtonEntityDescription,
    async_setup_entry,
)
from custom_components.signalrgb.const import DOMAIN
from signalrgb import SignalRGBException

# Import fixtures from conftest.py


async def test_async_setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test setting up the entry with button entities."""
    # Prepare hass.data for the entry
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: {"client": mock_signalrgb_client}}

    # Call async_setup_entry
    entities = []

    def async_add_entities(added_entities):
        return entities.extend(added_entities)

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    # Check that the entities were added
    assert len(entities) == 3  # next, previous, random buttons
    for entity in entities:
        assert isinstance(entity, SignalRGBButton)


@pytest.fixture
def mock_button_description():
    """Create a mock button entity description."""
    return SignalRGBButtonEntityDescription(
        key=NEXT_EFFECT_BUTTON,
        name="Next Effect",
        icon="mdi:skip-next",
        action_method="apply_next_effect",
    )


@pytest.fixture
def mock_button(mock_hass, mock_signalrgb_client, mock_config_entry, mock_button_description):
    """Create a mock button entity."""
    button = SignalRGBButton(
        mock_signalrgb_client,
        mock_config_entry,
        mock_button_description,
    )
    button.hass = mock_hass
    button.entity_id = f"button.signalrgb_{NEXT_EFFECT_BUTTON}_{mock_config_entry.entry_id}"
    return button


class TestSignalRGBButton:
    """Unit tests for the SignalRGBButton class."""

    async def test_button_properties(self, mock_button):
        """Test basic button properties."""
        assert mock_button.name == "Next Effect"
        assert mock_button.unique_id == f"test_{NEXT_EFFECT_BUTTON}"
        assert mock_button.entity_id == f"button.signalrgb_{NEXT_EFFECT_BUTTON}_test"

    async def test_button_press(self, mock_button, mock_hass):
        """Test pressing the button calls the appropriate method."""
        # Set up hass.data with a coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        mock_coordinator.data = {}
        # Configure MagicMock instead of AsyncMock since async_set_updated_data is not actually async
        mock_coordinator.async_set_updated_data = MagicMock()

        # Mock the client's get methods that are called during direct refresh
        mock_state = MagicMock()
        mock_state.id = "effect_1"
        mock_state.attributes.enabled = True
        mock_state.attributes.global_brightness = 100
        mock_button._client.get_current_state = AsyncMock(return_value=mock_state)
        mock_button._client.get_effect = AsyncMock()

        mock_hass.data[DOMAIN] = {
            mock_button._config_entry.entry_id: {
                "client": mock_button._client,
                "coordinator": mock_coordinator,
            }
        }

        # Press the button
        await mock_button.async_press()

        # Verify the action was called directly (no executor job)
        mock_button._client.apply_next_effect.assert_called_once()

        # Verify the direct state fetching was called (single combined state call)
        mock_button._client.get_current_state.assert_called_once()
        mock_button._client.get_effect.assert_called_once_with("effect_1")

        # Verify coordinator was updated directly
        mock_coordinator.async_set_updated_data.assert_called_once()

    async def test_button_press_error(self, mock_button, mock_hass):
        """Test error handling when pressing the button."""
        # Set up hass.data with a coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        mock_hass.data[DOMAIN] = {
            mock_button._config_entry.entry_id: {
                "client": mock_button._client,
                "coordinator": mock_coordinator,
            }
        }

        # Set up the mock to raise an exception when awaited
        mock_button._client.apply_next_effect = AsyncMock(
            side_effect=SignalRGBException("Test error")
        )

        # Press the button and expect an error
        with pytest.raises(HomeAssistantError):
            await mock_button.async_press()

    async def test_button_press_unknown_method(self, mock_button, mock_hass):
        """Test error when pressing a button with an unknown method."""
        # Set up hass.data
        mock_hass.data[DOMAIN] = {
            mock_button._config_entry.entry_id: {
                "client": mock_button._client,
            }
        }

        # Create a new button with a method name that doesn't exist
        with patch.object(mock_button._client, "unknown_method", None):
            # Use a method that doesn't exist on the client
            mock_button.entity_description = SignalRGBButtonEntityDescription(
                key="unknown",
                name="Unknown Button",
                action_method="unknown_method",
            )

            # Patch hasattr to return False for the unknown method
            with (
                patch("builtins.hasattr", return_value=False),
                pytest.raises(HomeAssistantError),
            ):
                # Press the button and expect an error
                await mock_button.async_press()

    async def test_all_button_types(self, mock_hass, mock_signalrgb_client, mock_config_entry):
        """Test that all button types call the correct methods."""
        # Create a coordinator mock
        mock_coordinator = MagicMock()
        mock_coordinator.async_request_refresh = AsyncMock()
        mock_coordinator.data = {}
        # Configure MagicMock instead of AsyncMock since async_set_updated_data is not actually async
        mock_coordinator.async_set_updated_data = MagicMock()

        # Mock the client's get methods that are called during direct refresh
        mock_state = MagicMock()
        mock_state.id = "effect_1"
        mock_state.attributes.enabled = True
        mock_state.attributes.global_brightness = 100
        mock_signalrgb_client.get_current_state = AsyncMock(return_value=mock_state)
        mock_signalrgb_client.get_effect = AsyncMock()

        # Set up hass.data
        mock_hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "client": mock_signalrgb_client,
                "coordinator": mock_coordinator,
            }
        }

        # Create and test the next effect button
        next_button_desc = SignalRGBButtonEntityDescription(
            key=NEXT_EFFECT_BUTTON,
            name="Next Effect",
            action_method="apply_next_effect",
        )
        next_button = SignalRGBButton(mock_signalrgb_client, mock_config_entry, next_button_desc)
        next_button.hass = mock_hass

        await next_button.async_press()
        mock_signalrgb_client.apply_next_effect.assert_called_once()
        mock_coordinator.async_set_updated_data.assert_called_once()

        # Reset mocks
        mock_signalrgb_client.apply_next_effect.reset_mock()
        mock_coordinator.async_set_updated_data.reset_mock()
        mock_signalrgb_client.get_current_state.reset_mock()
        mock_signalrgb_client.get_effect.reset_mock()

        # Create and test the previous effect button
        prev_button_desc = SignalRGBButtonEntityDescription(
            key=PREVIOUS_EFFECT_BUTTON,
            name="Previous Effect",
            action_method="apply_previous_effect",
        )
        prev_button = SignalRGBButton(mock_signalrgb_client, mock_config_entry, prev_button_desc)
        prev_button.hass = mock_hass

        await prev_button.async_press()
        mock_signalrgb_client.apply_previous_effect.assert_called_once()
        mock_coordinator.async_set_updated_data.assert_called_once()

        # Reset mocks
        mock_signalrgb_client.apply_previous_effect.reset_mock()
        mock_coordinator.async_set_updated_data.reset_mock()
        mock_signalrgb_client.get_current_state.reset_mock()
        mock_signalrgb_client.get_effect.reset_mock()

        # Create and test the random effect button
        random_button_desc = SignalRGBButtonEntityDescription(
            key=RANDOM_EFFECT_BUTTON,
            name="Random Effect",
            action_method="apply_random_effect",
        )
        random_button = SignalRGBButton(
            mock_signalrgb_client, mock_config_entry, random_button_desc
        )
        random_button.hass = mock_hass

        await random_button.async_press()
        mock_signalrgb_client.apply_random_effect.assert_called_once()
        mock_coordinator.async_set_updated_data.assert_called_once()
