"""Binary sensor platform for IrrigationPro."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    """Set up IrrigationPro binary sensor entities."""
    coordinator: SmartIrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for zone in coordinator.zones:
        entities.append(ZoneWillRunTodayBinarySensor(coordinator, zone))

    async_add_entities(entities)


class ZoneWillRunTodayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating if zone will run today."""

    def __init__(self, coordinator: SmartIrrigationCoordinator, zone: ZoneData):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.zone = zone
        self._attr_name = f"{zone.name} Will Run Today"
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.entry.entry_id}_zone_{zone.zone_id}_will_run"
        )

    @property
    def is_on(self) -> bool:
        """Return true if zone will run today."""
        if not self.coordinator.scheduled_run:
            return False

        # Check if scheduled run is today and zone has duration > 0
        today = dt_util.now().date()
        scheduled_date = self.coordinator.scheduled_run.date()

        return scheduled_date == today and self.zone.duration > 0 and self.zone.enabled

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self.is_on:
            return "mdi:calendar-check"
        return "mdi:calendar-remove"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "zone_id": self.zone.zone_id,
            "scheduled_time": (
                self.coordinator.scheduled_run.isoformat()
                if self.coordinator.scheduled_run
                else None
            ),
            "duration": round(self.zone.duration, 1) if self.zone.duration else 0,
        }
