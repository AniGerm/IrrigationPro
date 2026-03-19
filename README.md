# IrrigationPro for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Release](https://img.shields.io/github/release/AniGerm/IrrigationPro.svg)](https://github.com/AniGerm/IrrigationPro/releases)

[🇬🇧 English](#english) | [🇩🇪 Deutsch](#deutsch)

## English

IrrigationPro is a scientifically based irrigation controller for Home Assistant. The integration calculates water demand per zone based on FAO-56 Penman-Monteith evapotranspiration, provides a dedicated dashboard in the Home Assistant frontend, supports backup and restore of the configuration, and can optionally offer a native HomeKit sprinkler bridge.

The current stable release is version 2.1.8. This repository is structured as a HACS custom repository and already includes the required validation workflows for HACS and hassfest.

## Features

- Climate-adaptive irrigation scheduling for up to 16 zones
- Native Home Assistant integration with config flow, services, and dashboard panel
- Native HomeKit sprinkler bridge with QR pairing, automatic port suggestion, zones, runtime, and separate runtime switches
- Master switch to globally pause/resume irrigation
- Pushover notifications using the Pushover API
- Daily morning report with planned run and weather summary
- Backup, restore, and prepared legacy import of the entire configuration
- DE/EN language toggle in the UI and runtime notifications
- Home Assistant weather entities or OpenWeatherMap as fallback
- Stable startup even if the weather entity is temporarily unavailable, with automatic retry
- Zone-specific weekdays, months, adaptive parameters, and runtime diagnostics

## Requirements

- Home Assistant 2023.1 or newer
- At least one switchable valve/relay infrastructure in Home Assistant
- A weather entity in Home Assistant or alternatively an OpenWeatherMap API key
- Optional for HomeKit: a free TCP port for the HAP server

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Go to Integrations.
3. Open the menu in the top right and select Custom Repositories.
4. Add https://github.com/AniGerm/IrrigationPro as an integration.
5. Install IrrigationPro and restart Home Assistant.

Note: As long as the repository is not yet included in the HACS default list, installation is done via Custom Repositories. After successful inclusion in HACS, IrrigationPro can be found directly via search.

### Manual

1. Copy the folder `custom_components/irrigationpro` to `config/custom_components/`.
2. Restart Home Assistant.

## Setup

1. Open Settings → Devices & Services.
2. Click Add Integration.
3. Search for IrrigationPro.
4. Follow the wizard for weather source, zones, and schedule.

Important configuration points:

- Zone name, area, flow rate, emitter count, efficiency, crop coefficient, plant density, and exposure factor
- Weekdays and months per zone
- Rain threshold, rain factoring, and maximum runtime
- Sunrise offset, cycles, temperature thresholds, and recheck interval
- Language, Pushover, daily report, and HomeKit

## Dashboard & Runtime Features

The built-in dashboard provides:

- Status overview for runtimes, weather, and schedule
- Zone cards with manual start/stop
- Runtime switches for master switch and Pushover
- Backup/restore dialog with native export/import and prepared legacy conversion
- HomeKit dialog with port, PIN, QR code, and note about available alternative ports
- Test functions for relays, scheduling, and Pushover
- Status and diagnostic values for duration, ETo, rain, water demand, and next run

## HomeKit

When HomeKit is enabled, IrrigationPro starts its own native HAP bridge.

Provided are:

- A native irrigation system in Apple Home
- A valve service mapping per zone
- A separate master switch as a HomeKit switch
- A separate notification switch for Pushover
- QR pairing and PIN-based pairing
- AccessoryInformation with manufacturer, model, serial number, and firmware version

Notes:

- The HomeKit port must be free and must not conflict with an existing HA HomeKit bridge.
- If the configured port is occupied, IrrigationPro automatically suggests a free alternative port.
- After structural HomeKit changes, it may be necessary to re-pair the bridge in Apple Home.

## Pushover & Daily Report

IrrigationPro talks to the Pushover API directly. A separate Home Assistant Pushover integration is not required.

Supported:

- Start and stop notifications
- Zone start notifications
- Error notifications
- Test notifications from the dashboard
- Optional daily morning report with planned irrigation and weather data
- Runtime toggle directly from dashboard and HomeKit

## Entities

Typically the following entities are created per zone:

- switch.irrigation_zone_X
- valve.irrigation_zone_X
- sensor.irrigation_zone_X_duration
- sensor.irrigation_zone_X_eto
- sensor.irrigation_zone_X_next_run
- binary_sensor.irrigation_zone_X_will_run_today

## Services

### irrigationpro.start_zone

Starts a zone manually for a specified duration.

```yaml
service: irrigationpro.start_zone
data:
  zone_id: 1
  duration: 15
```

### irrigationpro.stop_zone

Stops a running zone.

```yaml
service: irrigationpro.stop_zone
data:
  zone_id: 1
```

### irrigationpro.recalculate

Forces a recalculation of the irrigation schedule.

```yaml
service: irrigationpro.recalculate
```

## Backup & Restore

The integration supports export and restore of the complete configuration.

- Native backup format: irrigationpro-backup-v1
- Legacy import from SmartSprinklers-like setups
- Zone-specific weekdays and months are preserved
- Restore via dashboard API with prepared validation and editing step

A conversion script for legacy data is also provided:

- tools/convert_legacy_setup_to_backup.py

## Behavior When Weather Data Is Missing

If the configured weather entity is temporarily unavailable at startup or runtime, the integration stays loaded. IrrigationPro puts scheduling into a safe waiting state and automatically retries fetching weather data every 2 minutes until a valid forecast is available again.

## Automations

IrrigationPro does not control real hardware directly. The actual valve switching is done via your existing Home Assistant entities and automations.

Example:

```yaml
automation:
  - alias: "Irrigation Zone 1 - Control valve"
    trigger:
      - platform: state
        entity_id: switch.irrigation_zone_1
    action:
      - service: switch.turn_{{ trigger.to_state.state }}
        target:
          entity_id: switch.gardena_valve_1
```

## Scientific Background

The reference evapotranspiration is calculated according to FAO-56. Among other things, the following are taken into account:

- Min/Max temperature
- Relative humidity
- Wind speed
- Solar radiation
- Atmospheric pressure
- Geographic location and season

In simplified form:

```text
Water demand = (ETo - rain) × crop coefficient × plant density × exposure factor × area / efficiency
Duration = water demand / (flow rate × number of emitters)
```

## Troubleshooting

### Keine Bewässerung geplant

- Prüfe, ob die Temperaturschwellen erreicht wurden.
- Prüfe, ob die Zone aktiviert ist.
- Prüfe, ob Wetterdaten verfügbar sind.
- Prüfe die Logs von custom_components.irrigationpro.

### HomeKit startet nicht

- Prüfe, ob der konfigurierte HAP-Port frei ist.
- Prüfe, ob HAP-python installiert wurde.
- Prüfe, ob Apple Home noch eine alte Bridge-Konfiguration zwischengespeichert hat.

### Debug Logging

```yaml
logger:
  default: info
  logs:
    custom_components.irrigationpro: debug
```

## Support

- GitHub Issues: [Issues](https://github.com/AniGerm/IrrigationPro/issues)
- Home Assistant Community: [Community](https://community.home-assistant.io/)

## Release-Workflow

- Vor einer HACS-Veröffentlichung sollten HACS-Validation und Hassfest in GitHub Actions grün sein.
- Für die Aufnahme in die HACS-Standardliste ist ein echtes GitHub Release erforderlich; ein Tag allein reicht dafür nicht aus.
- Repository-Beschreibung, Topics und aktivierte Issues werden in GitHub geprüft und sollten vor dem Einreichen gesetzt sein.
- Historische rote Workflow-Läufe bleiben in GitHub sichtbar; bereinigt werden nur zukünftige Läufe über einen enger gefassten Workflow.

## Beitragen

1. Forke das Repository.
2. Erstelle einen Feature-Branch.
3. Committe deine Änderungen.
4. Öffne einen Pull Request.

## Lizenz

MIT License, siehe [LICENSE](LICENSE).

## Danksagung

- [MTry/homebridge-smart-irrigation](https://github.com/MTry/homebridge-smart-irrigation) für die ursprüngliche Idee
- [FAO Irrigation and Drainage Paper No. 56](http://www.fao.org/3/X0490E/x0490e00.htm) für die wissenschaftliche Grundlage
