"""API endpoints for IrrigationPro panel."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CYCLES,
    CONF_DAILY_REPORT_ENABLED,
    CONF_DAILY_REPORT_HOUR,
    CONF_HIGH_THRESHOLD,
    CONF_HOMEKIT_ENABLED,
    CONF_HOMEKIT_PIN,
    CONF_HOMEKIT_PORT,
    CONF_LANGUAGE,
    CONF_LOW_THRESHOLD,
    CONF_MASTER_ENABLED,
    CONF_OWM_API_KEY,
    CONF_PUSHOVER_API_TOKEN,
    CONF_PUSHOVER_DEVICE,
    CONF_PUSHOVER_ENABLED,
    CONF_PUSHOVER_PRIORITY,
    CONF_PUSHOVER_USER_KEY,
    CONF_RECHECK_TIME,
    CONF_SOLAR_RADIATION,
    CONF_SUNRISE_OFFSET,
    CONF_USE_OWM,
    CONF_WEATHER_ENTITY,
    CONF_ZONE_ADAPTIVE,
    CONF_ZONE_ADJUSTMENT_PERCENT,
    CONF_ZONE_AREA,
    CONF_ZONE_CROP_COEF,
    CONF_ZONE_EFFICIENCY,
    CONF_ZONE_EMITTER_COUNT,
    CONF_ZONE_ENABLED,
    CONF_ZONE_EXPOSURE_FACTOR,
    CONF_ZONE_FLOW_RATE,
    CONF_ZONE_LEARNING_ENABLED,
    CONF_ZONE_MAX_DURATION,
    CONF_ZONE_MONTHS,
    CONF_ZONE_NAME,
    CONF_ZONE_PLANT_DENSITY,
    CONF_ZONE_RAIN_FACTORING,
    CONF_ZONE_RAIN_THRESHOLD,
    CONF_ZONE_SOIL_MOISTURE_ENTITY,
    CONF_ZONE_SWITCH_ENTITY,
    CONF_ZONE_TARGET_MOISTURE_MAX,
    CONF_ZONE_TARGET_MOISTURE_MIN,
    CONF_ZONE_VEGETATION_TYPE,
    CONF_ZONE_WEEKDAYS,
    CONF_ZONES,
    DEFAULT_CYCLES,
    DEFAULT_DAILY_REPORT_ENABLED,
    DEFAULT_DAILY_REPORT_HOUR,
    DEFAULT_HIGH_THRESHOLD,
    DEFAULT_HOMEKIT_ENABLED,
    DEFAULT_HOMEKIT_PIN,
    DEFAULT_HOMEKIT_PORT,
    DEFAULT_LANGUAGE,
    DEFAULT_LOW_THRESHOLD,
    DEFAULT_MASTER_ENABLED,
    DEFAULT_PUSHOVER_ENABLED,
    DEFAULT_PUSHOVER_PRIORITY,
    DEFAULT_RECHECK_TIME,
    DEFAULT_SOLAR_RADIATION,
    DEFAULT_SUNRISE_OFFSET,
    DEFAULT_ZONE_ADAPTIVE,
    DEFAULT_ZONE_ADJUSTMENT_PERCENT,
    DEFAULT_ZONE_AREA,
    DEFAULT_ZONE_CROP_COEF,
    DEFAULT_ZONE_EFFICIENCY,
    DEFAULT_ZONE_EMITTER_COUNT,
    DEFAULT_ZONE_ENABLED,
    DEFAULT_ZONE_EXPOSURE_FACTOR,
    DEFAULT_ZONE_FLOW_RATE,
    DEFAULT_ZONE_LEARNING_ENABLED,
    DEFAULT_ZONE_MAX_DURATION,
    DEFAULT_ZONE_PLANT_DENSITY,
    DEFAULT_ZONE_RAIN_FACTORING,
    DEFAULT_ZONE_RAIN_THRESHOLD,
    DEFAULT_ZONE_VEGETATION_TYPE,
    DOMAIN,
    VEGETATION_TYPES,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)

BACKUP_FORMAT = "irrigationpro-backup-v1"

_LEGACY_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_LEGACY_WEEKDAY_MAP = {
    "monday": "monday",
    "tuesday": "tuesday",
    "wednesday": "wednesday",
    "thursday": "thursday",
    "friday": "friday",
    "saturday": "saturday",
    "sunday": "sunday",
}


def _resolve_coordinator(hass: HomeAssistant, entry_id: str | None = None):
    """Return coordinator by optional entry_id, otherwise first coordinator."""
    coordinators = hass.data.get(DOMAIN, {})
    if not coordinators:
        return None
    if entry_id and entry_id in coordinators:
        return coordinators[entry_id]
    return next(iter(coordinators.values()))


def _sanitize_entry_data(data: dict[str, Any]) -> dict[str, Any]:
    """Keep only integration config keys needed for backup/restore."""
    allowed = {
        CONF_WEATHER_ENTITY,
        CONF_USE_OWM,
        CONF_OWM_API_KEY,
        CONF_ZONES,
        CONF_SUNRISE_OFFSET,
        CONF_CYCLES,
        CONF_LOW_THRESHOLD,
        CONF_HIGH_THRESHOLD,
        CONF_RECHECK_TIME,
        CONF_LANGUAGE,
        CONF_PUSHOVER_ENABLED,
        CONF_PUSHOVER_API_TOKEN,
        CONF_PUSHOVER_USER_KEY,
        CONF_PUSHOVER_DEVICE,
        CONF_PUSHOVER_PRIORITY,
        CONF_DAILY_REPORT_ENABLED,
        CONF_DAILY_REPORT_HOUR,
        CONF_SOLAR_RADIATION,
    }
    return {k: v for k, v in data.items() if k in allowed}


def _normalize_months(value: Any) -> list[int]:
    """Normalize month values to integer month list [1..12]."""
    months: list[int] = []
    for item in value or []:
        if isinstance(item, int) and 1 <= item <= 12:
            months.append(item)
            continue
        if isinstance(item, str):
            key = item.strip().lower()[:3]
            mapped = _LEGACY_MONTH_MAP.get(key)
            if mapped:
                months.append(mapped)
    return sorted(set(months)) or list(range(1, 13))


def _normalize_weekdays(value: Any) -> list[str]:
    """Normalize weekdays to integration weekday tokens."""
    days: list[str] = []
    for item in value or []:
        if isinstance(item, str):
            day = _LEGACY_WEEKDAY_MAP.get(item.strip().lower())
            if day:
                days.append(day)
    return sorted(set(days), key=WEEKDAYS.index) if days else WEEKDAYS.copy()


def _build_backup_payload(coordinator) -> dict[str, Any]:
    """Build canonical export payload."""
    return {
        "backup_format": BACKUP_FORMAT,
        "created_at": dt_util.now().isoformat(),
        "domain": DOMAIN,
        "data": _sanitize_entry_data(dict(coordinator.entry.data)),
    }


def _convert_legacy_payload(raw: dict[str, Any], existing_data: dict[str, Any]) -> dict[str, Any]:
    """Convert legacy SmartSprinklers-like setup payload into IrrigationPro config data."""
    zones_raw = raw.get("zones") or []
    existing_zones = existing_data.get(CONF_ZONES, [])

    converted_zones: list[dict[str, Any]] = []
    for idx, legacy_zone in enumerate(zones_raw):
        existing_zone = existing_zones[idx] if idx < len(existing_zones) else {}
        drip_nos = int(legacy_zone.get("dripNos", 1) or 1)
        total_lph = float(legacy_zone.get("dripLPH", 0.0) or 0.0)
        flow_per_emitter = total_lph / drip_nos if drip_nos > 0 and total_lph > 0 else float(existing_zone.get(CONF_ZONE_FLOW_RATE, 2.0))

        converted_zones.append(
            {
                CONF_ZONE_NAME: legacy_zone.get("zoneName", existing_zone.get(CONF_ZONE_NAME, f"Zone {idx + 1}")),
                CONF_ZONE_ENABLED: bool(legacy_zone.get("enabled", existing_zone.get(CONF_ZONE_ENABLED, True))),
                CONF_ZONE_ADAPTIVE: bool(legacy_zone.get("adaptive", existing_zone.get(CONF_ZONE_ADAPTIVE, True))),
                CONF_ZONE_RAIN_FACTORING: bool(legacy_zone.get("rainFactoring", existing_zone.get(CONF_ZONE_RAIN_FACTORING, True))),
                CONF_ZONE_ADJUSTMENT_PERCENT: int(existing_zone.get(CONF_ZONE_ADJUSTMENT_PERCENT, DEFAULT_ZONE_ADJUSTMENT_PERCENT)),
                CONF_ZONE_MAX_DURATION: int(legacy_zone.get("maxDuration", existing_zone.get(CONF_ZONE_MAX_DURATION, 60))),
                CONF_ZONE_RAIN_THRESHOLD: float(legacy_zone.get("rainThreshold", existing_zone.get(CONF_ZONE_RAIN_THRESHOLD, 2.5))),
                CONF_ZONE_AREA: float(legacy_zone.get("dripArea", existing_zone.get(CONF_ZONE_AREA, 10.0))),
                CONF_ZONE_FLOW_RATE: float(flow_per_emitter),
                CONF_ZONE_EMITTER_COUNT: int(drip_nos),
                CONF_ZONE_EFFICIENCY: int(legacy_zone.get("efficiency", existing_zone.get(CONF_ZONE_EFFICIENCY, 90))),
                CONF_ZONE_CROP_COEF: float(legacy_zone.get("cropCoef", existing_zone.get(CONF_ZONE_CROP_COEF, 0.6))),
                CONF_ZONE_PLANT_DENSITY: float(legacy_zone.get("plantDensity", existing_zone.get(CONF_ZONE_PLANT_DENSITY, 1.0))),
                CONF_ZONE_EXPOSURE_FACTOR: float(legacy_zone.get("expFactor", existing_zone.get(CONF_ZONE_EXPOSURE_FACTOR, 1.0))),
                CONF_ZONE_WEEKDAYS: _normalize_weekdays(legacy_zone.get("wateringWeekdays")),
                CONF_ZONE_MONTHS: _normalize_months(legacy_zone.get("wateringMonths")),
                CONF_ZONE_SWITCH_ENTITY: legacy_zone.get("switch_entity") or existing_zone.get(CONF_ZONE_SWITCH_ENTITY),
            }
        )

    solar = {
        1: float(raw.get("JanRad", DEFAULT_SOLAR_RADIATION[1])),
        2: float(raw.get("FebRad", DEFAULT_SOLAR_RADIATION[2])),
        3: float(raw.get("MarRad", DEFAULT_SOLAR_RADIATION[3])),
        4: float(raw.get("AprRad", DEFAULT_SOLAR_RADIATION[4])),
        5: float(raw.get("MayRad", DEFAULT_SOLAR_RADIATION[5])),
        6: float(raw.get("JunRad", DEFAULT_SOLAR_RADIATION[6])),
        7: float(raw.get("JulRad", DEFAULT_SOLAR_RADIATION[7])),
        8: float(raw.get("AugRad", DEFAULT_SOLAR_RADIATION[8])),
        9: float(raw.get("SepRad", DEFAULT_SOLAR_RADIATION[9])),
        10: float(raw.get("OctRad", DEFAULT_SOLAR_RADIATION[10])),
        11: float(raw.get("NovRad", DEFAULT_SOLAR_RADIATION[11])),
        12: float(raw.get("DecRad", DEFAULT_SOLAR_RADIATION[12])),
    }

    return {
        CONF_WEATHER_ENTITY: existing_data.get(CONF_WEATHER_ENTITY),
        CONF_USE_OWM: bool(existing_data.get(CONF_USE_OWM, False)),
        CONF_OWM_API_KEY: existing_data.get(CONF_OWM_API_KEY),
        CONF_ZONES: converted_zones,
        CONF_SUNRISE_OFFSET: int(raw.get("sunriseOffset", DEFAULT_SUNRISE_OFFSET)),
        CONF_CYCLES: int(raw.get("cycles", DEFAULT_CYCLES)),
        CONF_LOW_THRESHOLD: int(raw.get("lowThreshold", DEFAULT_LOW_THRESHOLD)),
        CONF_HIGH_THRESHOLD: int(raw.get("highThreshold", DEFAULT_HIGH_THRESHOLD)),
        CONF_RECHECK_TIME: int(raw.get("recheckTime", DEFAULT_RECHECK_TIME)),
        CONF_LANGUAGE: existing_data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
        CONF_PUSHOVER_ENABLED: bool(raw.get("pushEnable", DEFAULT_PUSHOVER_ENABLED)),
        CONF_PUSHOVER_API_TOKEN: raw.get("tokenPO", ""),
        CONF_PUSHOVER_USER_KEY: raw.get("userPO", ""),
        CONF_PUSHOVER_DEVICE: existing_data.get(CONF_PUSHOVER_DEVICE, ""),
        CONF_PUSHOVER_PRIORITY: int(raw.get("priorityPO", DEFAULT_PUSHOVER_PRIORITY)),
        CONF_DAILY_REPORT_ENABLED: bool(existing_data.get(CONF_DAILY_REPORT_ENABLED, DEFAULT_DAILY_REPORT_ENABLED)),
        CONF_DAILY_REPORT_HOUR: int(existing_data.get(CONF_DAILY_REPORT_HOUR, DEFAULT_DAILY_REPORT_HOUR)),
        CONF_SOLAR_RADIATION: solar,
    }


def _normalize_restore_payload(payload: dict[str, Any], existing_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize accepted restore payload formats to entry.data-like dict."""
    if payload.get("backup_format") == BACKUP_FORMAT and isinstance(payload.get("data"), dict):
        return payload["data"]

    if isinstance(payload.get("backup"), dict):
        nested = payload["backup"]
        if nested.get("backup_format") == BACKUP_FORMAT and isinstance(nested.get("data"), dict):
            return nested["data"]

    if isinstance(payload.get("zones"), list) and payload.get("accessory"):
        return _convert_legacy_payload(payload, existing_data)

    raise ValueError("Unsupported backup payload")


