"""Common identity and command handling for SignalRGB entities."""

from collections.abc import Awaitable, Callable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SignalRGBError
from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SignalRGBConfigEntry, SignalRGBCoordinator


class SignalRGBEntity(CoordinatorEntity[SignalRGBCoordinator]):
    """An entity backed by the entry's shared snapshot."""

    _attr_has_entity_name = True

    def __init__(self, entry: SignalRGBConfigEntry, key: str) -> None:
        """Keep the device and entity identifiers stable across upgrades."""
        super().__init__(entry.runtime_data)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{MODEL} {entry.data['host']}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def _async_command(self, command: Callable[[], Awaitable[None]]) -> None:
        """Execute a command and refresh every entity from the server."""
        try:
            await command()
        except SignalRGBError as err:
            # A multi-part command can partially succeed before a later request fails.
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError(f"SignalRGB command failed: {err}") from err
        await self.coordinator.async_request_refresh()
