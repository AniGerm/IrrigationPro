# HACS Installation für IrrigationPro

## Was ist der Unterschied zwischen Add-on und Integration?

### 🔌 Integration (IrrigationPro)
- **Was:** Python-Code, der IN Home Assistant läuft
- **Beispiele:** Integrationen wie Zigbee2MQTT-Binding, OpenWeatherMap, Tasmota
- **Installation:** Über HACS → Integrationen
- **Konfiguration:** Einstellungen → Geräte & Dienste

### 📦 Add-on
- **Was:** Separate Programme, die NEBEN Home Assistant laufen
- **Beispiele:** Mosquitto MQTT Broker, Zigbee2MQTT, Node-RED
- **Installation:** Supervisor → Add-on Store
- **Nur verfügbar:** Bei Home Assistant OS und Supervised

## ✅ Installation von IrrigationPro

### Schritt 1: HACS öffnen
1. Gehe in Home Assistant zu **HACS** (im Seitenmenü)
2. Klicke auf **Integrationen** (nicht Add-ons!)

### Schritt 2: Custom Repository hinzufügen
1. Klicke auf die **drei Punkte** (⋮) oben rechts
2. Wähle **Benutzerdefinierte Repositories**
3. Füge folgende URL ein:
   ```
   https://github.com/AniGerm/IrrigationPro
   ```
4. Wähle als Kategorie: **Integration**
5. Klicke auf **Hinzufügen**

### Schritt 3: IrrigationPro installieren
1. Suche in HACS nach **IrrigationPro**
2. Klicke auf die Integration
3. Klicke auf **Herunterladen**
4. Bestätige den Download
5. **Starte Home Assistant neu** (wichtig!)

### Schritt 4: Integration einrichten
1. Gehe zu **Einstellungen** → **Geräte & Dienste**
2. Klicke auf **Integration hinzufügen** (unten rechts, blauer Button)
3. Suche nach **IrrigationPro**
4. Folge dem Setup-Assistenten

## 🔍 Häufige Probleme

### "Not a valid add-on repository"
❌ **Problem:** Du versuchst es als Add-on zu installieren  
✅ **Lösung:** Gehe zu HACS → **Integrationen** (nicht Add-on Store!)

### "Integration nicht gefunden"
❌ **Problem:** HA wurde nach Installation nicht neu gestartet  
✅ **Lösung:** Gehe zu Entwicklertools → YAML → Neu starten → Neustart

### "HACS findet das Repository nicht"
❌ **Problem:** URL falsch eingegeben oder Kategorie falsch  
✅ **Lösung:** 
   - URL genau kopieren: `https://github.com/AniGerm/IrrigationPro`
   - Kategorie muss **Integration** sein

### "Custom Repositories-Option nicht sichtbar"
❌ **Problem:** HACS ist im Experimental Mode  
✅ **Lösung:** 
   1. HACS → Konfiguration (drei Punkte)
   2. Aktiviere "Experimental Features"
   3. Option erscheint nun

## 📱 Pushover Setup (optional)

Für Push-Benachrichtigungen:

### 1. Pushover Account erstellen
1. Gehe zu [pushover.net](https://pushover.net/)
2. Erstelle einen Account (30 Tage kostenlos, dann $5 einmalig)
3. Installiere die App auf deinem Smartphone

### 2. User Key kopieren
1. Logge dich im Pushover Dashboard ein
2. Kopiere deinen **User Key** (sichtbar auf der Startseite)

### 3. In IrrigationPro konfigurieren
1. Gehe zu **Einstellungen** → **Geräte & Dienste**
2. Suche **IrrigationPro**
3. Klicke auf **Optionen konfigurieren**
4. Aktiviere **Pushover**
5. Füge deinen **User Key** ein
6. Optional: Spezifisches Gerät angeben
7. Wähle Priorität:
   - `-2` = Keine Benachrichtigung, nur im Pushover Log
   - `-1` = Leise Benachrichtigung, keine Vibration
   - `0` = Standard (empfohlen)
   - `1` = Hohe Priorität mit Ton
   - `2` = Notfall (erfordert Bestätigung)

### Benachrichtigungen
Du erhältst automatisch Meldungen bei:
- 🚿 Start eines Bewässerungszyklus
- 💧 Start einzelner Zonen (niedrige Priorität)
- ✅ Erfolgreicher Abschluss
- ❌ Fehlern während der Bewässerung

## 🆘 Support

Bei Problemen:
1. Prüfe die [GitHub Issues](https://github.com/AniGerm/IrrigationPro/issues)
2. Aktiviere Debug-Logging:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.irrigationpro: debug
   ```
3. Erstelle ein [neues Issue](https://github.com/AniGerm/IrrigationPro/issues/new) mit:
   - Home Assistant Version
   - IrrigationPro Version
   - Debug-Logs
   - Beschreibung des Problems
