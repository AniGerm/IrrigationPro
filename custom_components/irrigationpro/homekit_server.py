"""Native HomeKit IrrigationSystem accessory for IrrigationPro.

Runs an independent HAP server that exposes a single HomeKit accessory with
the ``IrrigationSystem`` service and one linked ``Valve`` service per zone.
Apple Home renders this as the native iOS sprinkler UI with per‐zone toggles,
timers, and the sprinkler icon.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from .coordinator import SmartIrrigationCoordinator, ZoneData

_LOGGER = logging.getLogger(__name__)

HAS_HAP = False
try:
    from pyhap.accessory import Accessory
    from pyhap.accessory_driver import AccessoryDriver

    try:
        from pyhap.const import CATEGORY_SPRINKLER
    except ImportError:
        CATEGORY_SPRINKLER = 28

    HAS_HAP = True
except ImportError:
    _LOGGER.info("HAP-python not installed – HomeKit sprinkler feature unavailable")


# ---------------------------------------------------------------------------
# HAP Accessory
# ---------------------------------------------------------------------------

if HAS_HAP:

    class IrrigationSystemAccessory(Accessory):
        """Single HAP accessory: IrrigationSystem + linked Valves."""

        category = CATEGORY_SPRINKLER  # type: ignore[assignment]

        def __init__(
            self,
            driver: "AccessoryDriver",
            display_name: str,
            *,
            zones: list["ZoneData"],
            coordinator: "SmartIrrigationCoordinator",
            hass: HomeAssistant,
            **kwargs: Any,
        ) -> None:
            super().__init__(driver, display_name, **kwargs)
            self._coordinator = coordinator
            self._hass_loop = hass.loop
            self._homekit_durations: dict[int, int] = {}
            self._valve_services: dict[int, Any] = {}

            # -- Primary IrrigationSystem service --
            irr = self.add_preload_service(
                "IrrigationSystem", chars=["RemainingDuration"]
            )
            irr.configure_char("Active", value=1)
            irr.configure_char("ProgramMode", value=1)  # 1 = scheduled
            irr.configure_char("InUse", value=0)
            irr.configure_char("RemainingDuration", value=0)
            irr.is_primary_service = True
            self._irr_service = irr

            # -- One Valve per zone --
            for zone in zones:
                valve = self.add_preload_service(
                    "Valve",
                    chars=[
                        "SetDuration",
                        "RemainingDuration",
                        "IsConfigured",
                        "Name",
                    ],
                )
                valve.configure_char("ValveType", value=1)  # 1 = IRRIGATION
                valve.configure_char(
                    "IsConfigured", value=1 if zone.enabled else 0
                )
                valve.configure_char("Name", value=zone.name)
                valve.configure_char("Active", value=0)
                valve.configure_char("InUse", value=0)
                valve.configure_char(
                    "SetDuration",
                    value=int(zone.duration * 60) if zone.duration > 0 else 600,
                    setter_callback=lambda v, zid=zone.zone_id: self._on_set_duration(
                        zid, v
                    ),
                )
                valve.configure_char("RemainingDuration", value=0)

                # Setter for Active (turn on/off from HomeKit)
                valve.configure_char(
                    "Active",
                    setter_callback=lambda v, zid=zone.zone_id: self._on_set_active(
                        zid, v
                    ),
                )

                # Link valve to the primary irrigation service
                irr.linked_services.append(valve)
                self._valve_services[zone.zone_id] = valve

        # -- HomeKit callbacks (run in HAP thread) --

        def _on_set_active(self, zone_id: int, value: int) -> None:
            """User toggled a valve in Apple Home."""
            zone = next(
                (z for z in self._coordinator.zones if z.zone_id == zone_id), None
            )
            if zone is None:
                return

            # Immediate InUse feedback
            svc = self._valve_services.get(zone_id)
            if svc:
                svc.get_characteristic("InUse").set_value(value)

            if value:
                dur_sec = self._homekit_durations.get(
                    zone_id,
                    int(zone.duration * 60) if zone.duration > 0 else 600,
                )
                dur_min = max(1, dur_sec // 60)
                asyncio.run_coroutine_threadsafe(
                    self._coordinator.async_start_zone_manual(zone_id, dur_min),
                    self._hass_loop,
                )
            else:
                asyncio.run_coroutine_threadsafe(
                    self._coordinator.async_stop_zone(zone_id),
                    self._hass_loop,
                )

        def _on_set_duration(self, zone_id: int, value: int) -> None:
            """User changed SetDuration for a valve in Apple Home."""
            self._homekit_durations[zone_id] = value

        # -- Periodic state sync (every 3 s) --

        @Accessory.run_at_interval(3)
        async def run(self) -> None:  # noqa: D102
            any_running = False
            total_remaining = 0

            for zone in self._coordinator.zones:
                svc = self._valve_services.get(zone.zone_id)
                if svc is None:
                    continue

                active = 1 if zone.is_running else 0
                svc.get_characteristic("Active").set_value(active)
                svc.get_characteristic("InUse").set_value(active)
                svc.get_characteristic("IsConfigured").set_value(
                    1 if zone.enabled else 0
                )

                remaining = 0
                if zone.is_running and zone.started_at:
                    elapsed = (dt_util.now() - zone.started_at).total_seconds()
                    remaining = max(0, int(zone.duration * 60 - elapsed))
                    any_running = True
                    total_remaining += remaining

                svc.get_characteristic("RemainingDuration").set_value(remaining)

                # Keep SetDuration in sync with calculated duration
                if zone.duration > 0 and zone.zone_id not in self._homekit_durations:
                    svc.get_characteristic("SetDuration").set_value(
                        int(zone.duration * 60)
                    )

            self._irr_service.get_characteristic("InUse").set_value(
                1 if any_running else 0
            )
            self._irr_service.get_characteristic("RemainingDuration").set_value(
                total_remaining
            )
            self._irr_service.get_characteristic("ProgramMode").set_value(
                1 if self._coordinator.scheduled_run is not None else 0
            )


# ---------------------------------------------------------------------------
# Lifecycle wrapper – usable regardless of HAP availability
# ---------------------------------------------------------------------------


class IrrigationProHomeKit:
    """Manages the HAP accessory driver lifecycle."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: "SmartIrrigationCoordinator",
        port: int,
        pin_code: str,
        persist_file: str,
    ) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._port = port
        self._pin_code = pin_code
        self._persist_file = persist_file
        self._driver: Any | None = None
        self._thread: threading.Thread | None = None
        self.is_running = False

    # -- public ---------------------------------------------------------

    def start(self) -> None:
        """Start the HAP driver in a daemon thread."""
        if not HAS_HAP:
            _LOGGER.error("Cannot start HomeKit – HAP-python not installed")
            return
        if self.is_running:
            return

        try:
            self._driver = AccessoryDriver(
                port=self._port,
                persist_file=self._persist_file,
                pincode=self._pin_code.encode("ascii"),
            )
            accessory = IrrigationSystemAccessory(
                self._driver,
                "IrrigationPro Sprinkler",
                zones=self._coordinator.zones,
                coordinator=self._coordinator,
                hass=self._hass,
            )
            self._driver.add_accessory(accessory)

            self._thread = threading.Thread(
                target=self._driver.start,
                daemon=True,
                name="irrigationpro-hap",
            )
            self._thread.start()
            self.is_running = True
            _LOGGER.info(
                "HomeKit server started on port %s (PIN: %s)",
                self._port,
                self._pin_code,
            )
        except Exception:
            _LOGGER.exception("Failed to start HomeKit server")
            self.is_running = False

    def stop(self) -> None:
        """Stop the HAP driver."""
        if self._driver is not None:
            try:
                self._driver.stop()
            except Exception:
                _LOGGER.exception("Error stopping HomeKit server")
            self._driver = None
        self._thread = None
        self.is_running = False
        _LOGGER.info("HomeKit server stopped")
