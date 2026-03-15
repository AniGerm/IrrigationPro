"""API endpoints for IrrigationPro panel."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import CONF_PUSHOVER_ENABLED, CONF_PUSHOVER_USER_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


class IrrigationProApiView(HomeAssistantView):
    """API view for IrrigationPro status data."""

    url = "/api/irrigationpro/status"
    name = "api:irrigationpro:status"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return current status of all zones and weather."""
        hass: HomeAssistant = request.app["hass"]

        coordinators = hass.data.get(DOMAIN, {})
        if not coordinators:
            return self.json({"error": "No IrrigationPro instance configured"})

        result: dict[str, Any] = {"entries": []}

        for entry_id, coordinator in coordinators.items():
            zones_data = []
            for zone in coordinator.zones:
                # Get actual entity state if configured
                entity_state = None
                if zone.switch_entity:
                    state_obj = hass.states.get(zone.switch_entity)
                    entity_state = state_obj.state if state_obj else "unknown"

                zones_data.append(
                    {
                        "zone_id": zone.zone_id,
                        "name": zone.name,
                        "enabled": zone.enabled,
                        "is_running": zone.is_running,
                        "switch_entity": zone.switch_entity,
                        "entity_state": entity_state,
                        "duration": round(zone.duration, 1),
                        "eto_total": round(zone.eto_total, 2),
                        "rain_total": round(zone.rain_total, 2),
                        "water_needed": round(zone.water_needed, 2),
                        "area": zone.area,
                        "flow_rate": zone.flow_rate,
                        "emitter_count": zone.emitter_count,
                        "efficiency": zone.efficiency,
                        "crop_coef": zone.crop_coef,
                        "max_duration": zone.max_duration,
                        "rain_threshold": zone.rain_threshold,
                        "adaptive": zone.adaptive,
                        "skip_reason": getattr(zone, "skip_reason", ""),
                        "run_until": (
                            (getattr(zone, "started_at", None) + timedelta(minutes=zone.duration)).isoformat()
                            if getattr(zone, "started_at", None) and zone.duration > 0
                            else None
                        ),
                        "last_run": (
                            zone.last_run.isoformat() if zone.last_run else None
                        ),
                        "next_run": (
                            zone.next_run.isoformat() if zone.next_run else None
                        ),
                        "weekdays": zone.weekdays,
                    }
                )

            forecast_data = []
            for day in coordinator.forecast:
                forecast_data.append(
                    {
                        "date": day.sunrise.strftime("%Y-%m-%d"),
                        "min_temp": round(day.min_temp, 1),
                        "max_temp": round(day.max_temp, 1),
                        "humidity": round(day.humidity),
                        "wind_speed": round(day.wind_speed, 1),
                        "rain": round(day.rain, 1),
                        "eto": round(day.eto, 2),
                        "condition": day.condition,
                    }
                )

            last_update = (
                getattr(coordinator, "last_refresh_time", None)
                or getattr(coordinator, "last_calculated", None)
                or (
                    coordinator.last_update_success_time
                    if hasattr(coordinator, "last_update_success_time")
                    else None
                )
                or (
                    coordinator.last_updated
                    if hasattr(coordinator, "last_updated")
                    else None
                )
            )
            next_automatic_calculation = (
                last_update + coordinator.update_interval
                if last_update and getattr(coordinator, "update_interval", None)
                else None
            )

            entry_data = {
                "entry_id": entry_id,
                "zones": zones_data,
                "forecast": forecast_data,
                "scheduled_run": (
                    coordinator.scheduled_run.isoformat()
                    if coordinator.scheduled_run
                    else None
                ),
                "schedule_reason": getattr(coordinator, "schedule_reason", ""),
                "recheck_scheduled": (
                    coordinator.recheck_scheduled.isoformat()
                    if getattr(coordinator, "recheck_scheduled", None)
                    else None
                ),
                "last_calculated": (
                    coordinator.last_calculated.isoformat()
                    if getattr(coordinator, "last_calculated", None)
                    else None
                ),
                "last_update": (
                    last_update.isoformat()
                    if last_update
                    else None
                ),
                "next_automatic_calculation": (
                    next_automatic_calculation.isoformat()
                    if next_automatic_calculation
                    else None
                ),
            }
            result["entries"].append(entry_data)

        return self.json(result)


