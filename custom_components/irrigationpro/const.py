"""Constants for the IrrigationPro integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "irrigationpro"
VERSION: Final = "2.2.4"

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
CONF_ZONE_ADJUSTMENT_PERCENT: Final = "zone_adjustment_percent"
CONF_ZONE_ENABLED: Final = "zone_enabled"
CONF_ZONE_ADAPTIVE: Final = "zone_adaptive"
CONF_ZONE_SWITCH_ENTITY: Final = "zone_switch_entity"
CONF_ZONE_WEEKDAYS: Final = "zone_weekdays"
CONF_ZONE_MONTHS: Final = "zone_months"

# Soil moisture learning
CONF_ZONE_VEGETATION_TYPE: Final = "zone_vegetation_type"
CONF_ZONE_SOIL_MOISTURE_ENTITY: Final = "zone_soil_moisture_entity"
CONF_ZONE_TARGET_MOISTURE_MIN: Final = "zone_target_moisture_min"
CONF_ZONE_TARGET_MOISTURE_MAX: Final = "zone_target_moisture_max"
CONF_ZONE_LEARNING_ENABLED: Final = "zone_learning_enabled"

# Scheduling
CONF_SUNRISE_OFFSET: Final = "sunrise_offset"
CONF_CYCLES: Final = "cycles"
CONF_LOW_THRESHOLD: Final = "low_threshold"
CONF_HIGH_THRESHOLD: Final = "high_threshold"
CONF_RECHECK_TIME: Final = "recheck_time"
CONF_LANGUAGE: Final = "language"

# Notifications
CONF_MASTER_ENABLED: Final = "master_enabled"
CONF_PUSHOVER_ENABLED: Final = "pushover_enabled"
CONF_PUSHOVER_API_TOKEN: Final = "pushover_api_token"
CONF_PUSHOVER_USER_KEY: Final = "pushover_user_key"
CONF_PUSHOVER_DEVICE: Final = "pushover_device"
CONF_PUSHOVER_PRIORITY: Final = "pushover_priority"
CONF_DAILY_REPORT_ENABLED: Final = "daily_report_enabled"
CONF_DAILY_REPORT_HOUR: Final = "daily_report_hour"

# Sensor health monitoring
CONF_SENSOR_ALERT_MINUTES: Final = "sensor_alert_minutes"
DEFAULT_SENSOR_ALERT_MINUTES: Final = 30
SENSOR_BATTERY_LOW_THRESHOLD: Final = 15  # percent

# Solar radiation (monthly average kWh/day)
CONF_SOLAR_RADIATION: Final = "solar_radiation"

# HomeKit native integration
CONF_HOMEKIT_ENABLED: Final = "homekit_enabled"
CONF_HOMEKIT_PORT: Final = "homekit_port"
CONF_HOMEKIT_PIN: Final = "homekit_pin"

# OWM fallback
CONF_OWM_API_KEY: Final = "owm_api_key"
CONF_USE_OWM: Final = "use_owm"

# Default values
DEFAULT_SUNRISE_OFFSET: Final = 0
DEFAULT_CYCLES: Final = 2
DEFAULT_LOW_THRESHOLD: Final = 5
DEFAULT_HIGH_THRESHOLD: Final = 15
DEFAULT_RECHECK_TIME: Final = 0
DEFAULT_LANGUAGE: Final = "de"
DEFAULT_MASTER_ENABLED: Final = True
DEFAULT_PUSHOVER_ENABLED: Final = False
DEFAULT_PUSHOVER_PRIORITY: Final = 0
DEFAULT_DAILY_REPORT_ENABLED: Final = False
DEFAULT_DAILY_REPORT_HOUR: Final = 7
DEFAULT_HOMEKIT_ENABLED: Final = False
DEFAULT_HOMEKIT_PORT: Final = 21064
DEFAULT_HOMEKIT_PIN: Final = "246-35-790"
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
DEFAULT_ZONE_ADJUSTMENT_PERCENT: Final = 100
DEFAULT_ZONE_ENABLED: Final = True
DEFAULT_ZONE_ADAPTIVE: Final = True
DEFAULT_ZONE_LEARNING_ENABLED: Final = True
DEFAULT_ZONE_VEGETATION_TYPE: Final = "lawn"

# ---------------------------------------------------------------------------
# Vegetation types with scientifically-based soil moisture targets (VWC %)
#
# Sources:
#   - FAO Irrigation & Drainage Paper 56 (Penman-Monteith) — crop coefficients
#     and Management Allowed Depletion (MAD) values
#   - Allen, R.G. et al. (1998) "Crop evapotranspiration – Guidelines for
#     computing crop water requirements"
#   - USDA NRCS Engineering Field Handbook, Chapter 15 — soil-plant-water
#     relationships and available water capacity
#
# Target moisture ranges are derived for a loamy garden soil with:
#   Field Capacity (FC) ≈ 30 % VWC
#   Permanent Wilting Point (PWP) ≈ 12 % VWC
#   Available Water Capacity (AWC) = FC − PWP ≈ 18 %
#
#   target_min = PWP + (1 − MAD_high) × AWC
#   target_max = FC (or slightly above for shallow-rooted plants)
#
# Kc = crop coefficient (FAO-56 mid-season representative value)
# MAD = management allowed depletion range (% of AWC)
# ---------------------------------------------------------------------------
VEGETATION_TYPES: Final = {
    "lawn": {
        "name_de": "Rasen",
        "name_en": "Lawn / Turf",
        "kc": 0.75,
        "mad_range": (40, 50),
        "target_min": 21,
        "target_max": 35,
        "description_de": "Kc 0.75, MAD 40–50 % (FAO-56 Table 22, warm-season turf)",
        "description_en": "Kc 0.75, MAD 40–50 % (FAO-56 Table 22, warm-season turf)",
    },
    "flowers": {
        "name_de": "Blumen / Einjährige",
        "name_en": "Flowers / Annuals",
        "kc": 0.65,
        "mad_range": (25, 35),
        "target_min": 23,
        "target_max": 38,
        "description_de": "Kc 0.65, MAD 25–35 % — flache Wurzeln, empfindlich",
        "description_en": "Kc 0.65, MAD 25–35 % — shallow roots, moisture-sensitive",
    },
    "vegetables": {
        "name_de": "Gemüse",
        "name_en": "Vegetables",
        "kc": 0.70,
        "mad_range": (30, 50),
        "target_min": 21,
        "target_max": 38,
        "description_de": "Kc 0.70, MAD 30–50 % (FAO-56 Table 22, Mischgemüse)",
        "description_en": "Kc 0.70, MAD 30–50 % (FAO-56 Table 22, mixed vegetables)",
    },
    "shrubs": {
        "name_de": "Sträucher",
        "name_en": "Shrubs",
        "kc": 0.50,
        "mad_range": (50, 60),
        "target_min": 19,
        "target_max": 30,
        "description_de": "Kc 0.50, MAD 50–60 % — tiefere Wurzeln, trockenheitstoleranter",
        "description_en": "Kc 0.50, MAD 50–60 % — deeper roots, more drought-tolerant",
    },
    "trees": {
        "name_de": "Bäume",
        "name_en": "Trees",
        "kc": 0.55,
        "mad_range": (50, 65),
        "target_min": 18,
        "target_max": 30,
        "description_de": "Kc 0.55, MAD 50–65 % (FAO-56, Obstbäume mid-season)",
        "description_en": "Kc 0.55, MAD 50–65 % (FAO-56, fruit trees mid-season)",
    },
    "herbs": {
        "name_de": "Kräuter",
        "name_en": "Herbs",
        "kc": 0.50,
        "mad_range": (35, 45),
        "target_min": 22,
        "target_max": 33,
        "description_de": "Kc 0.50, MAD 35–45 % — mediterrane Kräuter trockenheitstoleranter",
        "description_en": "Kc 0.50, MAD 35–45 % — Mediterranean herbs more drought-tolerant",
    },
    "succulents": {
        "name_de": "Sukkulenten",
        "name_en": "Succulents",
        "kc": 0.25,
        "mad_range": (60, 75),
        "target_min": 13,
        "target_max": 22,
        "description_de": "Kc 0.25, MAD 60–75 % — extrem trockenheitsresistent",
        "description_en": "Kc 0.25, MAD 60–75 % — extremely drought-resistant",
    },
    "ground_cover": {
        "name_de": "Bodendecker",
        "name_en": "Ground Cover",
        "kc": 0.55,
        "mad_range": (40, 50),
        "target_min": 21,
        "target_max": 33,
        "description_de": "Kc 0.55, MAD 40–50 % — ähnlich Rasen, flach wurzelnd",
        "description_en": "Kc 0.55, MAD 40–50 % — similar to turf, shallow-rooted",
    },
    "hedges": {
        "name_de": "Hecken",
        "name_en": "Hedges",
        "kc": 0.65,
        "mad_range": (45, 55),
        "target_min": 20,
        "target_max": 32,
        "description_de": "Kc 0.65, MAD 45–55 % — dichtes Blattwerk, mäßiger Bedarf",
        "description_en": "Kc 0.65, MAD 45–55 % — dense foliage, moderate demand",
    },
    "perennials": {
        "name_de": "Stauden",
        "name_en": "Perennials",
        "kc": 0.60,
        "mad_range": (30, 40),
        "target_min": 23,
        "target_max": 35,
        "description_de": "Kc 0.60, MAD 30–40 % — etablierte Stauden",
        "description_en": "Kc 0.60, MAD 30–40 % — established perennials",
    },
    "custom": {
        "name_de": "Benutzerdefiniert",
        "name_en": "Custom",
        "kc": 0.60,
        "mad_range": (30, 50),
        "target_min": 20,
        "target_max": 35,
        "description_de": "Eigene Zielwerte manuell festlegen",
        "description_en": "Set custom target values manually",
    },
}

# Learning algorithm parameters
LEARNING_FEEDBACK_DELAY_HOURS: Final = 6
LEARNING_MIN_ENTRIES: Final = 5
LEARNING_MAX_CORRECTION_STEP: Final = 0.05
LEARNING_CORRECTION_MIN: Final = 0.50
LEARNING_CORRECTION_MAX: Final = 2.00
LEARNING_JOURNAL_MAX_ENTRIES: Final = 50
LEARNING_STORAGE_KEY: Final = f"{DOMAIN}_learning"
LEARNING_STORAGE_VERSION: Final = 1

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
SERVICE_RESET_LEARNING: Final = "reset_learning"

# Attributes
ATTR_ZONE_ID: Final = "zone_id"
ATTR_DURATION: Final = "duration"
ATTR_ETO: Final = "eto"
ATTR_NEXT_RUN: Final = "next_run"
ATTR_LAST_RUN: Final = "last_run"
ATTR_RAIN: Final = "rain"
ATTR_WATER_NEEDED: Final = "water_needed"
ATTR_SCHEDULE: Final = "schedule"
