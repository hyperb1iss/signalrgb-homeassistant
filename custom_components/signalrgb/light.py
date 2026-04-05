"""Support for SignalRGB lights."""

# pylint: disable=abstract-method, duplicate-code

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
from signalrgb.model import Effect

from signalrgb import AsyncSignalRGBClient, SignalRGBException

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
    client: AsyncSignalRGBClient = hass.data[DOMAIN][entry.entry_id]["client"]

    async def async_update_data() -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            LOGGER.debug("Fetching current state from SignalRGB API")
            current_effect = await client.get_current_effect()
            is_on = await client.get_enabled()
            brightness = await client.get_brightness()
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
        config_entry=entry,
    )

    # Store coordinator in hass.data so buttons can access it
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    await coordinator.async_refresh()

    light = SignalRGBLight(coordinator, client, entry)
    LOGGER.info("Adding SignalRGB light for entry: %s", entry.entry_id)
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
        client: AsyncSignalRGBClient,
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
        self._current_effect: Effect | None = None
        self._is_on: bool = False
        self._brightness: int = 0  # This is now 0-100
        self._requested_effect: str | None = None
        self._retry_count: int = 0
        self._max_retries: int = 3
        self._refresh_task: asyncio.Task[None] | None = None
        LOGGER.debug("SignalRGBLight initialized for entry: %s", config_entry.entry_id)

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
        return str(effect) if effect else None

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        LOGGER.debug("Getting effect list for %s: %s", self.entity_id, self._effect_list)
        return self._effect_list

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        LOGGER.debug("Getting extra state attributes for %s", self.entity_id)
        if not self.is_on or not self._current_effect:
            LOGGER.debug("Light is off or no current effect, returning empty attributes")
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

        # Cancel any existing refresh task to prevent pile-up
        self._cancel_refresh_task()

        # Track if we need to schedule a refresh
        need_refresh = False

        if not self.is_on:
            LOGGER.debug("Light was off, turning on")
            await self._client.set_enabled(True)
            self._is_on = True
            self.async_write_ha_state()
            LOGGER.debug("Light turned on, new state: %s", self._is_on)
            # Need to verify on state took effect
            need_refresh = True

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            brightness_percent = round(brightness * 100 / 255)  # Convert 0-255 to 0-100
            LOGGER.debug("Setting brightness to %s%%", brightness_percent)
            await self._client.set_brightness(brightness_percent)
            self._brightness = brightness_percent
            self.async_write_ha_state()
            LOGGER.debug("Brightness set, new value: %s", self._brightness)
            # Don't need a refresh for just brightness changes

        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            LOGGER.debug("Requesting effect: %s", effect)
            self._requested_effect = effect
            self._retry_count = 0
            await self._apply_effect(effect)
            # Definitely need to verify effect change
            need_refresh = True

        # Only schedule refresh if needed (turning on or effect change)
        if need_refresh:
            self._schedule_delayed_refresh()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Instruct the light to turn off."""
        LOGGER.debug("Turning off %s", self.entity_id)

        # Cancel any existing refresh task
        self._cancel_refresh_task()

        await self._client.set_enabled(False)
        self._is_on = False
        self.async_write_ha_state()
        LOGGER.debug("Light turned off, new state: %s", self._is_on)
        await self.coordinator.async_request_refresh()

    async def _apply_effect(self, effect: str) -> None:
        """Apply the specified effect and update state immediately."""
        LOGGER.debug("Applying effect: %s for %s", effect, self.entity_id)
        try:
            effect_obj: Effect = await self._client.get_effect_by_name(effect)
            LOGGER.debug("Effect object retrieved: %s", effect_obj.id)

            # Use apply_effect_by_name which is more robust
            await self._client.apply_effect_by_name(effect)

            # Update state immediately
            self._current_effect = effect_obj
            self.async_write_ha_state()
            LOGGER.debug("Effect applied and state updated immediately: %s", effect)

        except SignalRGBException as err:
            LOGGER.error("Failed to apply effect %s: %s", effect, err)
            raise HomeAssistantError(f"Failed to apply effect: {err}") from err

    def _cancel_refresh_task(self) -> None:
        """Cancel any pending refresh task."""
        if self._refresh_task is not None and not self._refresh_task.done():
            LOGGER.debug("Cancelling existing refresh task")
            self._refresh_task.cancel()
        self._refresh_task = None

    def _schedule_delayed_refresh(self) -> None:
        """Schedule a delayed refresh to verify the effect was applied correctly."""
        self._cancel_refresh_task()
        LOGGER.debug("Scheduling new delayed refresh task")
        self._refresh_task = asyncio.create_task(self._delayed_refresh())

    async def _delayed_refresh(self) -> None:
        """Perform a delayed refresh and retry if necessary."""
        # Use a much shorter delay for better responsiveness
        await asyncio.sleep(0.2)  # Wait for 0.2 seconds before refreshing (down from 2 seconds)

        # Check if task has been cancelled while sleeping
        current_task = asyncio.current_task()
        if current_task is not None and current_task.cancelled():
            LOGGER.debug("Delayed refresh task was cancelled during sleep")
            return

        # Directly fetch the current state from the API for immediate feedback
        try:
            LOGGER.debug("Directly fetching current state after effect change")
            current_effect = await self._client.get_current_effect()
            is_on = await self._client.get_enabled()
            brightness = await self._client.get_brightness()

            # Update our coordinator data directly
            if self.coordinator.data:
                self.coordinator.data.update(
                    {
                        "current_effect": current_effect,
                        "is_on": is_on,
                        "brightness": brightness,
                    }
                )
                # Force an update to all entities using this coordinator
                self.coordinator.async_set_updated_data(self.coordinator.data)

            # Also refresh any other coordinators (particularly the effect/preset coordinator)
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
            for key, item in entry_data.items():
                if key not in {"client", "coordinator"} and hasattr(item, "async_request_refresh"):
                    LOGGER.debug("Refreshing additional coordinator: %s", key)
                    await item.async_request_refresh()

            # Check if the requested effect was applied correctly
            if self._requested_effect and self.effect != self._requested_effect:
                LOGGER.warning(
                    "Applied effect doesn't match requested effect. Requested: %s, Applied: %s",
                    self._requested_effect,
                    self.effect,
                )
                if self._retry_count < self._max_retries:
                    self._retry_count += 1
                    LOGGER.debug(
                        "Retrying effect application (Attempt %s of %s)",
                        self._retry_count,
                        self._max_retries,
                    )
                    await self._apply_effect(self._requested_effect)
                    self._schedule_delayed_refresh()
                else:
                    LOGGER.error(
                        "Failed to apply effect %s after %s attempts",
                        self._requested_effect,
                        self._max_retries,
                    )
                    self._requested_effect = None
                    self._retry_count = 0

        except SignalRGBException as refresh_err:
            LOGGER.warning("Error directly refreshing state: %s", refresh_err)
            # Fall back to regular coordinator refresh
            await self.coordinator.async_request_refresh()

            # Also refresh any other coordinators
            entry_data = self.hass.data[DOMAIN][self._config_entry.entry_id]
            for key, item in entry_data.items():
                if key not in {"client", "coordinator"} and hasattr(item, "async_request_refresh"):
                    LOGGER.debug("Refreshing additional coordinator: %s", key)
                    await item.async_request_refresh()

            # Check if we need to retry the effect application
            if self._requested_effect and self.effect != self._requested_effect:
                if self._retry_count < self._max_retries:
                    self._retry_count += 1
                    LOGGER.debug(
                        "Retrying effect application (Attempt %s of %s)",
                        self._retry_count,
                        self._max_retries,
                    )
                    await self._apply_effect(self._requested_effect)
                    self._schedule_delayed_refresh()
                else:
                    LOGGER.error(
                        "Failed to apply effect %s after %s attempts",
                        self._requested_effect,
                        self._max_retries,
                    )
                    self._requested_effect = None
                    self._retry_count = 0

    async def async_update_effect_list(self) -> None:
        """Update the list of available effects."""
        LOGGER.debug("Updating effect list for %s", self.entity_id)
        try:
            # Use the refresh_effects method to ensure we get the latest data
            await self._client.refresh_effects()
            effects = await self._client.get_effects()
            self._effect_list = [effect.attributes.name for effect in effects]
            LOGGER.debug("Effect list updated with %s effects", len(self._effect_list))
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
            new_effect = data.get("current_effect")
            self._is_on = data.get("is_on", False)
            self._brightness = data.get("brightness", 0)  # This is now 0-100

            if new_effect and (
                not self._current_effect or new_effect.id != self._current_effect.id
            ):
                self._current_effect = new_effect
                if self._requested_effect and new_effect.attributes.name != self._requested_effect:
                    LOGGER.warning(
                        "Applied effect doesn't match requested effect. Requested: %s, Applied: %s",
                        self._requested_effect,
                        new_effect.attributes.name,
                    )
                elif (
                    self._requested_effect and new_effect.attributes.name == self._requested_effect
                ):
                    LOGGER.info(
                        "Requested effect %s successfully applied",
                        self._requested_effect,
                    )
                    self._requested_effect = None
                    self._retry_count = 0

            LOGGER.debug(
                "Updated state - Effect: %s, Is On: %s, Brightness: %s",
                self._current_effect.attributes.name if self._current_effect else "None",
                self._is_on,
                self._brightness,
            )
        else:
            LOGGER.warning("No data received from coordinator for %s", self.entity_id)
        self.async_write_ha_state()
        LOGGER.debug("State updated after coordinator update")

    async def async_will_remove_from_hass(self) -> None:
        """Clean up resources when entity is removed."""
        self._cancel_refresh_task()
        await super().async_will_remove_from_hass()
