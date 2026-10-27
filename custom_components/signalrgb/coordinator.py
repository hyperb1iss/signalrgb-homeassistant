"""Fetch one consistent SignalRGB snapshot for every entity."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    AsyncSignalRGBClient,
    CurrentState,
    Effect,
    Layout,
    NotFoundError,
    Preset,
    SignalRGBError,
)
from .const import LOGGER, UPDATE_INTERVAL


@dataclass(frozen=True, slots=True)
class SignalRGBData:
    """The state shared by lights, buttons, and selectors."""

    state: CurrentState
    effects: list[Effect]
    current_effect: Effect | None
    layouts: list[Layout] | None
    current_layout: Layout | None
    presets: list[Preset] | None


type SignalRGBConfigEntry = ConfigEntry[SignalRGBCoordinator]


class SignalRGBCoordinator(DataUpdateCoordinator[SignalRGBData]):
    """Coordinate updates without platform-specific polling or retries."""

    def __init__(
        self, hass: HomeAssistant, entry: SignalRGBConfigEntry, client: AsyncSignalRGBClient
    ) -> None:
        """Initialize the shared coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=f"SignalRGB {entry.title}",
            config_entry=entry,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
            always_update=False,
        )
        self.client = client

    async def _async_layouts(self) -> tuple[list[Layout] | None, Layout | None]:
        """Keep optional layout failures separate from lighting availability."""
        try:
            layouts, current = await asyncio.gather(
                self.client.get_layouts(), self.client.get_current_layout()
            )
        except NotFoundError as err:
            LOGGER.debug("SignalRGB layouts unavailable: %s", err)
            return None, None
        return layouts, current

    async def _async_presets(self, effect_id: str) -> list[Preset] | None:
        """Fetch presets for the effect in this snapshot."""
        if not effect_id:
            return []
        try:
            return await self.client.get_effect_presets(effect_id)
        except NotFoundError as err:
            LOGGER.debug("SignalRGB presets unavailable: %s", err)
            return None

    async def _async_effect(self, effect_id: str) -> Effect | None:
        """Fetch active-effect metadata, allowing an idle canvas."""
        if not effect_id:
            return None
        try:
            return await self.client.get_effect(effect_id)
        except NotFoundError:
            return None

    async def _async_update_data(self) -> SignalRGBData:
        """Read lighting once and resolve its associated resources."""
        try:
            state = await self.client.get_current_state()
            effects, current_effect, layout_data, presets = await asyncio.gather(
                self.client.get_effects(),
                self._async_effect(state.effect_id),
                self._async_layouts(),
                self._async_presets(state.effect_id),
            )
        except SignalRGBError as err:
            raise UpdateFailed(f"Cannot update SignalRGB: {err}") from err
        return SignalRGBData(state, effects, current_effect, *layout_data, presets)
