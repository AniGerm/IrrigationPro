"""Config flow for IrrigationPro integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

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
    CONF_ZONE_NAME,
    CONF_ZONE_PLANT_DENSITY,
    CONF_ZONE_RAIN_FACTORING,
    CONF_ZONE_RAIN_THRESHOLD,
    CONF_ZONES,
    DEFAULT_CYCLES,
    DEFAULT_HIGH_THRESHOLD,
    DEFAULT_LOW_THRESHOLD,
    DEFAULT_PUSHOVER_ENABLED,
    DEFAULT_PUSHOVER_PRIORITY,
    DEFAULT_RECHECK_TIME,
    DEFAULT_SOLAR_RADIATION,
    DEFAULT_SUNRISE_OFFSET,
    DEFAULT_ZONE_ADAPTIVE,
    DEFAULT_ZONE_AREA,
    DEFAULT_ZONE_CROP_COEF,
    DEFAULT_ZONE_EFFICIENCY,
    DEFAULT_ZONE_EMITTER_COUNT,
    DEFAULT_ZONE_ENABLED,
    DEFAULT_ZONE_EXPOSURE_FACTOR,
    DEFAULT_ZONE_FLOW_RATE,
    DEFAULT_ZONE_MAX_DURATION,
    DEFAULT_ZONE_RAIN_FACTORING,
    DEFAULT_ZONE_RAIN_THRESHOLD,
    DOMAIN,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)


async def _get_weather_entities(hass: HomeAssistant) -> list[str]:
    """Get list of weather entities."""
    weather_entities = []
    for entity_id in hass.states.async_entity_ids("weather"):
        weather_entities.append(entity_id)
    return weather_entities


class SmartIrrigationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IrrigationPro."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._num_zones = 0
        self._current_zone = 0
        self._zones_config: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validate weather entity exists
                weather_entity = user_input.get(CONF_WEATHER_ENTITY)
                if weather_entity:
                    state = self.hass.states.get(weather_entity)
                    if state is None:
                        errors["base"] = "weather_entity_not_found"
                        _LOGGER.error("Weather entity %s not found", weather_entity)
                    else:
                        # Store initial configuration
                        self._data.update(user_input)
                        return await self.async_step_zones()
                else:
                    errors["base"] = "no_weather_entity"
            except Exception as err:
                _LOGGER.error("Error in user step: %s", err, exc_info=True)
                errors["base"] = "unknown"

        # Get available weather entities
        weather_entities = await _get_weather_entities(self.hass)

        if not weather_entities:
            errors["base"] = "no_weather_entities"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
                vol.Optional(CONF_USE_OWM, default=False): selector.BooleanSelector(),
                vol.Optional(CONF_OWM_API_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle zones configuration step."""
        errors = {}

        if user_input is not None:
            try:
                num_zones = user_input.get("num_zones", 1)
                if 1 <= num_zones <= 16:
                    self._num_zones = num_zones
                    self._current_zone = 0
                    self._zones_config = []
                    _LOGGER.debug("Configuring %d zones", num_zones)
                    return await self.async_step_zone_details()
                else:
                    errors["num_zones"] = "invalid_num_zones"
                    _LOGGER.warning("Invalid number of zones: %s", num_zones)
            except Exception as err:
                _LOGGER.error("Error in zones step: %s", err, exc_info=True)
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required("num_zones", default=4): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=16, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="zones", data_schema=data_schema, errors=errors
        )

    async def async_step_zone_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle individual zone configuration."""
        errors = {}

        if user_input is not None:
            try:
                # Store zone configuration
                _LOGGER.debug("Zone %d config received: %s", self._current_zone + 1, user_input)
                self._zones_config.append(user_input)
                self._current_zone += 1

                # Check if we need to configure more zones
                if self._current_zone < self._num_zones:
                    return await self.async_step_zone_details()
                else:
                    # All zones configured, move to scheduling
                    self._data[CONF_ZONES] = self._zones_config
                    return await self.async_step_scheduling()
            except Exception as err:
                _LOGGER.error("Error in zone_details step: %s", err, exc_info=True)
                errors["base"] = "unknown"

        # Schema for current zone
        zone_number = self._current_zone + 1
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_ZONE_NAME, default=f"Zone {zone_number}"
                ): selector.TextSelector(),
                vol.Required(
                    CONF_ZONE_AREA, default=DEFAULT_ZONE_AREA
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=1000,
                        step=0.1,
                        unit_of_measurement="m²",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_ZONE_FLOW_RATE, default=DEFAULT_ZONE_FLOW_RATE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=100,
                        step=0.1,
                        unit_of_measurement="L/h",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_ZONE_EMITTER_COUNT, default=DEFAULT_ZONE_EMITTER_COUNT
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=1000, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_ZONE_EFFICIENCY, default=DEFAULT_ZONE_EFFICIENCY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=50,
                        max=100,
                        unit_of_measurement="%",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_ZONE_CROP_COEF, default=DEFAULT_ZONE_CROP_COEF
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        max=0.9,
                        step=0.1,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_ZONE_PLANT_DENSITY, default=DEFAULT_ZONE_PLANT_DENSITY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=1.3,
                        step=0.1,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_ZONE_EXPOSURE_FACTOR, default=DEFAULT_ZONE_EXPOSURE_FACTOR
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5,
                        max=1.4,
                        step=0.1,
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_ZONE_MAX_DURATION, default=DEFAULT_ZONE_MAX_DURATION
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=180,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_ZONE_RAIN_THRESHOLD, default=DEFAULT_ZONE_RAIN_THRESHOLD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=50,
                        step=0.5,
                        unit_of_measurement="mm",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_ZONE_RAIN_FACTORING, default=DEFAULT_ZONE_RAIN_FACTORING
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ZONE_ENABLED, default=DEFAULT_ZONE_ENABLED
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_ZONE_ADAPTIVE, default=DEFAULT_ZONE_ADAPTIVE
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="zone_details",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"zone_number": str(zone_number)},
        )

    async def async_step_scheduling(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle scheduling configuration step."""
        errors = {}

        if user_input is not None:
            try:
                # Store scheduling configuration
                self._data.update(user_input)

                # Validate Pushover configuration if enabled
                if user_input.get(CONF_PUSHOVER_ENABLED, False):
                    if not user_input.get(CONF_PUSHOVER_USER_KEY):
                        errors["base"] = "pushover_no_key"
                        _LOGGER.warning("Pushover enabled but no user key provided")

                if errors:
                    # Return form with errors
                    pass
                else:
                    # Add default solar radiation if not provided
                    if CONF_SOLAR_RADIATION not in self._data:
                        self._data[CONF_SOLAR_RADIATION] = DEFAULT_SOLAR_RADIATION

                    _LOGGER.debug("Creating config entry with data: %s", {k: v for k, v in self._data.items() if 'key' not in k.lower()})

                    # Create the config entry
                    return self.async_create_entry(
                        title="IrrigationPro", data=self._data
                    )
            except Exception as err:
                _LOGGER.error("Error in scheduling step: %s", err, exc_info=True)
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SUNRISE_OFFSET, default=DEFAULT_SUNRISE_OFFSET
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-1440,
                        max=1440,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_CYCLES, default=DEFAULT_CYCLES
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_LOW_THRESHOLD, default=DEFAULT_LOW_THRESHOLD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-20,
                        max=30,
                        unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_HIGH_THRESHOLD, default=DEFAULT_HIGH_THRESHOLD
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=50,
                        unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_RECHECK_TIME, default=DEFAULT_RECHECK_TIME
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=120,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PUSHOVER_ENABLED, default=DEFAULT_PUSHOVER_ENABLED
                ): selector.BooleanSelector(),
                vol.Optional(CONF_PUSHOVER_USER_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_PUSHOVER_DEVICE): selector.TextSelector(),
                vol.Optional(
                    CONF_PUSHOVER_PRIORITY, default=DEFAULT_PUSHOVER_PRIORITY
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-2, max=2, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="scheduling", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmartIrrigationOptionsFlow:
        """Get the options flow for this handler."""
        return SmartIrrigationOptionsFlow(config_entry)


class SmartIrrigationOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for IrrigationPro."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            try:
                # Validate Pushover configuration if enabled
                if user_input.get(CONF_PUSHOVER_ENABLED, False):
                    if not user_input.get(CONF_PUSHOVER_USER_KEY):
                        errors["base"] = "pushover_no_key"
                
                if not errors:
                    # Update config entry data with new options
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={**self.config_entry.data, **user_input}
                    )
                    return self.async_create_entry(title="", data={})
            except Exception as err:
                _LOGGER.error("Error in options flow: %s", err, exc_info=True)
                errors["base"] = "unknown"

        # Get current configuration
        current_config = self.config_entry.data

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SUNRISE_OFFSET,
                    default=current_config.get(CONF_SUNRISE_OFFSET, DEFAULT_SUNRISE_OFFSET),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-1440,
                        max=1440,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_CYCLES,
                    default=current_config.get(CONF_CYCLES, DEFAULT_CYCLES),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=5, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_LOW_THRESHOLD,
                    default=current_config.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-20,
                        max=30,
                        unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_HIGH_THRESHOLD,
                    default=current_config.get(CONF_HIGH_THRESHOLD, DEFAULT_HIGH_THRESHOLD),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=50,
                        unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_RECHECK_TIME,
                    default=current_config.get(CONF_RECHECK_TIME, DEFAULT_RECHECK_TIME),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=120,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PUSHOVER_ENABLED,
                    default=current_config.get(CONF_PUSHOVER_ENABLED, DEFAULT_PUSHOVER_ENABLED),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_PUSHOVER_USER_KEY,
                    default=current_config.get(CONF_PUSHOVER_USER_KEY, ""),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(
                    CONF_PUSHOVER_DEVICE,
                    default=current_config.get(CONF_PUSHOVER_DEVICE, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_PUSHOVER_PRIORITY,
                    default=current_config.get(CONF_PUSHOVER_PRIORITY, DEFAULT_PUSHOVER_PRIORITY),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-2, max=2, mode=selector.NumberSelectorMode.BOX
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
