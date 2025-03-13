"""Test the SignalRGB integration initialization."""

from homeassistant.exceptions import ConfigEntryNotReady
import pytest

from custom_components.signalrgb import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.signalrgb.const import DOMAIN, PLATFORMS
from signalrgb.client import SignalRGBException


async def test_setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test successful setup of the config entry."""
    # Mock the client get_current_effect method to not raise an exception
    mock_hass.async_add_executor_job.return_value = None

    # Call async_setup_entry
    assert await async_setup_entry(mock_hass, mock_config_entry)

    # Verify that the client was stored in hass.data
    assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
    assert "client" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]

    # Verify that the integration was set up for all platforms
    mock_hass.config_entries.async_forward_entry_setups.assert_called_with(
        mock_config_entry, PLATFORMS
    )


async def test_setup_entry_failed(mock_hass, mock_config_entry):
    """Test setup when the client raises an exception."""
    # Make the client raise an exception during connection test
    error = SignalRGBException("Connection failed")
    mock_hass.async_add_executor_job.side_effect = error

    # Call async_setup_entry and expect it to raise ConfigEntryNotReady
    with pytest.raises(ConfigEntryNotReady) as exc_info:
        await async_setup_entry(mock_hass, mock_config_entry)

    # Verify that the exception contains the original error
    assert isinstance(exc_info.value.__cause__, SignalRGBException)


async def test_unload_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test successful unloading of the config entry."""
    # Set up the entry first
    mock_hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "client": mock_signalrgb_client,
            "coordinator": None,
        }
    }

    # Make sure unload platforms returns True
    mock_hass.config_entries.async_unload_platforms.return_value = True

    # Call async_unload_entry
    result = await async_unload_entry(mock_hass, mock_config_entry)

    # Verify results
    assert result is True
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]
    mock_hass.config_entries.async_unload_platforms.assert_called_with(
        mock_config_entry, PLATFORMS
    )
