"""Weather data provider for IrrigationPro."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.components.weather import (
    ATTR_WEATHER_HUMIDITY,
    ATTR_WEATHER_PRESSURE,
    ATTR_WEATHER_TEMPERATURE,
    ATTR_WEATHER_WIND_SPEED,
)
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_location
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

OWM_API_URL = "https://api.openweathermap.org/data/3.0/onecall"


class WeatherData:
    """Weather data container."""

    def __init__(self):
        """Initialize weather data."""
        self.sunrise: datetime | None = None
        self.min_temp: float = 0
        self.max_temp: float = 0
        self.humidity: float = 0
        self.pressure: float = 0
        self.wind_speed: float = 0
        self.rain: float = 0
        self.clouds: float = 0
        self.summary: str = ""


class WeatherProvider:
    """Weather data provider supporting HA weather entity and OWM."""

    def __init__(
        self,
        hass: HomeAssistant,
        weather_entity: str | None = None,
        owm_api_key: str | None = None,
        use_owm: bool = False,
    ):
        """Initialize the weather provider."""
        self.hass = hass
        self.weather_entity = weather_entity
        self.owm_api_key = owm_api_key
        self.use_owm = use_owm
        self._session: aiohttp.ClientSession | None = None

    async def async_get_forecast(self, days: int = 8) -> list[WeatherData]:
        """Get weather forecast for the next N days."""
        if self.weather_entity and not self.use_owm:
            try:
                return await self._get_ha_forecast(days)
            except Exception as err:
                _LOGGER.warning(
                    "Failed to get weather from HA entity, trying OWM: %s", err
                )
                if self.owm_api_key:
                    return await self._get_owm_forecast(days)
                raise

        if self.owm_api_key and self.use_owm:
            return await self._get_owm_forecast(days)

        raise ValueError("No weather source configured")

    async def _get_ha_forecast(self, days: int) -> list[WeatherData]:
        """Get forecast from Home Assistant weather entity."""
        _LOGGER.debug("Fetching weather from HA entity: %s", self.weather_entity)

        # Get weather entity state
        state = self.hass.states.get(self.weather_entity)
        if not state:
            raise ValueError(f"Weather entity {self.weather_entity} not found")

        # Get forecast from weather entity
        forecast_data = []
        
        # Try to get forecast attribute
        forecast_attr = state.attributes.get("forecast")
        if not forecast_attr:
            # Try calling the forecast service
            try:
                response = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"entity_id": self.weather_entity, "type": "daily"},
                    blocking=True,
                    return_response=True,
                )
                forecast_attr = response.get(self.weather_entity, {}).get("forecast", [])
            except Exception as err:
                _LOGGER.debug("Could not call get_forecasts service: %s", err)
                forecast_attr = []

        # Get location for sunrise calculation
        location = await get_astral_location(self.hass)
        lat = self.hass.config.latitude
        lon = self.hass.config.longitude

        # Parse forecast data
        for i in range(min(days, len(forecast_attr) if forecast_attr else 0)):
            forecast_day = forecast_attr[i] if i < len(forecast_attr) else {}
            
            weather = WeatherData()
            
            # Calculate sunrise for this day
            target_date = dt_util.now() + timedelta(days=i)
            weather.sunrise = location.sunrise(target_date, local=True)
            
            # Temperature
            weather.min_temp = forecast_day.get("templow", forecast_day.get("temperature", 15))
            weather.max_temp = forecast_day.get("temperature", 20)
            
            # Humidity (estimate if not available)
            weather.humidity = forecast_day.get("humidity", 60)
            
            # Pressure (use standard if not available)
            weather.pressure = forecast_day.get("pressure", 1013)
            
            # Wind speed
            weather.wind_speed = forecast_day.get("wind_speed", 2)
            
            # Rain (precipitation)
            weather.rain = forecast_day.get("precipitation", 0) or 0
            
            # Cloud coverage
            weather.clouds = forecast_day.get("cloud_coverage", 50)
            
            # Weather condition
            weather.summary = forecast_day.get("condition", "unknown")
            
            forecast_data.append(weather)
            _LOGGER.debug(
                "Day %d: temp=%s-%s°C, humidity=%s%%, rain=%smm",
                i,
                weather.min_temp,
                weather.max_temp,
                weather.humidity,
                weather.rain,
            )

        # If we don't have enough forecast data, fill with estimates
        while len(forecast_data) < days:
            weather = WeatherData()
            target_date = dt_util.now() + timedelta(days=len(forecast_data))
            weather.sunrise = location.sunrise(target_date, local=True)
            weather.min_temp = 15
            weather.max_temp = 20
            weather.humidity = 60
            weather.pressure = 1013
            weather.wind_speed = 2
            weather.rain = 0
            weather.clouds = 50
            weather.summary = "unknown"
            forecast_data.append(weather)

        return forecast_data

    async def _get_owm_forecast(self, days: int) -> list[WeatherData]:
        """Get forecast from OpenWeatherMap API (One Call 3.0)."""
        _LOGGER.debug("Fetching weather from OpenWeatherMap")

        if not self.owm_api_key:
            raise ValueError("OWM API key not configured")

        lat = self.hass.config.latitude
        lon = self.hass.config.longitude

        if self._session is None:
            self._session = aiohttp.ClientSession()

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.owm_api_key,
            "units": "metric",
            "exclude": "current,minutely,hourly,alerts",
        }

        try:
            async with self._session.get(OWM_API_URL, params=params) as response:
                if response.status != 200:
                    raise ValueError(f"OWM API error: {response.status}")
                
                data = await response.json()
                
        except Exception as err:
            _LOGGER.error("Error fetching OWM data: %s", err)
            raise

        # Parse daily forecast
        forecast_data = []
        daily = data.get("daily", [])

        for i in range(min(days, len(daily))):
            day = daily[i]
            
            weather = WeatherData()
            weather.sunrise = datetime.fromtimestamp(
                day["sunrise"], tz=dt_util.DEFAULT_TIME_ZONE
            )
            weather.min_temp = day["temp"]["min"]
            weather.max_temp = day["temp"]["max"]
            weather.humidity = day["humidity"]
            weather.pressure = day["pressure"]
            weather.wind_speed = day["wind_speed"]
            weather.rain = day.get("rain", 0)
            weather.clouds = day["clouds"]
            weather.summary = day["weather"][0]["description"]
            
            forecast_data.append(weather)
            _LOGGER.debug(
                "Day %d (OWM): temp=%s-%s°C, humidity=%s%%, rain=%smm",
                i,
                weather.min_temp,
                weather.max_temp,
                weather.humidity,
                weather.rain,
            )

        return forecast_data

    async def async_close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None
