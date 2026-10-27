"""Support for SignalRGB effect navigation."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AsyncSignalRGBClient
from .coordinator import SignalRGBConfigEntry
from .entity import SignalRGBEntity


@dataclass(frozen=True, kw_only=True)
class SignalRGBButtonDescription(ButtonEntityDescription):
    """Describe a navigation command with a typed callable."""

    action: Callable[[AsyncSignalRGBClient], Awaitable[None]]


BUTTONS = (
    SignalRGBButtonDescription(
        key="next_effect",
        name="Next Effect",
        icon="mdi:skip-next",
        action=lambda client: client.apply_next_effect(),
    ),
    SignalRGBButtonDescription(
        key="previous_effect",
        name="Previous Effect",
        icon="mdi:skip-previous",
        action=lambda client: client.apply_previous_effect(),
    ),
    SignalRGBButtonDescription(
        key="random_effect",
        name="Random Effect",
        icon="mdi:shuffle-variant",
        action=lambda client: client.apply_random_effect(),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant, entry: SignalRGBConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add effect navigation buttons."""
    async_add_entities(SignalRGBButton(entry, description) for description in BUTTONS)


class SignalRGBButton(SignalRGBEntity, ButtonEntity):
    """A navigation button with the same availability as the light."""

    def __init__(
        self, entry: SignalRGBConfigEntry, description: SignalRGBButtonDescription
    ) -> None:
        """Initialize the button."""
        super().__init__(entry, description.key)
        self.entity_description = description
        self._action = description.action

    async def async_press(self) -> None:
        """Navigate effects and refresh the shared snapshot."""
        await self._async_command(lambda: self._action(self.coordinator.client))
