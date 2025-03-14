"""Test the SignalRGB integration initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import ConfigEntryNotReady
import pytest

from custom_components.signalrgb import (
    async_setup_entry,
    async_unload_entry,
)
from custom_components.signalrgb.const import DOMAIN, PLATFORMS
from signalrgb.exceptions import SignalRGBException


@pytest.fixture
def mock_get_current_effect():
    """Mock the get_current_effect method to avoid HTTP calls."""
    # Instead of mocking _get_current_state, we should mock get_current_effect directly
    with patch(
        "signalrgb.AsyncSignalRGBClient.get_current_effect", new_callable=AsyncMock
    ) as mock:
        # Create a mock effect with the right attributes
        mock_effect = MagicMock()
        mock_effect.attributes.name = "Test Effect"
        mock.return_value = mock_effect
        yield mock


@pytest.fixture
def mock_httpx_client():
    """Mock the httpx client to prevent socket connections."""
    with patch("httpx.AsyncClient", autospec=True) as mock:
        client_instance = MagicMock()
        client_instance.aclose = AsyncMock()
        client_instance.request = AsyncMock()
        mock.return_value = client_instance
        yield mock


async def test_setup_entry(
    mock_hass, mock_config_entry, mock_get_current_effect, mock_httpx_client
):
    """Test successful setup of the config entry."""
    # Call async_setup_entry
    assert await async_setup_entry(mock_hass, mock_config_entry)

    # Verify that a client was stored in hass.data
    assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
    assert "client" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]

    # Verify that the integration was set up for all platforms
    mock_hass.config_entries.async_forward_entry_setups.assert_called_with(
        mock_config_entry, PLATFORMS
    )


async def test_setup_entry_failed(mock_hass, mock_config_entry, mock_httpx_client):
    """Test setup when the client raises an exception."""
    # Set up the error
    error = SignalRGBException("Connection failed")

    # Directly patch at the method level
    with (
        patch(
            "signalrgb.AsyncSignalRGBClient.get_current_effect",
            new_callable=AsyncMock,
            side_effect=error,
        ),
        pytest.raises(ConfigEntryNotReady) as exc_info,
    ):
        # Call async_setup_entry and expect it to raise ConfigEntryNotReady
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
    # Verify the client was properly closed
    mock_signalrgb_client.aclose.assert_called_once()
