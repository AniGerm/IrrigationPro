# Translations für IrrigationPro

## Deutsches Translation File

Erstelle: `custom_components/irrigationpro/translations/de.json`

```json
{
  "config": {
    "step": {
      "user": {
        "title": "IrrigationPro Einrichtung",
        "description": "Konfiguriere dein intelligentes Bewässerungssystem",
        "data": {
          "weather_entity": "Wetter-Entity",
          "use_owm": "OpenWeatherMap als Fallback nutzen",
          "owm_api_key": "OpenWeatherMap API-Schlüssel (optional)"
        }
      },
      "zones": {
        "title": "Zonen konfigurieren",
        "description": "Wie viele Bewässerungszonen möchtest du konfigurieren?",
        "data": {
          "num_zones": "Anzahl der Zonen (1-16)"
        }
      },
      "zone_details": {
        "title": "Zone {zone_number} Konfiguration",
        "description": "Konfiguriere Details für Zone {zone_number}",
        "data": {
          "zone_name": "Zonenname",
          "zone_area": "Fläche (m²)",
          "zone_flow_rate": "Emitter-Durchfluss (L/h)",
          "zone_emitter_count": "Anzahl Emitter",
          "zone_efficiency": "System-Effizienz (%)",
          "zone_crop_coef": "Pflanzen-Koeffizient (0.1-0.9)",
          "zone_plant_density": "Pflanzendichte (0.5-1.3)",
          "zone_exposure_factor": "Exposure-Faktor (0.5-1.4)",
          "zone_max_duration": "Max. Dauer (Minuten)",
          "zone_rain_threshold": "Regen-Schwellwert (mm)",
          "zone_rain_factoring": "Regen berücksichtigen",
          "zone_enabled": "Zone aktiviert",
          "zone_adaptive": "Adaptive Bewässerung"
        }
      },
      "scheduling": {
        "title": "Zeitplan-Konfiguration",
        "description": "Konfiguriere Bewässerungs-Parameter",
        "data": {
          "sunrise_offset": "Minuten vor Sonnenaufgang (kann negativ sein)",
          "cycles": "Anzahl Zyklen pro Durchlauf (1-5)",
          "low_threshold": "Niedrige Temperatur-Schwelle (°C)",
          "high_threshold": "Hohe Temperatur-Schwelle (°C)",
          "recheck_time": "Recheck vor Start (Minuten, 0 zum Deaktivieren)"
        }
      }
    },
    "error": {
      "cannot_connect": "Verbindung zur Wetterquelle fehlgeschlagen",
      "invalid_auth": "Ungültiger API-Schlüssel",
      "unknown": "Unerwarteter Fehler aufgetreten"
    },
    "abort": {
      "already_configured": "Gerät ist bereits konfiguriert"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Konfiguration aktualisieren",
        "description": "Aktualisiere deine IrrigationPro Einstellungen"
      }
    }
  }
}
```

## Weitere Sprachen

### Englisch (en.json)
Bereits in `strings.json` enthalten

### Französisch (fr.json)

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Configuration de l'irrigation intelligente",
        "data": {
          "weather_entity": "Entité météo",
          "use_owm": "Utiliser OpenWeatherMap comme solution de secours",
          "owm_api_key": "Clé API OpenWeatherMap (optionnel)"
        }
      }
    }
  }
}
```

### Spanisch (es.json)

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Configuración de riego inteligente",
        "data": {
          "weather_entity": "Entidad meteorológica",
          "use_owm": "Usar OpenWeatherMap como respaldo",
          "owm_api_key": "Clave API de OpenWeatherMap (opcional)"
        }
      }
    }
  }
}
```
