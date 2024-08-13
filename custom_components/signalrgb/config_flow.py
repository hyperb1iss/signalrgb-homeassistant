"""Config flow for SignalRGB integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from signalrgb.client import SignalRGBClient

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
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        try:
            client = SignalRGBClient(user_input[CONF_HOST], user_input[CONF_PORT])
            await self.hass.async_add_executor_job(client.get_current_effect)
        except InvalidAuthError:
            errors["base"] = "invalid_auth"
        except InvalidHostError:
            errors["base"] = "invalid_host"
        except CannotConnectError:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidHostError(HomeAssistantError):
    """Error to indicate there is an invalid host."""
