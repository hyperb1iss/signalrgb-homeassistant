"""Support for SignalRGB button controls."""

# pylint: disable=duplicate-code

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Final

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from signalrgb import AsyncSignalRGBClient, SignalRGBException

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
    client: AsyncSignalRGBClient = hass.data[DOMAIN][entry.entry_id]["client"]

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
        "Adding %s SignalRGB button entities for entry ID %s: %s",
        len(entities),
        entry.entry_id,
        [e.entity_description.key for e in entities],
    )
    async_add_entities(entities)


class SignalRGBButton(ButtonEntity):
    """Representation of a SignalRGB button entity."""

    _attr_has_entity_name = True
    entity_description: SignalRGBButtonEntityDescription

    def __init__(
        self,
        client: AsyncSignalRGBClient,
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
        LOGGER.debug(
            "SignalRGBButton %s initialized for entry: %s",
            description.key,
            config_entry.entry_id,
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        LOGGER.debug(
            "Button pressed: %s for entry: %s",
            self.entity_description.key,
            self._config_entry.entry_id,
        )
        method_name = self.entity_description.action_method

        if not method_name or not hasattr(self._client, method_name):
            LOGGER.error("Method %s not found on AsyncSignalRGBClient", method_name)
            raise HomeAssistantError(f"Action not supported: {method_name}")

        try:
            # Get the method and call it directly (it's already async)
            method = getattr(self._client, method_name)
            await method()
            LOGGER.info("Successfully executed %s on SignalRGB", method_name)

            # Instead of just refreshing coordinators, let's directly fetch the current state
            # and update the light entity's state with it
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]

            # Very short delay to allow SignalRGB to process the change
            # This is much shorter than the 2 seconds in the light entity
            await asyncio.sleep(0.2)

            # Directly fetch the current state from the API
            try:
                LOGGER.debug("Directly fetching current state after button press")
                current_effect = await self._client.get_current_effect()
                is_on = await self._client.get_enabled()
                brightness = await self._client.get_brightness()

                # If we have a light coordinator, update its data directly
                if "coordinator" in entry_data:
                    coordinator = entry_data["coordinator"]
                    LOGGER.debug("Updating light coordinator data directly")
                    coordinator.data = {
                        "current_effect": current_effect,
                        "is_on": is_on,
                        "brightness": brightness,
                    }
                    # Force an update to all entities using this coordinator
                    coordinator.async_set_updated_data(coordinator.data)

                # Also refresh any other coordinators (like the effect/preset coordinator)
                for key, item in entry_data.items():
                    if key not in {"client", "coordinator"} and hasattr(
                        item, "async_request_refresh"
                    ):
                        LOGGER.debug("Refreshing additional coordinator: %s", key)
                        await item.async_request_refresh()

            except SignalRGBException as refresh_err:
                LOGGER.warning(
                    "Error refreshing state after button press: %s", refresh_err
                )
                # Fall back to regular coordinator refresh if direct update fails
                if "coordinator" in entry_data:
                    await entry_data["coordinator"].async_request_refresh()

        except SignalRGBException as err:
            LOGGER.error("Failed to execute %s: %s", method_name, err)
            raise HomeAssistantError(f"Failed to execute {method_name}: {err}") from err
