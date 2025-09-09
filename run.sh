#!/usr/bin/with-contenv bashio

# Get configuration
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

# Web server configuration
export WEB_HOST="0.0.0.0"
export WEB_PORT="8080"
export DEBUG="false"

bashio::log.info "Starting Tado° Smart Scheduler..."
bashio::log.info "Entity Prefix: ${ENTITY_PREFIX}"
bashio::log.info "Log Level: ${LOG_LEVEL}"
bashio::log.info "Auto Discover Zones: ${AUTO_DISCOVER_ZONES}"
bashio::log.info "Schedule Backup: ${SCHEDULE_BACKUP}"

# Create config directory if it doesn't exist
mkdir -p /data/config

# Start the application with gunicorn for production
cd /app
exec gunicorn --bind 0.0.0.0:8080 --workers 1 --worker-class eventlet --worker-connections 1000 --timeout 120 --keepalive 2 --max-requests 1000 --max-requests-jitter 50 --preload --log-level info app:app
