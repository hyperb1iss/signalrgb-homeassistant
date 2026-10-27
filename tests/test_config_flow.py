"""Test configuration through Home Assistant's flow manager."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.signalrgb.api import APIError, SignalRGBConnectionError
from custom_components.signalrgb.const import DOMAIN
from custom_components.signalrgb.coordinator import SignalRGBConfigEntry


@pytest.fixture(autouse=True)
def bypass_setup() -> Generator[None]:
    """Keep these tests focused on flow behavior."""
    with patch("custom_components.signalrgb.async_setup_entry", return_value=True):
        yield


async def test_user_flow(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """Normalize the address and create a unique entry using a borrowed session."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    session = async_get_clientsession(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": " PC.Example. ", "port": 16038}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"host": "pc.example", "port": 16038}
    mock_client.get_current_state.assert_awaited_once()
    assert not session.closed
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (SignalRGBConnectionError("offline"), "cannot_connect"),
        (APIError("403", "Pro required"), "api_error"),
        (RuntimeError("broken"), "unknown"),
    ],
)
async def test_errors_preserve_shared_session(
    hass: HomeAssistant, mock_client: AsyncMock, error: Exception, key: str
) -> None:
    """Every error path leaves HA's shared session open for other integrations."""
    mock_client.get_current_state.side_effect = error
    session = async_get_clientsession(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"host": "pc", "port": 16038}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": key}
    assert not session.closed


@pytest.mark.parametrize("host", ["http://pc", "pc:16038", "", "pc/path", "bad host"])
async def test_reject_url_and_invalid_host(
    hass: HomeAssistant, mock_client: AsyncMock, host: str
) -> None:
    """Addresses cannot smuggle URL paths, ports, or credentials."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data={"host": host, "port": 16038}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"host": "invalid_host"}
    mock_client.get_current_state.assert_not_awaited()


async def test_duplicate_aborts_before_network(
    hass: HomeAssistant, config_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """A configured host is rejected without probing it again."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}, data=dict(config_entry.data)
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_client.get_current_state.assert_not_awaited()


async def test_reconfigure_preserves_entry(
    hass: HomeAssistant, config_entry: SignalRGBConfigEntry, mock_client: AsyncMock
) -> None:
    """Changing address updates the existing entry and its uniqueness key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": config_entry.entry_id},
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "new-pc", "port": 16039}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data == {"host": "new-pc", "port": 16039}
    assert config_entry.unique_id == "new-pc:16039"
    await hass.async_block_till_done()
