"""Config flow for SignalRGB integration."""

from __future__ import annotations

from typing import Any

from signalrgb.client import SignalRGBClient, SignalRGBException
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError

from .const import DEFAULT_PORT, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class SignalRGBConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SignalRGB."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        errors = {}

        try:
            client = SignalRGBClient(user_input[CONF_HOST], user_input[CONF_PORT])
            await self.hass.async_add_executor_job(client.get_current_effect)
        except SignalRGBException as ex:
            if str(ex) == "Invalid Authentication":
                errors["base"] = "invalid_auth"
            elif str(ex) == "Invalid Host":
                errors["base"] = "invalid_host"
            else:
                errors["base"] = "cannot_connect"
        else:
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidHost(HomeAssistantError):
    """Error to indicate there is an invalid host."""
