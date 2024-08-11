"""Support for SignalRGB lights."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from signalrgb.client import SignalRGBClient, SignalRGBException
from signalrgb.model import Effect

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DEFAULT_EFFECT,
    DOMAIN,
    LOGGER,
    MANUFACTURER,
    MODEL,
    UPDATE_INTERVAL,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SignalRGB light based on a config entry."""
    client: SignalRGBClient = hass.data[DOMAIN][entry.entry_id]

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            current_effect = await hass.async_add_executor_job(
                client.get_current_effect
            )
            is_on = await hass.async_add_executor_job(lambda: client.enabled)
            brightness = await hass.async_add_executor_job(lambda: client.brightness)
            return {
                "current_effect": current_effect,
                "is_on": is_on,
                "brightness": brightness,
            }
        except SignalRGBException as err:
            raise HomeAssistantError(f"Error communicating with API: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name="signalrgb_light",
        update_method=async_update_data,
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    light = SignalRGBLight(coordinator, client, entry)
    async_add_entities([light], update_before_add=True)


class SignalRGBLight(CoordinatorEntity, LightEntity):
    """Representation of a SignalRGB light."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: SignalRGBClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._client = client
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_light"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"{MODEL} {config_entry.data['host']}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
        self._effect_list: list[str] = []
        self.entity_id = f"light.signalrgb_{config_entry.entry_id}"
        self._current_effect: Effect | None = None
        self._is_on: bool = False
        self._brightness: int = 0  # This is now 0-100

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        await self.async_update_effect_list()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return round(self._brightness * 255 / 100)  # Convert 0-100 to 0-255

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        return self._current_effect.attributes.name if self._current_effect else None

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        if not self.is_on or not self._current_effect:
            return {}

        effect = self._current_effect
        return {
            "effect_name": effect.attributes.name,
            "effect_description": effect.attributes.description,
            "effect_developer": effect.attributes.developer_effect,
            "effect_publisher": effect.attributes.publisher,
            "effect_uses_audio": effect.attributes.uses_audio,
            "effect_uses_input": effect.attributes.uses_input,
            "effect_uses_meters": effect.attributes.uses_meters,
            "effect_uses_video": effect.attributes.uses_video,
            "effect_parameters": effect.attributes.parameters,
            "effect_image": effect.attributes.image,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        if not self.is_on:
            await self.hass.async_add_executor_job(
                setattr, self._client, "enabled", True
            )
            self._is_on = True
            self.async_write_ha_state()

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            brightness_percent = round(brightness * 100 / 255)  # Convert 0-255 to 0-100
            await self.hass.async_add_executor_job(
                setattr, self._client, "brightness", brightness_percent
            )
            self._brightness = brightness_percent
            self.async_write_ha_state()

        if ATTR_EFFECT in kwargs:
            await self._apply_effect(kwargs[ATTR_EFFECT])
        elif not self._current_effect:
            await self._apply_effect(DEFAULT_EFFECT)

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        await self.hass.async_add_executor_job(setattr, self._client, "enabled", False)
        self._is_on = False
        self.async_write_ha_state()
        await asyncio.sleep(0.5)  # Small delay to ensure the client has time to update
        await self.coordinator.async_request_refresh()

    async def _apply_effect(self, effect: str) -> None:
        """Apply the specified effect."""
        LOGGER.debug("Applying effect: %s", effect)
        try:
            effect_obj: Effect = await self.hass.async_add_executor_job(
                self._client.get_effect_by_name, effect
            )
            await self.hass.async_add_executor_job(
                self._client.apply_effect, effect_obj.id
            )

            self._current_effect = effect_obj
            self.async_write_ha_state()

        except SignalRGBException as err:
            LOGGER.error("Failed to apply effect %s: %s", effect, err)
            raise HomeAssistantError(f"Failed to apply effect: {err}") from err

    async def async_update_effect_list(self) -> None:
        """Update the list of available effects."""
        try:
            effects = await self.hass.async_add_executor_job(self._client.get_effects)
            self._effect_list = [effect.attributes.name for effect in effects]
        except SignalRGBException as err:
            LOGGER.error("Failed to fetch effect list: %s", err)
            self._effect_list = []

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if data:
            self._current_effect = data.get("current_effect")
            self._is_on = data.get("is_on", False)
            self._brightness = data.get("brightness", 0)  # This is now 0-100
        self.async_write_ha_state()
