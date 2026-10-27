"""Exercise SignalRGB's documented protocol against a real HTTP server."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

from aiohttp import ClientConnectionError, ClientSession, web
from aiohttp.test_utils import TestServer
import pytest

from custom_components.signalrgb.api import (
    APIError,
    AsyncSignalRGBClient,
    AuthenticationError,
    CurrentState,
    Effect,
    Layout,
    NotFoundError,
    Preset,
    SignalRGBConnectionError,
)

EFFECT_ID = "Neon Shift.html"


def envelope(data: Any) -> dict[str, Any]:
    """Wrap a resource like the documented local API."""
    return {"api_version": "1.0", "status": "ok", "data": data}


@dataclass
class LocalAPI:
    """A local server with explicit responses and captured HTTP requests."""

    client: AsyncSignalRGBClient
    routes: dict[tuple[str, str], web.Response] = field(default_factory=dict)
    requests: list[tuple[str, str, Any]] = field(default_factory=list)

    def respond(self, method: str, path: str, payload: Any, *, status: int = 200) -> None:
        """Register a JSON response for one API route."""
        self.routes[method, f"/api/v1/{path}"] = web.json_response(payload, status=status)


@pytest.fixture
async def api(socket_enabled: None) -> AsyncIterator[LocalAPI]:
    """Run the actual aiohttp transport against a local fake SignalRGB API."""

    async def handler(request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else None
        local.requests.append((request.method, request.raw_path, body))
        return local.routes.get((request.method, request.path), web.Response(status=404))

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", handler)
    async with TestServer(app) as server, ClientSession() as session:
        assert server.port is not None
        local = LocalAPI(AsyncSignalRGBClient(session, "127.0.0.1", server.port))
        yield local
        assert not session.closed


async def test_current_state(api: LocalAPI) -> None:
    """The lighting resource replaces all legacy state endpoints."""
    api.respond(
        "GET",
        "lighting",
        envelope(
            {
                "id": EFFECT_ID,
                "type": "current_effect",
                "attributes": {"name": "Neon Shift", "enabled": True, "global_brightness": 52.5},
            }
        ),
    )
    assert await api.client.get_current_state() == CurrentState(EFFECT_ID, "Neon Shift", True, 52.5)
    assert api.requests == [("GET", "/api/v1/lighting", None)]


async def test_catalogs_and_nested_layout(api: LocalAPI) -> None:
    """Lists use data.items and current layout has an additional nesting level."""
    api.respond(
        "GET",
        "lighting/effects",
        envelope({"items": [{"id": EFFECT_ID, "attributes": {"name": "Neon Shift"}}]}),
    )
    api.respond("GET", "scenes/layouts", envelope({"items": [{"id": "Desk"}, {"id": "Room"}]}))
    api.respond(
        "GET",
        "scenes/current_layout",
        envelope({"current_layout": {"id": "Room", "type": "layout"}}),
    )
    api.respond(
        "GET",
        f"lighting/effects/{EFFECT_ID}/presets",
        envelope({"items": [{"id": "Default"}, {"id": "Purple"}]}),
    )
    assert await api.client.get_effects() == [Effect(EFFECT_ID, "Neon Shift")]
    assert await api.client.get_layouts() == [Layout("Desk"), Layout("Room")]
    assert await api.client.get_current_layout() == Layout("Room")
    assert await api.client.get_effect_presets(EFFECT_ID) == [Preset("Default"), Preset("Purple")]


async def test_effect_details(api: LocalAPI) -> None:
    """Full effect resources preserve metadata and parameter values."""
    api.respond(
        "GET",
        f"lighting/effects/{EFFECT_ID}",
        envelope(
            {
                "id": EFFECT_ID,
                "attributes": {
                    "name": "Neon Shift",
                    "description": "Color waves",
                    "uses_audio": True,
                    "publisher": "SignalRGB",
                    "parameters": {"color": {"value": "#8800ff"}},
                },
            }
        ),
    )
    effect = await api.client.get_effect(EFFECT_ID)
    assert effect.uses_audio
    assert effect.description == "Color waves"
    assert effect.parameters == {"color": {"value": "#8800ff"}}


async def test_mutation_payloads(api: LocalAPI) -> None:
    """Controls send the exact methods and JSON keys expected by API v1."""
    for method, path in [
        ("PATCH", "lighting/enabled"),
        ("PATCH", "lighting/global_brightness"),
        ("PATCH", "scenes/current_layout"),
        ("PATCH", f"lighting/effects/{EFFECT_ID}/presets"),
        ("POST", f"lighting/effects/{EFFECT_ID}/apply"),
        ("POST", "lighting/next"),
        ("POST", "lighting/previous"),
        ("POST", "lighting/shuffle"),
    ]:
        api.respond(method, path, {"status": "ok"})

    await api.client.set_enabled(False)
    await api.client.set_brightness(73)
    await api.client.set_current_layout("Desk")
    await api.client.apply_effect_preset(EFFECT_ID, "Purple")
    await api.client.apply_effect(EFFECT_ID)
    await api.client.apply_next_effect()
    await api.client.apply_previous_effect()
    await api.client.apply_random_effect()

    assert api.requests == [
        ("PATCH", "/api/v1/lighting/enabled", {"enabled": False}),
        ("PATCH", "/api/v1/lighting/global_brightness", {"global_brightness": 73}),
        ("PATCH", "/api/v1/scenes/current_layout", {"layout": "Desk"}),
        ("PATCH", "/api/v1/lighting/effects/Neon%20Shift%2Ehtml/presets", {"preset": "Purple"}),
        ("POST", "/api/v1/lighting/effects/Neon%20Shift%2Ehtml/apply", None),
        ("POST", "/api/v1/lighting/next", None),
        ("POST", "/api/v1/lighting/previous", None),
        ("POST", "/api/v1/lighting/shuffle", None),
    ]


@pytest.mark.parametrize(
    ("status", "payload", "error_type", "detail"),
    [
        (
            403,
            {"status": "error", "errors": [{"code": "pro_required", "detail": "Pro required"}]},
            AuthenticationError,
            "Pro required",
        ),
        (401, {"status": "error"}, AuthenticationError, "401"),
        (403, [], AuthenticationError, "403"),
        (
            404,
            {"status": "error", "errors": [{"code": "missing", "detail": "Missing effect"}]},
            NotFoundError,
            "Missing effect",
        ),
        (
            200,
            {"status": "error", "errors": [{"code": "403", "detail": "Sign in"}]},
            AuthenticationError,
            "Sign in",
        ),
        (
            409,
            {"status": "error", "errors": [{"code": "409", "detail": "History empty"}]},
            APIError,
            "History empty",
        ),
        (302, {}, APIError, "302"),
        (200, {"data": {}}, APIError, "successful API status"),
        (200, [], APIError, "JSON object"),
        (200, {"status": "ok"}, APIError, "JSON object"),
    ],
)
async def test_api_errors(
    api: LocalAPI, status: int, payload: Any, error_type: type[APIError], detail: str
) -> None:
    """Authentication, server errors, and bad envelopes remain distinguishable."""
    api.respond("GET", "lighting", payload, status=status)
    with pytest.raises(error_type, match=detail):
        await api.client.get_current_state()


@pytest.mark.parametrize("status", [200, 403, 500])
async def test_non_json_response(api: LocalAPI, status: int) -> None:
    """An HTML response cannot escape as a JSON decoding error."""
    api.routes["GET", "/api/v1/lighting"] = web.Response(
        text="<html>Unavailable</html>", status=status
    )
    error_type = AuthenticationError if status == 403 else APIError
    with pytest.raises(error_type):
        await api.client.get_current_state()


@pytest.mark.parametrize("exception", [TimeoutError(), ClientConnectionError("PC offline")])
async def test_network_errors(exception: Exception) -> None:
    """Transport failures become retryable errors without closing the shared session."""
    async with ClientSession() as session:
        client = AsyncSignalRGBClient(session, "signalrgb.local")
        with (
            patch.object(session, "request", side_effect=exception),
            pytest.raises(SignalRGBConnectionError),
        ):
            await client.get_current_state()
        assert not session.closed


@pytest.mark.parametrize("brightness", [True, "50", None, -1, 101, float("nan")])
async def test_invalid_state_brightness(api: LocalAPI, brightness: Any) -> None:
    """Invalid server state is rejected instead of silently becoming a light state."""
    api.respond(
        "GET",
        "lighting",
        envelope(
            {
                "id": EFFECT_ID,
                "attributes": {
                    "name": "Neon Shift",
                    "enabled": True,
                    "global_brightness": brightness,
                },
            }
        ),
    )
    with pytest.raises(APIError, match="Brightness"):
        await api.client.get_current_state()


@pytest.mark.parametrize("data", [{}, {"items": None}, {"items": [{}]}, {"items": ["name"]}])
async def test_malformed_catalog(api: LocalAPI, data: Any) -> None:
    """Malformed catalogs do not silently become empty option lists."""
    api.respond("GET", "lighting/effects", envelope(data))
    with pytest.raises(APIError):
        await api.client.get_effects()


@pytest.mark.parametrize("brightness", [-1, 101, True])
async def test_invalid_requested_brightness(api: LocalAPI, brightness: int) -> None:
    """Out-of-range input is rejected before issuing a request."""
    with pytest.raises(ValueError, match="Brightness"):
        await api.client.set_brightness(brightness)
    assert not api.requests


@pytest.mark.parametrize("effect_id", ["Neon / Shift?#%.html", ".."])
async def test_effect_id_is_one_encoded_segment(api: LocalAPI, effect_id: str) -> None:
    """Reserved characters and dot segments cannot escape the effect ID."""
    api.respond("POST", f"lighting/effects/{effect_id}/apply", {"status": "ok"})
    await api.client.apply_effect(effect_id)
    expected = {
        "Neon / Shift?#%.html": "Neon%20%2F%20Shift%3F%23%25%2Ehtml",
        "..": "%2E%2E",
    }
    assert api.requests == [("POST", f"/api/v1/lighting/effects/{expected[effect_id]}/apply", None)]
