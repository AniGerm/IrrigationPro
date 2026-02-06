# Contributing to IrrigationPro

Danke für dein Interesse, zu IrrigationPro beizutragen! 🎉

## Wie kann ich beitragen?

### Bug Reports
- Nutze [GitHub Issues](https://github.com/AniGerm/IrrigationPro/issues)
- Beschreibe das Problem detailliert
- Füge Logs hinzu (mit aktiviertem Debug-Level)
- Home Assistant Version angeben
- IrrigationPro Version angeben

### Feature Requests
- Öffne ein Issue mit Label "enhancement"
- Beschreibe den Use Case
- Erkläre, warum das Feature nützlich wäre

### Code Contributions

1. **Fork das Repository**
2. **Erstelle einen Branch**
   ```bash
   git checkout -b feature/mein-feature
   ```
3. **Mache deine Änderungen**
   - Halte dich an den bestehenden Code-Stil
   - Füge Type Hints hinzu
   - Dokumentiere neue Features
4. **Teste deine Änderungen**
   - Teste mit echter Hardware wenn möglich
   - Prüfe Logs auf Fehler
5. **Commit**
   ```bash
   git commit -m "feat: Beschreibung der Änderung"
   ```
6. **Push und Pull Request**
   ```bash
   git push origin feature/mein-feature
   ```

## Code-Stil

- Python 3.11+
- Type Hints für alle Funktionen
- Async/await wo möglich
- Docstrings für Module und Klassen
- Logging statt print()
- Home Assistant Best Practices

## Commit Messages

Nutze [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` Neue Features
- `fix:` Bug Fixes
- `docs:` Dokumentation
- `refactor:` Code-Refactoring
- `test:` Tests
- `chore:` Maintenance

## Testen

```bash
# Home Assistant Installation
# Kopiere custom_components/irrigationpro nach config/custom_components/
# Starte HA neu
# Teste die Integration

# Logs prüfen
tail -f /config/home-assistant.log | grep irrigationpro
```

## Übersetzungen

Neue Sprachen sind willkommen!

1. Kopiere `custom_components/irrigationpro/translations/de.json`
2. Übersetze die Strings
3. Speichere als `xx.json` (ISO 639-1 Code)
4. Pull Request erstellen

## Fragen?

Öffne ein Issue oder frage in der [Home Assistant Community](https://community.home-assistant.io/).

Danke! 🙏
