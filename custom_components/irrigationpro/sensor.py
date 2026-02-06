"""Sensor platform for IrrigationPro."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
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
    """Set up IrrigationPro sensor entities."""
    coordinator: SmartIrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for zone in coordinator.zones:
        entities.append(ZoneDurationSensor(coordinator, zone))
        entities.append(ZoneEtoSensor(coordinator, zone))
        entities.append(ZoneNextRunSensor(coordinator, zone))

    async_add_entities(entities)


class IrrigationSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for irrigation sensors."""

    def __init__(self, coordinator: SmartIrrigationCoordinator, zone: ZoneData):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.zone = zone

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class ZoneDurationSensor(IrrigationSensorBase):
    """Sensor for zone duration."""

    def __init__(self, coordinator: SmartIrrigationCoordinator, zone: ZoneData):
        """Initialize the sensor."""
        super().__init__(coordinator, zone)
        self._attr_name = f"{zone.name} Duration"
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.entry.entry_id}_zone_{zone.zone_id}_duration"
        )
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return round(self.zone.duration, 1) if self.zone.duration else 0

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:timer-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        cycles = self.coordinator.entry.data.get("cycles", 2)
        return {
            "zone_id": self.zone.zone_id,
            "total_duration": round(self.zone.duration * cycles, 1),
            "cycles": cycles,
        }


class ZoneEtoSensor(IrrigationSensorBase):
    """Sensor for zone ETo."""

    def __init__(self, coordinator: SmartIrrigationCoordinator, zone: ZoneData):
        """Initialize the sensor."""
        super().__init__(coordinator, zone)
        self._attr_name = f"{zone.name} ETo"
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.entry.entry_id}_zone_{zone.zone_id}_eto"
        )
        self._attr_native_unit_of_measurement = "mm"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return round(self.zone.eto_total, 2) if self.zone.eto_total else 0

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:water-percent"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "zone_id": self.zone.zone_id,
            "rain_total": round(self.zone.rain_total, 2),
            "water_needed": round(self.zone.water_needed, 2),
        }


class ZoneNextRunSensor(IrrigationSensorBase):
    """Sensor for zone next run time."""

    def __init__(self, coordinator: SmartIrrigationCoordinator, zone: ZoneData):
        """Initialize the sensor."""
        super().__init__(coordinator, zone)
        self._attr_name = f"{zone.name} Next Run"
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.entry.entry_id}_zone_{zone.zone_id}_next_run"
        )
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        if self.zone.is_running:
            return self.zone.next_run
        return self.coordinator.scheduled_run

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:clock-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {
            "zone_id": self.zone.zone_id,
            "last_run": self.zone.last_run.isoformat() if self.zone.last_run else None,
            "is_running": self.zone.is_running,
        }