def _to_bool(value: Any, default: bool = False) -> bool:
    """Coerce arbitrary value to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "y"}
    return bool(value) if value is not None else default


def _to_int(value: Any, default: int) -> int:
    """Coerce arbitrary value to int with fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    """Coerce arbitrary value to float with fallback."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_solar_radiation(value: Any) -> dict[int, float]:
    """Normalize solar radiation config to month->float map with int keys."""
    raw = value if isinstance(value, dict) else {}
    normalized: dict[int, float] = {}
    for month in range(1, 13):
        month_val = raw.get(month)
        if month_val is None:
            month_val = raw.get(str(month))
        normalized[month] = _to_float(month_val, float(DEFAULT_SOLAR_RADIATION[month]))
    return normalized


def _normalize_zone(zone: dict[str, Any], index: int, existing_zone: dict[str, Any]) -> dict[str, Any]:
    """Normalize a zone payload into canonical zone config values."""
    defaults = {
        CONF_ZONE_NAME: f"Zone {index}",
        CONF_ZONE_ENABLED: DEFAULT_ZONE_ENABLED,
        CONF_ZONE_ADAPTIVE: DEFAULT_ZONE_ADAPTIVE,
        CONF_ZONE_RAIN_FACTORING: DEFAULT_ZONE_RAIN_FACTORING,
        CONF_ZONE_MAX_DURATION: DEFAULT_ZONE_MAX_DURATION,
        CONF_ZONE_RAIN_THRESHOLD: DEFAULT_ZONE_RAIN_THRESHOLD,
        CONF_ZONE_AREA: DEFAULT_ZONE_AREA,
        CONF_ZONE_FLOW_RATE: DEFAULT_ZONE_FLOW_RATE,
        CONF_ZONE_EMITTER_COUNT: DEFAULT_ZONE_EMITTER_COUNT,
        CONF_ZONE_EFFICIENCY: DEFAULT_ZONE_EFFICIENCY,
        CONF_ZONE_CROP_COEF: DEFAULT_ZONE_CROP_COEF,
        CONF_ZONE_PLANT_DENSITY: DEFAULT_ZONE_PLANT_DENSITY,
        CONF_ZONE_EXPOSURE_FACTOR: DEFAULT_ZONE_EXPOSURE_FACTOR,
        CONF_ZONE_ADJUSTMENT_PERCENT: DEFAULT_ZONE_ADJUSTMENT_PERCENT,
        CONF_ZONE_WEEKDAYS: WEEKDAYS,
        CONF_ZONE_MONTHS: list(range(1, 13)),
        CONF_ZONE_SWITCH_ENTITY: "",
        CONF_ZONE_VEGETATION_TYPE: DEFAULT_ZONE_VEGETATION_TYPE,
        CONF_ZONE_SOIL_MOISTURE_ENTITY: None,
        CONF_ZONE_TARGET_MOISTURE_MIN: None,
        CONF_ZONE_TARGET_MOISTURE_MAX: None,
        CONF_ZONE_LEARNING_ENABLED: DEFAULT_ZONE_LEARNING_ENABLED,
    }
    src = {**defaults, **existing_zone, **(zone or {})}

    # Resolve vegetation-based moisture defaults
    veg_type = str(src.get(CONF_ZONE_VEGETATION_TYPE, DEFAULT_ZONE_VEGETATION_TYPE) or DEFAULT_ZONE_VEGETATION_TYPE)
    veg_info = VEGETATION_TYPES.get(veg_type, VEGETATION_TYPES["lawn"])

    return {
        CONF_ZONE_NAME: str(src.get(CONF_ZONE_NAME, defaults[CONF_ZONE_NAME])).strip() or defaults[CONF_ZONE_NAME],
        CONF_ZONE_ENABLED: _to_bool(src.get(CONF_ZONE_ENABLED), DEFAULT_ZONE_ENABLED),
        CONF_ZONE_ADAPTIVE: _to_bool(src.get(CONF_ZONE_ADAPTIVE), DEFAULT_ZONE_ADAPTIVE),
        CONF_ZONE_RAIN_FACTORING: _to_bool(src.get(CONF_ZONE_RAIN_FACTORING), DEFAULT_ZONE_RAIN_FACTORING),
        CONF_ZONE_MAX_DURATION: _to_int(src.get(CONF_ZONE_MAX_DURATION), DEFAULT_ZONE_MAX_DURATION),
        CONF_ZONE_RAIN_THRESHOLD: _to_float(src.get(CONF_ZONE_RAIN_THRESHOLD), DEFAULT_ZONE_RAIN_THRESHOLD),
        CONF_ZONE_AREA: _to_float(src.get(CONF_ZONE_AREA), DEFAULT_ZONE_AREA),
        CONF_ZONE_FLOW_RATE: _to_float(src.get(CONF_ZONE_FLOW_RATE), DEFAULT_ZONE_FLOW_RATE),
        CONF_ZONE_EMITTER_COUNT: max(1, _to_int(src.get(CONF_ZONE_EMITTER_COUNT), DEFAULT_ZONE_EMITTER_COUNT)),
        CONF_ZONE_EFFICIENCY: _to_int(src.get(CONF_ZONE_EFFICIENCY), DEFAULT_ZONE_EFFICIENCY),
        CONF_ZONE_CROP_COEF: _to_float(src.get(CONF_ZONE_CROP_COEF), DEFAULT_ZONE_CROP_COEF),
        CONF_ZONE_PLANT_DENSITY: _to_float(src.get(CONF_ZONE_PLANT_DENSITY), DEFAULT_ZONE_PLANT_DENSITY),
        CONF_ZONE_EXPOSURE_FACTOR: _to_float(src.get(CONF_ZONE_EXPOSURE_FACTOR), DEFAULT_ZONE_EXPOSURE_FACTOR),
        CONF_ZONE_ADJUSTMENT_PERCENT: max(10, min(250, _to_int(src.get(CONF_ZONE_ADJUSTMENT_PERCENT), DEFAULT_ZONE_ADJUSTMENT_PERCENT))),
        CONF_ZONE_WEEKDAYS: _normalize_weekdays(src.get(CONF_ZONE_WEEKDAYS)),
        CONF_ZONE_MONTHS: _normalize_months(src.get(CONF_ZONE_MONTHS)),
        CONF_ZONE_SWITCH_ENTITY: str(src.get(CONF_ZONE_SWITCH_ENTITY) or "").strip() or None,
        CONF_ZONE_VEGETATION_TYPE: veg_type if veg_type in VEGETATION_TYPES else DEFAULT_ZONE_VEGETATION_TYPE,
        CONF_ZONE_SOIL_MOISTURE_ENTITY: str(src.get(CONF_ZONE_SOIL_MOISTURE_ENTITY) or "").strip() or None,
        CONF_ZONE_TARGET_MOISTURE_MIN: _to_float(src.get(CONF_ZONE_TARGET_MOISTURE_MIN), veg_info["target_min"]) if src.get(CONF_ZONE_TARGET_MOISTURE_MIN) else None,
        CONF_ZONE_TARGET_MOISTURE_MAX: _to_float(src.get(CONF_ZONE_TARGET_MOISTURE_MAX), veg_info["target_max"]) if src.get(CONF_ZONE_TARGET_MOISTURE_MAX) else None,
        CONF_ZONE_LEARNING_ENABLED: _to_bool(src.get(CONF_ZONE_LEARNING_ENABLED), DEFAULT_ZONE_LEARNING_ENABLED),
    }


def _normalize_config_data(data: dict[str, Any], existing_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a full integration config data payload."""
    zones_raw = data.get(CONF_ZONES)
    if not isinstance(zones_raw, list):
        zones_raw = existing_data.get(CONF_ZONES, [])

    existing_zones = existing_data.get(CONF_ZONES, [])
    zones = []
    for idx, zone_raw in enumerate(zones_raw, start=1):
        existing_zone = existing_zones[idx - 1] if idx - 1 < len(existing_zones) else {}
        zones.append(_normalize_zone(zone_raw if isinstance(zone_raw, dict) else {}, idx, existing_zone))

    out = {
        CONF_WEATHER_ENTITY: str(data.get(CONF_WEATHER_ENTITY, existing_data.get(CONF_WEATHER_ENTITY, ""))).strip(),
        CONF_USE_OWM: _to_bool(data.get(CONF_USE_OWM, existing_data.get(CONF_USE_OWM, False)), False),
        CONF_OWM_API_KEY: str(data.get(CONF_OWM_API_KEY, existing_data.get(CONF_OWM_API_KEY, "")) or "").strip(),
        CONF_ZONES: zones,
        CONF_SUNRISE_OFFSET: _to_int(data.get(CONF_SUNRISE_OFFSET, existing_data.get(CONF_SUNRISE_OFFSET, DEFAULT_SUNRISE_OFFSET)), DEFAULT_SUNRISE_OFFSET),
        CONF_CYCLES: _to_int(data.get(CONF_CYCLES, existing_data.get(CONF_CYCLES, DEFAULT_CYCLES)), DEFAULT_CYCLES),
        CONF_LOW_THRESHOLD: _to_int(data.get(CONF_LOW_THRESHOLD, existing_data.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD)), DEFAULT_LOW_THRESHOLD),
        CONF_HIGH_THRESHOLD: _to_int(data.get(CONF_HIGH_THRESHOLD, existing_data.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD)), DEFAULT_HIGH_THRESHOLD),
        CONF_RECHECK_TIME: _to_int(data.get(CONF_RECHECK_TIME, existing_data.get(CONF_RECHECK_TIME, DEFAULT_RECHECK_TIME)), DEFAULT_RECHECK_TIME),
        CONF_LANGUAGE: str(data.get(CONF_LANGUAGE, existing_data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)) or DEFAULT_LANGUAGE),
        CONF_PUSHOVER_ENABLED: _to_bool(data.get(CONF_PUSHOVER_ENABLED, existing_data.get(CONF_PUSHOVER_ENABLED, DEFAULT_PUSHOVER_ENABLED)), DEFAULT_PUSHOVER_ENABLED),
        CONF_PUSHOVER_API_TOKEN: str(data.get(CONF_PUSHOVER_API_TOKEN, existing_data.get(CONF_PUSHOVER_API_TOKEN, "")) or "").strip(),
        CONF_PUSHOVER_USER_KEY: str(data.get(CONF_PUSHOVER_USER_KEY, existing_data.get(CONF_PUSHOVER_USER_KEY, "")) or "").strip(),
        CONF_PUSHOVER_DEVICE: str(data.get(CONF_PUSHOVER_DEVICE, existing_data.get(CONF_PUSHOVER_DEVICE, "")) or "").strip(),
        CONF_PUSHOVER_PRIORITY: _to_int(data.get(CONF_PUSHOVER_PRIORITY, existing_data.get(CONF_PUSHOVER_PRIORITY, DEFAULT_PUSHOVER_PRIORITY)), DEFAULT_PUSHOVER_PRIORITY),
        CONF_DAILY_REPORT_ENABLED: _to_bool(data.get(CONF_DAILY_REPORT_ENABLED, existing_data.get(CONF_DAILY_REPORT_ENABLED, DEFAULT_DAILY_REPORT_ENABLED)), DEFAULT_DAILY_REPORT_ENABLED),
        CONF_DAILY_REPORT_HOUR: _to_int(data.get(CONF_DAILY_REPORT_HOUR, existing_data.get(CONF_DAILY_REPORT_HOUR, DEFAULT_DAILY_REPORT_HOUR)), DEFAULT_DAILY_REPORT_HOUR),
        CONF_SOLAR_RADIATION: _normalize_solar_radiation(data.get(CONF_SOLAR_RADIATION, existing_data.get(CONF_SOLAR_RADIATION, DEFAULT_SOLAR_RADIATION))),
    }
    if out[CONF_LANGUAGE] not in ("de", "en"):
        out[CONF_LANGUAGE] = DEFAULT_LANGUAGE
    return out


