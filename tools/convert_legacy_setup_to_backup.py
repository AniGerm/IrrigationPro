#!/usr/bin/env python3
"""Convert legacy SmartSprinklers setup file to IrrigationPro backup v1."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

BACKUP_FORMAT = "irrigationpro-backup-v1"

MONTH_MAP = {
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

WEEKDAY_MAP = {
    "monday": "monday",
    "tuesday": "tuesday",
    "wednesday": "wednesday",
    "thursday": "thursday",
    "friday": "friday",
    "saturday": "saturday",
    "sunday": "sunday",
}


def _parse_legacy_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    normalized = text
    if not normalized.startswith("{"):
        normalized = "{" + normalized
    if not normalized.endswith("}"):
        normalized = normalized + "}"
    return json.loads(normalized)


def _normalize_months(values: list[str] | None) -> list[int]:
    out: list[int] = []
    for item in values or []:
        key = str(item).strip().lower()[:3]
        m = MONTH_MAP.get(key)
        if m:
            out.append(m)
    return sorted(set(out)) or list(range(1, 13))


def _normalize_weekdays(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for item in values or []:
        day = WEEKDAY_MAP.get(str(item).strip().lower())
        if day:
            out.append(day)
    order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    unique = sorted(set(out), key=order.index) if out else order
    return unique


def _convert(legacy: dict, weather_entity: str, language: str) -> dict:
    zones = []
    for idx, z in enumerate(legacy.get("zones", []), start=1):
        drip_nos = int(z.get("dripNos", 1) or 1)
        total_lph = float(z.get("dripLPH", 0.0) or 0.0)
        flow_per_emitter = total_lph / drip_nos if drip_nos > 0 and total_lph > 0 else 2.0

        zones.append(
            {
                "zone_name": z.get("zoneName", f"Zone {idx}"),
                "zone_enabled": bool(z.get("enabled", True)),
                "zone_adaptive": bool(z.get("adaptive", True)),
                "zone_rain_factoring": bool(z.get("rainFactoring", True)),
                "zone_max_duration": int(z.get("maxDuration", 60)),
                "zone_rain_threshold": float(z.get("rainThreshold", 2.5)),
                "zone_area": float(z.get("dripArea", 10.0)),
                "zone_flow_rate": float(flow_per_emitter),
                "zone_emitter_count": int(drip_nos),
                "zone_efficiency": int(z.get("efficiency", 90)),
                "zone_crop_coef": float(z.get("cropCoef", 0.6)),
                "zone_plant_density": float(z.get("plantDensity", 1.0)),
                "zone_exposure_factor": float(z.get("expFactor", 1.0)),
                "zone_weekdays": _normalize_weekdays(z.get("wateringWeekdays")),
                "zone_months": _normalize_months(z.get("wateringMonths")),
                "zone_switch_entity": None,
            }
        )

    data = {
        "weather_entity": weather_entity,
        "use_owm": bool(legacy.get("keyAPI")),
        "owm_api_key": legacy.get("keyAPI", ""),
        "zones": zones,
        "sunrise_offset": int(legacy.get("sunriseOffset", 0)),
        "cycles": int(legacy.get("cycles", 2)),
        "low_threshold": int(legacy.get("lowThreshold", 5)),
        "high_threshold": int(legacy.get("highThreshold", 15)),
        "recheck_time": int(legacy.get("recheckTime", 0)),
        "language": language,
        "pushover_enabled": bool(legacy.get("pushEnable", False)),
        "pushover_api_token": legacy.get("tokenPO", ""),
        "pushover_user_key": legacy.get("userPO", ""),
        "pushover_device": "",
        "pushover_priority": int(legacy.get("priorityPO", 0)),
        "daily_report_enabled": False,
        "daily_report_hour": 7,
        "solar_radiation": {
            "1": float(legacy.get("JanRad", 6.0)),
            "2": float(legacy.get("FebRad", 6.0)),
            "3": float(legacy.get("MarRad", 6.0)),
            "4": float(legacy.get("AprRad", 6.0)),
            "5": float(legacy.get("MayRad", 6.0)),
            "6": float(legacy.get("JunRad", 6.0)),
            "7": float(legacy.get("JulRad", 6.0)),
            "8": float(legacy.get("AugRad", 6.0)),
            "9": float(legacy.get("SepRad", 6.0)),
            "10": float(legacy.get("OctRad", 6.0)),
            "11": float(legacy.get("NovRad", 6.0)),
            "12": float(legacy.get("DecRad", 6.0)),
        },
    }

    return {
        "backup_format": BACKUP_FORMAT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "domain": "irrigationpro",
        "source": "legacy_smartsprinklers",
        "data": data,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to legacy setup file")
    parser.add_argument("output", type=Path, help="Path to output backup json")
    parser.add_argument(
        "--weather-entity",
        default="weather.example_home",
        help="Fallback weather entity for new setup (default: weather.example_home)",
    )
    parser.add_argument(
        "--language",
        default="de",
        choices=["de", "en"],
        help="Language in generated backup (default: de)",
    )
    args = parser.parse_args()

    legacy = _parse_legacy_file(args.input)
    backup = _convert(legacy, weather_entity=args.weather_entity, language=args.language)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(backup, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