class IrrigationProZoneControlView(HomeAssistantView):
    """API view to control zones."""

    url = "/api/irrigationpro/zone/{action}"
    name = "api:irrigationpro:zone_control"
    requires_auth = True

    async def post(self, request: web.Request, action: str) -> web.Response:
        """Handle zone control actions."""
        hass: HomeAssistant = request.app["hass"]
        data = await request.json()

        zone_id = data.get("zone_id")
        duration = data.get("duration", 10)

        if zone_id is None:
            return self.json({"error": "zone_id required"}, status_code=400)

        coordinators = hass.data.get(DOMAIN, {})

        for coordinator in coordinators.values():
            zone = next(
                (z for z in coordinator.zones if z.zone_id == zone_id), None
            )
            if zone is None:
                continue

            if action == "start":
                await coordinator.async_start_zone_manual(zone_id, duration)
                return self.json({"status": "started", "zone_id": zone_id})
            elif action == "stop":
                await coordinator.async_stop_zone(zone_id)
                return self.json({"status": "stopped", "zone_id": zone_id})
            elif action == "toggle":
                if zone.is_running:
                    await coordinator.async_stop_zone(zone_id)
                    return self.json({"status": "stopped", "zone_id": zone_id})
                else:
                    await coordinator.async_start_zone_manual(zone_id, duration)
                    return self.json({"status": "started", "zone_id": zone_id})
            elif action == "enable":
                await coordinator.async_set_zone_enabled(zone_id, True)
                return self.json({"status": "enabled", "zone_id": zone_id})
            elif action == "disable":
                await coordinator.async_set_zone_enabled(zone_id, False)
                return self.json({"status": "disabled", "zone_id": zone_id})

        return self.json({"error": f"Zone {zone_id} not found"}, status_code=404)


class IrrigationProRecalculateView(HomeAssistantView):
    """API view to trigger recalculation."""

    url = "/api/irrigationpro/recalculate"
    name = "api:irrigationpro:recalculate"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Trigger recalculation for all coordinators."""
        hass: HomeAssistant = request.app["hass"]

        coordinators = hass.data.get(DOMAIN, {})
        for coordinator in coordinators.values():
            await coordinator.async_request_refresh()

        return self.json({"status": "recalculation_triggered"})


class IrrigationProTestView(HomeAssistantView):
    """API view for test mode (relay test + schedule simulation)."""

    url = "/api/irrigationpro/test"
    name = "api:irrigationpro:test"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Run test mode."""
        hass: HomeAssistant = request.app["hass"]
        data = await request.json()
        mode = data.get("mode", "schedule")

        coordinators = hass.data.get(DOMAIN, {})
        if not coordinators:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        coordinator = next(iter(coordinators.values()))

        if mode == "relay":
            # Start each enabled zone for 1 minute (non-blocking)
            zones_started = []
            for zone in coordinator.zones:
                if zone.enabled:
                    await coordinator.async_start_zone_manual(zone.zone_id, 1)
                    zones_started.append({
                        "zone_id": zone.zone_id,
                        "name": zone.name,
                        "switch_entity": zone.switch_entity,
                    })
            return self.json({"status": "relay_test_started", "zones": zones_started})

        elif mode == "schedule":
            result = await coordinator.async_test_schedule()
            return self.json(result)

        return self.json({"error": f"Unknown mode: {mode}"}, status_code=400)


class IrrigationProHistoryView(HomeAssistantView):
    """API view for irrigation history."""

    url = "/api/irrigationpro/history"
    name = "api:irrigationpro:history"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return irrigation history sorted newest-first."""
        hass: HomeAssistant = request.app["hass"]
        coordinators = hass.data.get(DOMAIN, {})
        if not coordinators:
            return self.json({"history": []})
        coordinator = next(iter(coordinators.values()))
        history = getattr(coordinator, "history", [])
        # Sort newest first using ts_start (runs) or ts (skip events)
        sorted_history = sorted(
            history,
            key=lambda x: x.get("ts_start") or x.get("ts") or "",
            reverse=True,
        )
        return self.json({"history": sorted_history})


class IrrigationProTestNotificationView(HomeAssistantView):
    """API view to send a test Pushover notification."""

    url = "/api/irrigationpro/test_notification"
    name = "api:irrigationpro:test_notification"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Send a test notification to verify Pushover token and priority."""
        hass: HomeAssistant = request.app["hass"]
        coordinators = hass.data.get(DOMAIN, {})
        if not coordinators:
            return self.json({"error": "Keine IrrigationPro-Instanz konfiguriert"}, status_code=404)

        coordinator = next(iter(coordinators.values()))

        if not coordinator.entry.data.get(CONF_PUSHOVER_USER_KEY):
            return self.json(
                {"error": "Kein Pushover User Key konfiguriert."},
                status_code=400,
            )

        try:
            data = await request.json()
        except Exception:
            data = {}

        priority = int(data.get("priority", 0))

        try:
            await coordinator._send_pushover_notification(
                "\U0001f514 IrrigationPro Test",
                f"Test-Benachrichtigung erfolgreich! Priorit\u00e4t: {priority}",
                priority=priority,
                force=True,
                test_mode=True,
            )
            return self.json({"status": "sent", "priority": priority})
        except Exception as err:
            _LOGGER.error("test_notification error: %s", err)
            return self.json(
                {"error": str(err), "details": type(err).__name__},
                status_code=500,
            )


def async_register_api(hass: HomeAssistant) -> None:
    """Register API views."""
    hass.http.register_view(IrrigationProApiView)
    hass.http.register_view(IrrigationProZoneControlView)
    hass.http.register_view(IrrigationProRecalculateView)
    hass.http.register_view(IrrigationProTestView)
    hass.http.register_view(IrrigationProTestNotificationView)
    hass.http.register_view(IrrigationProHistoryView)
