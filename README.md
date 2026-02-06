# IrrigationPro für Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Release](https://img.shields.io/github/release/AniGerm/IrrigationPro.svg)](https://github.com/AniGerm/IrrigationPro/releases)

Eine moderne, intelligente Bewässerungssteuerung für Home Assistant, basierend auf wissenschaftlichen Prinzipien der Evapotranspiration (ETo).

## 🌟 Features

- **Wissenschaftlich fundiert**: Berechnung der Evapotranspiration nach FAO-56 Penman-Monteith Methode
- **Klimaadaptiv**: Automatische Anpassung der Bewässerung basierend auf Wetter und Pflanzenbedarf
- **Multi-Zonen**: Unterstützung für bis zu 16 unabhängige Bewässerungszonen
- **Intelligente Planung**: Automatische Berechnung optimaler Bewässerungszeiten
- **Wetterintegration**: Nutzung von Home Assistant Weather Entities oder OpenWeatherMap API
- **Regenfaktorisierung**: Berücksichtigung von Niederschlag zur Wassereinsparung
- **Flexible Konfiguration**: UI-basiertes Setup über Config Flow
- **Home Assistant Native**: Vollständig async, mit modernen HA-Patterns

## 📋 Voraussetzungen

- Home Assistant 2023.1 oder neuer
- Eine Weather Entity in Home Assistant **ODER** OpenWeatherMap API Key (One Call 3.0)
- Bewässerungssystem mit schaltbaren Ventilen (z.B. über Smart Plugs, Sonoff, etc.)

## 🚀 Installation

### HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Gehe zu "Integrationen"
3. Klicke auf die drei Punkte oben rechts und wähle "Benutzerdefinierte Repositories"
4. Füge diese Repository-URL hinzu: `https://github.com/AniGerm/IrrigationPro`
5. Kategorie: "Integration"
6. Klicke auf "Hinzufügen"
7. Suche nach "IrrigationPro" und installiere es
8. Starte Home Assistant neu

### Manuell

1. Kopiere den `custom_components/irrigationpro` Ordner in dein Home Assistant `config/custom_components/` Verzeichnis
2. Starte Home Assistant neu

## ⚙️ Konfiguration

### UI Setup

1. Gehe zu **Einstellungen** → **Geräte & Dienste**
2. Klicke auf **Integration hinzufügen**
3. Suche nach **IrrigationPro**
4. Folge dem Setup-Assistenten:

#### Schritt 1: Wetterquelle
- Wähle deine Weather Entity aus
- Optional: Aktiviere OpenWeatherMap als Fallback
- Optional: Gib deinen OWM API Key ein

#### Schritt 2: Anzahl der Zonen
- Wähle die Anzahl der Bewässerungszonen (1-16)

#### Schritt 3: Zonenkonfiguration
Für jede Zone:
- **Name**: Beschreibender Name (z.B. "Rasen vorne")
- **Fläche**: Bewässerte Fläche in m²
- **Durchflussrate**: Emitter-Durchfluss in L/h (pro Emitter)
- **Anzahl Emitter**: Anzahl der Tropfer/Sprinkler
- **Effizienz**: System-Effizienz in % (typisch 90% für Tropfbewässerung)
- **Crop Coefficient**: Pflanzen-Koeffizient (0.1-0.9)
  - 0.1-0.3: Trockenheitstolerante Pflanzen, Sukkulenten
  - 0.4-0.6: Durchschnittliche Sträucher, Stauden
  - 0.7-0.9: Rasen, wasserliebende Pflanzen
- **Pflanzendichte**: (0.5-1.3)
  - 0.5-0.9: Spärlich bepflanzt
  - 1.0: Durchschnittliche Bepflanzung
  - 1.1-1.3: Dichte Bepflanzung
- **Exposure Factor**: Mikroklimat-Faktor (0.5-1.4)
  - 0.5-0.9: Geschützt, teilweise schattig
  - 1.0: Freies Feld
  - 1.1-1.4: Exponiert, windig
- **Max. Dauer**: Maximale Bewässerungsdauer in Minuten
- **Regenschwelle**: Niederschlagsmenge (mm), ab der Bewässerung übersprungen wird
- **Regenfaktorisierung**: Regen in Berechnung einbeziehen
- **Zone aktiviert**: Zone einschalten
- **Adaptive Bewässerung**: Klimabasierte Berechnung nutzen

#### Schritt 4: Zeitplanung
- **Sonnenaufgang-Offset**: Minuten vor Sonnenaufgang (negativ = nach Sonnenaufgang)
- **Zyklen**: Anzahl der Bewässerungszyklen pro Durchgang (1-5)
- **Niedrige Temperatur**: Min. Temperatur-Schwellwert (°C)
- **Hohe Temperatur**: Min. Max-Temperatur-Schwellwert (°C)
- **Recheck-Zeit**: Minuten vor Start erneut prüfen (0 = deaktiviert)

## 📊 Entities

Die Integration erstellt pro Zone folgende Entities:

### Switch
- `switch.irrigation_zone_X` - Zonensteuerung (Ein/Aus)

### Sensoren
- `sensor.irrigation_zone_X_duration` - Geplante Bewässerungsdauer (Minuten)
- `sensor.irrigation_zone_X_eto` - Evapotranspiration bis zur nächsten Bewässerung (mm)
- `sensor.irrigation_zone_X_next_run` - Zeitstempel der nächsten Bewässerung

### Binary Sensoren
- `binary_sensor.irrigation_zone_X_will_run_today` - Wird heute bewässert?

## 🔧 Services

