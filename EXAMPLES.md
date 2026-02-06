# IrrigationPro - Beispiele

## Vollständige Automation für Zone 1

```yaml
# Ventil mit Zone synchronisieren
automation:
  - id: irrigation_zone_1_valve_control
    alias: "Bewässerung Zone 1 - Ventil steuern"
    description: "Steuert das physische Ventil basierend auf Zone 1 Status"
    trigger:
      - platform: state
        entity_id: switch.irrigation_zone_1
    action:
      - service: "switch.turn_{{ trigger.to_state.state }}"
        target:
          entity_id: switch.sonoff_zone_1
    mode: single

  # Failsafe: Ventil nach max Zeit abschalten
  - id: irrigation_zone_1_failsafe
    alias: "Bewässerung Zone 1 - Failsafe"
    description: "Schaltet Ventil nach 90 Minuten ab (Sicherheit)"
    trigger:
      - platform: state
        entity_id: switch.sonoff_zone_1
        to: "on"
        for:
          hours: 0
          minutes: 90
          seconds: 0
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.sonoff_zone_1
      - service: notify.mobile_app
        data:
          title: "⚠️ Bewässerung - Failsafe"
          message: "Zone 1 wurde nach 90 Minuten automatisch abgeschaltet!"
    mode: single
```

## Benachrichtigungen

```yaml
automation:
  # Start-Benachrichtigung mit Details
  - id: irrigation_start_notification
    alias: "Bewässerung - Start-Benachrichtigung"
    trigger:
      - platform: state
        entity_id: 
          - switch.irrigation_zone_1
          - switch.irrigation_zone_2
          - switch.irrigation_zone_3
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "💧 Bewässerung gestartet"
          message: >
            {{ trigger.to_state.name }} wird bewässert.
            Dauer: {{ state_attr(trigger.entity_id.replace('switch', 'sensor').replace('zone', 'zone') ~ '_duration', 'state') }} Minuten
            ETo: {{ state_attr(trigger.entity_id.replace('switch', 'sensor').replace('zone', 'zone') ~ '_eto', 'state') }} mm
          data:
            tag: irrigation_active
            group: irrigation

  # Ende-Benachrichtigung
  - id: irrigation_end_notification
    alias: "Bewässerung - Ende-Benachrichtigung"
    trigger:
      - platform: state
        entity_id:
          - switch.irrigation_zone_1
          - switch.irrigation_zone_2
          - switch.irrigation_zone_3
        to: "off"
        for:
          seconds: 5
    action:
      - service: notify.mobile_app
        data:
          title: "✅ Bewässerung abgeschlossen"
          message: "{{ trigger.from_state.name }} wurde bewässert"
          data:
            tag: irrigation_complete
            group: irrigation
```

## Dashboard Karten

### Lovelace YAML

```yaml
# Übersichtskarte für alle Zonen
type: entities
title: IrrigationPro
entities:
  - entity: switch.irrigation_zone_1
    name: Rasen vorne
    secondary_info: last-changed
  - entity: sensor.irrigation_zone_1_duration
    name: Geplante Dauer
  - entity: sensor.irrigation_zone_1_eto
    name: ETo
  - entity: sensor.irrigation_zone_1_next_run
    name: Nächster Lauf
  - entity: binary_sensor.irrigation_zone_1_will_run_today
    name: Läuft heute
  - type: divider
  - entity: switch.irrigation_zone_2
    name: Blumenbeet
  - entity: sensor.irrigation_zone_2_duration
  - type: divider
  - type: button
    name: Neu berechnen
    tap_action:
      action: call-service
      service: irrigationpro.recalculate
```

### Mushroom Cards (Modern)

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: IrrigationPro
    subtitle: Intelligente Bewässerungssteuerung
  
  # Zone 1
  - type: custom:mushroom-entity-card
    entity: switch.irrigation_zone_1
    name: Rasen vorne
    icon: mdi:sprinkler-variant
    tap_action:
      action: toggle
    hold_action:
      action: more-info
    layout: horizontal
  
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        entity: sensor.irrigation_zone_1_duration
        primary: "{{ states(entity) }} min"
        secondary: Dauer
        icon: mdi:timer
        icon_color: blue
      
      - type: custom:mushroom-template-card
        entity: sensor.irrigation_zone_1_eto
        primary: "{{ states(entity) }} mm"
        secondary: ETo
        icon: mdi:water-percent
        icon_color: cyan
      
      - type: custom:mushroom-template-card
        entity: binary_sensor.irrigation_zone_1_will_run_today
        primary: "{{ 'Ja' if is_state(entity, 'on') else 'Nein' }}"
        secondary: Heute
        icon: mdi:calendar-check
        icon_color: "{{ 'green' if is_state(entity, 'on') else 'grey' }}"
  
  # Zone 2
  - type: custom:mushroom-entity-card
    entity: switch.irrigation_zone_2
    name: Blumenbeet
    icon: mdi:flower
```

## Manuelle Steuerung

### Script für manuelle 10-Minuten-Bewässerung

```yaml
script:
  water_zone_manual:
    alias: Zone manuell bewässern
    fields:
      zone_id:
        description: Zone ID
        example: 1
      duration:
        description: Dauer in Minuten
        example: 10
        default: 10
    sequence:
      - service: irrigationpro.start_zone
        data:
          zone_id: "{{ zone_id }}"
          duration: "{{ duration }}"
      - service: notify.mobile_app
        data:
          title: "💧 Manuelle Bewässerung"
          message: "Zone {{ zone_id }} wird {{ duration }} Minuten bewässert"
