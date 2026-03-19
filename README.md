# IrrigationPro für Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Release](https://img.shields.io/github/release/AniGerm/IrrigationPro.svg)](https://github.com/AniGerm/IrrigationPro/releases)

IrrigationPro ist eine wissenschaftlich fundierte Bewässerungssteuerung für Home Assistant. Die Integration berechnet den Wasserbedarf pro Zone auf Basis der FAO-56 Penman-Monteith Evapotranspiration, bietet ein eigenes Dashboard im Home Assistant Frontend, unterstützt Backup und Restore der Konfiguration und kann optional eine native HomeKit-Sprinkler-Bridge bereitstellen.

Der aktuelle veröffentlichungsreife Stand ist Version 2.1.7. Das Repository ist als HACS-Custom-Repository strukturiert und enthält bereits die nötigen Validierungs-Workflows für HACS und Hassfest.

## Features

- Klimaadaptive Bewässerungsplanung für bis zu 16 Zonen
- Native Home Assistant Integration mit Config Flow, Services und Dashboard-Panel
- Native HomeKit-Sprinkler-Bridge mit QR-Pairing, automatischer Port-Empfehlung, Zonen, Laufzeit und separaten Runtime-Schaltern
- Master-Schalter zum globalen Pausieren/Freigeben der Bewässerung
- Pushover-Benachrichtigungen direkt über die Pushover-API
- Täglicher Morgenbericht mit geplantem Lauf und Wetterzusammenfassung
- Backup, Restore und vorbereiteter Legacy-Import der kompletten Konfiguration
- DE/EN Sprachumschaltung im UI und für Laufzeit-Benachrichtigungen
- Home Assistant Wetterdaten oder OpenWeatherMap als Fallback
- Stabiler Start auch bei vorübergehend nicht verfügbarer Wetter-Entity mit automatischem Retry
- Zone-spezifische Wochentage, Monate, adaptive Parameter und Laufzeitdiagnosen

## Voraussetzungen

- Home Assistant 2023.1 oder neuer
- Mindestens eine schaltbare Ventil-/Relais-Infrastruktur in Home Assistant
- Eine Weather-Entity in Home Assistant oder alternativ ein OpenWeatherMap API Key
- Optional für HomeKit: freier TCP-Port für den HAP-Server

## Installation

### HACS

1. Öffne HACS in Home Assistant.
2. Gehe zu Integrationen.
3. Öffne das Menü oben rechts und wähle Benutzerdefinierte Repositories.
4. Füge https://github.com/AniGerm/IrrigationPro als Integration hinzu.
5. Installiere IrrigationPro und starte Home Assistant neu.

Hinweis: Solange das Repository noch nicht in der HACS-Standardliste aufgenommen wurde, erfolgt die Installation über Benutzerdefinierte Repositories. Nach erfolgreicher Aufnahme in HACS kann IrrigationPro direkt über die Suche gefunden werden.

### Manuell

1. Kopiere den Ordner custom_components/irrigationpro nach config/custom_components/.
2. Starte Home Assistant neu.

## Einrichtung

1. Öffne Einstellungen → Geräte & Dienste.
2. Klicke auf Integration hinzufügen.
3. Suche nach IrrigationPro.
4. Folge dem Assistenten für Wetterquelle, Zonen und Zeitplanung.

Wichtige Konfigurationspunkte:

- Zonenname, Fläche, Durchflussrate, Emitter-Anzahl, Effizienz, Crop Coefficient, Pflanzendichte und Expositionsfaktor
- Wochentage und Monate pro Zone
- Niederschlagsgrenze, Regenfaktorisierung und maximale Laufzeit
- Sonnenaufgang-Offset, Zyklen, Temperaturschwellen und Recheck-Zeit
- Sprache, Pushover, Tagesbericht und HomeKit

## Dashboard und Laufzeitfunktionen

Das integrierte Dashboard bietet:

- Statusübersicht für Laufzeiten, Wetter und Planung
- Zonenkarten mit manuellem Start/Stop
- Runtime-Schalter für Hauptschalter und Pushover
- Backup/Restore-Dialog mit nativer Export-/Importfunktion und vorbereiteter Legacy-Konvertierung
- HomeKit-Dialog mit Port, PIN, QR-Code und Hinweis auf freie Alternativ-Ports
- Testfunktionen für Relais, Planung und Pushover
- Status- und Diagnosewerte für Dauer, ETo, Niederschlag, Wasserbedarf und nächsten Lauf

