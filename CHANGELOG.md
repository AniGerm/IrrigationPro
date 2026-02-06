# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

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
