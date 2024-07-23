"""Config flow for SignalRGB."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from signalrgb.client import SignalRGBClient, SignalRGBException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_PORT, DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    client = SignalRGBClient(data[CONF_HOST], data[CONF_PORT])

    try:
        await hass.async_add_executor_job(client.get_current_effect)
    except SignalRGBException as err:
        LOGGER.error("Connection test failed: %s", err)
        raise CannotConnect from err

    return {"title": f"SignalRGB ({data[CONF_HOST]})"}


class SignalRGBConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SignalRGB."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except vol.Invalid:
                errors["base"] = "invalid_input"
            except Exception as err:  # noqa: BLE001
                LOGGER.exception("Unexpected exception during SignalRGB setup: %s", err)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthorization if the connection is lost."""
        return await self.async_step_user(dict(entry_data))


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
