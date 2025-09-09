"""
Home Assistant Panel Integration for Tado Local Control

Add this to your Home Assistant configuration.yaml:

panel_iframe:
  tado_local:
    title: "Tado Local Control"
    icon: mdi:thermostat
    url: "http://YOUR_DOCKER_IP:8080"
    require_admin: false

Or for a more integrated approach, use this script:
"""

# Add to your Home Assistant's configuration.yaml
PANEL_CONFIG = """
panel_iframe:
  tado_local:
    title: "Tado Local Control"
    icon: mdi:thermostat
    url: "http://localhost:8080"  # Change to your container IP
    require_admin: false
"""

# Alternative: Python script to register panel programmatically
PYTHON_SCRIPT = """
# Save as: python_scripts/register_tado_panel.py

# Register the Tado Local Control panel
hass.components.frontend.async_register_built_in_panel(
    "iframe",
    "Tado Local",
    "mdi:thermostat",
    "tado-local",
    {"url": "http://localhost:8080"},
    require_admin=False,
)

logger.info("Tado Local Control panel registered")
"""
