"""Support for SignalRGB button controls."""

# pylint: disable=duplicate-code

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from signalrgb.client import SignalRGBClient, SignalRGBException

from .const import (
    DOMAIN,
    LOGGER,
    MANUFACTURER,
    MODEL,
)

# Button types
NEXT_EFFECT_BUTTON: Final = "next_effect"
PREVIOUS_EFFECT_BUTTON: Final = "previous_effect"
RANDOM_EFFECT_BUTTON: Final = "random_effect"


@dataclass(frozen=True)
class SignalRGBButtonEntityDescription(ButtonEntityDescription):
    """Class describing SignalRGB button entities."""

    key: str  # Required field from parent class
    name: str | None = None  # Required field from parent class
    icon: str = "mdi:led-strip-variant"
    action_method: str = ""  # Make this required and non-None


BUTTON_TYPES: Final[list[SignalRGBButtonEntityDescription]] = [
    SignalRGBButtonEntityDescription(
        key=NEXT_EFFECT_BUTTON,
        name="Next Effect",
        icon="mdi:skip-next",
        action_method="apply_next_effect",
    ),
    SignalRGBButtonEntityDescription(
        key=PREVIOUS_EFFECT_BUTTON,
        name="Previous Effect",
        icon="mdi:skip-previous",
        action_method="apply_previous_effect",
    ),
    SignalRGBButtonEntityDescription(
        key=RANDOM_EFFECT_BUTTON,
        name="Random Effect",
        icon="mdi:shuffle-variant",
        action_method="apply_random_effect",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SignalRGB button entities based on a config entry."""
    LOGGER.debug("Setting up SignalRGB button entities for entry: %s", entry.entry_id)
    client: SignalRGBClient = hass.data[DOMAIN][entry.entry_id]["client"]

    entities = []
    for description in BUTTON_TYPES:
        entities.append(
            SignalRGBButton(
                client,
                entry,
                description,
            )
        )

    LOGGER.info(
        "Adding %s SignalRGB button entities: %s",
        len(entities),
        [e.entity_id for e in entities],
    )
    async_add_entities(entities)


class SignalRGBButton(ButtonEntity):
    """Representation of a SignalRGB button entity."""

    _attr_has_entity_name = True
    entity_description: SignalRGBButtonEntityDescription

    def __init__(
        self,
        client: SignalRGBClient,
        config_entry: ConfigEntry,
        description: SignalRGBButtonEntityDescription,
    ) -> None:
        """Initialize the button entity."""
        self.entity_description = description
        self._client = client
        self._config_entry = config_entry
        self._attr_name = str(description.name) if description.name else None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"{MODEL} {config_entry.data['host']}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
        self.entity_id = f"button.signalrgb_{description.key}_{config_entry.entry_id}"
        LOGGER.debug("SignalRGBButton initialized: %s", self.entity_id)

    async def async_press(self) -> None:
        """Handle the button press."""
        LOGGER.debug("Button pressed: %s", self.entity_id)
        method_name = self.entity_description.action_method

        if not method_name or not hasattr(self._client, method_name):
            LOGGER.error("Method %s not found on SignalRGBClient", method_name)
            raise HomeAssistantError(f"Action not supported: {method_name}")

        try:
            # Get the method and call it
            method = getattr(self._client, method_name)
            await self.hass.async_add_executor_job(method)
            LOGGER.info("Successfully executed %s on SignalRGB", method_name)

            # The action changes the state of other entities, so we need to
            # request a refresh of any data coordinators in the domain
            # This will update the light entity and select entities
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
            for key, item in entry_data.items():
                if key != "client" and hasattr(item, "async_request_refresh"):
                    await item.async_request_refresh()

        except SignalRGBException as err:
            LOGGER.error("Failed to execute %s: %s", method_name, err)
            raise HomeAssistantError(f"Failed to execute {method_name}: {err}") from err
