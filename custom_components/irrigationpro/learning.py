"""Soil moisture feedback learning module for IrrigationPro.

Implements a post-hoc feedback loop that:
1. Records soil moisture before and after each watering cycle
2. Compares measured moisture with vegetation-specific targets
3. Gradually adjusts a per-zone correction factor over multiple cycles
4. Persists learning journal and correction factors in HA storage

Scientific basis:
    Target moisture ranges are derived from FAO-56 Management Allowed Depletion
    (MAD) values for different vegetation types, applied to a reference loamy
    soil profile (FC ≈ 30 % VWC, PWP ≈ 12 % VWC).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    LEARNING_CORRECTION_MAX,
    LEARNING_CORRECTION_MIN,
    LEARNING_FEEDBACK_DELAY_HOURS,
    LEARNING_JOURNAL_MAX_ENTRIES,
    LEARNING_MAX_CORRECTION_STEP,
    LEARNING_MIN_ENTRIES,
    LEARNING_STORAGE_KEY,
    LEARNING_STORAGE_VERSION,
    VEGETATION_TYPES,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class JournalEntry:
    """Single feedback observation for a zone."""

    timestamp: str
    watering_duration_min: float
    moisture_before: float | None
    moisture_after: float | None
    target_min: float
    target_max: float
    eto_total: float
    rain_total: float
    correction_at_time: float
    deviation: float  # positive = too dry, negative = too wet

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JournalEntry:
        return cls(
            timestamp=data.get("timestamp", ""),
            watering_duration_min=data.get("watering_duration_min", 0),
            moisture_before=data.get("moisture_before"),
            moisture_after=data.get("moisture_after"),
            target_min=data.get("target_min", 20),
            target_max=data.get("target_max", 35),
            eto_total=data.get("eto_total", 0),
            rain_total=data.get("rain_total", 0),
            correction_at_time=data.get("correction_at_time", 1.0),
            deviation=data.get("deviation", 0),
        )


@dataclass
class ZoneLearningData:
    """Learning state for a single zone."""

    correction_factor: float = 1.0
    confidence: int = 0  # number of journal entries used
    journal: list[JournalEntry] = field(default_factory=list)
    last_updated: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "correction_factor": round(self.correction_factor, 4),
            "confidence": self.confidence,
            "journal": [e.to_dict() for e in self.journal],
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ZoneLearningData:
        journal = [JournalEntry.from_dict(e) for e in data.get("journal", [])]
        return cls(
            correction_factor=data.get("correction_factor", 1.0),
            confidence=data.get("confidence", 0),
            journal=journal,
            last_updated=data.get("last_updated"),
        )


class FeedbackCollector:
    """Manages soil moisture feedback collection and learning for all zones.

    Lifecycle:
        1. Created by the coordinator at startup
        2. async_load() restores persisted learning data
        3. schedule_feedback(zone_id, ...) is called after each watering
        4. After FEEDBACK_DELAY_HOURS, the sensor is read and a journal entry written
        5. When enough entries exist (MIN_ENTRIES), the correction factor is recalculated
        6. The coordinator reads correction_factor when computing zone duration
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._store = Store(hass, LEARNING_STORAGE_VERSION, LEARNING_STORAGE_KEY)
        self._zones: dict[int, ZoneLearningData] = {}
        self._pending_callbacks: dict[int, Any] = {}  # zone_id -> cancel callable

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def async_load(self) -> None:
        """Load learning data from storage."""
        data = await self._store.async_load()
        if not data or not isinstance(data, dict):
            _LOGGER.debug("No existing learning data found")
            return
        for zone_id_str, zone_data in data.get("zones", {}).items():
            try:
                zone_id = int(zone_id_str)
                self._zones[zone_id] = ZoneLearningData.from_dict(zone_data)
                _LOGGER.debug(
                    "Loaded learning data for zone %d: correction=%.4f, entries=%d",
                    zone_id,
                    self._zones[zone_id].correction_factor,
                    len(self._zones[zone_id].journal),
                )
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Skipping invalid learning data for zone '%s': %s", zone_id_str, err)

    async def async_save(self) -> None:
        """Persist learning data to storage."""
        data = {
            "zones": {
                str(zone_id): zdata.to_dict()
                for zone_id, zdata in self._zones.items()
            }
        }
        await self._store.async_save(data)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_zone_data(self, zone_id: int) -> ZoneLearningData:
        """Return learning data for a zone (creates empty if missing)."""
        if zone_id not in self._zones:
            self._zones[zone_id] = ZoneLearningData()
        return self._zones[zone_id]

    def get_correction_factor(self, zone_id: int) -> float:
        """Return the current correction factor for a zone."""
        return self.get_zone_data(zone_id).correction_factor

    def get_confidence(self, zone_id: int) -> int:
        """Return confidence (number of data points used) for a zone."""
        return self.get_zone_data(zone_id).confidence

    def get_journal(self, zone_id: int) -> list[dict[str, Any]]:
        """Return journal entries as dicts for a zone."""
        return [e.to_dict() for e in self.get_zone_data(zone_id).journal]

    def read_soil_moisture(self, entity_id: str) -> float | None:
        """Read current soil moisture from a HA sensor entity."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", None):
            _LOGGER.debug("Soil moisture entity '%s' not available", entity_id)
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Cannot parse soil moisture from '%s': %s", entity_id, state.state)
            return None

    def schedule_feedback(
        self,
        zone_id: int,
        moisture_entity: str,
        moisture_before: float | None,
        watering_duration: float,
        target_min: float,
        target_max: float,
        eto_total: float,
        rain_total: float,
    ) -> None:
        """Schedule a delayed feedback reading after watering completes."""
        # Cancel any existing pending callback for this zone
        if zone_id in self._pending_callbacks:
            cancel = self._pending_callbacks.pop(zone_id)
            if cancel:
                cancel()

        delay_seconds = LEARNING_FEEDBACK_DELAY_HOURS * 3600

        @callback
        def _feedback_callback(_now) -> None:
            """Read sensor and record feedback (runs on event loop)."""
            self._pending_callbacks.pop(zone_id, None)
            self.hass.async_create_task(
                self._async_collect_feedback(
                    zone_id=zone_id,
                    moisture_entity=moisture_entity,
                    moisture_before=moisture_before,
                    watering_duration=watering_duration,
                    target_min=target_min,
                    target_max=target_max,
                    eto_total=eto_total,
                    rain_total=rain_total,
                )
            )

        cancel_cb = async_call_later(self.hass, delay_seconds, _feedback_callback)
        self._pending_callbacks[zone_id] = cancel_cb

        _LOGGER.info(
            "Feedback reading scheduled for zone %d in %d hours (moisture_before=%.1f%%)",
            zone_id,
            LEARNING_FEEDBACK_DELAY_HOURS,
            moisture_before if moisture_before is not None else -1,
        )

    async def async_reset_zone(self, zone_id: int) -> None:
        """Reset all learning data for a zone."""
        self._zones[zone_id] = ZoneLearningData()
        # Cancel pending feedback
        cancel = self._pending_callbacks.pop(zone_id, None)
        if cancel:
            cancel()
        await self.async_save()
        _LOGGER.info("Learning data reset for zone %d", zone_id)

    async def async_reset_all(self) -> None:
        """Reset learning data for all zones."""
        for zone_id in list(self._pending_callbacks):
            cancel = self._pending_callbacks.pop(zone_id, None)
            if cancel:
                cancel()
        self._zones.clear()
        await self.async_save()
        _LOGGER.info("All learning data reset")

    def cancel_all_pending(self) -> None:
        """Cancel all pending feedback callbacks (for shutdown)."""
        for zone_id, cancel in list(self._pending_callbacks.items()):
            if cancel:
                cancel()
        self._pending_callbacks.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _async_collect_feedback(
        self,
        zone_id: int,
        moisture_entity: str,
        moisture_before: float | None,
        watering_duration: float,
        target_min: float,
        target_max: float,
        eto_total: float,
        rain_total: float,
    ) -> None:
        """Read sensor, create journal entry, recalculate correction."""
        moisture_after = self.read_soil_moisture(moisture_entity)
        if moisture_after is None:
            _LOGGER.warning(
                "Zone %d: Cannot read soil moisture after watering — skipping feedback",
                zone_id,
            )
            return

        target_mid = (target_min + target_max) / 2.0
        deviation = target_mid - moisture_after  # positive = too dry

        zone_data = self.get_zone_data(zone_id)

        entry = JournalEntry(
            timestamp=dt_util.now().isoformat(),
            watering_duration_min=round(watering_duration, 1),
            moisture_before=moisture_before,
            moisture_after=moisture_after,
            target_min=target_min,
            target_max=target_max,
            eto_total=round(eto_total, 2),
            rain_total=round(rain_total, 2),
            correction_at_time=round(zone_data.correction_factor, 4),
            deviation=round(deviation, 2),
        )
        zone_data.journal.append(entry)

        # Trim journal to max entries
        if len(zone_data.journal) > LEARNING_JOURNAL_MAX_ENTRIES:
            zone_data.journal = zone_data.journal[-LEARNING_JOURNAL_MAX_ENTRIES:]

        _LOGGER.info(
            "Zone %d feedback: before=%.1f%%, after=%.1f%%, target=%.0f–%.0f%%, "
            "deviation=%.1f%%, duration=%.1fmin",
            zone_id,
            moisture_before if moisture_before is not None else -1,
            moisture_after,
            target_min,
            target_max,
            deviation,
            watering_duration,
        )

        # Recalculate correction factor
        self._recalculate_correction(zone_id)

        zone_data.last_updated = dt_util.now().isoformat()
        await self.async_save()

    def _recalculate_correction(self, zone_id: int) -> None:
        """Recalculate correction factor from journal entries.

        Algorithm:
            1. Require at least LEARNING_MIN_ENTRIES observations
            2. Use the most recent 10 entries
            3. Calculate weighted average relative deviation
               (more recent entries weighted higher)
            4. Clamp step to ±LEARNING_MAX_CORRECTION_STEP
            5. Apply step to current correction factor
            6. Clamp total correction to [CORRECTION_MIN, CORRECTION_MAX]
        """
        zone_data = self.get_zone_data(zone_id)

        if len(zone_data.journal) < LEARNING_MIN_ENTRIES:
            zone_data.confidence = len(zone_data.journal)
            _LOGGER.debug(
                "Zone %d: Only %d/%d entries — not enough for correction",
                zone_id,
                len(zone_data.journal),
                LEARNING_MIN_ENTRIES,
            )
            return

        # Use last 10 entries with linearly increasing weights
        recent = zone_data.journal[-10:]
        n = len(recent)
        weights = list(range(1, n + 1))  # 1, 2, 3, ..., n
        total_weight = sum(weights)

        weighted_deviation = 0.0
        for i, entry in enumerate(recent):
            target_mid = (entry.target_min + entry.target_max) / 2.0
            if target_mid > 0:
                relative_dev = entry.deviation / target_mid  # normalized
            else:
                relative_dev = 0
            weighted_deviation += relative_dev * weights[i]

        avg_deviation = weighted_deviation / total_weight

        # Positive deviation = too dry → increase correction (more water)
        # Negative deviation = too wet → decrease correction (less water)
        step = max(
            -LEARNING_MAX_CORRECTION_STEP,
            min(LEARNING_MAX_CORRECTION_STEP, avg_deviation),
        )

        old_factor = zone_data.correction_factor
        new_factor = old_factor + step
        new_factor = max(LEARNING_CORRECTION_MIN, min(LEARNING_CORRECTION_MAX, new_factor))

        zone_data.correction_factor = round(new_factor, 4)
        zone_data.confidence = len(zone_data.journal)

        _LOGGER.info(
            "Zone %d learning: avg_deviation=%.3f, step=%.4f, "
            "correction %.4f → %.4f (confidence=%d)",
            zone_id,
            avg_deviation,
            step,
            old_factor,
            new_factor,
            zone_data.confidence,
        )


def get_vegetation_defaults(vegetation_type: str) -> tuple[float, float]:
    """Return (target_min, target_max) for a vegetation type."""
    veg = VEGETATION_TYPES.get(vegetation_type, VEGETATION_TYPES["lawn"])
    return (veg["target_min"], veg["target_max"])