```

### Button für Lovelace

```yaml
type: button
name: "Zone 1: 10 Min"
icon: mdi:play
tap_action:
  action: call-service
  service: script.water_zone_manual
  data:
    zone_id: 1
    duration: 10
```

## Erweiterte Automationen

### Bewässerung bei Anwesenheit pausieren

```yaml
automation:
  - id: irrigation_pause_when_home
    alias: "Bewässerung - Bei Anwesenheit pausieren"
    trigger:
      - platform: state
        entity_id: person.max
        to: "home"
    condition:
      - condition: state
        entity_id: switch.irrigation_zone_1
        state: "on"
    action:
      - service: irrigationpro.stop_zone
        data:
          zone_id: 1
      - service: notify.mobile_app
        data:
          title: "Bewässerung pausiert"
          message: "Zone 1 wurde gestoppt, da jemand zu Hause ist"
```

### Bewässerung bei starkem Wind verhindern

```yaml
automation:
  - id: irrigation_prevent_wind
    alias: "Bewässerung - Bei Wind verhindern"
    trigger:
      - platform: numeric_state
        entity_id: sensor.wind_speed
        above: 20  # km/h
    condition:
      - condition: or
        conditions:
          - condition: state
            entity_id: switch.irrigation_zone_1
            state: "on"
          - condition: state
            entity_id: switch.irrigation_zone_2
            state: "on"
    action:
      - service: irrigationpro.stop_zone
        data:
          zone_id: 1
      - service: irrigationpro.stop_zone
        data:
          zone_id: 2
      - service: notify.mobile_app
        data:
          title: "⚠️ Bewässerung gestoppt"
          message: "Bewässerung wegen starkem Wind ({{ states('sensor.wind_speed') }} km/h) gestoppt"
```

## Statistiken und Tracking

### History Stats für Bewässerungszeit

```yaml
sensor:
  - platform: history_stats
    name: Zone 1 Bewässerungszeit heute
    entity_id: switch.irrigation_zone_1
    state: "on"
    type: time
    start: "{{ now().replace(hour=0, minute=0, second=0) }}"
    end: "{{ now() }}"
  
  - platform: history_stats
    name: Zone 1 Bewässerungen diese Woche
    entity_id: switch.irrigation_zone_1
    state: "on"
    type: count
    start: "{{ as_timestamp(now()) - (7*86400) }}"
    end: "{{ now() }}"
```

### Template Sensor für Wasserverbrauch

```yaml
template:
  - sensor:
      - name: "Zone 1 Wasserverbrauch heute"
        unit_of_measurement: "L"
        state: >
          {% set duration = states('sensor.zone_1_bewasserungszeit_heute') | float(0) %}
          {% set flow_rate = state_attr('switch.irrigation_zone_1', 'flow_rate') | float(2) %}
          {% set emitters = state_attr('switch.irrigation_zone_1', 'emitter_count') | int(10) %}
          {{ (duration * flow_rate * emitters) | round(1) }}
```

## Node-RED Flow

```json
[
    {
        "id": "irrigation_monitor",
        "type": "server-state-changed",
        "name": "Zone 1 Status",
        "server": "home_assistant",
        "version": 3,
        "entityidfilter": "switch.irrigation_zone_1",
        "outputs": 2,
        "outputInitially": false,
        "state_type": "str",
        "x": 150,
        "y": 100
    },
    {
        "id": "check_state",
        "type": "switch",
        "name": "Status prüfen",
        "property": "payload",
        "rules": [
            {"t": "eq", "v": "on"},
            {"t": "eq", "v": "off"}
        ],
        "x": 350,
        "y": 100
    },
    {
        "id": "valve_on",
        "type": "api-call-service",
        "name": "Ventil EIN",
        "server": "home_assistant",
        "service_domain": "switch",
        "service": "turn_on",
        "entityId": "switch.sonoff_zone_1",
        "x": 550,
        "y": 80
    },
    {
        "id": "valve_off",
        "type": "api-call-service",
        "name": "Ventil AUS",
        "server": "home_assistant",
        "service_domain": "switch",
        "service": "turn_off",
        "entityId": "switch.sonoff_zone_1",
        "x": 550,
        "y": 120
    }
]
```

## Sprachsteuerung

### Alexa / Google Home

```yaml
# In der configuration.yaml
alexa:
  smart_home:
    entity_config:
      switch.irrigation_zone_1:
        name: "Rasen Bewässerung"
        description: "Bewässerung für den vorderen Rasen"

# Sprachbefehle:
# "Alexa, schalte Rasen Bewässerung ein"
# "Ok Google, schalte Rasen Bewässerung aus"
```

## Kalender-Integration

```yaml
# Kalender für Bewässerungsplan
calendar:
  - platform: caldav
    url: https://your-caldav-server.com/calendars/irrigation
    username: user
    password: pass
    calendars:
      - "Bewässerungsplan"

# Automation: Zeige nächste Bewässerung im Kalender
automation:
  - id: irrigation_calendar_update
    alias: "Bewässerung - Kalender aktualisieren"
    trigger:
      - platform: state
        entity_id: sensor.irrigation_zone_1_next_run
    action:
      - service: calendar.create_event
        target:
          entity_id: calendar.bewasserungsplan
        data:
          summary: "Zone 1 Bewässerung"
          start: "{{ states('sensor.irrigation_zone_1_next_run') }}"
          duration:
            minutes: "{{ states('sensor.irrigation_zone_1_duration') | int }}"
```
