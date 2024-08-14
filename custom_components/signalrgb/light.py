"""Support for SignalRGB lights."""

# pylint: disable=too-many-instance-attributes, abstract-method

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

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
from signalrgb.client import SignalRGBClient, SignalRGBException
from signalrgb.model import Effect

from .const import (
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
    LOGGER.debug("Setting up SignalRGB light for entry: %s", entry.entry_id)
    client: SignalRGBClient = hass.data[DOMAIN][entry.entry_id]

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            LOGGER.debug("Fetching current state from SignalRGB API")
            current_effect = await hass.async_add_executor_job(
                client.get_current_effect
            )
            is_on = await hass.async_add_executor_job(lambda: client.enabled)
            brightness = await hass.async_add_executor_job(lambda: client.brightness)
            LOGGER.debug(
                "API Response - Effect: %s, Is On: %s, Brightness: %s",
                current_effect.attributes.name if current_effect else "None",
                is_on,
                brightness,
            )
            return {
                "current_effect": current_effect,
                "is_on": is_on,
                "brightness": brightness,
            }
        except SignalRGBException as err:
            LOGGER.error("Error communicating with SignalRGB API: %s", err)
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
    LOGGER.info("Adding SignalRGB light entity: %s", light.entity_id)
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
        LOGGER.debug("SignalRGBLight initialized: %s", self.entity_id)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        LOGGER.debug("SignalRGBLight being added to hass: %s", self.entity_id)
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        await self.async_update_effect_list()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        LOGGER.debug("Getting is_on state for %s: %s", self.entity_id, self._is_on)
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        brightness = round(self._brightness * 255 / 100)  # Convert 0-100 to 0-255
        LOGGER.debug("Getting brightness for %s: %s", self.entity_id, brightness)
        return brightness

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        effect = self._current_effect.attributes.name if self._current_effect else None
        LOGGER.debug("Getting current effect for %s: %s", self.entity_id, effect)
        return effect

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        LOGGER.debug(
            "Getting effect list for %s: %s", self.entity_id, self._effect_list
        )
        return self._effect_list

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        LOGGER.debug("Getting extra state attributes for %s", self.entity_id)
        if not self.is_on or not self._current_effect:
            LOGGER.debug(
                "Light is off or no current effect, returning empty attributes"
            )
            return {}

        effect = self._current_effect
        attributes = {
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
        LOGGER.debug("Extra state attributes: %s", attributes)
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the light to turn on."""
        LOGGER.debug("Turning on %s with kwargs: %s", self.entity_id, kwargs)
        if not self.is_on:
            LOGGER.debug("Light was off, turning on")
            await self.hass.async_add_executor_job(
                setattr, self._client, "enabled", True
            )
            self._is_on = True
            self.async_write_ha_state()
            LOGGER.debug("Light turned on, new state: %s", self._is_on)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            brightness_percent = round(brightness * 100 / 255)  # Convert 0-255 to 0-100
            LOGGER.debug("Setting brightness to %s%%", brightness_percent)
            await self.hass.async_add_executor_job(
                setattr, self._client, "brightness", brightness_percent
            )
            self._brightness = brightness_percent
            self.async_write_ha_state()
            LOGGER.debug("Brightness set, new value: %s", self._brightness)

        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            LOGGER.debug("Applying effect: %s", effect)
            await self._apply_effect(effect)

        LOGGER.debug("Requesting coordinator refresh")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        LOGGER.debug("Turning off %s", self.entity_id)
        await self.hass.async_add_executor_job(setattr, self._client, "enabled", False)
        self._is_on = False
        self.async_write_ha_state()
        LOGGER.debug("Light turned off, new state: %s", self._is_on)
        await asyncio.sleep(0.5)  # Small delay to ensure the client has time to update
        LOGGER.debug("Requesting coordinator refresh after turn off")
        await self.coordinator.async_request_refresh()

    async def _apply_effect(self, effect: str) -> None:
        """Apply the specified effect."""
        LOGGER.debug("Applying effect: %s for %s", effect, self.entity_id)
        try:
            effect_obj: Effect = await self.hass.async_add_executor_job(
                self._client.get_effect_by_name, effect
            )
            LOGGER.debug("Effect object retrieved: %s", effect_obj.id)
            await self.hass.async_add_executor_job(
                self._client.apply_effect, effect_obj.id
            )

            self._current_effect = effect_obj
            self.async_write_ha_state()
            LOGGER.debug("Effect applied successfully")

        except SignalRGBException as err:
            LOGGER.error("Failed to apply effect %s: %s", effect, err)
            raise HomeAssistantError(f"Failed to apply effect: {err}") from err

    async def async_update_effect_list(self) -> None:
        """Update the list of available effects."""
        LOGGER.debug("Updating effect list for %s", self.entity_id)
        try:
            effects = await self.hass.async_add_executor_job(self._client.get_effects)
            self._effect_list = [effect.attributes.name for effect in effects]
            LOGGER.debug("Effect list updated: %s", self._effect_list)
        except SignalRGBException as err:
            LOGGER.error("Failed to fetch effect list: %s", err)
            self._effect_list = []

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        LOGGER.debug("Handling coordinator update for %s", self.entity_id)
        data = self.coordinator.data
        if data:
            LOGGER.debug("Coordinator data: %s", data)
            self._current_effect = data.get("current_effect")
            self._is_on = data.get("is_on", False)
            self._brightness = data.get("brightness", 0)  # This is now 0-100
            LOGGER.debug(
                "Updated state - Effect: %s, Is On: %s, Brightness: %s",
                self._current_effect.attributes.name
                if self._current_effect
                else "None",
                self._is_on,
                self._brightness,
            )
        else:
            LOGGER.warning("No data received from coordinator for %s", self.entity_id)
        self.async_write_ha_state()
        LOGGER.debug("State updated after coordinator update")
