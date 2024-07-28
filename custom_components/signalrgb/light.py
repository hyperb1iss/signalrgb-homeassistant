"""Support for SignalRGB lights."""

from __future__ import annotations

import asyncio
from datetime import timedelta
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
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ALL_OFF_EFFECT,
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
            return await hass.async_add_executor_job(client.get_current_effect)
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
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_supported_features = LightEntityFeature.EFFECT
    _current_effect_task: asyncio.Task | None = None

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
        self._last_active_effect: str | None = None
        self._effect_list: list[str] = []
        self.entity_id = f"light.signalrgb_{config_entry.entry_id}"
        self._current_effect: Effect | None = None

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        await self.async_update_effect_list()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return (
            self._current_effect is not None
            and self._current_effect.attributes.name != ALL_OFF_EFFECT
        )

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
        effect = kwargs.get(ATTR_EFFECT, self._last_active_effect or DEFAULT_EFFECT)
        await self._apply_effect(effect)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        await self._apply_effect(ALL_OFF_EFFECT)

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

            if effect != ALL_OFF_EFFECT:
                self._last_active_effect = effect

            self._current_effect = effect_obj
            await self.coordinator.async_request_refresh()
            self.async_write_ha_state()

        except SignalRGBException as err:
            LOGGER.error("Failed to apply effect %s: %s", effect, err)
            raise HomeAssistantError(f"Failed to apply effect: {err}") from err

    async def _async_apply_effect(self, effect_obj: Effect) -> None:
        """Asynchronously apply the effect and update coordinator."""
        try:
            await self.hass.async_add_executor_job(
                self._client.apply_effect, effect_obj.id
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:  # noqa: BLE001
            LOGGER.error("Error applying effect: %s", err)
            # You might want to update the state here to reflect the error
            self.async_write_ha_state()

    async def async_update_effect_list(self) -> None:
        """Update the list of available effects."""
        try:
            effects = await self.hass.async_add_executor_job(self._client.get_effects)
            self._effect_list = [
                effect.attributes.name
                for effect in effects
                if effect.attributes.name != ALL_OFF_EFFECT
            ]
        except SignalRGBException as err:
            LOGGER.error("Failed to fetch effect list: %s", err)
            self._effect_list = []

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if isinstance(self.coordinator.data, Effect):
            self._current_effect = self.coordinator.data
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()
