"""Coordinator for IrrigationPro integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.sun import get_astral_location
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CYCLES,
    CONF_HIGH_THRESHOLD,
    CONF_LOW_THRESHOLD,
    CONF_OWM_API_KEY,
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
    CONF_ZONE_AREA,
    CONF_ZONE_CROP_COEF,
    CONF_ZONE_EFFICIENCY,
    CONF_ZONE_EMITTER_COUNT,
    CONF_ZONE_ENABLED,
    CONF_ZONE_EXPOSURE_FACTOR,
    CONF_ZONE_FLOW_RATE,
    CONF_ZONE_MAX_DURATION,
    CONF_ZONE_PLANT_DENSITY,
    CONF_ZONE_RAIN_FACTORING,
    CONF_ZONE_RAIN_THRESHOLD,
    CONF_ZONES,
    DEFAULT_SOLAR_RADIATION,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL_MINUTES,
    WEEKDAYS,
)
from .eto import calculate_eto
from .weather_provider import WeatherData, WeatherProvider

_LOGGER = logging.getLogger(__name__)


class ZoneData:
    """Data for a single irrigation zone."""

    def __init__(self, zone_id: int, config: dict[str, Any]):
        """Initialize zone data."""
        self.zone_id = zone_id
        self.name = config.get("zone_name", f"Zone {zone_id}")
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
        self._storage: Store | None = None
        
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

    def _init_zones(self):
        """Initialize zones from configuration."""
        zones_config = self.entry.data.get(CONF_ZONES, [])
        self.zones = [
            ZoneData(i + 1, zone_config)
            for i, zone_config in enumerate(zones_config)
        ]
        _LOGGER.debug("Initialized %d zones", len(self.zones))

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
                solar_rad = solar_rad_data.get(month, 6.0)
                
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
        cycles = self.entry.data.get(CONF_CYCLES, 2)
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
        
        if total_duration == 0:
            _LOGGER.info("No watering needed")
            self.scheduled_run = None
            return
        
        # Calculate start and end times
        sunrise = self.forecast[day_index].sunrise
        start_time = sunrise - timedelta(minutes=total_duration + sunrise_offset)
        end_time = start_time + timedelta(minutes=total_duration)
        
        self.scheduled_run = start_time
        
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
            return 0
        
        # Check if this is a valid watering day
        forecast_day = self.forecast[day_index]
        weekday = WEEKDAYS[forecast_day.sunrise.weekday()]
        month = forecast_day.sunrise.month
        
        if weekday not in zone.weekdays or month not in zone.months:
            _LOGGER.debug("Zone '%s': Not scheduled for this day", zone.name)
            return 0
        
        if not zone.adaptive:
            # Non-adaptive mode: use default duration
            _LOGGER.debug("Zone '%s': Non-adaptive, using default", zone.name)
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
        cycles = self.entry.data.get(CONF_CYCLES, 2)
        
        _LOGGER.info("Starting watering cycle (1/%d)", cycles)
        
        # Send start notification
        await self._send_pushover_notification(
            f"🚿 Bewässerung gestartet",
            f"Starte Bewässerungszyklus ({cycles} Durchgänge)",
            priority=0
        )
        
        try:
            for cycle in range(cycles):
                if cycle > 0:
                    _LOGGER.info("Starting watering cycle (%d/%d)", cycle + 1, cycles)
                
                for zone in self.zones:
                    if zone.enabled and zone.duration > 0:
                        await self._water_zone(zone)
            
            _LOGGER.info("Watering cycle completed")
            
            # Send completion notification
            zones_watered = [z.name for z in self.zones if z.enabled and z.duration > 0]
            await self._send_pushover_notification(
                f"✅ Bewässerung abgeschlossen",
                f"Alle Zonen bewässert: {', '.join(zones_watered)}",
                priority=0
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
            # Send error notification
            await self._send_pushover_notification(
                f"❌ Bewässerungsfehler",
                f"Fehler beim Bewässern: {err}",
                priority=1
            )

    async def _water_zone(self, zone: ZoneData):
        """Water a single zone."""
        _LOGGER.info("Starting zone '%s' for %.1f minutes", zone.name, zone.duration)
        
        # Send zone start notification
        await self._send_pushover_notification(
            f"💧 Zone '{zone.name}' gestartet",
            f"Bewässere für {zone.duration:.1f} Minuten (ETo: {zone.eto_total:.1f}mm)",
            priority=-1  # Low priority for individual zones
        )
        
        zone.is_running = True
        zone.next_run = dt_util.now()
        
        # Notify entities to update
        self.async_set_updated_data(self.data)
        
        # Wait for duration
        await asyncio.sleep(zone.duration * 60)
        
        zone.is_running = False
        
        _LOGGER.info("Zone '%s' finished", zone.name)
        
        # Notify entities to update
        self.async_set_updated_data(self.data)

    async def async_start_zone_manual(self, zone_id: int, duration: int):
        """Manually start a zone."""
        zone = next((z for z in self.zones if z.zone_id == zone_id), None)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")
        
        _LOGGER.info("Manual start of zone '%s' for %d minutes", zone.name, duration)
        zone.duration = duration
        await self._water_zone(zone)

    async def async_stop_zone(self, zone_id: int):
        """Stop a running zone."""
        zone = next((z for z in self.zones if z.zone_id == zone_id), None)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")
        
        if zone.is_running:
            _LOGGER.info("Stopping zone '%s'", zone.name)
            zone.is_running = False
            self.async_set_updated_data(self.data)

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
            ]
        }
        
        await self._storage.async_save(data)

    async def _send_pushover_notification(
        self, title: str, message: str, priority: int = 0
    ):
        """Send Pushover notification if enabled."""
        if not self.entry.data.get(CONF_PUSHOVER_ENABLED, False):
            return
        
        user_key = self.entry.data.get(CONF_PUSHOVER_USER_KEY)
        if not user_key:
            _LOGGER.warning("Pushover enabled but no user key configured")
            return
        
        try:
            service_data = {
                "message": message,
                "title": title,
                "data": {
                    "priority": self.entry.data.get(CONF_PUSHOVER_PRIORITY, priority),
                }
            }
            
            # Add device if specified
            device = self.entry.data.get(CONF_PUSHOVER_DEVICE)
            if device:
                service_data["target"] = device
            
            # Call notify.pushover service
            await self.hass.services.async_call(
                "notify",
                "pushover",
                service_data,
                blocking=False,
            )
            _LOGGER.debug("Sent Pushover notification: %s", title)
            
        except Exception as err:
            _LOGGER.error("Failed to send Pushover notification: %s", err)

    async def async_shutdown(self):
        """Shutdown coordinator."""
        if self._schedule_checker_unsub:
            self._schedule_checker_unsub()
        
        if self._watering_task and not self._watering_task.done():
            self._watering_task.cancel()
        
        await self.weather_provider.async_close()
