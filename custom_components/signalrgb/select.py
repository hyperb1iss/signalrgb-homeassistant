"""Support for SignalRGB layout and preset selection."""

# pylint: disable=duplicate-code

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Final

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from signalrgb import AsyncSignalRGBClient, SignalRGBException
from signalrgb.model import Effect, Layout

from .const import (
    DOMAIN,
    LOGGER,
    MANUFACTURER,
    MODEL,
    UPDATE_INTERVAL,
)

# Entity types
LAYOUT_SELECT: Final = "layout"
PRESET_SELECT: Final = "preset"


@dataclass
class SelectEntityDescription:
    """Class describing SignalRGB select entities."""

    key: str
    name: str
    icon: str
    entity_registry_enabled_default: bool = True


SELECT_TYPES: Final[list[SelectEntityDescription]] = [
    SelectEntityDescription(
        key=LAYOUT_SELECT,
        name="Layout",
        icon="mdi:view-grid-outline",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SignalRGB select entities based on a config entry."""
    LOGGER.debug("Setting up SignalRGB select entities for entry: %s", entry.entry_id)
    client: AsyncSignalRGBClient = hass.data[DOMAIN][entry.entry_id]["client"]

    # Layout coordinator
    async def async_update_layouts() -> dict[str, Any]:
        """Fetch layouts from API endpoint."""
        try:
            LOGGER.debug("Fetching layouts from SignalRGB API")
            layouts = await client.get_layouts()
            current_layout = await client.get_current_layout()
            return {
                "layouts": layouts,
                "current_layout": current_layout,
            }
        except SignalRGBException as err:
            LOGGER.error("Error fetching layouts from SignalRGB API: %s", err)
            raise HomeAssistantError(f"Error fetching layouts: {err}") from err

    layout_coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name="signalrgb_layouts",
        update_method=async_update_layouts,
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
        config_entry=entry,
    )

    # Effect coordinator - Used for both effects and presets
    async def async_update_effects() -> dict[str, Any]:
        """Fetch current effect and available effects from API endpoint."""
        try:
            LOGGER.debug("Fetching current effect from SignalRGB API")
            current_effect = await client.get_current_effect()
            effects = await client.get_effects()
            LOGGER.debug(
                "Current effect: %s",
                current_effect.attributes.name if current_effect else "None",
            )

            # If we have a current effect, also get its presets
            presets = []
            if current_effect:
                try:
                    LOGGER.debug("Fetching presets for effect: %s", current_effect.id)
                    presets = await client.get_effect_presets(current_effect.id)
                    LOGGER.debug(
                        "Found %s presets for effect %s: %s",
                        len(presets),
                        current_effect.attributes.name,
                        [preset.id for preset in presets],
                    )
                except SignalRGBException as preset_err:
                    LOGGER.warning(
                        "Error fetching presets for effect %s: %s",
                        current_effect.attributes.name,
                        preset_err,
                    )

            return {
                "current_effect": current_effect,
                "effects": effects,
                "presets": presets,
            }
        except SignalRGBException as err:
            LOGGER.error("Error fetching effects from SignalRGB API: %s", err)
            raise HomeAssistantError(f"Error fetching effects: {err}") from err

    effect_coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name="signalrgb_effects",
        update_method=async_update_effects,
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
        config_entry=entry,
    )

    # Initial refresh
    await asyncio.gather(
        layout_coordinator.async_refresh(),
        effect_coordinator.async_refresh(),
    )

    entities: list[SignalRGBBaseSelect] = []

    # Add layout selector
    entities.append(
        SignalRGBLayoutSelect(
            layout_coordinator,
            client,
            entry,
        )
    )

    # Always add preset selector, regardless of whether presets are available
    entities.append(
        SignalRGBPresetSelect(
            effect_coordinator,
            client,
            entry,
        )
    )

    LOGGER.info(
        "Adding %s SignalRGB select entities for entry ID: %s: %s",
        len(entities),
        entry.entry_id,
        [type(e).__name__ for e in entities],
    )
    async_add_entities(entities)


class SignalRGBBaseSelect(CoordinatorEntity, SelectEntity):
    """Base class for SignalRGB select entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: AsyncSignalRGBClient,
        config_entry: ConfigEntry,
        select_type: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._client = client
        self._config_entry = config_entry
        self._select_type = select_type
        self._attr_unique_id = f"{config_entry.entry_id}_{select_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"{MODEL} {config_entry.data['host']}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
        LOGGER.debug(
            "SignalRGBSelect %s initialized for entry: %s",
            select_type.title(),
            config_entry.entry_id,
        )


class SignalRGBLayoutSelect(SignalRGBBaseSelect):
    """Representation of a SignalRGB layout selector."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: AsyncSignalRGBClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the layout select entity."""
        super().__init__(coordinator, client, config_entry, LAYOUT_SELECT)
        self._attr_name = "Layout"
        self._attr_icon = "mdi:view-grid-outline"
        self._layouts: dict[str, Layout] = {}
        self._current_layout_id: str | None = None
        self._update_data()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and bool(self._layouts)

    @property
    def options(self) -> list[str]:
        """Return a sorted list of available layouts."""
        return sorted(self._layouts.keys())

    @property
    def current_option(self) -> str | None:
        """Return the current selected layout."""
        if not self._current_layout_id:
            return None

        # Find the layout name that corresponds to the current ID
        for name, layout in self._layouts.items():
            if layout.id == self._current_layout_id:
                return name
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected layout."""
        LOGGER.debug("Selecting layout: %s", option)
        if option not in self._layouts:
            raise HomeAssistantError(f"Layout {option} not found")

        try:
            layout_id = self._layouts[option].id
            await self._client.set_current_layout(layout_id)
            self._current_layout_id = layout_id
            self.async_write_ha_state()

            # Fast refresh strategy
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]

            # Very short delay to allow SignalRGB to process the change
            await asyncio.sleep(0.2)

            # Directly fetch the current layout from the API
            try:
                LOGGER.debug("Directly fetching current layout after selection")
                current_layout = await self._client.get_current_layout()

                # Update our coordinator data directly
                if self.coordinator.data:
                    self.coordinator.data["current_layout"] = current_layout
                    # Force an update to all entities using this coordinator
                    self.coordinator.async_set_updated_data(self.coordinator.data)

                # Also refresh the light coordinator to update any effect changes
                if "coordinator" in entry_data:
                    LOGGER.debug("Refreshing light coordinator after layout change")
                    await entry_data["coordinator"].async_request_refresh()

            except SignalRGBException as refresh_err:
                LOGGER.warning("Error refreshing layout state: %s", refresh_err)
                # Fall back to regular coordinator refresh
                await self.coordinator.async_request_refresh()

        except SignalRGBException as err:
            LOGGER.error("Failed to select layout %s: %s", option, err)
            raise HomeAssistantError(f"Failed to select layout: {err}") from err

    def _update_data(self) -> None:
        """Update entity data from the coordinator."""
        data = self.coordinator.data
        if data and "layouts" in data and "current_layout" in data:
            layouts = data["layouts"]
            current_layout = data["current_layout"]

            # Update layouts dictionary (name -> layout)
            self._layouts = {layout.id: layout for layout in layouts}

            # Update current layout ID
            if current_layout:
                self._current_layout_id = current_layout.id
                LOGGER.debug("Current layout ID: %s", self._current_layout_id)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        LOGGER.debug("Handling coordinator update for %s", self.entity_id)
        self._update_data()
        self.async_write_ha_state()


class SignalRGBPresetSelect(SignalRGBBaseSelect):
    """Representation of a SignalRGB effect preset selector."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: AsyncSignalRGBClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the preset select entity."""
        super().__init__(coordinator, client, config_entry, PRESET_SELECT)
        self._attr_name = "Effect Preset"
        self._attr_icon = "mdi:playlist-star"
        self._presets: list[str] = []
        self._current_effect: Effect | None = None
        self._current_preset: str | None = None
        self._update_data()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Only available if we have an effect and presets
        return (
            self.coordinator.last_update_success
            and self._current_effect is not None
            and bool(self._presets)
        )

    @property
    def options(self) -> list[str]:
        """Return a list of available presets for the current effect."""
        return self._presets

    @property
    def current_option(self) -> str | None:
        """Return the current selected preset."""
        return self._current_preset

    async def async_select_option(self, option: str) -> None:
        """Apply the selected preset."""
        LOGGER.debug("Selecting preset: %s", option)
        if not self._current_effect:
            raise HomeAssistantError("No effect is currently active")
        if option not in self._presets:
            raise HomeAssistantError(f"Preset {option} not found")

        try:
            await self._client.apply_effect_preset(self._current_effect.id, option)
            self._current_preset = option
            self.async_write_ha_state()

            # Fast refresh strategy
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]

            # Very short delay to allow SignalRGB to process the change
            await asyncio.sleep(0.2)

            # Directly fetch the current effect from the API
            try:
                LOGGER.debug("Directly fetching current effect after preset selection")
                current_effect = await self._client.get_current_effect()

                # Update our coordinator data directly
                if self.coordinator.data:
                    self.coordinator.data["current_effect"] = current_effect
                    # Force an update to all entities using this coordinator
                    self.coordinator.async_set_updated_data(self.coordinator.data)

                # Also refresh the light coordinator to update the light entity
                if "coordinator" in entry_data:
                    LOGGER.debug("Refreshing light coordinator after preset change")
                    await entry_data["coordinator"].async_request_refresh()

            except SignalRGBException as refresh_err:
                LOGGER.warning("Error refreshing preset state: %s", refresh_err)
                # Fall back to regular coordinator refresh
                await self.coordinator.async_request_refresh()

        except SignalRGBException as err:
            LOGGER.error("Failed to apply preset %s: %s", option, err)
            raise HomeAssistantError(f"Failed to apply preset: {err}") from err

    def _update_data(self) -> None:
        """Update entity data from the coordinator."""
        data = self.coordinator.data
        if data and "current_effect" in data and "presets" in data:
            # Update current effect - this may have changed
            new_effect = data["current_effect"]
            effect_changed = not self._current_effect or (
                new_effect
                and self._current_effect
                and new_effect.id != self._current_effect.id
            )

            self._current_effect = new_effect
            presets = data["presets"]

            # Update presets list - make sure to get the preset IDs correctly
            self._presets = [preset.id for preset in presets] if presets else []
            LOGGER.debug(
                "Updated presets for effect %s: %s",
                new_effect.attributes.name if new_effect else "None",
                self._presets,
            )

            # Reset current preset when effect changes or if it's not set
            if effect_changed or self._current_preset is None:
                LOGGER.debug(
                    "Effect changed or preset not set, setting to first preset"
                )
                if self._presets:
                    self._current_preset = self._presets[0]
                else:
                    self._current_preset = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        LOGGER.debug("Handling coordinator update for %s", self.entity_id)
        self._update_data()
        self.async_write_ha_state()
