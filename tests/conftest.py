"""Pytest configuration file for the tests directory."""

# pylint: disable=unused-argument

import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import pytest

from custom_components.signalrgb.const import DEFAULT_PORT, DOMAIN

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add the custom_components directory to the Home Assistant component search path
os.environ["CUSTOM_COMPONENTS"] = str(project_root / "custom_components")

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in Home Assistant."""
    return


@pytest.fixture
def mock_signalrgb_client():
    """Mock SignalRGB client."""
    with patch("signalrgb.client.SignalRGBClient") as mock_client:
        client = mock_client.return_value
        client.get_current_effect = MagicMock()
        client.get_effects = MagicMock()
        client.apply_effect_by_name = MagicMock()
        client.get_layouts = MagicMock()
        client.current_layout = MagicMock()
        client.apply_next_effect = MagicMock()
        client.apply_previous_effect = MagicMock()
        client.apply_random_effect = MagicMock()
        client.get_effect_presets = MagicMock()
        client.apply_effect_preset = MagicMock()
        yield client


@pytest.fixture
def mock_config_entry():
    """Mock configuration entry."""
    return MagicMock(
        version=1,
        domain=DOMAIN,
        title="SignalRGB",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: DEFAULT_PORT,
        },
        source="user",
        entry_id="test",
        unique_id="192.168.1.100:16038",
    )


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
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
    coordinator.async_request_refresh = AsyncMock()
    coordinator.last_update_success = True
    return coordinator


@pytest.fixture
def setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Set up the entry in hass.data."""
    mock_hass.data[DOMAIN][mock_config_entry.entry_id] = {
        "client": mock_signalrgb_client,
    }
    return mock_hass
