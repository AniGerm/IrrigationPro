"""Constants for the IrrigationPro integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "irrigationpro"

# Configuration
CONF_WEATHER_ENTITY: Final = "weather_entity"
CONF_ZONES: Final = "zones"
CONF_ZONE_NAME: Final = "zone_name"
CONF_ZONE_AREA: Final = "zone_area"
CONF_ZONE_FLOW_RATE: Final = "zone_flow_rate"
CONF_ZONE_EFFICIENCY: Final = "zone_efficiency"
CONF_ZONE_CROP_COEF: Final = "zone_crop_coef"
CONF_ZONE_PLANT_DENSITY: Final = "zone_plant_density"
CONF_ZONE_EXPOSURE_FACTOR: Final = "zone_exposure_factor"
CONF_ZONE_EMITTER_COUNT: Final = "zone_emitter_count"
CONF_ZONE_MAX_DURATION: Final = "zone_max_duration"
CONF_ZONE_RAIN_THRESHOLD: Final = "zone_rain_threshold"
CONF_ZONE_RAIN_FACTORING: Final = "zone_rain_factoring"
CONF_ZONE_ENABLED: Final = "zone_enabled"
CONF_ZONE_ADAPTIVE: Final = "zone_adaptive"
CONF_ZONE_WEEKDAYS: Final = "zone_weekdays"
CONF_ZONE_MONTHS: Final = "zone_months"

# Scheduling
CONF_SUNRISE_OFFSET: Final = "sunrise_offset"
CONF_CYCLES: Final = "cycles"
CONF_LOW_THRESHOLD: Final = "low_threshold"
CONF_HIGH_THRESHOLD: Final = "high_threshold"
CONF_RECHECK_TIME: Final = "recheck_time"

# Notifications
CONF_PUSHOVER_ENABLED: Final = "pushover_enabled"
CONF_PUSHOVER_USER_KEY: Final = "pushover_user_key"
CONF_PUSHOVER_DEVICE: Final = "pushover_device"
CONF_PUSHOVER_PRIORITY: Final = "pushover_priority"

# Solar radiation (monthly average kWh/day)
CONF_SOLAR_RADIATION: Final = "solar_radiation"

# OWM fallback
CONF_OWM_API_KEY: Final = "owm_api_key"
CONF_USE_OWM: Final = "use_owm"

# Default values
DEFAULT_SUNRISE_OFFSET: Final = 0
DEFAULT_CYCLES: Final = 2
DEFAULT_LOW_THRESHOLD: Final = 5
DEFAULT_HIGH_THRESHOLD: Final = 15
DEFAULT_RECHECK_TIME: Final = 0
DEFAULT_PUSHOVER_ENABLED: Final = False
DEFAULT_PUSHOVER_PRIORITY: Final = 0
DEFAULT_ZONE_AREA: Final = 10.0
DEFAULT_ZONE_FLOW_RATE: Final = 2.0
DEFAULT_ZONE_EFFICIENCY: Final = 90
DEFAULT_ZONE_CROP_COEF: Final = 0.6
DEFAULT_ZONE_PLANT_DENSITY: Final = 1.0
DEFAULT_ZONE_EXPOSURE_FACTOR: Final = 1.0
DEFAULT_ZONE_EMITTER_COUNT: Final = 10
DEFAULT_ZONE_MAX_DURATION: Final = 60
DEFAULT_ZONE_RAIN_THRESHOLD: Final = 2.5
DEFAULT_ZONE_RAIN_FACTORING: Final = True
DEFAULT_ZONE_ENABLED: Final = True
DEFAULT_ZONE_ADAPTIVE: Final = True

# Default solar radiation (kWh/day per month)
DEFAULT_SOLAR_RADIATION: Final = {
    1: 6.0,  # January
    2: 6.0,
    3: 6.0,
    4: 6.0,
    5: 6.0,
    6: 6.0,
    7: 6.0,
    8: 6.0,
    9: 6.0,
    10: 6.0,
    11: 6.0,
    12: 6.0,
}

# Weekdays
WEEKDAYS: Final = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Months
MONTHS: Final = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]

# Update intervals
UPDATE_INTERVAL_MINUTES: Final = 60

# Storage
STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}_storage"

# Services
SERVICE_START_ZONE: Final = "start_zone"
SERVICE_STOP_ZONE: Final = "stop_zone"
SERVICE_RECALCULATE: Final = "recalculate"

# Attributes
ATTR_ZONE_ID: Final = "zone_id"
ATTR_DURATION: Final = "duration"
ATTR_ETO: Final = "eto"
ATTR_NEXT_RUN: Final = "next_run"
ATTR_LAST_RUN: Final = "last_run"
ATTR_RAIN: Final = "rain"
ATTR_WATER_NEEDED: Final = "water_needed"
ATTR_SCHEDULE: Final = "schedule"
