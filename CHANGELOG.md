# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

## [2.1.8] - 2026-03-19

### Behoben
- GitHub Actions Validate-Workflow für aktuelle GitHub Runner und Action-Auflösung stabilisiert
- Hassfest-Anforderungen für Komponenten-Abhängigkeiten im Manifest ergänzt
- Manifest-Schlüsselreihenfolge an Hassfest angepasst

### Geändert
- Release-Stand nach den abschließenden HACS- und CI-Fixes auf 2.1.8 angehoben

## [2.1.7] - 2026-03-19

### Behoben
- HACS- und Repository-Metadaten auf den aktuellen Release-Stand 2.1.7 gebracht
- Authentifizierungs- und Publish-Details für die Veröffentlichung bereinigt
- README und Branding für den HACS-Einsatz überarbeitet

## [2.1.6] - 2026-03-18

### Geändert
- Lokalisierte Namen für HomeKit-Valves und Runtime-Switches ergänzt
- UI- und HomeKit-Statusaktualisierung beschleunigt

## [2.1.5] - 2026-03-18

### Behoben
- UI-Sprache und Backend-Sprache für Laufzeit-Pushover-Texte synchronisiert

## [2.1.4] - 2026-03-17

### Geändert
- Runtime-Switches in HomeKit klarer vom Sprinkler getrennt
- Benennung in HomeKit verbessert

## [2.1.3] - 2026-03-17

### Hinzugefügt
- Separate Runtime-Toggles für Hauptschalter und Pushover im Dashboard und in HomeKit

## [2.1.2] - 2026-03-17

### Hinzugefügt
- HomeKit AccessoryInformation mit Hersteller, Modell, Seriennummer und Firmware-Version ergänzt

## [2.1.1] - 2026-03-17

### Hinzugefügt
- Automatischer Vorschlag eines freien Ports, wenn der konfigurierte HomeKit-Port belegt ist

## [1.1.0] - 2026-02-06

### Hinzugefügt
- **Pushover-Benachrichtigungen**: Automatische Push-Benachrichtigungen bei Bewässerungsereignissen
  - Benachrichtigung bei Start des Bewässerungszyklus
  - Benachrichtigung bei Start einzelner Zonen (niedrige Priorität)
  - Benachrichtigung bei erfolgreichem Abschluss
  - Fehlerbenachrichtigungen bei Problemen
- Konfigurierbare Pushover-Einstellungen im Config Flow und Options Flow:
  - User Key
  - Device (optional)
  - Priorität (-2 bis 2)
- HACS_INSTALLATION.md mit detaillierter Anleitung für Installation über HACS
- Unterscheidung zwischen Integration und Add-on in Dokumentation
- Pushover-Setup-Anleitung in README.md

### Geändert
- Erweiterte UI-Übersetzungen (Deutsch und Englisch) für Pushover-Felder
- Verbesserte Dokumentation mit Pushover-Konfiguration

## [1.0.0] - 2026-02-06

### Hinzugefügt
- Initiales Release der IrrigationPro Integration
- ETo-Berechnung nach FAO-56 Penman-Monteith Methode
- Unterstützung für bis zu 16 Bewässerungszonen
- Integration mit Home Assistant Weather Entities
- Optional: OpenWeatherMap One Call 3.0 API als Fallback
- Multi-Zonen Bewässerungssteuerung
- Adaptive Bewässerungsberechnung basierend auf:
  - Evapotranspiration (ETo)
  - Niederschlag
  - Pflanzen-Koeffizienten
  - Pflanzendichte
  - Exposure-Faktoren
  - System-Effizienz
- Automatische Zeitplanung mit Sonnenaufgang-Synchronisation
- Zyklische Bewässerung (1-5 Zyklen)
- Temperatur-Schwellwerte für automatische Übersprünge
- Recheck-Funktion vor geplanter Bewässerung
- Persistente Speicherung der letzten Bewässerungszeiten
- UI-basierter Config Flow für einfaches Setup
- Services:
  - `irrigationpro.start_zone` - Manuelle Zonensteuerung
  - `irrigationpro.stop_zone` - Zone stoppen
  - `irrigationpro.recalculate` - Schedule neu berechnen
- Entities pro Zone:
  - Switch für Zonensteuerung
  - Sensor für Bewässerungsdauer
  - Sensor für ETo
  - Sensor für nächsten Lauf
  - Binary Sensor für "Läuft heute"
- Umfangreiche Dokumentation
- Beispiel-Automationen
- Deutsche Übersetzung

### Technische Details
- Vollständig async/await
- Type Hints
- Moderne Home Assistant Patterns (Coordinator, Config Flow)
- Saubere Trennung von Logik und HA-Integration
- Umfangreiches Logging
- Fehlerbehandlung

## [Unreleased]

### Geplant für zukünftige Versionen
- MQTT-Unterstützung für direkte Ventil-Ansteuerung
- Durchflussmesser-Integration
- Erweiterte Statistiken und Berichte
- Soil Moisture Sensor Integration
- Wettervorhersage-basierte Prognosen
- Kalender-Integration
- Grafana-Dashboard Templates
- Home Assistant Energy Dashboard Integration
- Backup/Restore für Bewässerungshistorie
- Import von Konfigurationen aus Homebridge-Smart-Irrigation
