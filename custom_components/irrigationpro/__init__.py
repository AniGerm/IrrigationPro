"""The IrrigationPro integration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .api import async_register_api
from .const import (
    ATTR_DURATION,
    ATTR_ZONE_ID,
    DOMAIN,
    SERVICE_RECALCULATE,
    SERVICE_START_ZONE,
    SERVICE_STOP_ZONE,
)
from .coordinator import SmartIrrigationCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up IrrigationPro from a config entry."""
    _LOGGER.debug("Setting up IrrigationPro with entry: %s", entry.entry_id)

    try:
        # Create coordinator
        coordinator = SmartIrrigationCoordinator(hass, entry)

        # Store coordinator
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()

        # Setup platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register update listener for options
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        # Register services (only once)
        if not hass.services.has_service(DOMAIN, SERVICE_START_ZONE):
            await async_setup_services(hass)

        # Register API endpoints and panel (only once)
        if f"{DOMAIN}_panel_registered" not in hass.data:
            async_register_api(hass)

            # Register static path for frontend files
            frontend_path = Path(__file__).parent / "frontend"
            await hass.http.async_register_static_paths(
                [StaticPathConfig(f"/{DOMAIN}/frontend", str(frontend_path), False)]
            )

            # Register panel in sidebar
            async_register_built_in_panel(
                hass,
                component_name="iframe",
                sidebar_title="IrrigationPro",
                sidebar_icon="mdi:sprinkler-variant",
                frontend_url_path=DOMAIN,
                config={"url": f"/{DOMAIN}/frontend/index.html"},
                require_admin=False,
            )
            hass.data[f"{DOMAIN}_panel_registered"] = True

        _LOGGER.info("IrrigationPro setup completed successfully")
        return True
        
    except Exception as err:
        _LOGGER.error("Error setting up IrrigationPro: %s", err, exc_info=True)
        # Clean up if setup failed
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN].pop(entry.entry_id)
        raise


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading IrrigationPro")

    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: SmartIrrigationCoordinator = hass.data[DOMAIN][entry.entry_id]
        
        # Cancel any scheduled jobs
        await coordinator.async_shutdown()
        
        # Remove coordinator
        hass.data[DOMAIN].pop(entry.entry_id)
        
        # Unregister services if this was the last entry
        if not hass.data[DOMAIN]:
            for service_name in (SERVICE_START_ZONE, SERVICE_STOP_ZONE, SERVICE_RECALCULATE):
                hass.services.async_remove(DOMAIN, service_name)
            # Remove panel
            async_remove_panel(hass, DOMAIN)
            hass.data.pop(f"{DOMAIN}_panel_registered", None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_setup_services(
    hass: HomeAssistant,
) -> None:
    """Set up services for IrrigationPro."""

    async def handle_start_zone(call: ServiceCall) -> None:
        """Handle the start_zone service call."""
        zone_id = call.data[ATTR_ZONE_ID]
        duration = call.data[ATTR_DURATION]
        
        _LOGGER.info("Service call: start_zone (zone_id=%s, duration=%s)", zone_id, duration)
        
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            try:
                await coordinator.async_start_zone_manual(zone_id, duration)
                return
            except ValueError:
                continue
        _LOGGER.error("Zone %s not found in any coordinator", zone_id)

    async def handle_stop_zone(call: ServiceCall) -> None:
        """Handle the stop_zone service call."""
        zone_id = call.data[ATTR_ZONE_ID]
        
        _LOGGER.info("Service call: stop_zone (zone_id=%s)", zone_id)
        
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            try:
                await coordinator.async_stop_zone(zone_id)
                return
            except ValueError:
                continue
        _LOGGER.error("Zone %s not found in any coordinator", zone_id)

    async def handle_recalculate(call: ServiceCall) -> None:
        """Handle the recalculate service call."""
        _LOGGER.info("Service call: recalculate")
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            await coordinator.async_refresh()

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_ZONE,
        handle_start_zone,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ZONE_ID): cv.positive_int,
                vol.Required(ATTR_DURATION): cv.positive_int,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_ZONE,
        handle_stop_zone,
        schema=vol.Schema({vol.Required(ATTR_ZONE_ID): cv.positive_int}),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECALCULATE,
        handle_recalculate,
        schema=vol.Schema({}),
    )