def _validate_candidate(hass: HomeAssistant, candidate: dict[str, Any]) -> dict[str, list[str]]:
    """Validate candidate config and return errors/warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    weather_entity = candidate.get(CONF_WEATHER_ENTITY)
    if not weather_entity:
        errors.append("weather_entity is required")
    elif hass.states.get(weather_entity) is None:
        warnings.append(f"weather_entity not found: {weather_entity}")

    zones = candidate.get(CONF_ZONES, [])
    if not isinstance(zones, list) or not zones:
        errors.append("zones missing or empty")
    else:
        for idx, zone in enumerate(zones, start=1):
            if not zone.get(CONF_ZONE_NAME):
                errors.append(f"zone {idx}: zone_name is required")
            if not zone.get(CONF_ZONE_WEEKDAYS):
                errors.append(f"zone {idx}: zone_weekdays must not be empty")
            if not zone.get(CONF_ZONE_MONTHS):
                errors.append(f"zone {idx}: zone_months must not be empty")
            switch_entity = zone.get(CONF_ZONE_SWITCH_ENTITY)
            if not switch_entity:
                warnings.append(f"zone {idx}: switch_entity is empty")
            elif hass.states.get(switch_entity) is None:
                warnings.append(f"zone {idx}: switch_entity not found: {switch_entity}")

    return {"errors": errors, "warnings": warnings}


def _available_entities(hass: HomeAssistant) -> dict[str, list[str]]:
    """Return weather and switch-like entities for backup editor suggestions."""
    weather_entities = sorted(list(hass.states.async_entity_ids("weather")))
    switch_like = set(hass.states.async_entity_ids("switch"))
    switch_like.update(hass.states.async_entity_ids("light"))
    switch_like.update(hass.states.async_entity_ids("valve"))
    return {
        "weather_entities": weather_entities,
        "switch_entities": sorted(list(switch_like)),
    }


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
                        "duration_uncapped": round(zone.duration_uncapped, 1),
                        "days_until_next": getattr(zone, "days_until_next", 1),
                        "rain_total": round(zone.rain_total, 2),
                        "water_needed": round(zone.water_needed, 2),
                        "area": zone.area,
                        "flow_rate": zone.flow_rate,
                        "emitter_count": zone.emitter_count,
                        "efficiency": zone.efficiency,
                        "crop_coef": zone.crop_coef,
                        "plant_density": zone.plant_density,
                        "exposure_factor": zone.exposure_factor,
                        "rain_factoring": zone.rain_factoring,
                        "adjustment_percent": zone.adjustment_percent,
                        "max_duration": zone.max_duration,
                        "rain_threshold": zone.rain_threshold,
                        "adaptive": zone.adaptive,
                        "skip_reason": getattr(zone, "skip_reason", ""),
                        "run_until": (
                            (zone.started_at + timedelta(minutes=zone.duration)).isoformat()
                            if zone.started_at and zone.duration > 0
                            else None
                        ),
                        "last_run": (
                            zone.last_run.isoformat() if zone.last_run else None
                        ),
                        "next_run": (
                            zone.next_run.isoformat() if zone.next_run else None
                        ),
                        "weekdays": zone.weekdays,
                        "months": zone.months,
                        # Soil moisture learning
                        "vegetation_type": zone.vegetation_type,
                        "soil_moisture_entity": zone.soil_moisture_entity,
                        "target_moisture_min": zone.target_moisture_min,
                        "target_moisture_max": zone.target_moisture_max,
                        "learning_enabled": zone.learning_enabled,
                        "learning_correction": round(zone.learning_correction, 4),
                        "learning_confidence": zone.learning_confidence,
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
            month_now = dt_util.now().month
            solar_cfg = coordinator.entry.data.get(CONF_SOLAR_RADIATION, DEFAULT_SOLAR_RADIATION)
            solar_month_val = solar_cfg.get(month_now)
            if solar_month_val is None:
                solar_month_val = solar_cfg.get(str(month_now))
            if solar_month_val is None:
                solar_month_val = DEFAULT_SOLAR_RADIATION.get(month_now)

            # Build full 12-month solar radiation dict for the editor
            solar_all = {}
            for m in range(1, 13):
                v = solar_cfg.get(m)
                if v is None:
                    v = solar_cfg.get(str(m))
                if v is None:
                    v = DEFAULT_SOLAR_RADIATION.get(m, 6.0)
                solar_all[str(m)] = round(float(v), 2)

            entry_data = {
                "entry_id": entry_id,
                "language": coordinator.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                "cycles": int(coordinator.entry.data.get(CONF_CYCLES, DEFAULT_CYCLES)),
                "low_threshold": int(coordinator.entry.data.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD)),
                "high_threshold": int(coordinator.entry.data.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD)),
                "switch_entities": sorted(
                    list(
                        set(hass.states.async_entity_ids("switch"))
                        | set(hass.states.async_entity_ids("light"))
                        | set(hass.states.async_entity_ids("valve"))
                    )
                ),
                "current_month": month_now,
                "current_month_solar_radiation": round(float(solar_month_val), 2) if solar_month_val is not None else None,
                "solar_radiation": solar_all,
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
                "weather_status": getattr(coordinator, "weather_status", "ok"),
                "weather_entity": coordinator.entry.data.get(CONF_WEATHER_ENTITY, ""),
                "available_weather_entities": sorted(
                    list(hass.states.async_entity_ids("weather"))
                ),
                "master_enabled": bool(coordinator.entry.data.get(CONF_MASTER_ENABLED, DEFAULT_MASTER_ENABLED)),
                "pushover_enabled": bool(coordinator.entry.data.get(CONF_PUSHOVER_ENABLED, DEFAULT_PUSHOVER_ENABLED)),
                "homekit_enabled": bool(coordinator.entry.data.get(CONF_HOMEKIT_ENABLED, DEFAULT_HOMEKIT_ENABLED)),
                "homekit_port": int(coordinator.entry.data.get(CONF_HOMEKIT_PORT, DEFAULT_HOMEKIT_PORT)),
                "homekit_pin": str(coordinator.entry.data.get(CONF_HOMEKIT_PIN, DEFAULT_HOMEKIT_PIN)),
                "homekit_running": getattr(coordinator.homekit_server, "is_running", False) if coordinator.homekit_server else False,
                "homekit_xhm_uri": getattr(coordinator.homekit_server, "xhm_uri", None) if coordinator.homekit_server else None,
                "homekit_error": getattr(coordinator.homekit_server, "last_error", None) if coordinator.homekit_server else None,
                "homekit_name": getattr(coordinator.homekit_server, "accessory_name", "IrrigationPro Sprinkler") if coordinator.homekit_server else "IrrigationPro Sprinkler",
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
                coordinator._txt("title_test"),
                coordinator._txt("test_message", priority=priority),
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


class IrrigationProSettingsLanguageView(HomeAssistantView):
    """API view to persist language settings from the frontend."""

    url = "/api/irrigationpro/settings/language"
    name = "api:irrigationpro:settings_language"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Persist frontend language selection in the config entry."""
        hass: HomeAssistant = request.app["hass"]
        data = await request.json()
        language = data.get("language", DEFAULT_LANGUAGE)
        entry_id = data.get("entry_id")

        if language not in ("de", "en"):
            return self.json({"error": "invalid language"}, status_code=400)

        coordinators = hass.data.get(DOMAIN, {})
        if not coordinators:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        coordinator = None
        if entry_id:
            coordinator = coordinators.get(entry_id)
        if coordinator is None:
            coordinator = next(iter(coordinators.values()))

        hass.config_entries.async_update_entry(
            coordinator.entry,
            data={**coordinator.entry.data, CONF_LANGUAGE: language},
        )
        coordinator.entry = hass.config_entries.async_get_entry(coordinator.entry.entry_id) or coordinator.entry
        return self.json({"status": "ok", "language": language})


class IrrigationProSettingsSolarView(HomeAssistantView):
    """API view to update monthly solar radiation values."""

    url = "/api/irrigationpro/settings/solar"
    name = "api:irrigationpro:settings_solar"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Persist solar radiation values in the config entry."""
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        entry_id = data.get("entry_id") if isinstance(data, dict) else None
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        solar_values = data.get("solar_radiation") if isinstance(data, dict) else None
        if not isinstance(solar_values, dict):
            return self.json({"error": "solar_radiation dict required"}, status_code=400)

        # Normalize: accept string or int keys, build int-keyed dict
        normalized: dict[int, float] = {}
        for m in range(1, 13):
            raw = solar_values.get(str(m)) or solar_values.get(m)
            if raw is not None:
                try:
                    normalized[m] = round(float(raw), 2)
                except (TypeError, ValueError):
                    pass
            if m not in normalized:
                old_cfg = coordinator.entry.data.get(CONF_SOLAR_RADIATION, DEFAULT_SOLAR_RADIATION)
                fallback = old_cfg.get(m) or old_cfg.get(str(m)) or DEFAULT_SOLAR_RADIATION.get(m, 6.0)
                normalized[m] = round(float(fallback), 2)

        hass.config_entries.async_update_entry(
            coordinator.entry,
            data={**coordinator.entry.data, CONF_SOLAR_RADIATION: normalized},
        )
        return self.json({"status": "ok", "solar_radiation": {str(k): v for k, v in normalized.items()}})


class IrrigationProSettingsTemperatureView(HomeAssistantView):
    """API view to update temperature thresholds."""

    url = "/api/irrigationpro/settings/temperature"
    name = "api:irrigationpro:settings_temperature"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Persist low/high temperature thresholds in the config entry."""
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        entry_id = data.get("entry_id") if isinstance(data, dict) else None
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        low_raw = data.get("low_threshold") if isinstance(data, dict) else None
        high_raw = data.get("high_threshold") if isinstance(data, dict) else None

        low = _to_int(low_raw, coordinator.entry.data.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD))
        high = _to_int(high_raw, coordinator.entry.data.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD))

        # Keep thresholds in a practical range and ensure logical ordering.
        low = max(-20, min(40, low))
        high = max(-20, min(50, high))
        if high < low:
            return self.json({"error": "high_threshold must be >= low_threshold"}, status_code=400)

        hass.config_entries.async_update_entry(
            coordinator.entry,
            data={
                **coordinator.entry.data,
                CONF_LOW_THRESHOLD: low,
                CONF_HIGH_THRESHOLD: high,
            },
        )
        return self.json({"status": "ok", "low_threshold": low, "high_threshold": high})


class IrrigationProSettingsHomeKitView(HomeAssistantView):
    """API view to enable/disable the native HomeKit sprinkler server."""

    url = "/api/irrigationpro/settings/homekit"
    name = "api:irrigationpro:settings_homekit"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Toggle HomeKit server and persist settings."""
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        entry_id = data.get("entry_id") if isinstance(data, dict) else None
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        enabled = bool(data.get("enabled", False))
        port = int(data.get("port", coordinator.entry.data.get(CONF_HOMEKIT_PORT, DEFAULT_HOMEKIT_PORT)))
        pin = str(data.get("pin", coordinator.entry.data.get(CONF_HOMEKIT_PIN, DEFAULT_HOMEKIT_PIN)))

        # Basic validation
        if port < 1024 or port > 65535:
            return self.json({"error": "port must be between 1024 and 65535"}, status_code=400)

        import re
        if not re.match(r"^\d{3}-\d{2}-\d{3}$", pin):
            return self.json({"error": "pin must be in format XXX-XX-XXX"}, status_code=400)

        # Persist
        hass.config_entries.async_update_entry(
            coordinator.entry,
            data={
                **coordinator.entry.data,
                CONF_HOMEKIT_ENABLED: enabled,
                CONF_HOMEKIT_PORT: port,
                CONF_HOMEKIT_PIN: pin,
            },
        )

        # Start / stop server
        if enabled and not (coordinator.homekit_server and coordinator.homekit_server.is_running):
            try:
                from .homekit_server import IrrigationProHomeKit, HAS_HAP

                if not HAS_HAP:
                    return self.json({"error": "HAP-python not installed"}, status_code=500)

                if coordinator.homekit_server:
                    await coordinator.homekit_server.async_stop()

                hk = IrrigationProHomeKit(
                    hass, coordinator,
                    port=port,
                    pin_code=pin,
                    persist_file=hass.config.path("irrigationpro_homekit.state"),
                )
                await hk.async_start()
                coordinator.homekit_server = hk
                if not hk.is_running:
                    return self.json(
                        {
                            "error": hk.last_error or "HomeKit server failed to start",
                            "suggested_port": getattr(hk, "suggested_port", None),
                        },
                        status_code=500,
                    )
            except Exception as err:
                _LOGGER.exception("HomeKit start failed")
                return self.json({"error": str(err)}, status_code=500)

        elif not enabled and coordinator.homekit_server and coordinator.homekit_server.is_running:
            await coordinator.homekit_server.async_stop()

        running = getattr(coordinator.homekit_server, "is_running", False) if coordinator.homekit_server else False
        return self.json(
            {
                "status": "ok",
                "homekit_enabled": enabled,
                "homekit_running": running,
                "port": port,
                "pin": pin,
                "error": getattr(coordinator.homekit_server, "last_error", None) if coordinator.homekit_server else None,
                "name": getattr(coordinator.homekit_server, "accessory_name", "IrrigationPro Sprinkler") if coordinator.homekit_server else "IrrigationPro Sprinkler",
            }
        )


class IrrigationProSettingsRuntimeView(HomeAssistantView):
    """API view to toggle master irrigation and Pushover runtime switches."""

    url = "/api/irrigationpro/settings/runtime"
    name = "api:irrigationpro:settings_runtime"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Persist and apply runtime toggles."""
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        entry_id = data.get("entry_id") if isinstance(data, dict) else None
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        changed: dict[str, bool] = {}

        if "master_enabled" in data:
            enabled = bool(data.get("master_enabled"))
            await coordinator.async_set_master_enabled(enabled)
            changed["master_enabled"] = enabled

        if "pushover_enabled" in data:
            enabled = bool(data.get("pushover_enabled"))
            await coordinator.async_set_pushover_enabled(enabled)
            changed["pushover_enabled"] = enabled

        return self.json(
            {
                "status": "ok",
                **changed,
                "schedule_reason": getattr(coordinator, "schedule_reason", ""),
            }
        )


class IrrigationProHomeKitQRView(HomeAssistantView):
    """Serve a QR code PNG for the HomeKit X-HM:// setup URI."""

    url = "/api/irrigationpro/homekit/qrcode"
    name = "api:irrigationpro:homekit_qrcode"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return QR-code PNG for the running HomeKit server setup URI."""
        hass: HomeAssistant = request.app["hass"]
        entry_id = request.query.get("entry_id")
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return web.Response(status=404, text="No IrrigationPro instance")

        hk = coordinator.homekit_server
        if not hk or not hk.is_running or not hk.xhm_uri:
            return web.Response(status=404, text="HomeKit server not running")

        xhm_uri = hk.xhm_uri

        def _generate_png() -> bytes:
            import io
            try:
                import qrcode
                img = qrcode.make(xhm_uri, box_size=8, border=2)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
            except ImportError:
                raise RuntimeError("qrcode library not available")

        try:
            png_data = await hass.async_add_executor_job(_generate_png)
            return web.Response(body=png_data, content_type="image/png")
        except RuntimeError as err:
            return web.Response(status=500, text=str(err))


class IrrigationProBackupExportView(HomeAssistantView):
    """API view to export current integration configuration as backup."""

    url = "/api/irrigationpro/backup/export"
    name = "api:irrigationpro:backup_export"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Export config of the selected (or first) entry."""
        hass: HomeAssistant = request.app["hass"]
        entry_id = request.query.get("entry_id")
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        return self.json(_build_backup_payload(coordinator))


class IrrigationProBackupRestoreView(HomeAssistantView):
    """API view to restore integration configuration from backup."""

    url = "/api/irrigationpro/backup/restore"
    name = "api:irrigationpro:backup_restore"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Restore config from native backup format or legacy setup format."""
        hass: HomeAssistant = request.app["hass"]
        try:
            payload = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        entry_id = payload.get("entry_id") if isinstance(payload, dict) else None
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        try:
            normalized = _normalize_restore_payload(payload, coordinator.entry.data)
        except ValueError as err:
            return self.json({"error": str(err)}, status_code=400)

        merged = {**coordinator.entry.data, **_sanitize_entry_data(normalized)}

        if not merged.get(CONF_WEATHER_ENTITY):
            return self.json(
                {"error": "weather_entity missing (legacy import needs existing configured weather entity)"},
                status_code=400,
            )
        if not isinstance(merged.get(CONF_ZONES), list) or not merged.get(CONF_ZONES):
            return self.json({"error": "zones missing or empty"}, status_code=400)

        hass.config_entries.async_update_entry(coordinator.entry, data=merged)
        return self.json(
            {
                "status": "ok",
                "restored": True,
                "zones": len(merged.get(CONF_ZONES, [])),
                "backup_format": BACKUP_FORMAT,
            }
        )


class IrrigationProBackupPrepareView(HomeAssistantView):
    """API view to parse/normalize backup payload before applying changes."""

    url = "/api/irrigationpro/backup/prepare"
    name = "api:irrigationpro:backup_prepare"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Prepare editable draft config from backup payload."""
        hass: HomeAssistant = request.app["hass"]
        try:
            payload = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        entry_id = payload.get("entry_id") if isinstance(payload, dict) else None
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        raw_backup = payload.get("backup") if isinstance(payload, dict) and isinstance(payload.get("backup"), dict) else payload
        if not isinstance(raw_backup, dict):
            return self.json({"error": "backup payload must be an object"}, status_code=400)
        try:
            normalized = _normalize_restore_payload(raw_backup, coordinator.entry.data)
        except ValueError as err:
            return self.json({"error": str(err)}, status_code=400)

        merged = {**coordinator.entry.data, **_sanitize_entry_data(normalized)}
        candidate = _normalize_config_data(merged, coordinator.entry.data)
        issues = _validate_candidate(hass, candidate)
        entities = _available_entities(hass)

        return self.json(
            {
                "status": "ok",
                "entry_id": coordinator.entry.entry_id,
                "draft": candidate,
                "issues": issues,
                "backup_format": BACKUP_FORMAT,
                **entities,
            }
        )


class IrrigationProBackupApplyView(HomeAssistantView):
    """API view to apply previously reviewed backup draft data."""

    url = "/api/irrigationpro/backup/apply"
    name = "api:irrigationpro:backup_apply"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Apply edited draft config to config entry."""
        hass: HomeAssistant = request.app["hass"]
        try:
            payload = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        entry_id = payload.get("entry_id") if isinstance(payload, dict) else None
        coordinator = _resolve_coordinator(hass, entry_id)
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else None
        if data is None:
            return self.json({"error": "data object required"}, status_code=400)

        candidate = _normalize_config_data(data, coordinator.entry.data)
        issues = _validate_candidate(hass, candidate)
        if issues["errors"]:
            return self.json({"error": "validation failed", "issues": issues}, status_code=400)

        hass.config_entries.async_update_entry(coordinator.entry, data=candidate)
        return self.json(
            {
                "status": "ok",
                "saved": True,
                "zones": len(candidate.get(CONF_ZONES, [])),
                "issues": issues,
            }
        )


class IrrigationProZoneScheduleView(HomeAssistantView):
    """API view to get/update weekdays and months per zone."""

    url = "/api/irrigationpro/zones/schedule"
    name = "api:irrigationpro:zones_schedule"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return current zone schedule constraints and valid values."""
        hass: HomeAssistant = request.app["hass"]
        coordinator = _resolve_coordinator(hass, request.query.get("entry_id"))
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        zones = []
        for idx, zone in enumerate(coordinator.entry.data.get(CONF_ZONES, []), start=1):
            zones.append(
                {
                    "zone_id": idx,
                    "zone_name": zone.get(CONF_ZONE_NAME),
                    "zone_weekdays": zone.get(CONF_ZONE_WEEKDAYS, WEEKDAYS),
                    "zone_months": zone.get(CONF_ZONE_MONTHS, list(range(1, 13))),
                    "zone_area": zone.get(CONF_ZONE_AREA, DEFAULT_ZONE_AREA),
                    "zone_flow_rate": zone.get(CONF_ZONE_FLOW_RATE, DEFAULT_ZONE_FLOW_RATE),
                    "zone_emitter_count": zone.get(CONF_ZONE_EMITTER_COUNT, DEFAULT_ZONE_EMITTER_COUNT),
                    "zone_efficiency": zone.get(CONF_ZONE_EFFICIENCY, DEFAULT_ZONE_EFFICIENCY),
                    "zone_crop_coef": zone.get(CONF_ZONE_CROP_COEF, DEFAULT_ZONE_CROP_COEF),
                    "zone_plant_density": zone.get(CONF_ZONE_PLANT_DENSITY, DEFAULT_ZONE_PLANT_DENSITY),
                    "zone_exposure_factor": zone.get(CONF_ZONE_EXPOSURE_FACTOR, DEFAULT_ZONE_EXPOSURE_FACTOR),
                    "zone_rain_threshold": zone.get(CONF_ZONE_RAIN_THRESHOLD, DEFAULT_ZONE_RAIN_THRESHOLD),
                    "zone_max_duration": zone.get(CONF_ZONE_MAX_DURATION, DEFAULT_ZONE_MAX_DURATION),
                    "zone_rain_factoring": zone.get(CONF_ZONE_RAIN_FACTORING, DEFAULT_ZONE_RAIN_FACTORING),
                    "zone_adaptive": zone.get(CONF_ZONE_ADAPTIVE, DEFAULT_ZONE_ADAPTIVE),
                    "zone_enabled": zone.get(CONF_ZONE_ENABLED, DEFAULT_ZONE_ENABLED),
                    "zone_adjustment_percent": zone.get(CONF_ZONE_ADJUSTMENT_PERCENT, DEFAULT_ZONE_ADJUSTMENT_PERCENT),
                    "zone_switch_entity": zone.get(CONF_ZONE_SWITCH_ENTITY),
                    "zone_vegetation_type": zone.get(CONF_ZONE_VEGETATION_TYPE, DEFAULT_ZONE_VEGETATION_TYPE),
                    "zone_soil_moisture_entity": zone.get(CONF_ZONE_SOIL_MOISTURE_ENTITY),
                    "zone_target_moisture_min": zone.get(CONF_ZONE_TARGET_MOISTURE_MIN),
                    "zone_target_moisture_max": zone.get(CONF_ZONE_TARGET_MOISTURE_MAX),
                    "zone_learning_enabled": zone.get(CONF_ZONE_LEARNING_ENABLED, DEFAULT_ZONE_LEARNING_ENABLED),
                }
            )

        return self.json(
            {
                "status": "ok",
                "entry_id": coordinator.entry.entry_id,
                "valid_weekdays": WEEKDAYS,
                "valid_months": list(range(1, 13)),
                "zones": zones,
            }
        )

    async def post(self, request: web.Request) -> web.Response:
        """Update schedule constraints for one or multiple zones."""
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except Exception:
            return self.json({"error": "invalid JSON payload"}, status_code=400)

        coordinator = _resolve_coordinator(hass, data.get("entry_id"))
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        zones_cfg = [dict(z) for z in coordinator.entry.data.get(CONF_ZONES, [])]
        if not zones_cfg:
            return self.json({"error": "No zones configured"}, status_code=400)

        updates: list[dict[str, Any]] = []
        if isinstance(data.get("zones"), list):
            updates = [u for u in data.get("zones", []) if isinstance(u, dict)]
        elif "zone_id" in data:
            updates = [data]

        if not updates:
            return self.json({"error": "zone_id or zones[] required"}, status_code=400)

        updated_zone_ids: list[int] = []
        for upd in updates:
            zone_id = upd.get("zone_id")
            if not isinstance(zone_id, int) or zone_id < 1 or zone_id > len(zones_cfg):
                return self.json({"error": f"invalid zone_id: {zone_id}"}, status_code=400)

            zone = zones_cfg[zone_id - 1]

            if CONF_ZONE_WEEKDAYS in upd:
                weekdays = [str(v).lower() for v in upd.get(CONF_ZONE_WEEKDAYS, [])]
                weekdays = [d for d in weekdays if d in WEEKDAYS]
                if not weekdays:
                    return self.json({"error": f"zone {zone_id}: zone_weekdays must not be empty"}, status_code=400)
                zone[CONF_ZONE_WEEKDAYS] = sorted(set(weekdays), key=WEEKDAYS.index)

            if CONF_ZONE_MONTHS in upd:
                months_in = upd.get(CONF_ZONE_MONTHS, [])
                months = []
                for m in months_in:
                    try:
                        m_int = int(m)
                    except (TypeError, ValueError):
                        continue
                    if 1 <= m_int <= 12:
                        months.append(m_int)
                if not months:
                    return self.json({"error": f"zone {zone_id}: zone_months must not be empty"}, status_code=400)
                zone[CONF_ZONE_MONTHS] = sorted(set(months))

            if CONF_ZONE_ADJUSTMENT_PERCENT in upd:
                zone[CONF_ZONE_ADJUSTMENT_PERCENT] = max(10, min(250, _to_int(upd.get(CONF_ZONE_ADJUSTMENT_PERCENT), DEFAULT_ZONE_ADJUSTMENT_PERCENT)))

            if CONF_ZONE_AREA in upd:
                zone[CONF_ZONE_AREA] = max(0.1, _to_float(upd.get(CONF_ZONE_AREA), DEFAULT_ZONE_AREA))
            if CONF_ZONE_FLOW_RATE in upd:
                zone[CONF_ZONE_FLOW_RATE] = max(0.1, _to_float(upd.get(CONF_ZONE_FLOW_RATE), DEFAULT_ZONE_FLOW_RATE))
            if CONF_ZONE_EMITTER_COUNT in upd:
                zone[CONF_ZONE_EMITTER_COUNT] = max(1, _to_int(upd.get(CONF_ZONE_EMITTER_COUNT), DEFAULT_ZONE_EMITTER_COUNT))
            if CONF_ZONE_EFFICIENCY in upd:
                zone[CONF_ZONE_EFFICIENCY] = max(1, min(100, _to_int(upd.get(CONF_ZONE_EFFICIENCY), DEFAULT_ZONE_EFFICIENCY)))
            if CONF_ZONE_CROP_COEF in upd:
                zone[CONF_ZONE_CROP_COEF] = max(0.01, _to_float(upd.get(CONF_ZONE_CROP_COEF), DEFAULT_ZONE_CROP_COEF))
            if CONF_ZONE_PLANT_DENSITY in upd:
                zone[CONF_ZONE_PLANT_DENSITY] = max(0.01, _to_float(upd.get(CONF_ZONE_PLANT_DENSITY), DEFAULT_ZONE_PLANT_DENSITY))
            if CONF_ZONE_EXPOSURE_FACTOR in upd:
                zone[CONF_ZONE_EXPOSURE_FACTOR] = max(0.01, _to_float(upd.get(CONF_ZONE_EXPOSURE_FACTOR), DEFAULT_ZONE_EXPOSURE_FACTOR))
            if CONF_ZONE_RAIN_THRESHOLD in upd:
                zone[CONF_ZONE_RAIN_THRESHOLD] = max(0.0, _to_float(upd.get(CONF_ZONE_RAIN_THRESHOLD), DEFAULT_ZONE_RAIN_THRESHOLD))
            if CONF_ZONE_MAX_DURATION in upd:
                zone[CONF_ZONE_MAX_DURATION] = max(1, _to_int(upd.get(CONF_ZONE_MAX_DURATION), DEFAULT_ZONE_MAX_DURATION))
            if CONF_ZONE_RAIN_FACTORING in upd:
                zone[CONF_ZONE_RAIN_FACTORING] = _to_bool(upd.get(CONF_ZONE_RAIN_FACTORING), DEFAULT_ZONE_RAIN_FACTORING)
            if CONF_ZONE_ADAPTIVE in upd:
                zone[CONF_ZONE_ADAPTIVE] = _to_bool(upd.get(CONF_ZONE_ADAPTIVE), DEFAULT_ZONE_ADAPTIVE)
            if CONF_ZONE_ENABLED in upd:
                zone[CONF_ZONE_ENABLED] = _to_bool(upd.get(CONF_ZONE_ENABLED), DEFAULT_ZONE_ENABLED)
            if CONF_ZONE_SWITCH_ENTITY in upd:
                zone[CONF_ZONE_SWITCH_ENTITY] = str(upd.get(CONF_ZONE_SWITCH_ENTITY) or "").strip() or None
            if CONF_ZONE_NAME in upd:
                zone[CONF_ZONE_NAME] = str(upd.get(CONF_ZONE_NAME) or zone.get(CONF_ZONE_NAME) or f"Zone {zone_id}").strip() or f"Zone {zone_id}"
            if CONF_ZONE_VEGETATION_TYPE in upd:
                vtype = str(upd.get(CONF_ZONE_VEGETATION_TYPE, DEFAULT_ZONE_VEGETATION_TYPE))
                zone[CONF_ZONE_VEGETATION_TYPE] = vtype if vtype in VEGETATION_TYPES else DEFAULT_ZONE_VEGETATION_TYPE
            if CONF_ZONE_SOIL_MOISTURE_ENTITY in upd:
                zone[CONF_ZONE_SOIL_MOISTURE_ENTITY] = str(upd.get(CONF_ZONE_SOIL_MOISTURE_ENTITY) or "").strip() or None
            if CONF_ZONE_TARGET_MOISTURE_MIN in upd:
                zone[CONF_ZONE_TARGET_MOISTURE_MIN] = max(5, min(60, _to_float(upd.get(CONF_ZONE_TARGET_MOISTURE_MIN), 20)))
            if CONF_ZONE_TARGET_MOISTURE_MAX in upd:
                zone[CONF_ZONE_TARGET_MOISTURE_MAX] = max(10, min(70, _to_float(upd.get(CONF_ZONE_TARGET_MOISTURE_MAX), 35)))
            if CONF_ZONE_LEARNING_ENABLED in upd:
                zone[CONF_ZONE_LEARNING_ENABLED] = _to_bool(upd.get(CONF_ZONE_LEARNING_ENABLED), DEFAULT_ZONE_LEARNING_ENABLED)

            updated_zone_ids.append(zone_id)

        merged = {**coordinator.entry.data, CONF_ZONES: zones_cfg}
        hass.config_entries.async_update_entry(coordinator.entry, data=merged)
        return self.json({"status": "ok", "updated_zones": sorted(set(updated_zone_ids))})


class IrrigationProLearningStatusView(HomeAssistantView):
    """API view for soil moisture learning status per zone."""

    url = "/api/irrigationpro/learning/status"
    name = "api:irrigationpro:learning_status"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return learning status for all zones."""
        hass: HomeAssistant = request.app["hass"]
        coordinator = _resolve_coordinator(hass, request.query.get("entry_id"))
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        zones = []
        for zone in coordinator.zones:
            zone_learning = coordinator.feedback_collector.get_zone_data(zone.zone_id)
            zones.append({
                "zone_id": zone.zone_id,
                "name": zone.name,
                "learning_enabled": zone.learning_enabled,
                "soil_moisture_entity": zone.soil_moisture_entity,
                "vegetation_type": zone.vegetation_type,
                "target_moisture_min": zone.target_moisture_min,
                "target_moisture_max": zone.target_moisture_max,
                "correction_factor": round(zone_learning.correction_factor, 4),
                "correction_percent": round(zone_learning.correction_factor * 100, 1),
                "confidence": zone_learning.confidence,
                "journal_entries": len(zone_learning.journal),
                "last_updated": zone_learning.last_updated,
                "current_moisture": (
                    coordinator.feedback_collector.read_soil_moisture(zone.soil_moisture_entity)
                    if zone.soil_moisture_entity else None
                ),
            })

        return self.json({"status": "ok", "zones": zones})


class IrrigationProLearningJournalView(HomeAssistantView):
    """API view for soil moisture learning journal per zone."""

    url = "/api/irrigationpro/learning/journal"
    name = "api:irrigationpro:learning_journal"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return learning journal for a specific zone."""
        hass: HomeAssistant = request.app["hass"]
        coordinator = _resolve_coordinator(hass, request.query.get("entry_id"))
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        zone_id_raw = request.query.get("zone_id")
        if not zone_id_raw:
            return self.json({"error": "zone_id query parameter required"}, status_code=400)
        try:
            zone_id = int(zone_id_raw)
        except (ValueError, TypeError):
            return self.json({"error": "invalid zone_id"}, status_code=400)

        journal = coordinator.feedback_collector.get_journal(zone_id)
        zone_data = coordinator.feedback_collector.get_zone_data(zone_id)

        return self.json({
            "status": "ok",
            "zone_id": zone_id,
            "correction_factor": round(zone_data.correction_factor, 4),
            "confidence": zone_data.confidence,
            "journal": list(reversed(journal)),  # newest first
        })


class IrrigationProLearningResetView(HomeAssistantView):
    """API view to reset learning data for a zone or all zones."""

    url = "/api/irrigationpro/learning/reset"
    name = "api:irrigationpro:learning_reset"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Reset learning data."""
        hass: HomeAssistant = request.app["hass"]
        try:
            data = await request.json()
        except Exception:
            data = {}

        coordinator = _resolve_coordinator(hass, data.get("entry_id"))
        if coordinator is None:
            return self.json({"error": "No IrrigationPro instance configured"}, status_code=404)

        zone_id = data.get("zone_id")
        if zone_id is not None:
            try:
                zone_id = int(zone_id)
            except (ValueError, TypeError):
                return self.json({"error": "invalid zone_id"}, status_code=400)

        await coordinator.async_reset_learning(zone_id)

        return self.json({
            "status": "ok",
            "reset_zone": zone_id if zone_id is not None else "all",
        })


class IrrigationProVegetationTypesView(HomeAssistantView):
    """API view returning available vegetation types with scientific defaults."""

    url = "/api/irrigationpro/vegetation_types"
    name = "api:irrigationpro:vegetation_types"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return all vegetation types with their scientific moisture targets."""
        result = []
        for key, veg in VEGETATION_TYPES.items():
            result.append({
                "key": key,
                "name_de": veg["name_de"],
                "name_en": veg["name_en"],
                "kc": veg["kc"],
                "mad_range": list(veg["mad_range"]),
                "target_min": veg["target_min"],
                "target_max": veg["target_max"],
                "description_de": veg["description_de"],
                "description_en": veg["description_en"],
            })
        return self.json({"vegetation_types": result})


def async_register_api(hass: HomeAssistant) -> None:
    """Register API views."""
    hass.http.register_view(IrrigationProApiView)
    hass.http.register_view(IrrigationProZoneControlView)
    hass.http.register_view(IrrigationProRecalculateView)
    hass.http.register_view(IrrigationProTestView)
    hass.http.register_view(IrrigationProTestNotificationView)
    hass.http.register_view(IrrigationProSettingsLanguageView)
    hass.http.register_view(IrrigationProSettingsSolarView)
    hass.http.register_view(IrrigationProSettingsTemperatureView)
    hass.http.register_view(IrrigationProSettingsHomeKitView)
    hass.http.register_view(IrrigationProSettingsRuntimeView)
    hass.http.register_view(IrrigationProHomeKitQRView)
    hass.http.register_view(IrrigationProBackupExportView)
    hass.http.register_view(IrrigationProBackupRestoreView)
    hass.http.register_view(IrrigationProBackupPrepareView)
    hass.http.register_view(IrrigationProBackupApplyView)
    hass.http.register_view(IrrigationProZoneScheduleView)
    hass.http.register_view(IrrigationProHistoryView)
    hass.http.register_view(IrrigationProLearningStatusView)
    hass.http.register_view(IrrigationProLearningJournalView)
    hass.http.register_view(IrrigationProLearningResetView)
    hass.http.register_view(IrrigationProVegetationTypesView)
