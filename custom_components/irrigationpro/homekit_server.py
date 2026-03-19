"""Native HomeKit IrrigationSystem accessory for IrrigationPro.

Runs an independent HAP server that exposes a single HomeKit accessory with
the ``IrrigationSystem`` service and one linked ``Valve`` service per zone.
Apple Home renders this as the native iOS sprinkler UI with per‐zone toggles,
timers, and the sprinkler icon.
"""
from __future__ import annotations

import asyncio
import errno
import logging
import socket
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from homeassistant.core import HomeAssistant
from homeassistant.components import zeroconf
from homeassistant.util import dt as dt_util

from .const import CONF_LANGUAGE, DEFAULT_LANGUAGE, VERSION

if TYPE_CHECKING:
    from .coordinator import SmartIrrigationCoordinator, ZoneData

_LOGGER = logging.getLogger(__name__)

HAS_HAP = False
try:
    from pyhap.accessory import Accessory, Bridge
    from pyhap.accessory_driver import AccessoryDriver

    try:
        from pyhap.const import CATEGORY_SPRINKLER
        from pyhap.const import CATEGORY_SWITCH
    except ImportError:
        CATEGORY_SPRINKLER = 28
        CATEGORY_SWITCH = 8

    HAS_HAP = True
except ImportError:
    _LOGGER.info("HAP-python not installed – HomeKit sprinkler feature unavailable")


# ---------------------------------------------------------------------------
# HAP Accessory
# ---------------------------------------------------------------------------

