#!/usr/bin/with-contenv bashio

# Check if running in Home Assistant add-on environment
if command -v bashio > /dev/null 2>&1 && bashio::supervisor.ping > /dev/null 2>&1; then
    # Running as Home Assistant add-on
    bashio::log.info "Running as Home Assistant add-on"
    
    # Get configuration from add-on options
    ENTITY_PREFIX=$(bashio::config 'entity_prefix')
    LOG_LEVEL=$(bashio::config 'log_level')
    AUTO_DISCOVER_ZONES=$(bashio::config 'auto_discover_zones')
    SCHEDULE_BACKUP=$(bashio::config 'schedule_backup')

    # Set environment variables
    export ENTITY_PREFIX="${ENTITY_PREFIX}"
    export LOG_LEVEL="${LOG_LEVEL}"
    export AUTO_DISCOVER_ZONES="${AUTO_DISCOVER_ZONES}"
    export SCHEDULE_BACKUP="${SCHEDULE_BACKUP}"

    # Home Assistant integration (automatic)
    export HA_URL="http://supervisor/core"
    export HA_TOKEN="${SUPERVISOR_TOKEN}"

    bashio::log.info "Entity Prefix: ${ENTITY_PREFIX}"
    bashio::log.info "Log Level: ${LOG_LEVEL}"
    bashio::log.info "Auto Discover Zones: ${AUTO_DISCOVER_ZONES}"
    bashio::log.info "Schedule Backup: ${SCHEDULE_BACKUP}"
else
    # Running standalone (for testing or development)
    echo "Running in standalone mode"
    
    # Use environment variables or defaults
    export ENTITY_PREFIX="${ENTITY_PREFIX:-tado_local}"
    export LOG_LEVEL="${LOG_LEVEL:-info}"
    export AUTO_DISCOVER_ZONES="${AUTO_DISCOVER_ZONES:-true}"
    export SCHEDULE_BACKUP="${SCHEDULE_BACKUP:-true}"
    
    # Use provided environment variables
    export HA_URL="${HA_URL:-http://homeassistant:8123}"
    export HA_TOKEN="${HA_TOKEN:-}"
    
    echo "Entity Prefix: ${ENTITY_PREFIX}"
    echo "Log Level: ${LOG_LEVEL}"
    echo "Auto Discover Zones: ${AUTO_DISCOVER_ZONES}"
    echo "Schedule Backup: ${SCHEDULE_BACKUP}"
fi

# Web server configuration
export WEB_HOST="0.0.0.0"
export WEB_PORT="8080"
export DEBUG="false"

# Create config directory if it doesn't exist
mkdir -p /data/config

# Start the application with gunicorn for production
cd /app
exec gunicorn --bind 0.0.0.0:8080 \
  --workers 1 \
  --worker-class eventlet \
  --worker-connections 1000 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --preload \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  app:app
