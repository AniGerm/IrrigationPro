# Changelog

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/lang/de/).

## [2.2.6] - 2026-04-09

### Behoben
- **Flow-Rate Obergrenze erhöht:** Config-Flow erlaubt jetzt bis 3000 L/h statt max. 100 — notwendig für Getrieberegner (500–1500 L/h) und Versenkregner (800–2500 L/h)

### Verbessert
- Labels in Config-Flow klarer formuliert: „Durchfluss pro Emitter/Sprinkler" statt nur „Emitter-Durchfluss"
- Tooltips im Frontend erweitert mit realistischen Bereichen für alle Sprinkler-Typen (MP-Rotator, Getrieberegner, Versenkregner)
- Beispielrechnung in Tooltips aktualisiert (3 Getrieberegner × 800 L/h = 2400 L/h)

### Geändert
- Manifest-Version auf 2.2.6 angehoben

## [2.2.5] - 2026-04-05

### Behoben
- **Pushover-Spam endgültig behoben:** Einzelne Feuchtigkeits-Pushover-Nachrichten pro Zone bei der stündlichen Neuberechnung komplett entfernt. Die Information wird stattdessen im täglichen Morgenreport übermittelt (Zonen mit Skip-Grund: ⏭ Zone: Bodenfeuchte zu hoch …)
- Safety-Net in `_water_zone()` loggt weiterhin den Skip, sendet aber keine separate Push-Nachricht mehr

### Geändert
- Manifest-Version auf 2.2.5 angehoben

## [2.2.4] - 2026-04-05

### Behoben
- **Pushover-Spam behoben:** Feuchtigkeits-Benachrichtigungen (Übersprungen/Reduziert) werden jetzt nur einmal pro Tag gesendet statt bei jedem stündlichen Update
- **"Keine Zonen konfiguriert" behoben:** Wenn alle Zonen wegen Bodenfeuchte übersprungen werden, zeigt die Meldung jetzt korrekt die Zonen mit ihren Skip-Gründen an (⏭ Zone: Grund)
- **Phantom-Bewässerung behoben:** Wenn alle Zonen 0 Dauer haben (z.B. Boden feucht), wird kein Bewässerungslauf mehr geplant (Start ≠ Ende, Dauer ≠ 00:00)
- **Daily Report:** Wird jetzt auch korrekt registriert wenn keine Bewässerung nötig ist

### Geändert
- Manifest-Version auf 2.2.4 angehoben

## [2.2.3] - 2025-07-12

### Behoben
- **Kritischer Bugfix:** Bodenfeuchte-Sensoren wurden bei der Bewässerungsplanung nicht berücksichtigt – Zonen liefen trotz 87–100% Feuchte mit voller Dauer
- Bewässerungsplanung prüft jetzt aktiv die aktuelle Bodenfeuchte pro Zone:
  - Feuchte ≥ Ziel-Maximum → Zone wird komplett übersprungen
  - Feuchte zwischen Min und Max → Dauer wird proportional reduziert
- Sicherheits-Nachprüfung direkt vor Ventilöffnung: Falls Feuchte seit der Planung gestiegen ist, wird die Zone übersprungen

### Hinzugefügt
- Pushover-Benachrichtigung bei feuchtigkeitsbedingtem Überspringen oder Reduzieren einer Zone
- Frontend: Feuchtigkeits-Badge wird rot bei Überschreitung des Zielwerts
- Frontend: Reduktions-Badge (⚡ -X%) bei feuchtigkeitsbedingter Dauerkürzung
- API: `moisture_reduction` pro Zone im Status-Endpoint

### Geändert
- Manifest-Version auf 2.2.3 angehoben

## [2.2.2] - 2026-03-28

### Hinzugefügt
- Pushover-Alerts bei Sensor-Verbindungsverlust (nach 30 Min. Offline → zweisprachige Benachrichtigung)
- Pushover-Alert wenn Sensor-Batterie unter 15% fällt (mit Aufforderung zum Tausch)
- Pushover-Recovery-Meldung wenn Sensor wieder erreichbar ist
- Frontend: Feuchtigkeits-Badge (💧) und Lern-Badge (🧠) in Zone-Kacheln
- Frontend: Lern-Detail-Modal mit Journal, Statistiken und Reset
- Frontend: Vegetationstyp-Auswahl, Sensor-Entity-Feld, Ziel-Feuchte in Zonen-Einstellungen
- API: `sensor_entities` Liste und `current_moisture` pro Zone in Status-Antwort

### Geändert
- Manifest-Version auf 2.2.2 angehoben

## [2.2.1] - 2026-03-28

### Hinzugefügt
- Lernmodul für automatische Bodenfeuchte-Nachregelung pro Zone (`learning.py`)
- Neue API-Endpoints für Learning-Status, Journal, Reset und Vegetationstypen
- Neue Sensoren pro Zone für Bodenfeuchte, Lernkorrektur und Lern-Konfidenz
- Neuer Service `irrigationpro.reset_learning` zum Zurücksetzen von Lernwerten

### Geändert
- Config Flow um Vegetationstyp, Bodenfeuchte-Sensor, Ziel-Feuchtebereich und Lernschalter erweitert
- Bewässerungsdauer-Berechnung um lernbasierten Korrekturfaktor ergänzt
- Manifest-Version auf 2.2.1 angehoben

### Technische Details
- Wissenschaftlich basierte Zielwerte pro Vegetationstyp (FAO-56/MAD-orientiert)
- Verzögerte Feedback-Erfassung nach Bewässerung zur robusteren Korrekturbildung
- Persistentes Learning-Journal mit gewichteter Auswertung und begrenzten Korrekturschritten

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
