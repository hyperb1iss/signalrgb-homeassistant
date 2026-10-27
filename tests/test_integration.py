"""Exercise real HTTP transport through Home Assistant setup and services."""

from aiohttp import web
from aiohttp.test_utils import TestServer
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.signalrgb.coordinator import SignalRGBConfigEntry

from .conftest import entity_id


@pytest.mark.usefixtures("socket_enabled")
async def test_http_setup_commands_and_unload(
    hass: HomeAssistant, config_entry: SignalRGBConfigEntry
) -> None:
    """Keep registry identity while commands reach the actual HTTP client."""
    state = {"enabled": True, "global_brightness": 45, "name": "Real"}
    calls: list[tuple[str, str]] = []

    async def handler(request: web.Request) -> web.Response:
        path = request.path.removeprefix("/api/v1/")
        calls.append((request.method, path))
        if request.method == "PATCH" and path == "lighting/enabled":
            state.update(await request.json())
            return web.json_response({"status": "ok"})
        resources = {
            "lighting": {"id": "real.html", "attributes": dict(state)},
            "lighting/effects": {"items": [{"id": "real.html", "attributes": {"name": "Real"}}]},
            "lighting/effects/real.html": {"id": "real.html", "attributes": {"name": "Real"}},
            "lighting/effects/real.html/presets": {"items": [{"id": "Default"}]},
            "scenes/layouts": {"items": [{"id": "Desk"}]},
            "scenes/current_layout": {"current_layout": {"id": "Desk"}},
        }
        return web.json_response({"status": "ok", "data": resources[path]})

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server:
        hass.config_entries.async_update_entry(
            config_entry, data={"host": "127.0.0.1", "port": server.port}
        )
        before = er.async_get(hass).async_get_or_create(
            "light",
            "signalrgb",
            f"{config_entry.entry_id}_light",
            config_entry=config_entry,
            suggested_object_id="my_existing_lights",
        )
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        light_id = entity_id(hass, config_entry, "light", "light")
        assert light_id == before.entity_id
        initial = hass.states.get(light_id)
        assert initial is not None
        assert initial.state == "on"
        assert initial.attributes["brightness"] == 115
        assert calls.count(("GET", "lighting")) == 1

        # The desktop app can change state before Home Assistant's next poll.
        state["enabled"] = False
        await hass.services.async_call("light", "turn_on", {"entity_id": light_id}, blocking=True)
        assert state["enabled"] is True
        assert ("PATCH", "lighting/enabled") in calls
        after = hass.states.get(light_id)
        assert after is not None and after.state == "on"

        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
        assert config_entry.state is ConfigEntryState.NOT_LOADED
        assert not async_get_clientsession(hass).closed
