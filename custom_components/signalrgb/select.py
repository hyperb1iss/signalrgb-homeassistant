"""Support for SignalRGB layout and preset selection."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SignalRGBConfigEntry
from .entity import SignalRGBEntity


async def async_setup_entry(
    _hass: HomeAssistant, entry: SignalRGBConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add selectors using the shared state."""
    async_add_entities([SignalRGBLayoutSelect(entry), SignalRGBPresetSelect(entry)])


class SignalRGBLayoutSelect(SignalRGBEntity, SelectEntity):
    """Select the active SignalRGB layout."""

    _attr_name = "Layout"
    _attr_icon = "mdi:view-grid-outline"

    def __init__(self, entry: SignalRGBConfigEntry) -> None:
        """Initialize the layout selector."""
        super().__init__(entry, "layout")
        self._update_attributes()

    @property
    def available(self) -> bool:
        """Return whether layout selection is supported and reachable."""
        return super().available and bool(self.coordinator.data.layouts)

    @callback
    def _update_attributes(self) -> None:
        """Preserve layout IDs as option values for existing automations."""
        self._attr_options = sorted({layout.id for layout in self.coordinator.data.layouts or []})
        layout = self.coordinator.data.current_layout
        self._attr_current_option = (
            layout.id if layout and layout.id in self._attr_options else None
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Publish the server's current layout."""
        self._update_attributes()
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        """Select a layout and read the resulting server state."""
        if option not in self.options:
            raise ServiceValidationError(f"Unknown layout: {option}")
        await self._async_command(lambda: self.coordinator.client.set_current_layout(option))


class SignalRGBPresetSelect(SignalRGBEntity, SelectEntity):
    """Select presets for the currently playing effect."""

    _attr_name = "Effect Preset"
    _attr_icon = "mdi:playlist-star"

    def __init__(self, entry: SignalRGBConfigEntry) -> None:
        """Initialize an unknown selection until a preset is applied locally."""
        super().__init__(entry, "preset")
        self._selected: tuple[str, str] | None = None
        self._update_attributes()

    @property
    def available(self) -> bool:
        """Return whether the current effect exposes presets."""
        return super().available and bool(self.coordinator.data.presets)

    @callback
    def _update_attributes(self) -> None:
        """Track the last local selection without inventing a default preset."""
        self._attr_options = sorted({preset.id for preset in self.coordinator.data.presets or []})
        if self._selected and (
            self._selected[0] != self.coordinator.data.state.effect_id
            or self._selected[1] not in self._attr_options
        ):
            self._selected = None
        self._attr_current_option = self._selected[1] if self._selected else None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Forget local selection when the effect or preset list changes."""
        self._update_attributes()
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        """Apply a preset to the current effect."""
        if option not in self.options:
            raise ServiceValidationError(f"Unknown preset: {option}")
        effect_id = self.coordinator.data.state.effect_id
        await self._async_command(
            lambda: self.coordinator.client.apply_effect_preset(effect_id, option)
        )
        self._selected = (effect_id, option)
        self._update_attributes()
        self.async_write_ha_state()
