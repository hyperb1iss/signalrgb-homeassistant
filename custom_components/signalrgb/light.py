"""Support for SignalRGB's global lighting controls."""

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SignalRGBConfigEntry
from .entity import SignalRGBEntity


async def async_setup_entry(
    _hass: HomeAssistant, entry: SignalRGBConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add the global SignalRGB light."""
    async_add_entities([SignalRGBLight(entry)])


class SignalRGBLight(SignalRGBEntity, LightEntity):
    """Represent global brightness, power, and the current effect."""

    _attr_name = None
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, entry: SignalRGBConfigEntry) -> None:
        """Initialize the light from its first snapshot."""
        super().__init__(entry, "light")
        self._update_attributes()

    @callback
    def _update_attributes(self) -> None:
        """Copy the server snapshot into Home Assistant's entity attributes."""
        data = self.coordinator.data
        self._attr_is_on = data.state.enabled
        self._attr_brightness = round(data.state.brightness * 255 / 100)
        self._attr_effect = data.state.effect_name or None
        self._attr_effect_list = sorted({effect.name for effect in data.effects})
        effect = data.current_effect
        self._attr_extra_state_attributes = {}
        if data.state.enabled and effect and effect.id == data.state.effect_id:
            self._attr_extra_state_attributes = {
                "effect_name": effect.name,
                "effect_description": effect.description,
                "effect_developer": effect.developer_effect,
                "effect_publisher": effect.publisher,
                "effect_uses_audio": effect.uses_audio,
                "effect_uses_input": effect.uses_input,
                "effect_uses_meters": effect.uses_meters,
                "effect_uses_video": effect.uses_video,
                "effect_parameters": effect.parameters,
                "effect_image": effect.image,
            }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Publish one coherent state update."""
        self._update_attributes()
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Apply requested changes, then read the resulting server state."""
        effect_id = None
        if ATTR_EFFECT in kwargs:
            matches = [
                effect
                for effect in self.coordinator.data.effects
                if effect.name == kwargs[ATTR_EFFECT]
            ]
            if len(matches) != 1:
                raise ServiceValidationError(f"Unknown or ambiguous effect: {kwargs[ATTR_EFFECT]}")
            effect_id = matches[0].id

        async def command() -> None:
            client = self.coordinator.client
            await client.set_enabled(True)
            if ATTR_BRIGHTNESS in kwargs:
                await client.set_brightness(round(kwargs[ATTR_BRIGHTNESS] * 100 / 255))
            if effect_id is not None:
                await client.apply_effect(effect_id)

        await self._async_command(command)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable global lighting."""
        await self._async_command(lambda: self.coordinator.client.set_enabled(False))
