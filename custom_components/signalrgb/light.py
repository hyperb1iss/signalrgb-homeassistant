"""Support for SignalRGB lights."""

from __future__ import annotations

from typing import Any

from signalrgb.client import SignalRGBClient, SignalRGBException
from signalrgb.model import Effect

from homeassistant.components.light import (
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ALL_OFF_EFFECT, DEFAULT_EFFECT, DOMAIN, LOGGER, MANUFACTURER, MODEL


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SignalRGB light based on a config entry."""
    client: SignalRGBClient = hass.data[DOMAIN][entry.entry_id]
    light = SignalRGBLight(client, entry)
    async_add_entities([light], update_before_add=True)


class SignalRGBLight(LightEntity):
    """Representation of a SignalRGB light."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_is_on = False
    _attr_should_poll = False
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(self, client: SignalRGBClient, config_entry: ConfigEntry) -> None:
        """Initialize the light."""
        self._client = client
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"{MODEL} {config_entry.data['host']}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
        self._last_active_effect: str | None = None
        self._current_effect: str | None = None
        self._effect_list: list[str] = []
        self._effect_attributes: dict[str, Any] = {}

    async def async_update(self) -> None:
        """Fetch new state data for this light."""
        LOGGER.debug("async_update")

        try:
            if not self._effect_list:
                effects = await self.hass.async_add_executor_job(
                    self._client.get_effects
                )
                self._effect_list.extend([effect.attributes.name for effect in effects])

            current_effect = await self.hass.async_add_executor_job(
                self._client.get_current_effect
            )

            if current_effect.attributes.name == ALL_OFF_EFFECT:
                self._last_active_effect = None
                self._attr_is_on = False
                self._effect_attributes = {}
            else:
                self._current_effect = current_effect.attributes.name
                self._attr_is_on = True
                await self._update_effect_attributes(current_effect)

        except SignalRGBException as err:
            raise HomeAssistantError(f"Error communicating with API: {err}") from err

        LOGGER.debug(
            "current_effect=%s is_on=%s", self._current_effect, self._attr_is_on
        )

    async def _update_effect_attributes(self, effect: Effect) -> None:
        """Update the effect attributes."""
        self._effect_attributes = {
            "effect_name": effect.attributes.name,
            "effect_image": effect.attributes.image,
            "effect_description": effect.attributes.description,
            "effect_developer": effect.attributes.developer_effect,
            "effect_publisher": effect.attributes.publisher,
            "effect_uses_audio": effect.attributes.uses_audio,
            "effect_uses_input": effect.attributes.uses_input,
            "effect_uses_meters": effect.attributes.uses_meters,
            "effect_uses_video": effect.attributes.uses_video,
            "effect_parameters": effect.attributes.parameters,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return self._effect_attributes

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        return self._current_effect

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        self._attr_is_on = True
        effect = kwargs.get(ATTR_EFFECT, self._last_active_effect)

        LOGGER.debug(
            "turn on light kwargs=%s last_active_effect=%s",
            effect,
            self._last_active_effect,
        )

        if effect is None:
            effect = self._last_active_effect or DEFAULT_EFFECT

        await self._apply_effect(effect)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._attr_is_on = False

        LOGGER.debug(
            "turn off light last_active_effect=%s is_on=%s",
            self._last_active_effect,
            self._attr_is_on,
        )

        await self._apply_effect(ALL_OFF_EFFECT)

    async def _apply_effect(self, effect: str) -> None:
        LOGGER.debug("apply effect %s", effect)

        try:
            effect_obj: Effect = await self.hass.async_add_executor_job(
                self._client.get_effect_by_name, effect
            )
            await self.hass.async_add_executor_job(
                self._client.apply_effect, effect_obj.id
            )
        except SignalRGBException as err:
            LOGGER.error("Failed to apply effect %s: %s", effect, err)
            raise HomeAssistantError(f"Failed to apply effect: {err}") from err

        if effect == ALL_OFF_EFFECT:
            self._last_active_effect = self._current_effect
            self._effect_attributes = {}
        else:
            self._last_active_effect = self._current_effect
            self._current_effect = effect
            await self._update_effect_attributes(effect_obj)

        self.async_write_ha_state()

        LOGGER.debug(
            "effect applied %s is_on=%s last %s",
            self._current_effect,
            self._attr_is_on,
            self._last_active_effect,
        )
