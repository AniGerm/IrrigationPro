# Upload zu GitHub - Anleitung

## ✅ Alle Anpassungen abgeschlossen!

### Was wurde geändert:

1. ✅ **Domain-Name**: `smart_irrigation` → `irrigationpro`
2. ✅ **Verzeichnis**: `custom_components/smart_irrigation/` → `custom_components/irrigationpro/`
3. ✅ **Integration Name**: "Smart Irrigation" → "IrrigationPro"
4. ✅ **GitHub-URL**: `https://github.com/AniGerm/IrrigationPro`
5. ✅ **Codeowner**: `@AniGerm`
6. ✅ **Alle Referenzen aktualisiert** in allen Dateien (.py, .json, .yaml, .md)

## 📦 Projektstruktur

```
IrrigationPro/
├── .github/
│   └── workflows/
│       └── validate.yaml          # GitHub Actions für HACS Validierung
├── custom_components/
│   └── irrigationpro/             # ✅ Umbenannt!
│       ├── __init__.py
│       ├── manifest.json          # ✅ Domain: irrigationpro
│       ├── const.py               # ✅ DOMAIN = "irrigationpro"
│       ├── coordinator.py
│       ├── config_flow.py
│       ├── eto.py
│       ├── weather_provider.py
│       ├── switch.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── services.yaml
│       ├── strings.json
│       └── translations/
│           └── de.json
├── .gitignore
├── hacs.json                      # ✅ HACS-Konfiguration
├── info.md                        # ✅ HACS Info-Seite
├── LICENSE
├── README.md                      # ✅ Alle Links aktualisiert
├── EXAMPLES.md
├── INSTALLATION.md
├── CHANGELOG.md
├── TRANSLATIONS.md
├── CONTRIBUTING.md                # ✅ Neu erstellt
└── PROJECT_OVERVIEW.md
```

## 🚀 Upload zu GitHub

### 1. Repository initialisieren

```bash
cd /home/max/Dokumente/Programme/IrrigationPro

# Git initialisieren
git init

# Alle Dateien hinzufügen
git add .

# Ersten Commit
git commit -m "feat: Initial release IrrigationPro v1.0.0

- FAO-56 Penman-Monteith ETo calculation
- Multi-zone irrigation control (up to 16 zones)
- Home Assistant Weather Entity integration
- OpenWeatherMap fallback support
- Adaptive watering based on ETo, rain, and plant factors
- UI-based Config Flow
- Services: start_zone, stop_zone, recalculate
- German and English translations
- Complete documentation and examples"
```

### 2. Remote Repository verbinden

```bash
# Remote hinzufügen
git remote add origin https://github.com/AniGerm/IrrigationPro.git

# Branch umbenennen zu main (falls nötig)
git branch -M main

# Push zu GitHub
git push -u origin main
```

### 3. GitHub Repository vorbereiten

Auf GitHub (https://github.com/AniGerm/IrrigationPro):

1. **About Section**:
   - Description: `Intelligente Bewässerungssteuerung für Home Assistant basierend auf FAO-56 Penman-Monteith ETo`
   - Website: `https://github.com/AniGerm/IrrigationPro`
   - Topics: `home-assistant`, `irrigation`, `smart-home`, `evapotranspiration`, `hacs`, `automation`, `iot`

2. **Release erstellen**:
   - Gehe zu "Releases" → "Create a new release"
   - Tag: `v1.0.0`
   - Title: `IrrigationPro v1.0.0 - Initial Release`
   - Description: (aus CHANGELOG.md kopieren)
   - Publish release

## 📦 HACS Integration

### Schritt 1: HACS Default Repository Request (Optional)

Für Aufnahme in HACS Default-Repositories:

1. Gehe zu: https://github.com/hacs/default
2. Erstelle einen Fork
3. Füge in `integration` hinzu:
   ```json
   {
     "name": "IrrigationPro",
     "domain": "irrigationpro"
   }
   ```
4. Pull Request erstellen

### Schritt 2: User Installation (sofort möglich)

User können jetzt installieren:

1. HACS öffnen
2. "Integrations" → "⋮" → "Custom repositories"
3. URL hinzufügen: `https://github.com/AniGerm/IrrigationPro`
4. Kategorie: "Integration"
5. "IrrigationPro" suchen und installieren

## ✅ Checkliste vor Upload

- [x] Domain-Name geändert (`irrigationpro`)
- [x] Verzeichnis umbenannt
- [x] manifest.json aktualisiert
- [x] hacs.json erstellt
- [x] info.md für HACS erstellt
- [x] GitHub-URLs aktualisiert
- [x] Codeowner gesetzt (@AniGerm)
- [x] README.md aktualisiert
- [x] Alle Services umbenannt
- [x] .github/workflows/validate.yaml erstellt
- [x] CONTRIBUTING.md erstellt
- [x] LICENSE vorhanden (MIT)
- [x] .gitignore vorhanden

## 🎯 Nach dem Upload

### Testen der Installation

1. **Via HACS Custom Repository**:
   ```
   HACS → Integrations → ⋮ → Custom repositories
   URL: https://github.com/AniGerm/IrrigationPro
   Kategorie: Integration
   ```

2. **Integration hinzufügen**:
   ```
   Einstellungen → Geräte & Dienste → Integration hinzufügen
   Suche: "IrrigationPro"
   ```

3. **Verifizieren**:
   - Config Flow öffnet sich
   - Wetterquelle auswählbar
   - Zonen konfigurierbar
   - Entities werden erstellt
   - Services verfügbar

### GitHub Repository Settings

1. **Branch Protection** (empfohlen):
   - Settings → Branches → Add rule
   - Branch name pattern: `main`
   - ☑ Require pull request reviews
   - ☑ Require status checks to pass

2. **Issues Templates**:
   - Erstelle `.github/ISSUE_TEMPLATE/`
   - Bug Report Template
   - Feature Request Template

3. **Discussions** (optional):
   - Settings → Features → Discussions aktivieren

## 📝 Commands Übersicht

```bash
# Lokales Git Setup
git init
git add .
git commit -m "feat: Initial release v1.0.0"

# Remote verbinden und pushen
git remote add origin https://github.com/AniGerm/IrrigationPro.git
git branch -M main
git push -u origin main

# Tag für Release erstellen
git tag -a v1.0.0 -m "IrrigationPro v1.0.0 - Initial Release"
git push origin v1.0.0

# Zukünftige Updates
git add .
git commit -m "fix: Beschreibung der Änderung"
git push

# Neues Release
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

## 🎉 Fertig!

Nach dem Upload ist IrrigationPro:
- ✅ Auf GitHub verfügbar
- ✅ Via HACS installierbar
- ✅ In Home Assistant nutzbar
- ✅ Für andere User verfügbar

## 📞 Support

Bei Fragen:
- GitHub Issues: https://github.com/AniGerm/IrrigationPro/issues
- Home Assistant Community
- Discussions (falls aktiviert)

---

**Viel Erfolg mit IrrigationPro! 🌱💧**