### `irrigationpro.start_zone`
Startet eine Zone manuell für eine bestimmte Dauer.

```yaml
service: irrigationpro.start_zone
data:
  zone_id: 1
  duration: 15  # Minuten
```

### `irrigationpro.stop_zone`
Stoppt eine laufende Zone.

```yaml
service: irrigationpro.stop_zone
data:
  zone_id: 1
```

### `irrigationpro.recalculate`
Erzwingt Neuberechnung des Bewässerungsplans.

```yaml
service: irrigationpro.recalculate
```

## 🤖 Automationen

### Beispiel: Ventil mit Zone synchronisieren

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

### Beispiel: Benachrichtigung bei Start

```yaml
automation:
  - alias: "Bewässerung - Start-Benachrichtigung"
    trigger:
      - platform: state
        entity_id: switch.irrigation_zone_1
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Bewässerung gestartet"
          message: "Zone 1 wird für {{ state_attr('sensor.irrigation_zone_1_duration', 'state') }} Minuten bewässert"
```

## 📐 Wissenschaftlicher Hintergrund

### Evapotranspiration (ETo)

Die Integration berechnet die Referenz-Evapotranspiration nach der [FAO-56 Penman-Monteith Methode](http://www.fao.org/3/X0490E/x0490e00.htm). Dabei werden berücksichtigt:

- Min/Max Temperaturen
- Relative Luftfeuchtigkeit
- Windgeschwindigkeit
- Solare Strahlung
- Atmosphärischer Druck
- Geografische Position (Breite, Höhe)
- Julianischer Tag

### Zonenbedarf Berechnung

Der Wasserbedarf einer Zone wird wie folgt berechnet:

```
Wasserbedarf = (ETo - Regen) × Crop_Koeff × Pflanzendichte × Exposure_Factor × Fläche / Effizienz
Dauer = Wasserbedarf / (Durchflussrate × Anzahl_Emitter)
```

## 🌤️ Wetterquellen

### Home Assistant Weather Entity
Die bevorzugte Methode nutzt eine bestehende Weather Entity in Home Assistant:
- Wettervorhersage wird von der Entity abgerufen
- Unterstützt alle HA Weather-Integrationen
- Keine zusätzlichen API-Schlüssel nötig

### OpenWeatherMap Fallback
Optional kann die moderne OWM One Call 3.0 API als Fallback genutzt werden:
- Kostenlose Tier: 1000 Aufrufe/Tag
- Anmeldung: [OpenWeatherMap](https://openweathermap.org/api)

## 🔧 Erweiterte Konfiguration

### Solar Radiation Daten

Die Integration nutzt standardmäßig durchschnittliche Werte von 6 kWh/m²/Tag. Für präzisere Berechnungen können monatliche Werte konfiguriert werden.

Quellen für deine Region:
- [WeatherSpark](https://weatherspark.com/)
- NASA POWER Data
- Lokale Wetterstationen

### Hardware-Empfehlungen

- **Ventile**: 12V/24V DC Magnetventile
- **Steuerung**: 
  - Sonoff 4CH Pro (4 Zonen)
  - Shelly 4Pro (4 Zonen)
  - Relais-Module über ESPHome
- **Durchflussmesser**: Optional zur Verbrauchsüberwachung

## 🐛 Troubleshooting

### Keine Bewässerung geplant

Überprüfe:
- Temperature Schwellwerte erreicht?
- Zone aktiviert?
- Wettervorhersage verfügbar?
- Logs in Home Assistant: `custom_components.irrigationpro`

### Wetterabfrage schlägt fehl

- Prüfe Weather Entity Status
- Bei OWM: API Key korrekt?
- Netzwerkverbindung OK?

### Debug Logging aktivieren

```yaml
logger:
  default: info
  logs:
    custom_components.irrigationpro: debug
```

## 📝 YAML Konfiguration (Alternative)

Obwohl die UI-Konfiguration empfohlen wird, ist auch YAML möglich:

```yaml
# Nicht empfohlen - nutze Config Flow!
# Diese Struktur ist nur zur Information
```

## 🤝 Beitragen

Contributions sind willkommen! Bitte:
1. Fork das Repository
2. Erstelle einen Feature Branch
3. Committe deine Änderungen
4. Öffne einen Pull Request

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE)

## 🙏 Danksagung

Basierend auf der Arbeit von:
- [MTry/homebridge-smart-irrigation](https://github.com/MTry/homebridge-smart-irrigation) - Original Konzept und Logik
- [FAO Irrigation and Drainage Paper No. 56](http://www.fao.org/3/X0490E/x0490e00.htm) - Wissenschaftliche Grundlagen

## 📚 Weitere Ressourcen

- [FAO Penman-Monteith Equation](https://edis.ifas.ufl.edu/pdffiles/ae/ae45900.pdf)
- [UC ANR - Plant Water Use](https://ucanr.edu/sites/UrbanHort/Water_Use_of_Turfgrass_and_Landscape_Plant_Materials/)
- [Drip Irrigation Scheduling](https://ucanr.edu/sites/scmg/files/30917.pdf)

## 💬 Support

- GitHub Issues: [Issues](https://github.com/AniGerm/IrrigationPro/issues)
- Home Assistant Community: [Community](https://community.home-assistant.io/)

---

**Hinweis**: Diese Integration führt keine tatsächlichen Schaltoperationen durch. Sie stellt nur Steuerungs-Entities bereit. Die physische Ansteuerung der Ventile erfolgt über Automationen mit deinen vorhandenen Smart-Home-Geräten.
