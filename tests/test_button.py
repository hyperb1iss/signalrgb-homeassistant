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

# Import fixtures from conftest.py


async def test_async_setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test setting up the entry with button entities."""
    # Prepare hass.data for the entry
    mock_hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {"client": mock_signalrgb_client}
    }

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
def mock_button(
    mock_hass, mock_signalrgb_client, mock_config_entry, mock_button_description
):
    """Create a mock button entity."""
    button = SignalRGBButton(
        mock_signalrgb_client,
        mock_config_entry,
        mock_button_description,
    )
    button.hass = mock_hass
    button.entity_id = (
        f"button.signalrgb_{NEXT_EFFECT_BUTTON}_{mock_config_entry.entry_id}"
    )
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
        mock_hass.data[DOMAIN] = {
            mock_button._config_entry.entry_id: {
                "client": mock_button._client,
                "coordinator": mock_coordinator,
            }
        }

        # Press the button
        await mock_button.async_press()

        # Verify the action was called
        mock_button.hass.async_add_executor_job.assert_called_with(
            mock_button._client.apply_next_effect
        )

        # Verify the coordinator was refreshed
        mock_coordinator.async_request_refresh.assert_called_once()

    async def test_button_press_error(self, mock_button):
        """Test error handling when pressing the button."""
        # Test with a non-existent method
        invalid_description = SignalRGBButtonEntityDescription(
            key="invalid",
            name="Invalid Button",
            action_method="nonexistent_method",
        )

        invalid_button = SignalRGBButton(
            mock_button._client,
            mock_button._config_entry,
            invalid_description,
        )
        invalid_button.hass = mock_button.hass

        # Set up hass.data with a mock entry
        mock_button.hass.data[DOMAIN] = {
            mock_button._config_entry.entry_id: {
                "client": mock_button._client,
            }
        }

        # Patch hasattr to return False for nonexistent_method
        with patch("builtins.hasattr", lambda obj, attr: attr != "nonexistent_method"):
            with pytest.raises(HomeAssistantError) as exc_info:
                await invalid_button.async_press()

            assert "Action not supported" in str(exc_info.value)

    async def test_all_button_types(
        self, mock_hass, mock_signalrgb_client, mock_config_entry
    ):
        """Test that all button types call the correct methods."""
        # Create a coordinator mock
        mock_coordinator = MagicMock()
        mock_coordinator.async_request_refresh = AsyncMock()

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
        next_button = SignalRGBButton(
            mock_signalrgb_client, mock_config_entry, next_button_desc
        )
        next_button.hass = mock_hass

        # When we call async_press, it will call the async_add_executor_job with the apply_next_effect method
        # We need to make sure this actually invokes the method on our mock when called
        mock_hass.async_add_executor_job.side_effect = (
            lambda method, *args, **kwargs: method(*args, **kwargs)
        )

        await next_button.async_press()
        mock_signalrgb_client.apply_next_effect.assert_called_once()

        # Reset the mock counters for the next test
        mock_signalrgb_client.reset_mock()

        # Create and test the previous effect button
        prev_button_desc = SignalRGBButtonEntityDescription(
            key=PREVIOUS_EFFECT_BUTTON,
            name="Previous Effect",
            action_method="apply_previous_effect",
        )
        prev_button = SignalRGBButton(
            mock_signalrgb_client, mock_config_entry, prev_button_desc
        )
        prev_button.hass = mock_hass
        await prev_button.async_press()
        mock_signalrgb_client.apply_previous_effect.assert_called_once()

        # Reset the mock counters for the next test
        mock_signalrgb_client.reset_mock()

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
