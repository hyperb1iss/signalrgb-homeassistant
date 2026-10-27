"""Typed client for SignalRGB's local v1 API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout
from yarl import URL


class SignalRGBError(Exception):
    """Base error raised by the local API client."""


class SignalRGBConnectionError(SignalRGBError):
    """The SignalRGB server could not be reached."""


class APIError(SignalRGBError):
    """The API rejected a request or returned an invalid response."""

    def __init__(self, code: str, detail: str) -> None:
        """Retain the server's error details."""
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class AuthenticationError(APIError):
    """SignalRGB requires a signed-in account with API access."""


class NotFoundError(APIError):
    """The requested resource does not exist."""


@dataclass(frozen=True, slots=True)
class CurrentState:
    """The active canvas state returned by the lighting endpoint."""

    effect_id: str
    effect_name: str
    enabled: bool
    brightness: float


@dataclass(frozen=True, slots=True)
class Effect:
    """An installed effect and its optional descriptive metadata."""

    id: str
    name: str
    description: str = ""
    publisher: str = ""
    developer_effect: bool = False
    uses_audio: bool = False
    uses_input: bool = False
    uses_meters: bool = False
    uses_video: bool = False
    image: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Layout:
    """A layout whose ID is its display name."""

    id: str


@dataclass(frozen=True, slots=True)
class Preset:
    """An effect preset whose ID is its display name."""

    id: str


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise APIError("invalid_response", "Expected a JSON object")
    return value