## HomeKit

Wenn HomeKit aktiviert ist, startet IrrigationPro eine eigene native HAP-Bridge.

Bereitgestellt werden:

- Eine native Bewässerungsanlage in Apple Home
- Eine Valve-Service-Zuordnung pro Zone
- Ein separater Hauptschalter als HomeKit-Switch
- Ein separater Benachrichtigungsschalter für Pushover
- QR-Pairing und PIN-basiertes Koppeln
- AccessoryInformation mit Hersteller, Modell, Seriennummer und Firmware-Version

Hinweise:

- Der HomeKit-Port muss frei sein und darf nicht mit einer bestehenden HA-HomeKit-Bridge kollidieren.
- Wenn der konfigurierte Port belegt ist, schlägt IrrigationPro automatisch einen freien alternativen Port vor.
- Nach strukturellen HomeKit-Änderungen kann es nötig sein, die Bridge in Apple Home neu zu koppeln.

## Pushover und Tagesbericht

IrrigationPro spricht die Pushover-API direkt an. Eine separate Home Assistant Pushover-Integration ist dafür nicht erforderlich.

Unterstützt werden:

- Start- und Stop-Benachrichtigungen
- Zonenstart-Benachrichtigungen
- Fehlermeldungen
- Testbenachrichtigungen aus dem Dashboard
- Optionaler täglicher Morgenbericht mit geplanter Bewässerung und Wetterdaten
- Laufzeitumschaltung direkt aus Dashboard und HomeKit

## Entities

Pro Zone werden typischerweise folgende Entities angelegt:

- switch.irrigation_zone_X
- valve.irrigation_zone_X
- sensor.irrigation_zone_X_duration
- sensor.irrigation_zone_X_eto
- sensor.irrigation_zone_X_next_run
- binary_sensor.irrigation_zone_X_will_run_today

## Services

### irrigationpro.start_zone

Startet eine Zone manuell für eine angegebene Dauer.

```yaml
service: irrigationpro.start_zone
data:
  zone_id: 1
  duration: 15
```

### irrigationpro.stop_zone

Stoppt eine laufende Zone.

```yaml
service: irrigationpro.stop_zone
data:
  zone_id: 1
```

### irrigationpro.recalculate

Erzwingt eine Neuberechnung des Bewässerungsplans.

```yaml
service: irrigationpro.recalculate
```

## Backup und Restore

Die Integration unterstützt Export und Restore der kompletten Konfiguration.

- Natives Backup-Format: irrigationpro-backup-v1
- Legacy-Import aus SmartSprinklers-ähnlichen Setups
- Zonenspezifische Wochentage und Monate werden mitgeführt
- Wiederherstellung über Dashboard-API mit vorbereiteter Prüf- und Bearbeitungsstufe

Zusätzlich steht ein Konvertierungsskript für Legacy-Daten bereit:

- tools/convert_legacy_setup_to_backup.py

## Verhalten bei fehlenden Wetterdaten

Wenn die konfigurierte Wetter-Entity beim Start oder zur Laufzeit vorübergehend nicht verfügbar ist, bleibt die Integration geladen. IrrigationPro setzt die Planung in einen sicheren Wartezustand und versucht automatisch im 2-Minuten-Takt erneut, Wetterdaten abzurufen, bis wieder eine valide Prognose verfügbar ist.

## Automationen

IrrigationPro steuert keine reale Hardware direkt. Die tatsächliche Ventilschaltung erfolgt über deine vorhandenen Home Assistant Entities und Automationen.

Beispiel:

```yaml
automation:
  - alias: "Bewässerung Zone 1 - Ventil steuern"
    trigger:
      - platform: state
        entity_id: switch.irrigation_zone_1
    action:
      - service: switch.turn_{{ trigger.to_state.state }}
        target:
          entity_id: switch.gardena_valve_1
```

## Wissenschaftlicher Hintergrund

Die Referenz-Evapotranspiration wird nach FAO-56 berechnet. Berücksichtigt werden unter anderem:

- Min-/Max-Temperatur
- relative Luftfeuchtigkeit
- Windgeschwindigkeit
- solare Strahlung
- atmosphärischer Druck
- geografische Lage und Jahreszeit

Vereinfacht gilt:

```text
Wasserbedarf = (ETo - Regen) × Crop_Koeff × Pflanzendichte × Exposure_Factor × Fläche / Effizienz
Dauer = Wasserbedarf / (Durchflussrate × Anzahl_Emitter)
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
