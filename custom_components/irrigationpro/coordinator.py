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
    CONF_ZONE_AREA,
    CONF_ZONE_CROP_COEF,
    CONF_ZONE_EFFICIENCY,
    CONF_ZONE_EMITTER_COUNT,
    CONF_ZONE_ENABLED,
    CONF_ZONE_EXPOSURE_FACTOR,
    CONF_ZONE_FLOW_RATE,
    CONF_ZONE_MAX_DURATION,
    CONF_ZONE_MONTHS,
    CONF_ZONE_NAME,
    CONF_ZONE_PLANT_DENSITY,
    CONF_ZONE_RAIN_FACTORING,
    CONF_ZONE_RAIN_THRESHOLD,
    CONF_ZONE_SWITCH_ENTITY,
    CONF_ZONE_WEEKDAYS,
    CONF_ZONES,
    DEFAULT_SOLAR_RADIATION,
    DEFAULT_DAILY_REPORT_ENABLED,
    DEFAULT_DAILY_REPORT_HOUR,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL_MINUTES,
    WEEKDAYS,
)
from .eto import calculate_eto
from .weather_provider import WeatherData, WeatherProvider

_LOGGER = logging.getLogger(__name__)

_WEEKDAYS_DE = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
]

_WEATHER_CONDITION_DE = {
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
        self.switch_entity = config.get(CONF_ZONE_SWITCH_ENTITY)
        # Use CONF keys for weekdays and months with proper defaults
        self.weekdays = config.get(CONF_ZONE_WEEKDAYS, WEEKDAYS)
        self.months = config.get(CONF_ZONE_MONTHS, list(range(1, 13)))
        
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
        self.history: list[dict] = []  # Irrigation & skip history (max 180 entries)
        self.last_calculated: datetime | None = None  # When the schedule was last calculated
        self._daily_report_unsub = None
        self._watering_started_at: datetime | None = None
        
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

    async def async_config_entry_first_refresh(self):
        """Refresh data for the first time when config entry is setup."""
        # Load stored data
        await self._async_load_storage()
        
        # Perform first refresh
        await super().async_config_entry_first_refresh()
        
        # Calculate initial schedule
        await self._async_calculate_schedule()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from weather provider and calculate irrigation needs."""
        try:
            _LOGGER.debug("Updating weather data and calculating irrigation needs")
            
            # Get weather forecast
            self.forecast = await self.weather_provider.async_get_forecast(days=8)
            
            if not self.forecast:
                raise UpdateFailed("No forecast data available")
            
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
            
            return {
                "forecast": self.forecast,
                "zones": self.zones,
                "scheduled_run": self.scheduled_run,
            }
            
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}")

    async def _async_calculate_schedule(self):
        """Calculate watering schedule for all zones."""
        if not self.forecast:
            _LOGGER.warning("No forecast data available for scheduling")
            return
        
        _LOGGER.info("Calculating irrigation schedule")
        
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
            self.schedule_reason = (
                f"Temperatur zu niedrig (min: {forecast_day.min_temp:.1f}°C, "
                f"max: {forecast_day.max_temp:.1f}°C – Schwelle: {low_threshold}/{high_threshold}°C)"
            )
            self._log_skip_event(self.schedule_reason, forecast_day)
            return
        
        # Recalculate durations for the selected day
        total_duration = 0
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
        
        # Track when calculation happened for cases with no watering
        self.last_calculated = dt_util.now()
        
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

    async def _calculate_zone_duration(
        self, zone: ZoneData, day_index: int
    ) -> float:
        """Calculate watering duration for a zone in minutes."""
        if not zone.enabled:
            zone.skip_reason = "Zone deaktiviert"
            return 0
        
        # Check if this is a valid watering day
        forecast_day = self.forecast[day_index]
        weekday = WEEKDAYS[forecast_day.sunrise.weekday()]
        month = forecast_day.sunrise.month
        
        if weekday not in zone.weekdays:
            _LOGGER.debug("Zone '%s': Not scheduled for this day", zone.name)
            zone.skip_reason = f"Kein Bewässerungstag ({weekday})"
            return 0
        
        if month not in zone.months:
            _LOGGER.debug("Zone '%s': Not scheduled for this month", zone.name)
            zone.skip_reason = "Kein Bewässerungsmonat"
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
                zone.skip_reason = (
                    f"Regenschwelle überschritten "
                    f"({self.forecast[day_index].rain:.1f} mm >= {zone.rain_threshold} mm)"
                )
                return 0
        
        # Apply crop and zone factors
        water_needed = (
            water_needed
            * zone.crop_coef
            * zone.plant_density
            * zone.exposure_factor
            * zone.area
        )
        
        # Adjust for efficiency
        water_needed = water_needed * 100 / zone.efficiency
        
        zone.water_needed = water_needed
        
        # Calculate duration in minutes
        # Water needed is in liters (mm * m² = liters)
        # Flow rate is in L/h per emitter
        total_flow_rate = zone.flow_rate * zone.emitter_count  # L/h
        
        if total_flow_rate > 0:
            duration = (water_needed * 60) / total_flow_rate  # minutes
        else:
            duration = 0
        
        # Limit to max duration
        if duration > zone.max_duration:
            _LOGGER.debug(
                "Zone '%s': Limiting duration from %.1f to %.1f minutes",
                zone.name,
                duration,
                zone.max_duration,
            )
            duration = zone.max_duration
        
        if duration == 0:
            zone.skip_reason = "Kein Wasserbedarf (ETo durch Regen gedeckt)"
        else:
            zone.skip_reason = ""
        
        _LOGGER.debug(
            "Zone '%s': ETo=%.2f mm, Rain=%.2f mm, Water needed=%.2f L, Duration=%.1f min",
            zone.name,
            eto_total,
            rain_total,
            water_needed,
            duration,
        )
        
        return duration

    async def _check_schedule(self, now):
        """Check if it's time to start watering or recheck."""
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
                next_calc = (
                    f"Nächste Neuberechnung vor geplantem Lauf: "
                    f"{self._fmt_dt(self.recheck_scheduled)}"
                )
            else:
                next_calc = (
                    "Keine zusätzliche Neuberechnung vor einem geplanten Lauf.\n"
                    f"Reguläres Wetter-Update und Neuplanung alle "
                    f"{UPDATE_INTERVAL_MINUTES} Minuten."
                )

            message = (
                f"Start: {self._fmt_dt(self._watering_started_at)}\n"
                f"Ende:  {self._fmt_dt(finished_at)}\n"
                f"Gesamtdauer: {self._fmt_duration(actual_min)} min.\n\n"
                f"{zone_lines}\n\n"
                f"{next_calc}\n\n"
                f"{self._format_weather_footer()}"
            )
            await self._send_pushover_notification(
                "\u2705 Bew\u00e4sserung abgeschlossen", message, priority=0
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
                "\u274c Bew\u00e4sserungsfehler",
                f"Fehler beim Bew\u00e4ssern: {err}",
                priority=0
            )

    async def _water_zone(self, zone: ZoneData):
        """Water a single zone."""
        _LOGGER.info("Starting zone '%s' for %.1f minutes", zone.name, zone.duration)
        
        zone.is_running = True
        zone.started_at = dt_util.now()
        zone_planned_duration = zone.duration
        
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
        
        # Cancel existing manual task for this zone if any
        if zone_id in self._manual_zone_tasks:
            existing = self._manual_zone_tasks.pop(zone_id)
            if not existing.done():
                existing.cancel()
        
        _LOGGER.info("Manual start of zone '%s' for %d minutes", zone.name, duration)
        zone.duration = duration

        await self._send_pushover_notification(
            "\U0001f6bf Manuelle Bew\u00e4sserung",
            f"Zone \u00ab{zone.name}\u00bb manuell gestartet\n"
            f"Geplante Dauer: {self._fmt_duration(duration)} min.",
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
                "\u2705 Manuelle Bew\u00e4sserung beendet",
                f"Zone \u00ab{zone.name}\u00bb beendet\n"
                f"Laufzeit: {self._fmt_duration(actual_min)} min.\n"
                f"Start: {self._fmt_dt(started)}\n"
                f"Ende:  {self._fmt_dt(ended)}",
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

    # ------------------------------------------------------------------
    # Notification helpers
    # ------------------------------------------------------------------

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
            if z.enabled and z.duration > 0:
                total = self._fmt_duration(z.duration * cycles)
                per_c = self._fmt_duration(z.duration)
                lines.append(
                    f"{prefix} {z.name}: {total} min.  ({cycles}\u00d7 {per_c} min.)"
                )
        return "\n".join(lines) if lines else "Keine Zonen konfiguriert"

    def _format_weather_footer(self) -> str:
        """Build a compact weather summary block for notifications."""
        if not self.forecast:
            return ""
        try:
            d = self.forecast[0]
            day_name = _WEEKDAYS_DE[d.sunrise.weekday()] if d.sunrise else ""
            raw_condition = (d.condition or d.summary or "").strip()
            condition = _WEATHER_CONDITION_DE.get(raw_condition.lower(), raw_condition)
            clouds = f"{d.clouds:.0f}" if d.clouds is not None else "?"
            sunrise_str = d.sunrise.strftime("%H:%M") if d.sunrise else "?"
            humidity = d.humidity if d.humidity is not None else 0
            min_t = d.min_temp if d.min_temp is not None else 0
            max_t = d.max_temp if d.max_temp is not None else 0
            pressure = d.pressure if d.pressure is not None else 0
            wind = d.wind_speed if d.wind_speed is not None else 0
            rain = d.rain if d.rain is not None else 0
            eto = d.eto if d.eto is not None else 0
            return (
                "\u2500\u2500\u2500\n"
                f"{day_name}: {condition}, {clouds}% Wolken\n"
                f"Sonnenaufgang: {sunrise_str} Uhr | Luftfeuchte: {humidity:.0f}%\n"
                f"Temp.: {min_t:.1f}\u00b0C \u2013 {max_t:.1f}\u00b0C\n"
                f"Luftdruck: {pressure:.0f}\u202fhPa | Wind: {wind:.1f}\u202fm/s\n"
                f"Niederschlag: {rain:.2f}\u202fmm | ETo: {eto:.2f}\u202fmm"
            )
        except Exception as err:
            _LOGGER.warning("Failed to format weather footer: %s", err)
            return ""

    def _fmt_dt(self, dt: datetime) -> str:
        """Format datetime as 'Wochentag DD.MM.YYYY, HH:MM Uhr'."""
        local = dt.astimezone(dt_util.now().tzinfo)
        return f"{_WEEKDAYS_DE[local.weekday()]} {local.strftime('%d.%m.%Y, %H:%M')} Uhr"

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
                recheck_str = (
                    f"Zusätzliche Neuberechnung vor Start: "
                    f"{self._fmt_dt(self.recheck_scheduled)}"
                )
            else:
                recheck_str = (
                    "Keine zusätzliche Neuberechnung vor Start.\n"
                    f"Reguläres Wetter-Update und Neuplanung alle "
                    f"{UPDATE_INTERVAL_MINUTES} Minuten."
                )

            message = (
                f"Start: {self._fmt_dt(self.scheduled_run)}\n"
                f"Ende:  {self._fmt_dt(end_time)}\n"
                f"Gesamtdauer: {self._fmt_duration(total_min)} min.\n\n"
                f"{zone_lines}\n\n"
                f"{recheck_str}\n\n"
                f"{weather}"
            )
            await self._send_pushover_notification(
                "\U0001f5d3 Bew\u00e4sserung geplant", message, priority=-1
            )
        else:
            reason = self.schedule_reason or "Kein Bew\u00e4sserungsbedarf"

            if self.recheck_scheduled:
                next_calc = (
                    f"Nächste zusätzliche Neuberechnung:\n"
                    f"{self._fmt_dt(self.recheck_scheduled)}\n"
                    f"(zusätzlich zum regulären Update alle {UPDATE_INTERVAL_MINUTES} Minuten)"
                )
            else:
                next_calc = (
                    "Keine zusätzliche Neuberechnung für heute geplant.\n"
                    f"Automatische Neuplanung beim nächsten Wetter-Update "
                    f"(alle {UPDATE_INTERVAL_MINUTES} Minuten)."
                )

            message = (
                f"Kein Zeitplan gesetzt:\n\u203a {reason}\n\n"
                f"{next_calc}\n\n"
                f"{weather}"
            )
            await self._send_pushover_notification(
                "\U0001f4a4 Keine Bew\u00e4sserung heute", message, priority=-2
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
        if "Bewässerungsbedarf" in reason or "Regen gedeckt" in reason:
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
                        "skip_reason": "Zone deaktiviert / Zone disabled",
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
            schedule_reason = "Kein Bewässerungsbedarf / No watering needed"

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

        if self._watering_task and not self._watering_task.done():
            self._watering_task.cancel()

        await self.weather_provider.async_close()
