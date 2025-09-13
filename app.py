# This must be the very first import to avoid eventlet monkey patching issues
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request, redirect
from flask_socketio import SocketIO, emit
import asyncio
import logging
from src.homeassistant_client import HomeAssistantClient
from src.config import Config
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if running inside Home Assistant
RUNNING_IN_HASSIO = os.path.exists('/data/options.json')
if RUNNING_IN_HASSIO:
    import json
    with open('/data/options.json') as f:
        hassio_config = json.load(f)
    
    # Override config with Hass.io options
    os.environ['ENTITY_PREFIX'] = hassio_config.get('entity_prefix', 'tado_local')
    os.environ['LOG_LEVEL'] = hassio_config.get('log_level', 'info')
    
    # Home Assistant API access
    os.environ['HA_URL'] = 'http://supervisor/core'
    os.environ['HA_TOKEN'] = os.environ.get('SUPERVISOR_TOKEN', '')

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tado-schedule-control-secret')
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   logger=True, 
                   engineio_logger=True,
                   async_mode='eventlet',
                   allow_unsafe_werkzeug=True)

# Initialize clients
config = Config()
ha_client = HomeAssistantClient(config) if config.homeassistant.get('enabled') else None

@app.route('/')
def index():
    """Main web interface for mobile control"""
    # Check if setup is needed
    if not config.is_configured():
        return redirect('/setup')
    return render_template('index.html')

@app.route('/setup')
def setup():
    """Setup interface for first-time configuration"""
    return render_template('setup.html')