def _string(data: dict[str, Any], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise APIError("invalid_response", f"Expected a string for {key}")
    return value


def _boolean(data: dict[str, Any], key: str, *, default: bool | None = None) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise APIError("invalid_response", f"Expected a boolean for {key}")
    return value


def _effect(value: Any) -> Effect:
    data = _object(value)
    attributes = _object(data.get("attributes"))
    return Effect(
        id=_string(data, "id"),
        name=_string(attributes, "name"),
        description=_string(attributes, "description", ""),
        publisher=_string(attributes, "publisher", ""),
        developer_effect=_boolean(attributes, "developer_effect", default=False),
        uses_audio=_boolean(attributes, "uses_audio", default=False),
        uses_input=_boolean(attributes, "uses_input", default=False),
        uses_meters=_boolean(attributes, "uses_meters", default=False),
        uses_video=_boolean(attributes, "uses_video", default=False),
        image=_string(attributes, "image", ""),
        parameters=_object(attributes.get("parameters", {})),
    )


def _items(data: dict[str, Any]) -> list[Any]:
    items = data.get("items")
    if not isinstance(items, list):
        raise APIError("invalid_response", "Expected a resource list")
    return items


def _effect_path(effect_id: str) -> str:
    if not effect_id:
        raise ValueError("An effect ID is required")
    # Quote a complete path segment, including dots to prevent dot-segment traversal.
    return f"lighting/effects/{quote(effect_id, safe='').replace('.', '%2E')}"


class AsyncSignalRGBClient:
    """Access the local API using a session owned by Home Assistant."""

    def __init__(
        self, session: ClientSession, host: str, port: int = 16038, *, timeout: float = 10
    ) -> None:
        """Use the supplied session without taking ownership of its lifetime."""
        self._session = session
        self._base_url = URL.build(scheme="http", host=host, port=port, path="/api/v1")
        self._timeout = ClientTimeout(total=timeout)

    async def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = URL(f"{self._base_url}/{path}", encoded=True)
        try:
            async with self._session.request(
                method,
                url,
                json=payload,
                timeout=self._timeout,
                allow_redirects=False,
            ) as response:
                try:
                    body = await response.json(content_type=None)
                except ValueError as err:
                    if response.status >= 400:
                        self._raise_api_error(str(response.status), response.reason or "HTTP error")
                    raise APIError("invalid_response", "SignalRGB returned invalid JSON") from err
                if response.status >= 300 and not isinstance(body, dict):
                    self._raise_api_error(str(response.status), response.reason or "HTTP error")
                data = _object(body)
                if response.status >= 300 or data.get("status") == "error":
                    errors = data.get("errors")
                    error = errors[0] if isinstance(errors, list) and errors else {}
                    error = error if isinstance(error, dict) else {}
                    code = str(error.get("code", response.status))
                    detail = str(error.get("detail", error.get("title", response.reason)))
                    # HTTP authentication failures remain authentication errors even
                    # when a server supplies a different application-specific code.
                    if response.status in {401, 403}:
                        raise AuthenticationError(code, detail)
                    if response.status == 404:
                        raise NotFoundError(code, detail)
                    self._raise_api_error(code, detail)
                if data.get("status") != "ok":
                    raise APIError("invalid_response", "Missing successful API status")
                return data
        except TimeoutError as err:
            raise SignalRGBConnectionError("Request to SignalRGB timed out") from err
        except ClientError as err:
            raise SignalRGBConnectionError(f"Cannot communicate with SignalRGB: {err}") from err

    @staticmethod
    def _raise_api_error(code: str, detail: str) -> None:
        if code in {"401", "403"}:
            raise AuthenticationError(code, detail)
        if code == "404":
            raise NotFoundError(code, detail)
        raise APIError(code, detail)

    async def _get(self, path: str) -> dict[str, Any]:
        return _object((await self._request("GET", path)).get("data"))

    async def get_current_state(self) -> CurrentState:
        """Fetch the effect identity, power, and brightness in one request."""
        data = await self._get("lighting")
        attributes = _object(data.get("attributes"))
        brightness = attributes.get("global_brightness")
        if (
            isinstance(brightness, bool)
            or not isinstance(brightness, (int, float))
            or not 0 <= brightness <= 100
        ):
            raise APIError("invalid_response", "Brightness must be a number between 0 and 100")
        return CurrentState(
            effect_id=_string(data, "id"),
            effect_name=_string(attributes, "name"),
            enabled=_boolean(attributes, "enabled"),
            brightness=float(brightness),
        )

    async def get_effect(self, effect_id: str) -> Effect:
        """Fetch an effect's details."""
        return _effect(await self._get(_effect_path(effect_id)))

    async def get_effects(self) -> list[Effect]:
        """Fetch the installed effect catalog."""
        return [_effect(item) for item in _items(await self._get("lighting/effects"))]

    async def get_layouts(self) -> list[Layout]:
        """Fetch all available layouts."""
        return [
            Layout(_string(_object(item), "id"))
            for item in _items(await self._get("scenes/layouts"))
        ]

    async def get_current_layout(self) -> Layout:
        """Fetch the current layout from the nested scenes response."""
        data = await self._get("scenes/current_layout")
        return Layout(_string(_object(data.get("current_layout")), "id"))

    async def get_effect_presets(self, effect_id: str) -> list[Preset]:
        """Fetch the presets available for an effect."""
        return [
            Preset(_string(_object(item), "id"))
            for item in _items(await self._get(f"{_effect_path(effect_id)}/presets"))
        ]

    async def set_enabled(self, enabled: bool) -> None:
        """Set whether the canvas sends colors to devices."""
        await self._request("PATCH", "lighting/enabled", {"enabled": enabled})

    async def set_brightness(self, brightness: int) -> None:
        """Set global brightness as a percentage."""
        if isinstance(brightness, bool) or not 0 <= brightness <= 100:
            raise ValueError("Brightness must be between 0 and 100")
        await self._request(
            "PATCH", "lighting/global_brightness", {"global_brightness": brightness}
        )

    async def apply_effect(self, effect_id: str) -> None:
        """Apply an installed effect by its stable ID."""
        await self._request("POST", f"{_effect_path(effect_id)}/apply")

    async def set_current_layout(self, layout_id: str) -> None:
        """Apply a layout by its name."""
        await self._request("PATCH", "scenes/current_layout", {"layout": layout_id})

    async def apply_effect_preset(self, effect_id: str, preset_id: str) -> None:
        """Apply a preset to the given effect."""
        await self._request("PATCH", f"{_effect_path(effect_id)}/presets", {"preset": preset_id})

    async def apply_next_effect(self) -> None:
        """Advance through effect history."""
        await self._request("POST", "lighting/next")

    async def apply_previous_effect(self) -> None:
        """Return to the previous effect in history."""
        await self._request("POST", "lighting/previous")

    async def apply_random_effect(self) -> None:
        """Shuffle to a random installed effect."""
        await self._request("POST", "lighting/shuffle")
