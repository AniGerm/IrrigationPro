"""Valve platform for IrrigationPro – HomeKit-compatible irrigation valves.

Creates one valve entity per zone with device_class WATER.
HA's HomeKit bridge maps these to HomeKit ValveType=IRRIGATION (1),
which shows proper sprinkler controls in Apple Home.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.valve import (
    ValveDeviceClass,
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SmartIrrigationCoordinator, ZoneData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up IrrigationPro valve entities for HomeKit compatibility."""
    coordinator: SmartIrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [IrrigationZoneValve(coordinator, zone) for zone in coordinator.zones]
    async_add_entities(entities)


class IrrigationZoneValve(CoordinatorEntity, ValveEntity):
    """HomeKit-compatible irrigation valve for a single zone.

    Exposes each irrigation zone as a water valve so that HA's HomeKit
    bridge presents it as a proper Apple Home irrigation accessory with
    sprinkler icon, on/off toggle, and remaining-duration display.
    """

    _attr_device_class = ValveDeviceClass.WATER
    _attr_reports_position = False
    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

    def __init__(
        self, coordinator: SmartIrrigationCoordinator, zone: ZoneData
    ) -> None:
        """Initialize the valve entity."""
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = f"{zone.name} Valve"
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.entry.entry_id}_zone_{zone.zone_id}_valve"
        )

    @property
    def device_info(self):
        """Group all IrrigationPro entities into one device."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry.entry_id)},
            "name": "IrrigationPro",
            "manufacturer": "IrrigationPro",
            "model": "Smart Irrigation Controller",
        }

    @property
    def is_closed(self) -> bool:
        """Return True when the zone is NOT watering."""
        return not self.zone.is_running

    @property
    def available(self) -> bool:
        """Return True when the zone is enabled in config."""
        return self.zone.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose duration and remaining time for HomeKit bridge."""
        duration_sec = int(self.zone.duration * 60)
        attrs: dict[str, Any] = {
            "zone_id": self.zone.zone_id,
            "duration": duration_sec,
        }

        if self.zone.is_running and self.zone.started_at:
            elapsed = (dt_util.now() - self.zone.started_at).total_seconds()
            attrs["remaining_duration"] = max(0, int(duration_sec - elapsed))
        else:
            attrs["remaining_duration"] = 0

        if self.zone.next_run:
            attrs["next_run"] = self.zone.next_run.isoformat()
        if self.zone.last_run:
            attrs["last_run"] = self.zone.last_run.isoformat()

        return attrs

    async def async_open_valve(self, **kwargs: Any) -> None:
        """Open valve = start irrigation on this zone."""
        duration = self.zone.duration if self.zone.duration > 0 else 10
        await self.coordinator.async_start_zone_manual(
            self.zone.zone_id, int(duration)
        )

    async def async_close_valve(self, **kwargs: Any) -> None:
        """Close valve = stop irrigation on this zone."""
        await self.coordinator.async_stop_zone(self.zone.zone_id)

    @property
    def icon(self) -> str:
        """Return an appropriate icon."""
        return "mdi:sprinkler-variant" if not self.is_closed else "mdi:sprinkler"
