"""Config flow for SignalRGB integration."""

from __future__ import annotations

from ipaddress import ip_address
import re
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import probatio

from .api import AsyncSignalRGBClient, SignalRGBConnectionError, SignalRGBError
from .const import DEFAULT_PORT, DOMAIN, LOGGER


def _normalize_host(host: str) -> str:
    """Accept a hostname or IP address without URL components."""
    host = host.strip().removesuffix(".").lower()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return ip_address(host).compressed
    except ValueError:
        if len(host) > 253 or not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in host.split(".")
        ):
            raise ValueError("Enter a hostname or IP address, without a URL or port") from None
        return host


def _schema(defaults: dict[str, Any] | None = None) -> probatio.Schema:
    """Build the connection form with existing values when reconfiguring."""
    defaults = defaults or {}
    return probatio.Schema(
        {
            probatio.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            probatio.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): cv.port,
        }
    )


class SignalRGBConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a SignalRGB host using Home Assistant's shared session."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Add a new host."""
        return await self._async_connection_step("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change a host or port without replacing its entities."""
        return await self._async_connection_step("reconfigure", user_input)

    async def _async_connection_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Validate the address and test the documented lighting endpoint."""
        entry = self._get_reconfigure_entry() if step_id == "reconfigure" else None
        errors: dict[str, str] = {}
        defaults = dict(entry.data) if entry else None
        if user_input is not None:
            data = dict(user_input)
            try:
                data[CONF_HOST] = _normalize_host(data[CONF_HOST])
            except ValueError:
                errors[CONF_HOST] = "invalid_host"
            else:
                unique_id = f"{data[CONF_HOST]}:{data[CONF_PORT]}"
                for configured in self._async_current_entries():
                    if configured.entry_id == (entry.entry_id if entry else None):
                        continue
                    if (
                        _normalize_host(configured.data[CONF_HOST]) == data[CONF_HOST]
                        and configured.data.get(CONF_PORT, DEFAULT_PORT) == data[CONF_PORT]
                    ):
                        return self.async_abort(reason="already_configured")
                try:
                    client = AsyncSignalRGBClient(
                        async_get_clientsession(self.hass), data[CONF_HOST], data[CONF_PORT]
                    )
                    await client.get_current_state()
                except SignalRGBConnectionError:
                    errors["base"] = "cannot_connect"
                except SignalRGBError as err:
                    LOGGER.debug("SignalRGB validation failed: %s", err)
                    errors["base"] = "api_error"
                except Exception:  # noqa: BLE001 - Config flows must return a usable form on failure.
                    LOGGER.exception("Unexpected error validating SignalRGB")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(unique_id)
                    if entry:
                        return self.async_update_reload_and_abort(
                            entry, unique_id=unique_id, title=data[CONF_HOST], data_updates=data
                        )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=data[CONF_HOST], data=data)
        return self.async_show_form(
            step_id=step_id,
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )
