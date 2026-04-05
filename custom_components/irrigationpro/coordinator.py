"""Coordinator for IrrigationPro integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CYCLES,
    CONF_HIGH_THRESHOLD,
    CONF_MASTER_ENABLED,
    CONF_LANGUAGE,
    CONF_LOW_THRESHOLD,
    CONF_OWM_API_KEY,
    CONF_PUSHOVER_API_TOKEN,
    CONF_PUSHOVER_DEVICE,
    CONF_PUSHOVER_ENABLED,
    CONF_PUSHOVER_PRIORITY,
    CONF_PUSHOVER_USER_KEY,
    CONF_DAILY_REPORT_ENABLED,
    CONF_DAILY_REPORT_HOUR,
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
    DEFAULT_LANGUAGE,
    DEFAULT_MASTER_ENABLED,
    DEFAULT_ZONE_ADJUSTMENT_PERCENT,
    DEFAULT_ZONE_LEARNING_ENABLED,
    DEFAULT_ZONE_VEGETATION_TYPE,
    DEFAULT_SOLAR_RADIATION,
    DEFAULT_DAILY_REPORT_ENABLED,
    DEFAULT_DAILY_REPORT_HOUR,
    DEFAULT_SENSOR_ALERT_MINUTES,
    SENSOR_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL_MINUTES,
    VEGETATION_TYPES,
    WEEKDAYS,
)
from .eto import calculate_eto
from .learning import FeedbackCollector, get_vegetation_defaults
from .weather_provider import WeatherData, WeatherProvider

_LOGGER = logging.getLogger(__name__)

_WEEKDAY_NAMES = {
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}

_WEATHER_CONDITION_TEXT = {
    "de": {
        "clear": "klar",
        "sunny": "sonnig",
        "partlycloudy": "teilweise bewölkt",
        "partly cloudy": "teilweise bewölkt",
        "cloudy": "bewölkt",
        "overcast": "bedeckt",
        "rain": "Regen",
        "rainy": "regnerisch",
        "pouring": "starker Regen",
        "showers": "Schauer",
        "light rain": "leichter Regen",
        "moderate rain": "mäßiger Regen",
        "heavy rain": "starker Regen",
        "snow": "Schnee",
        "snowy": "schneit",
        "snowy-rainy": "Schneeregen",
        "hail": "Hagel",
        "fog": "Nebel",
        "mist": "Dunst",
        "windy": "windig",
        "thunderstorm": "Gewitter",
        "lightning": "Blitze",
        "unknown": "unbekannt",
    },
    "en": {
        "clear": "clear",
        "sunny": "sunny",
        "partlycloudy": "partly cloudy",
        "partly cloudy": "partly cloudy",
        "cloudy": "cloudy",
        "overcast": "overcast",
        "rain": "rain",
        "rainy": "rainy",
        "pouring": "heavy rain",
        "showers": "showers",
        "light rain": "light rain",
        "moderate rain": "moderate rain",
        "heavy rain": "heavy rain",
        "snow": "snow",
        "snowy": "snow",
        "snowy-rainy": "sleet",
        "hail": "hail",
        "fog": "fog",
        "mist": "mist",
        "windy": "windy",
        "thunderstorm": "thunderstorm",
        "lightning": "lightning",
        "unknown": "unknown",
    },
}

_TEXT = {
    "de": {
        "zone_disabled": "Zone deaktiviert",
        "no_watering_day": "Kein Bewässerungstag ({weekday})",
        "no_watering_month": "Kein Bewässerungsmonat",
        "rain_threshold_exceeded": "Regenschwelle überschritten ({rain:.1f} mm >= {threshold} mm)",
        "no_water_needed": "Kein Wasserbedarf (ETo durch Regen gedeckt)",
        "temperature_too_low": "Temperatur zu niedrig (min: {min_temp:.1f}°C, max: {max_temp:.1f}°C – Schwelle min>= {low}°C und max>= {high}°C)",
        "master_disabled": "Hauptschalter ist deaktiviert – Bewässerung pausiert",
        "title_watering_done": "✅ Bewässerung abgeschlossen",
        "title_watering_error": "❌ Bewässerungsfehler",
        "title_manual_start": "🚿 Manuelle Bewässerung",
        "title_manual_done": "✅ Manuelle Bewässerung beendet",
        "title_master_off": "⏸️ Bewässerung pausiert",
        "title_master_on": "✅ Bewässerung aktiviert",
        "title_pushover_on": "🔔 Pushover aktiviert",
        "title_pushover_off": "🔕 Pushover deaktiviert",
        "title_plan_today": "🗓 Bewässerung geplant",
        "title_no_watering_today": "💤 Keine Bewässerung heute",
        "title_test": "🔔 IrrigationPro Test",
        "start": "Start",
        "end": "Ende",
        "total_duration": "Gesamtdauer",
        "planned_duration": "Geplante Dauer",
        "runtime": "Laufzeit",
        "no_zones_configured": "Keine Zonen konfiguriert",
        "next_recalc_before_run": "Nächste Neuberechnung vor geplantem Lauf: {when}",
        "no_extra_recalc_before_run": "Keine zusätzliche Neuberechnung vor einem geplanten Lauf.\nReguläres Wetter-Update und Neuplanung alle {minutes} Minuten.",
        "extra_recalc_before_start": "Zusätzliche Neuberechnung vor Start: {when}",
        "no_extra_recalc_before_start": "Keine zusätzliche Neuberechnung vor Start.\nReguläres Wetter-Update und Neuplanung alle {minutes} Minuten.",
        "next_extra_recalc": "Nächste zusätzliche Neuberechnung:\n{when}\n(zusätzlich zum regulären Update alle {minutes} Minuten)",
        "no_extra_recalc_today": "Keine zusätzliche Neuberechnung für heute geplant.\nAutomatische Neuplanung beim nächsten Wetter-Update (alle {minutes} Minuten).",
        "no_schedule_set": "Kein Zeitplan gesetzt",
        "weather_unavailable": "⚠️ Wetter-Entität nicht verfügbar – Retry alle 2 min. Prüfe die Konfiguration.",
        "manual_zone_started": "Zone «{zone}» manuell gestartet\nGeplante Dauer: {duration} min.",
        "manual_zone_stopped": "Zone «{zone}» beendet\nLaufzeit: {duration} min.\nStart: {start}\nEnde:  {end}",
        "master_disabled_message": "Der Hauptschalter wurde ausgeschaltet. Alle laufenden Zonen wurden gestoppt und die automatische Bewässerung bleibt pausiert, bis du sie wieder aktivierst.",
        "master_enabled_message": "Der Hauptschalter ist wieder aktiviert. Automatische und manuelle Bewässerung laufen ab jetzt wieder regulär.",
        "pushover_enabled_message": "Pushover ist jetzt aktiviert und wird dich wieder über Starts, Stopps und wichtige Ereignisse informieren.",
        "pushover_disabled_message": "Pushover ist jetzt deaktiviert. Ab sofort werden keine Benachrichtigungen mehr gesendet, bis du es manuell wieder aktivierst.",
        "master_blocked_manual_start": "Manueller Start blockiert: Hauptschalter deaktiviert",
        "watering_error": "Fehler beim Bewässern: {error}",
        "weather_footer": "───\n{day}: {condition}, {clouds}% Wolken\nSonnenaufgang: {sunrise} Uhr | Luftfeuchte: {humidity:.0f}%\nTemp.: {min_temp:.1f}°C – {max_temp:.1f}°C\nLuftdruck: {pressure:.0f} hPa | Wind: {wind:.1f} m/s\nNiederschlag: {rain:.2f} mm | ETo: {eto:.2f} mm",
        "test_message": "Test-Benachrichtigung erfolgreich! Priorität: {priority}",
        "learning_feedback_scheduled": "Bodenfeuchtesensor-Auswertung für Zone «{zone}» in {hours}h geplant",
        "learning_correction_updated": "Zone «{zone}» Lernkorrektur aktualisiert: {factor:.1%} (Konfidenz: {confidence})",
        # Sensor health alerts
        "title_sensor_offline": "⚠️ Sensor nicht erreichbar",
        "title_sensor_recovered": "✅ Sensor wieder erreichbar",
        "title_sensor_battery_low": "🪫 Sensor-Batterie schwach",
        "sensor_offline_message": "Der Feuchtigkeitssensor «{entity}» (Zone «{zone}») ist seit {minutes} Minuten nicht erreichbar.\nBitte prüfe die Verbindung.",
        "sensor_recovered_message": "Der Feuchtigkeitssensor «{entity}» (Zone «{zone}») ist wieder erreichbar.\nAktueller Wert: {value}%",
        "sensor_battery_low_message": "Die Batterie des Sensors «{entity}» (Zone «{zone}») ist bei {level}%.\nBitte Batterie bald tauschen.",
        # Soil moisture skip
        "moisture_too_high": "Bodenfeuchte zu hoch ({moisture:.0f}% >= {target_max}%) – Bewässerung übersprungen",
        "moisture_reduced": "Bodenfeuchte ausreichend ({moisture:.0f}%) – Dauer um {reduction:.0f}% reduziert",
        "title_moisture_skip": "💧 Bewässerung übersprungen (Boden feucht)",
        "moisture_skip_message": "Zone «{zone}»: Bodenfeuchte {moisture:.0f}% liegt über Zielwert {target_max}%.\nBewässerung wird verschoben, bis der Boden trockener ist.",
        "title_moisture_reduced": "💧 Bewässerung reduziert",
        "moisture_reduced_message": "Zone «{zone}»: Bodenfeuchte {moisture:.0f}% (Ziel: {target_min}–{target_max}%).\nDauer um {reduction:.0f}% reduziert.",
    },
    "en": {
        "zone_disabled": "Zone disabled",
        "no_watering_day": "Not a watering day ({weekday})",
        "no_watering_month": "Not a watering month",
        "rain_threshold_exceeded": "Rain threshold exceeded ({rain:.1f} mm >= {threshold} mm)",
        "no_water_needed": "No watering needed (ETo covered by rain)",
        "temperature_too_low": "Temperature too low (min: {min_temp:.1f}°C, max: {max_temp:.1f}°C - threshold min>= {low}°C and max>= {high}°C)",
        "master_disabled": "Master switch is off - irrigation paused",
        "title_watering_done": "✅ Watering completed",
        "title_watering_error": "❌ Watering error",
        "title_manual_start": "🚿 Manual watering",
        "title_manual_done": "✅ Manual watering finished",
        "title_master_off": "⏸️ Irrigation paused",
        "title_master_on": "✅ Irrigation enabled",
        "title_pushover_on": "🔔 Pushover enabled",
        "title_pushover_off": "🔕 Pushover disabled",
        "title_plan_today": "🗓 Irrigation scheduled",
        "title_no_watering_today": "💤 No watering today",
        "title_test": "🔔 IrrigationPro Test",
        "start": "Start",
        "end": "End",
        "total_duration": "Total duration",
        "planned_duration": "Planned duration",
        "runtime": "Runtime",
        "no_zones_configured": "No zones configured",
        "next_recalc_before_run": "Next recalculation before scheduled run: {when}",
        "no_extra_recalc_before_run": "No additional recalculation before a scheduled run.\nRegular weather update and replanning every {minutes} minutes.",
        "extra_recalc_before_start": "Additional recalculation before start: {when}",
        "no_extra_recalc_before_start": "No additional recalculation before start.\nRegular weather update and replanning every {minutes} minutes.",
        "next_extra_recalc": "Next additional recalculation:\n{when}\n(in addition to the regular update every {minutes} minutes)",
        "no_extra_recalc_today": "No additional recalculation planned for today.\nAutomatic replanning at the next weather update (every {minutes} minutes).",
        "no_schedule_set": "No schedule set",
        "weather_unavailable": "⚠️ Weather entity not available – retrying every 2 min. Check configuration.",
        "manual_zone_started": "Zone «{zone}» started manually\nPlanned duration: {duration} min.",
        "manual_zone_stopped": "Zone «{zone}» finished\nRuntime: {duration} min.\nStart: {start}\nEnd:   {end}",
        "master_disabled_message": "The master switch was turned off. All running zones were stopped and automatic irrigation will stay paused until you enable it again.",
        "master_enabled_message": "The master switch is enabled again. Automatic and manual irrigation now run normally.",
        "pushover_enabled_message": "Pushover is now enabled and will inform you again about starts, stops and important events.",
        "pushover_disabled_message": "Pushover is now disabled. No notifications will be sent until you enable it manually again.",
        "master_blocked_manual_start": "Manual start blocked: master switch disabled",
        "watering_error": "Watering error: {error}",
        "weather_footer": "───\n{day}: {condition}, {clouds}% clouds\nSunrise: {sunrise} | Humidity: {humidity:.0f}%\nTemp.: {min_temp:.1f}°C – {max_temp:.1f}°C\nPressure: {pressure:.0f} hPa | Wind: {wind:.1f} m/s\nPrecipitation: {rain:.2f} mm | ETo: {eto:.2f} mm",
        "test_message": "Test notification sent successfully! Priority: {priority}",
        "learning_feedback_scheduled": "Soil moisture feedback for zone «{zone}» scheduled in {hours}h",
        "learning_correction_updated": "Zone «{zone}» learning correction updated: {factor:.1%} (confidence: {confidence})",
        # Sensor health alerts
        "title_sensor_offline": "⚠️ Sensor offline",
        "title_sensor_recovered": "✅ Sensor recovered",
        "title_sensor_battery_low": "🪫 Sensor battery low",
        "sensor_offline_message": "The moisture sensor «{entity}» (zone «{zone}») has been unreachable for {minutes} minutes.\nPlease check the connection.",
        "sensor_recovered_message": "The moisture sensor «{entity}» (zone «{zone}») is reachable again.\nCurrent value: {value}%",
        "sensor_battery_low_message": "The battery of sensor «{entity}» (zone «{zone}») is at {level}%.\nPlease replace the battery soon.",
        # Soil moisture skip
        "moisture_too_high": "Soil moisture too high ({moisture:.0f}% >= {target_max}%) – watering skipped",
        "moisture_reduced": "Soil moisture adequate ({moisture:.0f}%) – duration reduced by {reduction:.0f}%",
        "title_moisture_skip": "💧 Watering skipped (soil wet)",
        "moisture_skip_message": "Zone «{zone}»: Soil moisture {moisture:.0f}% is above target {target_max}%.\nWatering postponed until soil is drier.",
        "title_moisture_reduced": "💧 Watering reduced",
        "moisture_reduced_message": "Zone «{zone}»: Soil moisture {moisture:.0f}% (target: {target_min}–{target_max}%).\nDuration reduced by {reduction:.0f}%.",
    },
}


class ZoneData:
    """Data for a single irrigation zone."""

    def __init__(self, zone_id: int, config: dict[str, Any]):
        """Initialize zone data."""
        self.zone_id = zone_id
        self.name = config.get(CONF_ZONE_NAME, f"Zone {zone_id}")
        self.enabled = config.get(CONF_ZONE_ENABLED, True)
        self.adaptive = config.get(CONF_ZONE_ADAPTIVE, True)
        self.area = config.get(CONF_ZONE_AREA, 10.0)
        self.flow_rate = config.get(CONF_ZONE_FLOW_RATE, 2.0)
        self.emitter_count = config.get(CONF_ZONE_EMITTER_COUNT, 10)
        self.efficiency = config.get(CONF_ZONE_EFFICIENCY, 90)
        self.crop_coef = config.get(CONF_ZONE_CROP_COEF, 0.6)
        self.plant_density = config.get(CONF_ZONE_PLANT_DENSITY, 1.0)
        self.exposure_factor = config.get(CONF_ZONE_EXPOSURE_FACTOR, 1.0)
        self.max_duration = config.get(CONF_ZONE_MAX_DURATION, 60)
        self.rain_threshold = config.get(CONF_ZONE_RAIN_THRESHOLD, 2.5)
        self.rain_factoring = config.get(CONF_ZONE_RAIN_FACTORING, True)
        self.adjustment_percent = config.get(CONF_ZONE_ADJUSTMENT_PERCENT, DEFAULT_ZONE_ADJUSTMENT_PERCENT)
        self.switch_entity = config.get(CONF_ZONE_SWITCH_ENTITY)
        # Use CONF keys for weekdays and months with proper defaults
        self.weekdays = config.get(CONF_ZONE_WEEKDAYS, WEEKDAYS)
        self.months = config.get(CONF_ZONE_MONTHS, list(range(1, 13)))
        
        # Soil moisture learning
        self.vegetation_type = config.get(CONF_ZONE_VEGETATION_TYPE, DEFAULT_ZONE_VEGETATION_TYPE)
        self.soil_moisture_entity = config.get(CONF_ZONE_SOIL_MOISTURE_ENTITY)
        veg_defaults = get_vegetation_defaults(self.vegetation_type)
        self.target_moisture_min = config.get(CONF_ZONE_TARGET_MOISTURE_MIN) or veg_defaults[0]
        self.target_moisture_max = config.get(CONF_ZONE_TARGET_MOISTURE_MAX) or veg_defaults[1]
        self.learning_enabled = config.get(CONF_ZONE_LEARNING_ENABLED, DEFAULT_ZONE_LEARNING_ENABLED)
        
        # Learning runtime data (set by coordinator from FeedbackCollector)
        self.learning_correction: float = 1.0
        self.learning_confidence: int = 0
        
        # Runtime data
        self.duration = 0  # Minutes for next run
        self.eto_total = 0  # Total ETo until next watering
        self.rain_total = 0  # Total rain until next watering
        self.water_needed = 0  # Water needed in mm
        self.next_run: datetime | None = None
        self.last_run: datetime | None = None
        self.is_running = False
        self.started_at: datetime | None = None  # When the zone was last started
        self.skip_reason: str = ""  # Why this zone is not scheduled
        self.duration_uncapped: float = 0.0  # Calculated duration before max_duration cap
        self.days_until_next: int = 1  # Days of ETo accumulated for this calculation
        self.current_moisture: float | None = None  # Live reading from sensor
        self.moisture_reduction: float = 1.0  # 1.0 = none, <1.0 = reduced due to moisture


class SmartIrrigationCoordinator(DataUpdateCoordinator):
    """Coordinator to manage IrrigationPro data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.entry = entry
        self.zones: list[ZoneData] = []
        self.forecast: list[WeatherData] = []
        self.scheduled_run: datetime | None = None
        self.recheck_scheduled: datetime | None = None
        self._schedule_timer = None
        self._recheck_timer = None
        self._watering_task = None
        self._manual_zone_tasks: dict[int, asyncio.Task] = {}
        self._storage: Store | None = None
        self._schedule_checker_unsub = None
        self.schedule_reason: str = ""  # Why no watering is scheduled
        self.weather_status: str = "ok"  # ok | unavailable | error
        self.history: list[dict] = []  # Irrigation & skip history (max 180 entries)
        self.last_calculated: datetime | None = None  # When the schedule was last calculated
        self.last_refresh_time: datetime | None = None  # Last successful coordinator refresh
        self._daily_report_unsub = None
        self._watering_started_at: datetime | None = None
        self.homekit_server = None  # Set by __init__.py if HomeKit enabled
        
        # Sensor health monitoring
        self._sensor_unavailable_since: dict[str, datetime] = {}
        self._sensor_alerted: dict[str, str] = {}  # entity_id -> last alert type
        
        # Soil moisture learning
        self.feedback_collector = FeedbackCollector(hass, entry.entry_id)
        
        # Validate configuration
        if not entry.data.get(CONF_WEATHER_ENTITY):
            raise ValueError("No weather entity configured")
        
        if not entry.data.get(CONF_ZONES):
            raise ValueError("No zones configured")
        
        _LOGGER.debug("Initializing coordinator with %d zones", len(entry.data.get(CONF_ZONES, [])))
        
        # Initialize weather provider
        self.weather_provider = WeatherProvider(
            hass,
            weather_entity=entry.data.get(CONF_WEATHER_ENTITY),
            owm_api_key=entry.data.get(CONF_OWM_API_KEY),
            use_owm=entry.data.get(CONF_USE_OWM, False),
        )
        
        # Initialize zones from config
        self._init_zones()
        
        # Start schedule checker (every minute)
        self._schedule_checker_unsub = async_track_time_interval(
            hass, self._check_schedule, timedelta(minutes=1)
        )
        # Set up daily morning report if configured
        self._setup_daily_report()

    def _init_zones(self):
        """Initialize zones from configuration."""
        zones_config = self.entry.data.get(CONF_ZONES, [])
        if not zones_config:
            _LOGGER.error("No zones configuration found in entry data")
            raise ValueError("No zones configured")
        
        _LOGGER.debug("Raw zones_config from entry: %s", zones_config)
        
        try:
            self.zones = []
            for i, zone_config in enumerate(zones_config):
                _LOGGER.debug("Processing zone %d config: %s", i + 1, zone_config)
                zone = ZoneData(i + 1, zone_config)
                self.zones.append(zone)
                _LOGGER.debug(
                    "Zone %d initialized: %s (enabled=%s, adaptive=%s, area=%.1fm²)",
                    zone.zone_id, zone.name, zone.enabled, zone.adaptive, zone.area
                )
            
            _LOGGER.info("Successfully initialized %d zones", len(self.zones))
            
        except Exception as err:
            _LOGGER.error("Error initializing zones: %s", err, exc_info=True)
            raise ValueError(f"Failed to initialize zones: {err}") from err

    def _sync_learning_to_zones(self) -> None:
        """Copy learning correction factors from FeedbackCollector to ZoneData."""
        for zone in self.zones:
            zone.learning_correction = self.feedback_collector.get_correction_factor(zone.zone_id)
            zone.learning_confidence = self.feedback_collector.get_confidence(zone.zone_id)

    async def async_config_entry_first_refresh(self):
        """Refresh data for the first time when config entry is setup."""
        # Load stored data
        await self._async_load_storage()
        
        # Load learning data
        await self.feedback_collector.async_load()
        self._sync_learning_to_zones()
        
        # Perform first refresh
        await super().async_config_entry_first_refresh()
        
        # Calculate initial schedule
        await self._async_calculate_schedule()

    async def async_apply_updated_entry(self, entry: ConfigEntry) -> None:
        """Apply updated config-entry data without unloading the integration.

        This keeps the dashboard panel alive when values are changed from the UI.
        """
        old_last_run = {z.zone_id: z.last_run for z in self.zones}

        self.entry = entry

        # Keep the weather provider in sync with changed entry values.
        self.weather_provider.weather_entity = entry.data.get(CONF_WEATHER_ENTITY)
        self.weather_provider.owm_api_key = entry.data.get(CONF_OWM_API_KEY)
        self.weather_provider.use_owm = entry.data.get(CONF_USE_OWM, False)

        # Rebuild zone configs from entry and preserve runtime timestamps.
        self._init_zones()
        for zone in self.zones:
            zone.last_run = old_last_run.get(zone.zone_id)

        # Re-register daily report timer if related settings changed.
        self._setup_daily_report()

        # Trigger recalculation/refresh with the new settings.
        await self.async_request_refresh()
        self.async_set_updated_data(self.data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from weather provider and calculate irrigation needs."""
        try:
            _LOGGER.debug("Updating weather data and calculating irrigation needs")
            
            # Get weather forecast – a missing/unavailable entity must not block startup
            try:
                self.forecast = await self.weather_provider.async_get_forecast(days=8)
                self.weather_status = "ok"
            except (ValueError, Exception) as weather_err:
                _LOGGER.warning(
                    "Weather data not available (%s) – will retry in 2 min. "
                    "Available weather entities: %s",
                    weather_err,
                    ", ".join(sorted(self.hass.states.async_entity_ids("weather"))) or "none",
                )
                self.forecast = []
                self.weather_status = "unavailable"

            if not self.forecast:
                # Retry much sooner than the normal 60-min interval
                self.update_interval = timedelta(minutes=2)
                self.schedule_reason = self._txt("weather_unavailable")
                _LOGGER.warning(
                    "No forecast data – scheduling retry in 2 min. "
                    "Watering will not be scheduled until weather data is available."
                )
                return {
                    "forecast": [],
                    "zones": self.zones,
                    "scheduled_run": self.scheduled_run,
                }

            # Weather is available – restore normal update interval
            self.update_interval = timedelta(minutes=UPDATE_INTERVAL_MINUTES)
            
            # Calculate ETo for each forecast day
            lat = self.hass.config.latitude
            alt = self.hass.config.elevation
            solar_rad_data = self.entry.data.get(
                CONF_SOLAR_RADIATION, DEFAULT_SOLAR_RADIATION
            )
            
            for day_data in self.forecast:
                month = day_data.sunrise.month
                # Keys may be strings after JSON serialization
                solar_rad = solar_rad_data.get(month) or solar_rad_data.get(str(month), 6.0)
                
                day_data.eto = calculate_eto(
                    min_temp=day_data.min_temp,
                    max_temp=day_data.max_temp,
                    humidity=day_data.humidity,
                    pressure=day_data.pressure,
                    wind_speed=day_data.wind_speed,
                    solar_radiation=solar_rad,
                    altitude=alt,
                    latitude=lat,
                    date=day_data.sunrise,
                )
                
                _LOGGER.debug(
                    "Day %s: ETo=%.2f mm, Rain=%.1f mm, Temp=%.1f-%.1f°C",
                    day_data.sunrise.date(),
                    day_data.eto,
                    day_data.rain,
                    day_data.min_temp,
                    day_data.max_temp,
                )
            
            # Recalculate zone requirements
            await self._async_calculate_schedule()
            self.last_refresh_time = dt_util.now()
            
            # Check soil moisture sensor health after schedule calculation
            await self._async_check_sensor_health()
            
            return {
                "forecast": self.forecast,
                "zones": self.zones,
                "scheduled_run": self.scheduled_run,
            }
            
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}")

    async def _async_check_sensor_health(self) -> None:
        """Check soil moisture sensors for availability and battery issues."""
        now = dt_util.now()
        alert_minutes = DEFAULT_SENSOR_ALERT_MINUTES

        for zone in self.zones:
            entity_id = zone.soil_moisture_entity
            if not entity_id:
                continue

            state_obj = self.hass.states.get(entity_id)
            is_unavailable = (
                state_obj is None
                or state_obj.state in ("unavailable", "unknown")
            )

            if is_unavailable:
                # Track when it first went unavailable
                if entity_id not in self._sensor_unavailable_since:
                    self._sensor_unavailable_since[entity_id] = now

                elapsed = (now - self._sensor_unavailable_since[entity_id]).total_seconds() / 60
                if elapsed >= alert_minutes and self._sensor_alerted.get(entity_id) != "offline":
                    self._sensor_alerted[entity_id] = "offline"
                    await self._send_pushover_notification(
                        self._txt("title_sensor_offline"),
                        self._txt(
                            "sensor_offline_message",
                            entity=entity_id,
                            zone=zone.name,
                            minutes=int(elapsed),
                        ),
                    )
            else:
                # Sensor is back online
                if entity_id in self._sensor_unavailable_since:
                    del self._sensor_unavailable_since[entity_id]
                    if self._sensor_alerted.get(entity_id) == "offline":
                        self._sensor_alerted.pop(entity_id, None)
                        try:
                            current_val = round(float(state_obj.state), 1)
                        except (ValueError, TypeError):
                            current_val = "?"
                        await self._send_pushover_notification(
                            self._txt("title_sensor_recovered"),
                            self._txt(
                                "sensor_recovered_message",
                                entity=entity_id,
                                zone=zone.name,
                                value=current_val,
                            ),
                        )

                # Check battery level from entity attributes
                battery = None
                if state_obj and state_obj.attributes:
                    for attr in ("battery_level", "battery", "Battery"):
                        val = state_obj.attributes.get(attr)
                        if val is not None:
                            try:
                                battery = float(val)
                            except (ValueError, TypeError):
                                pass
                            break

                if battery is not None and battery <= SENSOR_BATTERY_LOW_THRESHOLD:
                    if self._sensor_alerted.get(entity_id) != "battery":
                        self._sensor_alerted[entity_id] = "battery"
                        await self._send_pushover_notification(
                            self._txt("title_sensor_battery_low"),
                            self._txt(
                                "sensor_battery_low_message",
                                entity=entity_id,
                                zone=zone.name,
                                level=int(battery),
                            ),
                        )
                elif battery is not None and battery > SENSOR_BATTERY_LOW_THRESHOLD:
                    if self._sensor_alerted.get(entity_id) == "battery":
                        self._sensor_alerted.pop(entity_id, None)

    async def _async_calculate_schedule(self):
        """Calculate watering schedule for all zones."""
        if not self.forecast:
            _LOGGER.warning("No forecast data available for scheduling")
            return

        if not self.entry.data.get(CONF_MASTER_ENABLED, DEFAULT_MASTER_ENABLED):
            self.scheduled_run = None
            self.recheck_scheduled = None
            self.schedule_reason = self._txt("master_disabled")
            for zone in self.zones:
                zone.duration = 0
            self.async_set_updated_data(self.data)
            return
        
        _LOGGER.info("Calculating irrigation schedule")
        self.last_calculated = dt_util.now()
        
        # Get configuration
        sunrise_offset = self.entry.data.get(CONF_SUNRISE_OFFSET, 0)
        cycles = int(self.entry.data.get(CONF_CYCLES, 2))
        low_threshold = self.entry.data.get(CONF_LOW_THRESHOLD, 5)
        high_threshold = self.entry.data.get(CONF_HIGH_THRESHOLD, 15)
        
        # Determine if we can water today or need to schedule for tomorrow
        total_duration = 0
        
        for zone in self.zones:
            if zone.enabled:
                zone.duration = await self._calculate_zone_duration(zone, 0)
                total_duration += zone.duration * cycles
        
        # Calculate start time
        day_index = 0
        sunrise_today = self.forecast[0].sunrise
        earliest_today = sunrise_today - timedelta(
            minutes=total_duration + sunrise_offset
        )
        
        if earliest_today < dt_util.now():
            day_index = 1
        
        # Check temperature thresholds
        forecast_day = self.forecast[day_index]
        if (
            forecast_day.min_temp < low_threshold
            or forecast_day.max_temp < high_threshold
        ):
            _LOGGER.info(
                "Temperature thresholds not met (min: %.1f°C, max: %.1f°C), skipping schedule",
                forecast_day.min_temp,
                forecast_day.max_temp,
            )
            self.scheduled_run = None
            self.schedule_reason = self._txt(
                "temperature_too_low",
                min_temp=forecast_day.min_temp,
                max_temp=forecast_day.max_temp,
                low=low_threshold,
                high=high_threshold,
            )
            self._log_skip_event(self.schedule_reason, forecast_day)
            self.recheck_scheduled = None
            return
        
        # Recalculate durations for the selected day
        total_duration = 0
        moisture_skipped_zones = []
        moisture_reduced_zones = []
        for zone in self.zones:
            if zone.enabled:
                zone.duration = await self._calculate_zone_duration(zone, day_index)
                total_duration += zone.duration * cycles
                _LOGGER.info(
                    "Zone '%s': %.1f minutes (%d cycles of %.1f min)",
                    zone.name,
                    zone.duration * cycles,
                    cycles,
                    zone.duration,
                )
                # Track moisture-based decisions for notifications
                if zone.current_moisture is not None and zone.duration == 0 and zone.current_moisture >= zone.target_moisture_max:
                    moisture_skipped_zones.append(zone)
                elif zone.moisture_reduction < 1.0 and zone.duration > 0:
                    moisture_reduced_zones.append(zone)

        # If all zones ended up with 0 duration → nothing to water
        if total_duration == 0:
            self.scheduled_run = None
            self.recheck_scheduled = None
            if moisture_skipped_zones:
                self.schedule_reason = self._txt(
                    "moisture_too_high",
                    moisture=moisture_skipped_zones[0].current_moisture,
                    target_max=moisture_skipped_zones[0].target_moisture_max,
                )
            else:
                self.schedule_reason = self._txt("no_water_needed")
            self._setup_daily_report()
            return

        # Calculate start and end times
        sunrise = self.forecast[day_index].sunrise
        start_time = sunrise - timedelta(minutes=total_duration + sunrise_offset)
        end_time = start_time + timedelta(minutes=total_duration)
        
        self.scheduled_run = start_time
        self.schedule_reason = ""
        self._setup_daily_report()  # re-register in case hour changed in options
        
        _LOGGER.info(
            "Watering scheduled: Start=%s, End=%s, Duration=%.1f min",
            start_time.strftime("%Y-%m-%d %H:%M"),
            end_time.strftime("%Y-%m-%d %H:%M"),
            total_duration,
        )
        
        # Schedule recheck if configured
        recheck_minutes = self.entry.data.get(CONF_RECHECK_TIME, 0)
        if recheck_minutes > 0:
            recheck_time = start_time - timedelta(minutes=recheck_minutes)
            if recheck_time > dt_util.now():
                self.recheck_scheduled = recheck_time
                _LOGGER.info("Recheck scheduled for %s", recheck_time.strftime("%Y-%m-%d %H:%M"))
                return

        self.recheck_scheduled = None

    async def _calculate_zone_duration(
        self, zone: ZoneData, day_index: int
    ) -> float:
        """Calculate watering duration for a zone in minutes."""
        if not zone.enabled:
            zone.skip_reason = self._txt("zone_disabled")
            return 0
        
        # Check if this is a valid watering day
        forecast_day = self.forecast[day_index]
        weekday = WEEKDAYS[forecast_day.sunrise.weekday()]
        month = forecast_day.sunrise.month
        
        if weekday not in zone.weekdays:
            _LOGGER.debug("Zone '%s': Not scheduled for this day", zone.name)
            zone.skip_reason = self._txt("no_watering_day", weekday=weekday)
            return 0
        
        if month not in zone.months:
            _LOGGER.debug("Zone '%s': Not scheduled for this month", zone.name)
            zone.skip_reason = self._txt("no_watering_month")
            return 0
        
        if not zone.adaptive:
            # Non-adaptive mode: use default duration
            _LOGGER.debug("Zone '%s': Non-adaptive, using default", zone.name)
            zone.skip_reason = ""
            return zone.max_duration / 2  # Use half of max as default
        
        # Calculate days until next watering
        days_until_next = 1
        for future_day in range(1, 8):
            if day_index + future_day >= len(self.forecast):
                break
            future_forecast = self.forecast[day_index + future_day]
            future_weekday = WEEKDAYS[future_forecast.sunrise.weekday()]
            if future_weekday in zone.weekdays:
                days_until_next = future_day
                break

        zone.days_until_next = days_until_next
        
        # Calculate total ETo and rain until next watering
        eto_total = 0
        rain_total = 0
        
        for day_offset in range(days_until_next):
            if day_index + day_offset >= len(self.forecast):
                break
            day_forecast = self.forecast[day_index + day_offset]
            eto_total += day_forecast.eto
            rain_total += day_forecast.rain
        
        zone.eto_total = eto_total
        zone.rain_total = rain_total
        
        # Calculate water needed
        water_needed = eto_total
        
        if zone.rain_factoring:
            water_needed -= rain_total
            if water_needed < 0:
                water_needed = 0
            
            # Check rain threshold for today
            if self.forecast[day_index].rain >= zone.rain_threshold:
                _LOGGER.debug(
                    "Zone '%s': Rain threshold exceeded (%.1f mm), skipping",
                    zone.name,
                    self.forecast[day_index].rain,
                )
                zone.skip_reason = self._txt(
                    "rain_threshold_exceeded",
                    rain=self.forecast[day_index].rain,
                    threshold=zone.rain_threshold,
                )
                return 0
        
        # ── Soil moisture check: skip or reduce if soil is already wet ──
        moisture_reduction = 1.0  # 1.0 = no reduction, 0.0 = full skip
        if zone.soil_moisture_entity:
            current = self.feedback_collector.read_soil_moisture(zone.soil_moisture_entity)
            zone.current_moisture = current
            if current is not None:
                _LOGGER.debug(
                    "Zone '%s': soil moisture = %.1f%% (target: %d–%d%%)",
                    zone.name, current, zone.target_moisture_min, zone.target_moisture_max,
                )
                if current >= zone.target_moisture_max:
                    # Soil is wet enough (or too wet) → skip watering entirely
                    zone.skip_reason = self._txt(
                        "moisture_too_high",
                        moisture=current,
                        target_max=zone.target_moisture_max,
                    )
                    _LOGGER.info(
                        "Zone '%s': SKIPPED – soil moisture %.0f%% >= target_max %d%%",
                        zone.name, current, zone.target_moisture_max,
                    )
                    zone.water_needed = 0
                    zone.duration_uncapped = 0
                    return 0
                elif current > zone.target_moisture_min:
                    # Soil is in the target range → proportionally reduce
                    moisture_range = zone.target_moisture_max - zone.target_moisture_min
                    if moisture_range > 0:
                        excess = current - zone.target_moisture_min
                        moisture_reduction = max(0.0, 1.0 - (excess / moisture_range))
                    _LOGGER.info(
                        "Zone '%s': soil moisture %.0f%% in target range → "
                        "duration reduced to %.0f%%",
                        zone.name, current, moisture_reduction * 100,
                    )

        # Apply crop and zone factors
        water_needed = (
            water_needed
            * zone.crop_coef
            * zone.plant_density
            * zone.exposure_factor
            * zone.area
        )

        # Apply user tweak factor (e.g. 110% for slightly more water)
        water_needed = water_needed * max(10, float(zone.adjustment_percent)) / 100.0

        # Apply soil moisture learning correction factor
        if zone.learning_enabled and zone.soil_moisture_entity:
            learning_factor = self.feedback_collector.get_correction_factor(zone.zone_id)
            water_needed = water_needed * learning_factor
            zone.learning_correction = learning_factor
            zone.learning_confidence = self.feedback_collector.get_confidence(zone.zone_id)
        
        # Adjust for efficiency
        water_needed = water_needed * 100 / zone.efficiency

        # Apply soil moisture reduction (if sensor shows soil partially wet)
        if moisture_reduction < 1.0:
            water_needed = water_needed * moisture_reduction
        zone.moisture_reduction = moisture_reduction
        
        zone.water_needed = water_needed

        # Calculate duration in minutes
        # Water needed is in liters (mm * m² = liters)
        # Flow rate is in L/h per emitter
        total_flow_rate = zone.flow_rate * zone.emitter_count  # L/h

        if total_flow_rate > 0:
            duration = (water_needed * 60) / total_flow_rate  # minutes for ALL water in one pass
        else:
            duration = 0

        # Divide by cycles: each cycle delivers 1/N of the total water (cycle-and-soak principle)
        cycles = max(1, int(self.entry.data.get(CONF_CYCLES, DEFAULT_CYCLES)))
        duration = duration / cycles

        zone.duration_uncapped = duration  # per-cycle duration before max_duration cap

        # Limit to max duration per cycle
        capped = duration > zone.max_duration
        if capped:
            duration = zone.max_duration

        if duration == 0:
            zone.skip_reason = self._txt("no_water_needed")
        elif moisture_reduction < 1.0:
            zone.skip_reason = self._txt(
                "moisture_reduced",
                moisture=zone.current_moisture,
                reduction=(1.0 - moisture_reduction) * 100,
            )
        else:
            zone.skip_reason = ""

        _LOGGER.info(
            "Zone '%s': ETo=%.2f mm (%d Tage), Regen=%.2f mm, Bedarf=%.1f L, "
            "Dauer=%.1f%s min/Zyklus x%d [flow=%.1f L/h, effiz=%d%%, feuchte=%s%%, reduktion=%.0f%%]",
            zone.name,
            eto_total,
            days_until_next,
            rain_total,
            water_needed,
            duration,
            f" (begrenzt, unkappiert={zone.duration_uncapped:.1f})" if capped else "",
            cycles,
            total_flow_rate,
            zone.efficiency,
            f"{zone.current_moisture:.0f}" if zone.current_moisture is not None else "–",
            (1.0 - moisture_reduction) * 100,
        )

        return duration

    async def _check_schedule(self, now):
        """Check if it's time to start watering or recheck."""
        if not self.entry.data.get(CONF_MASTER_ENABLED, DEFAULT_MASTER_ENABLED):
            return

        # Check for recheck
        if self.recheck_scheduled and now >= self.recheck_scheduled:
            _LOGGER.info("Running scheduled recheck")
            self.recheck_scheduled = None
            await self._async_calculate_schedule()
            return
        
        # Check for watering start
        if self.scheduled_run and now >= self.scheduled_run:
            _LOGGER.info("Starting scheduled watering")
            await self._start_watering()

    async def _start_watering(self):
        """Start the watering cycle."""
        if not self.entry.data.get(CONF_MASTER_ENABLED, DEFAULT_MASTER_ENABLED):
            _LOGGER.info("Skipping watering start because master switch is disabled")
            return

        if self._watering_task and not self._watering_task.done():
            _LOGGER.warning("Watering already in progress")
            return
        
        self._watering_task = asyncio.create_task(self._run_watering_cycle())

    async def _run_watering_cycle(self):
        """Run the complete watering cycle for all zones."""
        cycles = int(self.entry.data.get(CONF_CYCLES, 2))
        self._watering_started_at = dt_util.now()
        _LOGGER.info("Starting watering cycle (1/%d)", cycles)
        
        try:
            for cycle in range(cycles):
                if cycle > 0:
                    _LOGGER.info("Starting watering cycle (%d/%d)", cycle + 1, cycles)
                
                for zone in self.zones:
                    if zone.enabled and zone.duration > 0:
                        await self._water_zone(zone)
            
            _LOGGER.info("Watering cycle completed")
            finished_at = dt_util.now()

            # Build rich completion notification
            actual_min = (finished_at - self._watering_started_at).total_seconds() / 60
            zone_lines = self._format_zone_lines("\u2705")

            if self.recheck_scheduled:
                next_calc = self._txt(
                    "next_recalc_before_run",
                    when=self._fmt_dt(self.recheck_scheduled),
                )
            else:
                next_calc = self._txt(
                    "no_extra_recalc_before_run",
                    minutes=UPDATE_INTERVAL_MINUTES,
                )

            message = (
                f"{self._txt('start')}: {self._fmt_dt(self._watering_started_at)}\n"
                f"{self._txt('end')}:  {self._fmt_dt(finished_at)}\n"
                f"{self._txt('total_duration')}: {self._fmt_duration(actual_min)} min.\n\n"
                f"{zone_lines}\n\n"
                f"{next_calc}\n\n"
                f"{self._format_weather_footer()}"
            )
            await self._send_pushover_notification(
                self._txt("title_watering_done"), message, priority=0
            )

            # Update last run times
            for zone in self.zones:
                if zone.enabled and zone.duration > 0:
                    zone.last_run = dt_util.now()
            
            await self._async_save_storage()
            
            # Clear schedule and recalculate
            self.scheduled_run = None
            await self._async_calculate_schedule()
            
        except Exception as err:
            _LOGGER.error("Error during watering cycle: %s", err)
            await self._send_pushover_notification(
                self._txt("title_watering_error"),
                self._txt("watering_error", error=err),
                priority=0
            )

    async def _water_zone(self, zone: ZoneData):
        """Water a single zone."""
        _LOGGER.info("Starting zone '%s' for %.1f minutes", zone.name, zone.duration)

        # Safety net: re-check soil moisture before actually opening the valve
        if zone.soil_moisture_entity:
            current = self.feedback_collector.read_soil_moisture(zone.soil_moisture_entity)
            if current is not None and current >= zone.target_moisture_max:
                _LOGGER.info(
                    "Zone '%s': SKIPPED at valve time – moisture %.0f%% >= %d%%",
                    zone.name, current, zone.target_moisture_max,
                )
                zone.skip_reason = self._txt(
                    "moisture_too_high",
                    moisture=current,
                    target_max=zone.target_moisture_max,
                )
                zone.current_moisture = current
                return
        
        zone.is_running = True
        zone.started_at = dt_util.now()
        zone_planned_duration = zone.duration
        
        # Read soil moisture BEFORE watering (for learning)
        moisture_before = None
        if zone.learning_enabled and zone.soil_moisture_entity:
            moisture_before = self.feedback_collector.read_soil_moisture(zone.soil_moisture_entity)
            if moisture_before is not None:
                _LOGGER.debug(
                    "Zone '%s': soil moisture before watering = %.1f%%",
                    zone.name, moisture_before,
                )
        
        # Turn on the actual switch/valve entity
        if zone.switch_entity:
            try:
                await self.hass.services.async_call(
                    "homeassistant", "turn_on",
                    {"entity_id": zone.switch_entity},
                    blocking=True,
                )
                _LOGGER.info(
                    "Turned ON entity '%s' for zone '%s'",
                    zone.switch_entity, zone.name,
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to turn on entity '%s': %s",
                    zone.switch_entity, err,
                )
                zone.is_running = False
                zone.started_at = None
                self.async_set_updated_data(self.data)
                return
        else:
            _LOGGER.warning("Zone '%s' has no switch entity configured", zone.name)
        
        # Notify entities to update
        self.async_set_updated_data(self.data)
        
        # Wait for duration
        try:
            await asyncio.sleep(zone_planned_duration * 60)
        finally:
            ts_end = dt_util.now()
            # Log history entry
            if zone.started_at:
                actual_min = round((ts_end - zone.started_at).total_seconds() / 60, 1)
                self._log_zone_run(zone, zone.started_at, ts_end, zone_planned_duration, actual_min)

            # Schedule soil moisture feedback reading (learning)
            if zone.learning_enabled and zone.soil_moisture_entity:
                self.feedback_collector.schedule_feedback(
                    zone_id=zone.zone_id,
                    moisture_entity=zone.soil_moisture_entity,
                    moisture_before=moisture_before,
                    watering_duration=zone_planned_duration,
                    target_min=zone.target_moisture_min,
                    target_max=zone.target_moisture_max,
                    eto_total=zone.eto_total,
                    rain_total=zone.rain_total,
                )

            # Always turn off when done (even if cancelled)
            if zone.switch_entity:
                try:
                    await self.hass.services.async_call(
                        "homeassistant", "turn_off",
                        {"entity_id": zone.switch_entity},
                        blocking=True,
                    )
                    _LOGGER.info(
                        "Turned OFF entity '%s' for zone '%s'",
                        zone.switch_entity, zone.name,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed to turn off entity '%s': %s",
                        zone.switch_entity, err,
                    )
            
            zone.is_running = False
            zone.started_at = None
            _LOGGER.info("Zone '%s' finished", zone.name)
            
            # Notify entities to update
            self.async_set_updated_data(self.data)

    async def async_start_zone_manual(self, zone_id: int, duration: int):
        """Manually start a zone (non-blocking)."""
        zone = next((z for z in self.zones if z.zone_id == zone_id), None)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")

        if not self.entry.data.get(CONF_MASTER_ENABLED, DEFAULT_MASTER_ENABLED):
            raise ValueError(self._txt("master_blocked_manual_start"))
        
        # Cancel existing manual task for this zone if any
        if zone_id in self._manual_zone_tasks:
            existing = self._manual_zone_tasks.pop(zone_id)
            if not existing.done():
                existing.cancel()
        
        _LOGGER.info("Manual start of zone '%s' for %d minutes", zone.name, duration)
        zone.duration = duration

        await self._send_pushover_notification(
            self._txt("title_manual_start"),
            self._txt(
                "manual_zone_started",
                zone=zone.name,
                duration=self._fmt_duration(duration),
            ),
            priority=-1,
        )

        # Run in background so the API can respond immediately
        task = asyncio.create_task(self._water_zone_manual(zone))
        self._manual_zone_tasks[zone_id] = task

    async def _water_zone_manual(self, zone: ZoneData):
        """Wrapper around _water_zone that sends a summary notification when done."""
        started = dt_util.now()
        try:
            await self._water_zone(zone)
        except asyncio.CancelledError:
            pass
        finally:
            ended = dt_util.now()
            actual_min = (ended - started).total_seconds() / 60
            await self._send_pushover_notification(
                self._txt("title_manual_done"),
                self._txt(
                    "manual_zone_stopped",
                    zone=zone.name,
                    duration=self._fmt_duration(actual_min),
                    start=self._fmt_dt(started),
                    end=self._fmt_dt(ended),
                ),
                priority=-1,
            )

    async def async_stop_zone(self, zone_id: int):
        """Stop a running zone."""
        zone = next((z for z in self.zones if z.zone_id == zone_id), None)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")
        
        # Cancel the background task – its finally-block will turn off the entity
        if zone_id in self._manual_zone_tasks:
            task = self._manual_zone_tasks.pop(zone_id)
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        
        if zone.is_running:
            _LOGGER.info("Stopping zone '%s'", zone.name)
            zone.is_running = False
            
            # Turn off the actual switch/valve entity (safety fallback)
            if zone.switch_entity:
                try:
                    await self.hass.services.async_call(
                        "homeassistant", "turn_off",
                        {"entity_id": zone.switch_entity},
                        blocking=True,
                    )
                    _LOGGER.info("Turned off entity '%s' for zone '%s'", zone.switch_entity, zone.name)
                except Exception as err:
                    _LOGGER.error("Failed to turn off entity '%s': %s", zone.switch_entity, err)
            
            self.async_set_updated_data(self.data)

    async def async_stop_all_watering(self) -> None:
        """Immediately stop all running watering tasks and entities."""
        if self._watering_task and not self._watering_task.done():
            self._watering_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._watering_task), timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        active_manual_tasks = list(self._manual_zone_tasks.items())
        self._manual_zone_tasks.clear()
        for _zone_id, task in active_manual_tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

        for zone in self.zones:
            if not zone.is_running:
                continue
            zone.is_running = False
            zone.started_at = None
            if zone.switch_entity:
                try:
                    await self.hass.services.async_call(
                        "homeassistant",
                        "turn_off",
                        {"entity_id": zone.switch_entity},
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "Failed emergency stop for entity '%s': %s",
                        zone.switch_entity,
                        err,
                    )

        self._watering_started_at = None
        self.async_set_updated_data(self.data)

    async def async_set_master_enabled(self, enabled: bool) -> None:
        """Persist and apply the global master irrigation switch."""
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, CONF_MASTER_ENABLED: enabled},
        )
        self.entry = self.hass.config_entries.async_get_entry(self.entry.entry_id) or self.entry

        if enabled:
            await self._send_pushover_notification(
                self._txt("title_master_on"),
                self._txt("master_enabled_message"),
                priority=0,
                force=True,
            )
            if self.forecast:
                await self._async_calculate_schedule()
            else:
                await self.async_request_refresh()
        else:
            await self.async_stop_all_watering()
            self.scheduled_run = None
            self.recheck_scheduled = None
            self.schedule_reason = self._txt("master_disabled")
            for zone in self.zones:
                zone.duration = 0
            self.async_set_updated_data(self.data)
            await self._send_pushover_notification(
                self._txt("title_master_off"),
                self._txt("master_disabled_message"),
                priority=1,
                force=True,
            )

    async def async_set_pushover_enabled(self, enabled: bool) -> None:
        """Persist and apply the Pushover notification switch."""
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, CONF_PUSHOVER_ENABLED: enabled},
        )
        self.entry = self.hass.config_entries.async_get_entry(self.entry.entry_id) or self.entry
        await self._send_pushover_notification(
            self._txt("title_pushover_on" if enabled else "title_pushover_off"),
            self._txt(
                "pushover_enabled_message" if enabled else "pushover_disabled_message"
            ),
            priority=0,
            force=True,
        )
        self.async_set_updated_data(self.data)

    # ------------------------------------------------------------------
    # Notification helpers
    # ------------------------------------------------------------------

    def _lang(self) -> str:
        """Return configured UI/notification language."""
        language = self.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        return language if language in ("de", "en") else DEFAULT_LANGUAGE

    def _txt(self, key: str, **kwargs: Any) -> str:
        """Return localized backend text."""
        text = _TEXT[self._lang()].get(key, key)
        return text.format(**kwargs) if kwargs else text

    def _weekday_name(self, weekday_index: int) -> str:
        """Return localized weekday name."""
        return _WEEKDAY_NAMES[self._lang()][weekday_index]

    def _weather_condition_text(self, raw_condition: str) -> str:
        """Return localized weather condition string."""
        language = self._lang()
        return _WEATHER_CONDITION_TEXT[language].get(raw_condition.lower(), raw_condition)

    @staticmethod
    def _fmt_duration(minutes: float) -> str:
        """Format minutes as MM:SS string (e.g. 06:42)."""
        total_sec = int(round(minutes * 60))
        return f"{total_sec // 60:02d}:{total_sec % 60:02d}"

    def _format_zone_lines(self, prefix: str = "\u2022") -> str:
        """Format per-zone watering times for a notification message."""
        cycles = int(self.entry.data.get(CONF_CYCLES, 2))
        lines = []
        for z in self.zones:
            if not z.enabled:
                continue
            if z.duration > 0:
                total = self._fmt_duration(z.duration * cycles)
                per_c = self._fmt_duration(z.duration)
                lines.append(
                    f"{prefix} {z.name}: {total} min.  ({cycles}\u00d7 {per_c} min.)"
                )
            elif z.skip_reason:
                lines.append(f"\u23ed {z.name}: {z.skip_reason}")
        return "\n".join(lines) if lines else self._txt("no_zones_configured")

    def _format_weather_footer(self) -> str:
        """Build a compact weather summary block for notifications."""
        if not self.forecast:
            return ""
        try:
            d = self.forecast[0]
            day_name = self._weekday_name(d.sunrise.weekday()) if d.sunrise else ""
            raw_condition = (d.condition or d.summary or "").strip()
            condition = self._weather_condition_text(raw_condition)
            clouds = f"{d.clouds:.0f}" if d.clouds is not None else "?"
            sunrise_str = d.sunrise.strftime("%H:%M") if d.sunrise else "?"
            humidity = d.humidity if d.humidity is not None else 0
            min_t = d.min_temp if d.min_temp is not None else 0
            max_t = d.max_temp if d.max_temp is not None else 0
            pressure = d.pressure if d.pressure is not None else 0
            wind = d.wind_speed if d.wind_speed is not None else 0
            rain = d.rain if d.rain is not None else 0
            eto = d.eto if d.eto is not None else 0
            return self._txt(
                "weather_footer",
                day=day_name,
                condition=condition,
                clouds=clouds,
                sunrise=sunrise_str,
                humidity=humidity,
                min_temp=min_t,
                max_temp=max_t,
                pressure=pressure,
                wind=wind,
                rain=rain,
                eto=eto,
            )
        except Exception as err:
            _LOGGER.warning("Failed to format weather footer: %s", err)
            return ""

    def _fmt_dt(self, dt: datetime) -> str:
        """Format datetime as 'Wochentag DD.MM.YYYY, HH:MM Uhr'."""
        local = dt.astimezone(dt_util.now().tzinfo)
        suffix = " Uhr" if self._lang() == "de" else ""
        return f"{self._weekday_name(local.weekday())} {local.strftime('%d.%m.%Y, %H:%M')}{suffix}"

    # ------------------------------------------------------------------

    def _setup_daily_report(self) -> None:
        """Register (or re-register) the daily morning report timer."""
        if self._daily_report_unsub:
            self._daily_report_unsub()
            self._daily_report_unsub = None
        if not self.entry.data.get(CONF_DAILY_REPORT_ENABLED, DEFAULT_DAILY_REPORT_ENABLED):
            return
        hour = int(self.entry.data.get(CONF_DAILY_REPORT_HOUR, DEFAULT_DAILY_REPORT_HOUR))
        self._daily_report_unsub = async_track_time_change(
            self.hass, self._async_send_daily_report, hour=hour, minute=0, second=5,
        )
        _LOGGER.debug("Daily report scheduled at %02d:00", hour)

    async def _async_send_daily_report(self, _now=None) -> None:
        """Send the daily morning report (geplant or keine Bewässerung) with full weather data."""
        cycles = int(self.entry.data.get(CONF_CYCLES, 2))
        weather = self._format_weather_footer()

        if self.scheduled_run:
            total_min = sum(
                z.duration * cycles for z in self.zones if z.enabled and z.duration > 0
            )
            end_time = self.scheduled_run + timedelta(minutes=total_min)
            zone_lines = self._format_zone_lines("\U0001f331")

            if self.recheck_scheduled:
                recheck_str = self._txt(
                    "extra_recalc_before_start",
                    when=self._fmt_dt(self.recheck_scheduled),
                )
            else:
                recheck_str = self._txt(
                    "no_extra_recalc_before_start",
                    minutes=UPDATE_INTERVAL_MINUTES,
                )

            message = (
                f"{self._txt('start')}: {self._fmt_dt(self.scheduled_run)}\n"
                f"{self._txt('end')}:  {self._fmt_dt(end_time)}\n"
                f"{self._txt('total_duration')}: {self._fmt_duration(total_min)} min.\n\n"
                f"{zone_lines}\n\n"
                f"{recheck_str}\n\n"
                f"{weather}"
            )
            await self._send_pushover_notification(
                self._txt("title_plan_today"), message, priority=-1
            )
        else:
            reason = self.schedule_reason or self._txt("no_water_needed")

            if self.recheck_scheduled:
                next_calc = self._txt(
                    "next_extra_recalc",
                    when=self._fmt_dt(self.recheck_scheduled),
                    minutes=UPDATE_INTERVAL_MINUTES,
                )
            else:
                next_calc = self._txt(
                    "no_extra_recalc_today",
                    minutes=UPDATE_INTERVAL_MINUTES,
                )

            message = (
                f"{self._txt('no_schedule_set')}:\n\u203a {reason}\n\n"
                f"{next_calc}\n\n"
                f"{weather}"
            )
            await self._send_pushover_notification(
                self._txt("title_no_watering_today"), message, priority=-2
            )

    def _log_zone_run(
        self,
        zone: ZoneData,
        ts_start: datetime,
        ts_end: datetime,
        planned_min: float,
        actual_min: float,
    ) -> None:
        """Append a zone-run event to history and persist."""
        self.history.append({
            "type": "zone_run",
            "date": ts_start.strftime("%Y-%m-%d"),
            "ts_start": ts_start.isoformat(),
            "ts_end": ts_end.isoformat(),
            "duration_planned": round(planned_min, 1),
            "duration_actual": round(actual_min, 1),
            "zone_id": zone.zone_id,
            "zone_name": zone.name,
            "eto": round(zone.eto_total, 2),
            "rain": round(zone.rain_total, 2),
            "water_needed": round(zone.water_needed, 2),
            "switch_entity": zone.switch_entity or "",
        })
        if len(self.history) > 180:
            self.history = self.history[-180:]
        # Async-safe fire-and-forget save
        self.hass.async_create_task(self._async_save_storage())

    def _log_skip_event(self, reason: str, forecast_day) -> None:
        """Append a skip event to history (deduplicated by date)."""
        date_str = forecast_day.sunrise.strftime("%Y-%m-%d")
        # Never log twice for the same date and type
        if any(
            e.get("date") == date_str and e.get("type") in ("skip", "no_water")
            for e in self.history[-20:]
        ):
            return
        event_type = "skip"
        if any(token in reason for token in (
            "Kein Wasserbedarf",
            "No watering needed",
            "Regen gedeckt",
            "covered by rain",
        )):
            event_type = "no_water"
        self.history.append({
            "type": event_type,
            "date": date_str,
            "ts": dt_util.now().isoformat(),
            "reason": reason,
            "eto": round(forecast_day.eto, 2),
            "rain": round(forecast_day.rain, 2),
            "min_temp": round(forecast_day.min_temp, 1),
            "max_temp": round(forecast_day.max_temp, 1),
        })
        if len(self.history) > 180:
            self.history = self.history[-180:]
        self.hass.async_create_task(self._async_save_storage())

    async def async_set_zone_enabled(self, zone_id: int, enabled: bool) -> None:
        """Enable or disable a zone and recalculate schedule."""
        zone = next((z for z in self.zones if z.zone_id == zone_id), None)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")
        
        zone.enabled = enabled
        _LOGGER.info("Zone '%s' %s", zone.name, "aktiviert" if enabled else "deaktiviert")
        
        if self.forecast:
            await self._async_calculate_schedule()
        self.async_set_updated_data(self.data)

    async def async_reset_learning(self, zone_id: int | None = None) -> None:
        """Reset learning data for a zone (or all zones if zone_id is None)."""
        if zone_id is not None:
            await self.feedback_collector.async_reset_zone(zone_id)
            zone = next((z for z in self.zones if z.zone_id == zone_id), None)
            if zone:
                zone.learning_correction = 1.0
                zone.learning_confidence = 0
        else:
            await self.feedback_collector.async_reset_all()
            for zone in self.zones:
                zone.learning_correction = 1.0
                zone.learning_confidence = 0
        self.async_set_updated_data(self.data)

    async def async_test_schedule(self) -> dict:
        """Simulate schedule with spoofed hot/dry weather (read-only, does not modify real state)."""
        lat = self.hass.config.latitude
        alt = self.hass.config.elevation
        solar_rad = 8.0  # Peak summer solar radiation kWh/m²/day

        # Build 8 fake days: hot, dry summer
        fake_forecast: list[WeatherData] = []
        now = dt_util.now()
        for i in range(8):
            day = WeatherData()
            day.sunrise = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=i)
            day.min_temp = 18.0
            day.max_temp = 35.0
            day.humidity = 30.0
            day.pressure = 1013.0
            day.wind_speed = 4.0
            day.rain = 0.0
            day.condition = "sunny"
            day.summary = "Sunny"
            day.eto = calculate_eto(
                min_temp=day.min_temp,
                max_temp=day.max_temp,
                humidity=day.humidity,
                pressure=day.pressure,
                wind_speed=day.wind_speed,
                solar_radiation=solar_rad,
                altitude=alt,
                latitude=lat,
                date=day.sunrise,
            )
            fake_forecast.append(day)

        # Temporarily replace forecast for duration calculations
        real_forecast = self.forecast
        self.forecast = fake_forecast

        cycles = int(self.entry.data.get(CONF_CYCLES, 2))
        sunrise_offset = self.entry.data.get(CONF_SUNRISE_OFFSET, 0)

        zone_results = []
        total_duration = 0.0
        try:
            for zone in self.zones:
                if zone.enabled:
                    duration = await self._calculate_zone_duration(zone, 0)
                    zone_results.append({
                        "zone_id": zone.zone_id,
                        "name": zone.name,
                        "duration": round(duration, 1),
                        "skip_reason": getattr(zone, "skip_reason", ""),
                    })
                    total_duration += duration * cycles
                else:
                    zone_results.append({
                        "zone_id": zone.zone_id,
                        "name": zone.name,
                        "duration": 0,
                        "skip_reason": self._txt("zone_disabled"),
                    })
        finally:
            self.forecast = real_forecast

        scheduled_would_be = None
        schedule_reason = ""
        if total_duration > 0:
            sunrise = fake_forecast[0].sunrise
            start_time = sunrise - timedelta(minutes=total_duration + sunrise_offset)
            if start_time < now:
                sunrise = fake_forecast[1].sunrise
                start_time = sunrise - timedelta(minutes=total_duration + sunrise_offset)
            scheduled_would_be = start_time.isoformat()
        else:
            schedule_reason = self._txt("no_water_needed")

        return {
            "zones": zone_results,
            "total_duration_minutes": round(total_duration, 1),
            "cycles": cycles,
            "scheduled_would_be": scheduled_would_be,
            "schedule_reason": schedule_reason,
            "fake_weather": {
                "max_temp": 35,
                "min_temp": 18,
                "humidity": 30,
                "wind": 4.0,
                "rain": 0,
                "eto": round(fake_forecast[0].eto, 2),
            },
        }

    async def _async_load_storage(self):
        """Load stored data."""
        if self._storage is None:
            self._storage = Store(self.hass, STORAGE_VERSION, STORAGE_KEY)
        
        data = await self._storage.async_load()
        
        if data:
            # Restore last run times
            for zone_data in data.get("zones", []):
                zone = next(
                    (z for z in self.zones if z.zone_id == zone_data["zone_id"]), None
                )
                if zone and zone_data.get("last_run"):
                    zone.last_run = dt_util.parse_datetime(zone_data["last_run"])
                    _LOGGER.debug(
                        "Restored last run for zone '%s': %s",
                        zone.name,
                        zone.last_run,
                    )
            # Restore history
            self.history = data.get("history", [])

    async def _async_save_storage(self):
        """Save data to storage."""
        if self._storage is None:
            self._storage = Store(self.hass, STORAGE_VERSION, STORAGE_KEY)
        
        data = {
            "zones": [
                {
                    "zone_id": zone.zone_id,
                    "last_run": zone.last_run.isoformat() if zone.last_run else None,
                }
                for zone in self.zones
            ],
            "history": self.history[-180:],
        }
        
        await self._storage.async_save(data)

    async def _send_pushover_notification(
        self,
        title: str,
        message: str,
        priority: int = 0,
        force: bool = False,
        test_mode: bool = False,
    ):
        """Send notification directly via Pushover API (no HA notify service needed).
        
        Args:
            test_mode: If True, raises on error for frontend feedback.
                      If False, only logs errors.
        """
        if not force and not self.entry.data.get(CONF_PUSHOVER_ENABLED, False):
            return

        api_token = self.entry.data.get(CONF_PUSHOVER_API_TOKEN)
        if not api_token:
            msg = "No Pushover API token configured"
            if test_mode:
                raise ValueError(msg)
            _LOGGER.warning(msg)
            return

        user_key = self.entry.data.get(CONF_PUSHOVER_USER_KEY)
        if not user_key:
            msg = "No Pushover user key configured"
            if test_mode:
                raise ValueError(msg)
            _LOGGER.warning(msg)
            return

        # Pushover API endpoint
        api_url = "https://api.pushover.net/1/messages.json"
        
        payload = {
            "token": api_token,
            "user": user_key,
            "title": title,
            "message": message,
            "priority": priority,
        }

        # Add device if specified
        device = self.entry.data.get(CONF_PUSHOVER_DEVICE)
        if device:
            payload["device"] = device

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("status") == 1:
                            _LOGGER.debug("Pushover notification sent: %s", title)
                            return
                        else:
                            errors = result.get("errors", ["Unknown error"])
                            msg = f"Pushover API error: {', '.join(errors)}"
                            if test_mode:
                                raise RuntimeError(msg)
                            _LOGGER.error(msg)
                            return
                    else:
                        msg = f"Pushover HTTP {resp.status}: {await resp.text()}"
                        if test_mode:
                            raise RuntimeError(msg)
                        _LOGGER.error(msg)
                        return

        except aiohttp.ClientError as err:
            msg = f"Pushover connection error: {err}"
            if test_mode:
                raise RuntimeError(msg) from err
            _LOGGER.error(msg)
        except Exception as err:
            msg = f"Pushover error: {err}"
            if test_mode:
                raise RuntimeError(msg) from err
            _LOGGER.error(msg)

    async def async_shutdown(self):
        """Shutdown coordinator."""
        if self._schedule_checker_unsub:
            self._schedule_checker_unsub()

        if self._daily_report_unsub:
            self._daily_report_unsub()

        # Cancel any pending soil moisture feedback timers
        self.feedback_collector.cancel_all_pending()

        if self._watering_task and not self._watering_task.done():
            self._watering_task.cancel()

        await self.weather_provider.async_close()