if HAS_HAP:

    class IrrigationSystemAccessory(Accessory):
        """Sprinkler accessory: IrrigationSystem + linked Valves."""

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
            self._hass = hass
            self._homekit_durations: dict[int, int] = {}
            self._valve_services: dict[int, Any] = {}

            # -- AccessoryInformation (shown in Apple Home → Geräteinfos) --
            self.set_info_service(
                manufacturer="IrrigationPro",
                model="Smart Irrigation Controller",
                serial_number="IRRIGPRO-001",
                firmware_revision=VERSION,
            )

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
                    unique_id=f"zone-{zone.zone_id}",
                )
                # Set service display_name so Apple Home shows the zone name
                valve.display_name = zone.name
                valve.configure_char("ValveType", value=1)  # 1 = IRRIGATION
                
                try:
                    valve.configure_char("ConfiguredName", value=zone.name)
                except Exception:
                    pass
                try:
                    valve.configure_char("ServiceLabelIndex", value=zone.zone_id)
                except Exception:
                    pass
                valve.configure_char(
                    "IsConfigured", value=1 if zone.enabled else 0
                )
                valve.configure_char("Name", value=zone.name)
                try:
                    valve.configure_char("ConfiguredName", value=zone.name)
                except Exception:
                    # Optional characteristic depending on service definition.
                    pass
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
                self._hass.async_create_task(
                    self._coordinator.async_start_zone_manual(zone_id, dur_min)
                )
            else:
                self._hass.async_create_task(
                    self._coordinator.async_stop_zone(zone_id)
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


    class RuntimeSwitchAccessory(Accessory):
        """Standalone HomeKit switch accessory for runtime settings."""

        category = CATEGORY_SWITCH  # type: ignore[assignment]

        def __init__(
            self,
            driver: "AccessoryDriver",
            display_name: str,
            *,
            hass: HomeAssistant,
            serial_suffix: str,
            getter: Callable[[], bool],
            setter: Callable[[bool], Awaitable[None]],
            **kwargs: Any,
        ) -> None:
            super().__init__(driver, display_name, **kwargs)
            self._hass = hass
            self._getter = getter
            self._setter = setter

            self.set_info_service(
                manufacturer="IrrigationPro",
                model="Runtime Switch",
                serial_number=f"IRRIGPRO-{serial_suffix}",
                firmware_revision=VERSION,
            )

            svc = self.add_preload_service("Switch", chars=["Name"])
            svc.display_name = display_name
            svc.configure_char("Name", value=display_name)
            svc.configure_char(
                "On",
                value=1 if self._getter() else 0,
                setter_callback=self._on_set,
            )
            self._switch_service = svc

        def _on_set(self, value: int) -> None:
            self._hass.async_create_task(self._setter(bool(value)))

        @Accessory.run_at_interval(3)
        async def run(self) -> None:  # noqa: D102
            self._switch_service.get_characteristic("On").set_value(
                1 if self._getter() else 0
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
        self._hap_task: asyncio.Task | None = None
        self.is_running = False
        self.xhm_uri: str | None = None  # X-HM:// URI for QR pairing
        self.last_error: str | None = None
        self.suggested_port: int | None = None
        self.accessory_name: str = "IrrigationPro Garden Bridge"

    def _is_port_available(self, port: int) -> bool:
        """Return True if a TCP bind on all interfaces would succeed."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("", port))
                return True
            except OSError as err:
                if err.errno == errno.EADDRINUSE:
                    return False
                return False

    def _homekit_name(self, key: str) -> str:
        """Return HomeKit display names based on the current configured language."""
        lang = str(
            self._coordinator.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        ).lower()

        names = {
            "mainswitch": {
                "de": "Hauptschalter",
                "en": "Mainswitch",
            },
            "pushover": {
                "de": "Benachrichtigungen",
                "en": "Notifications",
            },
            "sprinkler": {
                "de": "Bewässerung",
                "en": "Sprinkler",
            },
        }

        return names.get(key, {}).get(lang, names.get(key, {}).get("en", key))

    @staticmethod
    def find_free_port(start: int, max_attempts: int = 50) -> int | None:
        """Return the next free TCP port starting at *start*, or None."""
        for candidate in range(start, start + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind(("", candidate))
                    return candidate
                except OSError:
                    continue
        return None

    # -- public ---------------------------------------------------------

    async def async_start(self) -> None:
        """Start the HAP driver asynchronously."""
        self.last_error = None

        if not HAS_HAP:
            self.last_error = "HAP-python not installed"
            _LOGGER.error("Cannot start HomeKit – %s", self.last_error)
            return
        if self.is_running:
            return

        if not self._is_port_available(self._port):
            suggested = self.find_free_port(self._port + 1)
            self.suggested_port: int | None = suggested
            self.last_error = (
                f"Port {self._port} is already in use."
                + (f" Suggested free port: {suggested}." if suggested else "")
                + " Please select a different HomeKit port."
            )
            _LOGGER.error("Cannot start HomeKit – %s", self.last_error)
            return

        try:
            # Use Home Assistant's zeroconf instance for mDNS sharing!
            # Otherwise we get network conflicts when pyhap creates its own zeroconf server.
            async_zc = await zeroconf.async_get_async_instance(self._hass)

            self._driver = AccessoryDriver(
                port=self._port,
                persist_file=self._persist_file,
                pincode=self._pin_code.encode("ascii"),
                loop=self._hass.loop,
                async_zeroconf_instance=async_zc,
            )
            assert self._driver is not None

            # Log the address HAP-python will actually bind to
            try:
                bind_addr = getattr(
                    getattr(self._driver, "state", None), "address", None
                )
                if bind_addr:
                    _LOGGER.info(
                        "HomeKit driver will bind to %s:%s", bind_addr, self._port
                    )
            except Exception:
                pass

            bridge = Bridge(self._driver, self.accessory_name)
            bridge.set_info_service(
                manufacturer="IrrigationPro",
                model="HomeKit Bridge",
                serial_number="IRRIGPRO-BRIDGE",
                firmware_revision=VERSION,
            )

            sprinkler = IrrigationSystemAccessory(
                self._driver,
                self._homekit_name("sprinkler"),
                zones=self._coordinator.zones,
                coordinator=self._coordinator,
                hass=self._hass,
            )
            mainswitch = RuntimeSwitchAccessory(
                self._driver,
                self._homekit_name("mainswitch"),
                hass=self._hass,
                serial_suffix="MAIN",
                getter=lambda: bool(
                    self._coordinator.entry.data.get("master_enabled", True)
                ),
                setter=self._coordinator.async_set_master_enabled,
            )
            pushover_switch = RuntimeSwitchAccessory(
                self._driver,
                self._homekit_name("pushover"),
                hass=self._hass,
                serial_suffix="PUSH",
                getter=lambda: bool(
                    self._coordinator.entry.data.get("pushover_enabled", False)
                ),
                setter=self._coordinator.async_set_pushover_enabled,
            )

            bridge.add_accessory(sprinkler)
            bridge.add_accessory(mainswitch)
            bridge.add_accessory(pushover_switch)
            self._driver.add_accessory(bridge)

            # Generate the X-HM:// URI for QR code pairing
            try:
                self.xhm_uri = bridge.xhm_uri()
                _LOGGER.info("HomeKit setup URI: %s", self.xhm_uri)
            except Exception:
                _LOGGER.debug("Could not generate xhm_uri", exc_info=True)
                self.xhm_uri = None

            # async_start() correctly links pyhap into Home Assistant's event loop
            await self._driver.async_start()
            self.is_running = True
            
            _LOGGER.info(
                "HomeKit server started on port %s (PIN: %s)",
                self._port,
                self._pin_code,
            )
        except Exception as err:
            self.last_error = str(err)
            _LOGGER.exception("Failed to start HomeKit server")
            self.is_running = False
            self.xhm_uri = None

    async def async_stop(self) -> None:
        """Stop the HAP driver."""
        if self._driver is not None:
            try:
                await self._driver.async_stop()
            except Exception:
                _LOGGER.exception("Error stopping HomeKit server")
            self._driver = None
        self.is_running = False
        self.xhm_uri = None
        self.last_error = None
        _LOGGER.info("HomeKit server stopped")
