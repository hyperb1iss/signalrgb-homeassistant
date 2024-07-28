"""Test the SignalRGB config flow."""

from unittest.mock import patch

import pytest
from signalrgb.client import SignalRGBException

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.signalrgb.const import DOMAIN
from homeassistant.core import HomeAssistant


async def test_form(hass: HomeAssistant, mock_signalrgb) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.signalrgb.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "port": 5000,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "1.1.1.1"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "port": 5000,
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("side_effect", "error_base"),
    [
        (SignalRGBException("Invalid Authentication"), "invalid_auth"),
        (SignalRGBException("Invalid Host"), "invalid_host"),
        (SignalRGBException("Some other error"), "cannot_connect"),
    ],
)
async def test_form_error(
    hass: HomeAssistant, mock_signalrgb, side_effect, error_base
) -> None:
    """Test we handle errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_signalrgb.return_value.get_current_effect.side_effect = side_effect
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": "1.1.1.1",
            "port": 5000,
        },
    )

    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": error_base}

    async def test_form_unknown_exception(hass: HomeAssistant, mock_signalrgb) -> None:
        """Test we handle unknown exceptions."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        mock_signalrgb.return_value.get_current_effect.side_effect = Exception
        with pytest.raises(Exception):  # noqa: B017
            await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    "host": "1.1.1.1",
                    "port": 5000,
                },
            )


@pytest.fixture(name="mock_signalrgb")
def mock_signalrgb_client():
    """Mock SignalRGBClient."""
    with patch(
        "homeassistant.components.signalrgb.config_flow.SignalRGBClient"
    ) as mock_client:
        yield mock_client
