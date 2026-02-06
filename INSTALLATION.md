# Installation und Update Guide

## Erstinstallation

### Option 1: HACS Installation (Empfohlen)

1. **HACS öffnen**
   - Navigiere zu HACS in Home Assistant
   - Klicke auf "Integrationen"

2. **Repository hinzufügen**
   - Klicke auf die drei Punkte (⋮) oben rechts
   - Wähle "Benutzerdefinierte Repositories"
   - Füge die URL hinzu: `https://github.com/AniGerm/IrrigationPro`
   - Kategorie: "Integration"
   - Klicke "Hinzufügen"

3. **Integration installieren**
   - Suche nach "IrrigationPro"
   - Klicke auf "Herunterladen"
   - Warte bis der Download abgeschlossen ist

4. **Home Assistant neu starten**
   - Gehe zu Einstellungen → System → Neu starten
   - Warte bis HA vollständig neu gestartet ist

5. **Integration konfigurieren**
   - Gehe zu Einstellungen → Geräte & Dienste
   - Klicke "+ Integration hinzufügen"
   - Suche "IrrigationPro"
   - Folge dem Setup-Assistenten

### Option 2: Manuelle Installation

1. **Dateien kopieren**
   ```bash
   cd /config
   mkdir -p custom_components
   cd custom_components
   git clone https://github.com/AniGerm/IrrigationPro.git irrigationpro
   # Oder: ZIP herunterladen und entpacken
   ```

2. **Verzeichnisstruktur prüfen**
   ```
   /config/custom_components/irrigationpro/
   ├── __init__.py
   ├── manifest.json
   ├── config_flow.py
   ├── coordinator.py
   ├── const.py
   ├── eto.py
   ├── weather_provider.py
   ├── switch.py
   ├── sensor.py
   ├── binary_sensor.py
   ├── services.yaml
   ├── strings.json
   └── translations/
       └── de.json
   ```

3. **Home Assistant neu starten**

4. **Integration hinzufügen** (siehe Schritt 5 oben)

## Update

### Via HACS

1. Öffne HACS → Integrationen
2. Suche "IrrigationPro"
3. Klicke auf die Integration
4. Wenn ein Update verfügbar ist, klicke "Aktualisieren"
5. Starte Home Assistant neu

### Manuell

1. **Backup erstellen** (wichtig!)
   ```bash
   cd /config/custom_components
   cp -r irrigationpro irrigationpro.backup
   ```

2. **Neue Version herunterladen**
   ```bash
   cd /config/custom_components/irrigationpro
   git pull
   # Oder: Neue ZIP herunterladen und ersetzen
   ```

3. **Home Assistant neu starten**

4. **Konfiguration prüfen**
   - Gehe zu Einstellungen → Geräte & Dienste
   - Finde IrrigationPro
   - Prüfe ob alle Zonen korrekt angezeigt werden

## Migration von anderen Systemen

### Von Homebridge IrrigationPro

Wenn du von der Homebridge-Version migrierst:

1. **Notiere deine aktuelle Konfiguration**
   - Zoneneinstellungen
   - Crop Coefficients
   - Solar Radiation Werte
   - Zeitplan-Parameter

2. **Installiere IrrigationPro** (siehe oben)

3. **Übertrage Einstellungen im Setup**
   - Die meisten Parameter sind identisch
   - Crop Coefficient: Gleicher Wert
   - Plant Density: Gleicher Wert
   - Exposure Factor: Gleicher Wert

4. **Automationen anpassen**
   - Ersetze Homebridge-Entities durch neue IrrigationPro Entities
   - Beispiel:
     ```yaml
     # Alt:
     entity_id: switch.homebridge_zone_1
     
     # Neu:
     entity_id: switch.irrigation_zone_1
     ```

## Troubleshooting Installation

### Problem: Integration erscheint nicht

**Lösung:**
```bash
# Prüfe Logs
tail -f /config/home-assistant.log | grep irrigationpro

# Prüfe Berechtigungen
ls -la /config/custom_components/irrigationpro/

# Alle Dateien sollten lesbar sein
chmod -R 755 /config/custom_components/irrigationpro/
```

### Problem: "Domain bereits geladen"

**Lösung:**
1. Stoppe Home Assistant
2. Lösche `__pycache__` Verzeichnisse:
   ```bash
   find /config/custom_components/irrigationpro -type d -name __pycache__ -exec rm -rf {} +
   ```
3. Starte Home Assistant

### Problem: Config Flow startet nicht

**Lösung:**
1. Prüfe ob eine Weather Entity existiert:
   ```bash
   # In Home Assistant Developer Tools → States
   # Suche nach "weather."
   ```
2. Wenn keine vorhanden, installiere eine Weather Integration zuerst
3. Versuche die Integration erneut hinzuzufügen

## Deinstallation

1. **Integration entfernen**
   - Gehe zu Einstellungen → Geräte & Dienste
   - Finde IrrigationPro
   - Klicke auf die drei Punkte (⋮)
   - Wähle "Löschen"

2. **Dateien entfernen**
   ```bash
   rm -rf /config/custom_components/irrigationpro
   ```

3. **Storage bereinigen** (optional)
   ```bash
   rm /config/.storage/irrigationpro_storage
   ```

4. **Home Assistant neu starten**

## Backup & Restore

### Backup erstellen

```bash
# Vollständiges Backup
cd /config
tar -czf irrigationpro_backup_$(date +%Y%m%d).tar.gz \
  custom_components/irrigationpro \
  .storage/irrigationpro_storage \
  .storage/core.config_entries

# Nur Konfiguration
cp .storage/core.config_entries .storage/core.config_entries.backup
```

### Backup wiederherstellen

```bash
# Vollständiges Restore
cd /config
tar -xzf irrigationpro_backup_20260206.tar.gz

# Nur Konfiguration
cp .storage/core.config_entries.backup .storage/core.config_entries
```

## Systemanforderungen

- **Home Assistant**: Version 2023.1 oder neuer
- **Python**: 3.11+ (wird von HA bereitgestellt)
- **Speicher**: < 10 MB
- **CPU**: Minimal (nur bei Berechnungen)
- **Netzwerk**: 
  - Für HA Weather Entity: Lokal
  - Für OWM API: Internet-Zugang erforderlich

## Support

Bei Problemen:
1. Prüfe die [README.md](README.md)
2. Durchsuche [GitHub Issues](https://github.com/AniGerm/IrrigationPro/issues)
3. Erstelle ein neues Issue mit:
   - Home Assistant Version
   - IrrigationPro Version
   - Relevante Logs
   - Beschreibung des Problems
