"""Tado Local Control integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import frontend

_LOGGER = logging.getLogger(__name__)

DOMAIN = "tado_local"
PLATFORMS = ["climate", "sensor"]

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Tado Local Control component."""
    
    # Register custom panel
    hass.http.register_static_path(
        "/tado-local-static",
        hass.config.path("custom_components/tado_local/www"),
        cache_headers=False,
    )
    
    # Register the panel
    frontend.async_register_built_in_panel(
        hass,
        "iframe",
        "Tado Local",
        "mdi:thermostat",
        "tado-local",
        {"url": "/tado-local-static/index.html"},
        require_admin=False,
    )
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Tado Local Control from a config entry."""
    
    # Store the config entry
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Forward the setup to the platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
