"""Switch platform for IrrigationPro."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartIrrigationCoordinator, ZoneData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IrrigationPro switch entities."""
    coordinator: SmartIrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for zone in coordinator.zones:
        entities.append(IrrigationZoneSwitch(coordinator, zone))

    async_add_entities(entities)


class IrrigationZoneSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an irrigation zone switch."""

    def __init__(self, coordinator: SmartIrrigationCoordinator, zone: ZoneData):
        """Initialize the switch."""
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = f"{zone.name}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry.entry_id}_zone_{zone.zone_id}_switch"

    @property
    def is_on(self) -> bool:
        """Return true if the zone is running."""
        return self.zone.is_running

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.zone.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "zone_id": self.zone.zone_id,
            "duration": self.zone.duration,
            "eto_total": round(self.zone.eto_total, 2),
            "rain_total": round(self.zone.rain_total, 2),
            "water_needed": round(self.zone.water_needed, 2),
            "last_run": self.zone.last_run.isoformat() if self.zone.last_run else None,
            "next_run": self.zone.next_run.isoformat() if self.zone.next_run else None,
            "area": self.zone.area,
            "crop_coefficient": self.zone.crop_coef,
            "efficiency": self.zone.efficiency,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the zone."""
        duration = kwargs.get("duration", self.zone.duration or 10)
        await self.coordinator.async_start_zone_manual(self.zone.zone_id, duration)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the zone."""
        await self.coordinator.async_stop_zone(self.zone.zone_id)

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self.is_on:
            return "mdi:water"
        return "mdi:water-off"
