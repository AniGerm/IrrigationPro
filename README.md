# IrrigationPro for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Release](https://img.shields.io/github/release/AniGerm/IrrigationPro.svg)](https://github.com/AniGerm/IrrigationPro/releases)

[🇬🇧 English](#english) | [🇩🇪 Deutsch](#deutsch)

## English

IrrigationPro is a scientifically based irrigation controller for Home Assistant. The integration calculates water demand per zone based on 
FAO-56 Penman-Monteith evapotranspiration, provides a dedicated dashboard in the Home Assistant frontend, supports backup and restore of 
the configuration, and can optionally offer a native HomeKit sprinkler bridge.

The current stable release is version 2.2.1. This repository is structured as a HACS custom repository and already includes the required
validation workflows for HACS and hassfest.

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

Note: As long as the repository is not yet included in the HACS default list, installation is done via Custom Repositories. After 
successful inclusion in HACS, IrrigationPro can be found directly via search.

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

## Support

- GitHub Issues: [Issues](https://github.com/AniGerm/IrrigationPro/issues)
- Home Assistant Community: [Community](https://community.home-assistant.io/)

## Licence

MIT License, see [LICENSE](LICENSE).

## Acknowledgement

- [MTry/homebridge-smart-irrigation](https://github.com/MTry/homebridge-smart-irrigation) for the original idea
- [FAO Irrigation and Drainage Paper No. 56](http://www.fao.org/3/X0490E/x0490e00.htm) for the scientific basis

## Deutsch

IrrigationPro ist ein irrigationssteuerndes Addon für Home Assistant, das die Wasserdüngung pro Zone auf der Basis von FAO-56 Penman-Monteith berechnet und 
einen eigenen Dashboard in der Frontend-Benutzeroberfläche von Home Assistant bietet. Die Komponente unterstützt zudem den Backup und Restore des 
Konfigurationsspeichers und kann optionale Unterstützung für einen HomeKit-Bewässerungsbereich anbieten.

Die aktuelle stabile Version ist 2.2.1. Das Repository ist als Custom Repository für HACS strukturiert und enthält bereits die benötigten
Validierungsworkflows für HACS und Hassfest.

## Funktionen

- Anpassung des Bewässerungsprogramms an den Klimaverlauf für bis zu 16 Zonen
- Native Home Assistant Integration mit Flow, Services und Dashboardpanel
- Native HomeKit-Bewässerungsbereich mit QR-Code-Paring, automatischer Portsuche, Zonen, Laufdauer und separaten Laufschalter
- Masterschalter zum globalen Pause/Fortsetzen des Bewässerns
- Pushover-Benachrichtigungen über die API
- Morgendiätendurchsicht mit geplantem Bewässerungsplan und Wettervoraussagen
- Backup, Restore und Vorbereitung der Legacy-Importierung der gesamten Konfiguration
- Spracheinstellung DE/EN im Benutzerinterface und Laufschalterbenachrichtigungen
- Home Assistant Wetterdaten oder OpenWeatherMap als Fallback
- Stabiler Start auch wenn die Wetterdaten vorübergehend nicht verfügbar sind
- Zonenspezifische Konfiguration von Wochentagen, Monaten, Anpassungsparametern und Laufdiagnostik

## Voraussetzungen

- Home Assistant 2023.1 oder höher
- Mindestens ein switchbares Bewässerungssystem in Home Assistant
- Eine Wetterdatenquelle in Home Assistant oder alternativ eine OpenWeatherMap API-Schlüssel
- Optional: frei verfügbarer TCP-Port für den HAP-Server bei HomeKit

## Installation

### HACS

1. Öffne HACS in Home Assistant.
2. Gehe zu Integrationen.
3. Klicke auf das Menü am oberen rechten Rand und wähle Custom Repositories aus.
4. Füge https://github.com/AniGerm/IrrigationPro hinzu.
5. Installiere IrrigationPro und start Home Assistant neu.

Note: Bis das Repository in die Standardliste von HACS aufgenommen wird, muss es über Custom Repositories installiert werden. Nach erfolgreicher Aufnahme kann 
IrrigationPro direkt über die Suche gefunden werden.

### Manual

1. Kopiere den Ordner custom_components/irrigationpro in config/custom_components/.
2. Starte Home Assistant neu.

## Konfiguration

1. Öffne Einstellungen → Geräte und Dienste.
2. Klicke auf "Add Integration" und suche nach IrrigationPro.
3. Folge der Anleitung für die Wetterquelle, Zonen und Programmierung.

Wichtige Konfigurationspunkte:

- Zonebezeichnung, Fläche, Wasserdüngungsrate, Anzahl von Ausläufern, Effizienz, Koeffizient des Wasserverbrauchs, Pflanzenanzahl und Belüftungskoeffizient
- Wochentage und Monate pro Zone
- Regenwurfschwelle, Regenfaktor und maximale Laufdauer
- Sonnenaufgangswinkel, Zyklen, Temperaturschwellen und Prüfläufe
- Spracheinstellung, Pushover, Morgendiätendurchsicht und HomeKit

## Dashboard und Lauffunktionen

Das integrierte Dashboard bietet:

- Übersicht über den Zustand von Laufdauer, Wetterdaten und Programmierung
- Karten für jede Zone mit manuellem Start und Stopp
- Laufschalter für Masterschalter und Pushover
- Backup-/Restore-Dialog mit nativer Import-Export-Unterstützung und Vorbereitung der Legacy-Importierung
- HomeKit-Dialog mit Port, Pin, QR-Code und Hinweis auf verfügbare Alternativen
- Testfunktionen für Relays, Programmierung und Pushover
- Status- und Diagnosewerte für Laufdauer, ETo, Regenmenge, Wasserdüngung und nächster Start

## HomeKit

Wenn HomeKit aktiviert ist, startet IrrigationPro sein eigenes native HAP-Bridge.

Es werden folgende Funktionen angeboten:

- Ein eigener Bewässerungsbereich in Apple Home
- Eine Mapping-Funktion für jede Zone für die Verwaltung der Valves
- Separate Masterschalter als HomeKit-Switch und separate Pushover-Benachrichtigungsschalter
- QR-Code-Paring und automatische Portsuche
- AccessoryInformation mit Hersteller, Modellnummer, Seriennummer und Firmwareversion

Notizen:

- Der konfigurierte HAP-Port muss frei sein und darf nicht mit einem bestehenden Home Assistant HomeKit Bridge konflizieren.
- Sollte der konfigurierte Port bereits belegt sein, wird IrrigationPro einen freien alternativen Vorschlag machen.
- Nach einer strukturellen Änderung im HomeKit kann es erforderlich sein, den Bridge neu zuzupaaren in Apple Home.

## Pushover und Morgendiätendurchsicht

IrrigationPro kommuniziert direkt mit der Pushover API. Eine separate Home Assistant-Pushover Integration ist nicht notwendig.

Unterstützte Funktionen:

- Start- und Stoppbenachrichtigungen
- Zone-Startbenachrichtigungen
- Fehlerbenachrichtigungen
- Morgendiätendurchsicht mit geplantem Bewässerungsplan und Wettervoraussagen
- Laufschalter direkt aus dem Dashboard und HomeKit

## Entitäten

Es werden für jede Zone folgende Entitäten erstellt:

- switch.irrigation_zone_X
- valve.irrigation_zone_X
- sensor.irrigation_zone_X_duration
- sensor.irrigation_zone_X_eto
- sensor.irrigation_zone_X_next_run
- binary_sensor.irrigation_zone_X_running

## Unterstützung

- GitHub Issues: [Issues](https://github.com/AniGerm/IrrigationPro/issues)
- Home Assistant Community: [Community](https://community.home-assistant.io/)


## Beitragen

1. Klone das Repository.
2. Erzeuge einen Feature-Branch.
3. Kommite deine Änderungen.
4. Öffne einen Pull Request.