@app.route('/api/zones')
def get_zones():
    """Get all Tado climate entities from Home Assistant"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        zones = ha_client.get_tado_entities()
        return jsonify(zones)
    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones/<entity_id>')
def get_zone(entity_id):
    """Get specific zone details"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        zone = ha_client.get_entity_state(entity_id)
        return jsonify(zone)
    except Exception as e:
        logger.error(f"Error getting zone {entity_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones/<entity_id>/temperature', methods=['POST'])
def set_zone_temperature(entity_id):
    """Set zone target temperature"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        data = request.get_json()
        temperature = data.get('temperature')
        
        if temperature is None:
            return jsonify({'error': 'Temperature is required'}), 400
            
        result = ha_client.set_climate_temperature(entity_id, temperature)
        
        # Emit real-time update
        socketio.emit('zone_update', {
            'entity_id': entity_id,
            'temperature': temperature
        })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting temperature for {entity_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones/<entity_id>/mode', methods=['POST'])
def set_zone_mode(entity_id):
    """Set zone heating mode"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        data = request.get_json()
        mode = data.get('mode')
        
        if mode not in ['auto', 'heat', 'off']:
            return jsonify({'error': 'Invalid mode'}), 400
            
        result = ha_client.set_climate_mode(entity_id, mode)
        
        # Emit real-time update
        socketio.emit('zone_update', {
            'entity_id': entity_id,
            'mode': mode
        })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting mode for {entity_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules')
def get_schedules():
    """Get all custom schedules"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        schedules = ha_client.get_schedules()
        return jsonify(schedules)
    except Exception as e:
        logger.error(f"Error getting schedules: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    """Create new schedule"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        data = request.get_json()
        schedule = ha_client.create_schedule(data)
        
        return jsonify(schedule)
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """Update existing schedule"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        data = request.get_json()
        schedule = ha_client.update_schedule(schedule_id, data)
        
        return jsonify(schedule)
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/automations')
def get_automations():
    """Get all Tado-related automations from Home Assistant"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        # Get all automations that are related to Tado/heating
        automations = ha_client.get_tado_automations()
        return jsonify(automations)
    except Exception as e:
        logger.error(f"Error getting automations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete schedule"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        result = ha_client.delete_schedule(schedule_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>/activate', methods=['POST'])
def activate_schedule(schedule_id):
    """Activate a schedule"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        result = ha_client.activate_schedule(schedule_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error activating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<schedule_id>/deactivate', methods=['POST'])
def deactivate_schedule(schedule_id):
    """Deactivate a schedule"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        result = ha_client.deactivate_schedule(schedule_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error deactivating schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimization/stats')
def get_optimization_stats():
    """Get optimization statistics"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        stats = ha_client.get_optimization_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting optimization stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones/<zone_id>/schedule-state')
def get_zone_schedule_state(zone_id):
    """Get current schedule state for a zone"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        state = ha_client.get_schedule_state_for_zone(zone_id)
        return jsonify(state)
    except Exception as e:
        logger.error(f"Error getting zone schedule state: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/discovery')
def discover_devices():
    """Discover Tado devices on local network"""
    try:
        # For now, return devices from Home Assistant
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        entities = ha_client.get_tado_entities()
        devices = []
        for entity in entities:
            devices.append({
                'name': entity.get('attributes', {}).get('friendly_name', entity['entity_id']),
                'type': 'climate',
                'entity_id': entity['entity_id']
            })
        
        return jsonify(devices)
    except Exception as e:
        logger.error(f"Error discovering devices: {e}")
        return jsonify({'error': str(e)}), 500

# Setup API endpoints
@app.route('/api/setup/status')
def setup_status():
    """Check if setup is completed"""
    return jsonify({'configured': config.is_configured()})

@app.route('/api/setup/test-ha-connection', methods=['POST'])
def test_ha_connection():
    """Test Home Assistant connection"""
    try:
        data = request.get_json()
        url = data.get('url')
        token = data.get('token')
        
        if not url or not token:
            return jsonify({'success': False, 'error': 'URL and token are required'})
        
        # Test the connection
        from src.homeassistant_client import HomeAssistantClient
        
        # Create a mock config object
        class MockConfig:
            def __init__(self, ha_config):
                self.homeassistant = ha_config
        
        test_config = MockConfig({'base_url': url, 'token': token})
        test_client = HomeAssistantClient(test_config)
        
        result = test_client.test_connection()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing HA connection: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/setup/get-tado-entities', methods=['POST'])
def get_tado_entities():
    """Get available Tado entities from Home Assistant"""
    try:
        data = request.get_json()
        url = data.get('url')
        token = data.get('token')
        
        if not url or not token:
            return jsonify({'success': False, 'error': 'URL and token are required'})
        
        # Create temporary client
        class MockConfig:
            def __init__(self, ha_config):
                self.homeassistant = ha_config
        
        test_config = MockConfig({'base_url': url, 'token': token})
        test_client = HomeAssistantClient(test_config)
        
        entities = test_client.get_tado_entities()
        
        return jsonify({'success': True, 'entities': entities})
        
    except Exception as e:
        logger.error(f"Error getting Tado entities: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/away-home/entities', methods=['POST'])
def get_away_home_entities():
    """Get available away/home entities from Home Assistant"""
    try:
        data = request.get_json()
        url = data.get('url')
        token = data.get('token')
        
        # If token is 'current', use the existing ha_client
        if token == 'current' and ha_client:
            entities = ha_client.get_away_home_entities()
            return jsonify({'success': True, 'entities': entities})
        elif url and token and token != 'current':
            # Create temporary client for setup
            class MockConfig:
                def __init__(self, ha_config):
                    self.homeassistant = ha_config
            
            test_config = MockConfig({'base_url': url, 'token': token})
            test_client = HomeAssistantClient(test_config)
            
            entities = test_client.get_away_home_entities()
            return jsonify({'success': True, 'entities': entities})
        else:
            return jsonify({'success': False, 'error': 'URL and token are required or Home Assistant not configured'})
        
    except Exception as e:
        logger.error(f"Error getting away/home entities: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/away-home/status')
def get_away_home_status():
    """Get current away/home status"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        status = ha_client.get_away_home_state()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting away/home status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/away-home/set', methods=['POST'])
def set_away_home_state():
    """Set away/home state"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        data = request.get_json()
        state = data.get('state')
        
        if not state:
            return jsonify({'error': 'State is required'}), 400
            
        result = ha_client.set_away_home_state(state)
        
        # Emit real-time update
        socketio.emit('away_home_update', {
            'state': state,
            'result': result
        })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting away/home state: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/away-home/apply-away-mode', methods=['POST'])
def apply_away_mode():
    """Apply away mode to all configured zones"""
    try:
        if not ha_client:
            return jsonify({'error': 'Home Assistant not configured'}), 500
            
        # Get configured zones from config
        zones = config.homeassistant.get('selected_entities', [])
        
        if not zones:
            return jsonify({'error': 'No zones configured'}), 400
            
        result = ha_client.apply_away_mode_to_zones(zones)
        
        # Emit real-time update
        socketio.emit('away_mode_applied', result)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error applying away mode: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/away-home/save-config', methods=['POST'])
def save_away_home_config():
    """Save away/home configuration"""
    try:
        data = request.get_json()
        away_home_config = data.get('homeassistant', {}).get('away_home', {})
        
        # Get current configuration
        current_config = config._config.copy()
        
        # Update the away_home section
        if 'homeassistant' not in current_config:
            current_config['homeassistant'] = {}
        
        current_config['homeassistant']['away_home'] = away_home_config
        
        # Save to config file
        config.save_setup_config(current_config)
        
        # Reload the configuration
        config._config = config._load_config()
        
        # Update the global ha_client with new config
        global ha_client
        ha_client = HomeAssistantClient(config) if config.homeassistant.get('enabled') else None
        
        return jsonify({'success': True, 'message': 'Away/Home configuration saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving away/home config: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/setup/save-config', methods=['POST'])
def save_setup_config():
    """Save configuration from setup"""
    try:
        data = request.get_json()
        
        # Validate required fields
        ha_config = data.get('homeassistant', {})
        if not ha_config.get('url') or not ha_config.get('token'):
            return jsonify({'success': False, 'error': 'Home Assistant URL and token are required'})
        
        # Save configuration
        config.save_setup_config(data)
        
        # Restart clients with new config
        global ha_client
        config._config = config._load_config()  # Reload config
        ha_client = HomeAssistantClient(config) if config.homeassistant.get('enabled') else None
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info('Client connected')
    emit('status', {'message': 'Connected to Tado Local Control'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info('Client disconnected')

# Background task to sync with Home Assistant
def sync_with_homeassistant():
    """Periodic sync with Home Assistant"""
    if ha_client:
        try:
            # Just log that sync is available - actual syncing handled by HA
            logger.info("Home Assistant sync available")
        except Exception as e:
            logger.error(f"Error syncing with Home Assistant: {e}")

if __name__ == '__main__':
    logger.info("Starting Tado Schedule Manager application")
    
    # Start Home Assistant sync if configured
    if ha_client:
        logger.info("Home Assistant integration enabled")
    
    # Run the app with development server
    logger.info("Running in development mode with Flask dev server")
    socketio.run(app, 
                host=config.web.get('host', '0.0.0.0'), 
                port=config.web.get('port', 5000),
                debug=config.web.get('debug', False),
                allow_unsafe_werkzeug=True)

# For gunicorn deployment
def create_app():
    """Factory function for gunicorn"""
    return app
