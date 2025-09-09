import yaml
import os
from typing import Dict, Any

class Config:
    """Configuration management for Tado Local Control"""
    
    def __init__(self, config_file: str = None):
        # Use /data for add-on persistent storage, fallback to app_config for local development
        if os.path.exists('/data'):
            # Running as Home Assistant add-on
            self.config_file = config_file or os.path.join('/data', 'config', 'config.yaml')
        else:
            # Running locally for development
            self.config_file = config_file or os.path.join('app_config', 'config.yaml')
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment variables"""
        config = {
            'tado': {
                'bridge_ip': None,  # Auto-discover if not set
                'polling_interval': 30,
                'timeout': 10
            },
            'homeassistant': {
                'enabled': True,
                'base_url': os.getenv('HA_URL', 'http://homeassistant:8123'),
                'token': os.getenv('HA_TOKEN'),
                'entity_prefix': 'tado_local',
                'sync_interval': 60,
                'homekit_bridge': None,
                'away_home': {
                    'enabled': False,
                    'entity_id': None,
                    'home_state': 'home',
                    'away_state': 'not_home',
                    'away_temperature': 16.0,
                    'away_mode': 'auto'
                }
            },
            'web': {
                'host': os.getenv('WEB_HOST', '0.0.0.0'),
                'port': int(os.getenv('WEB_PORT', 5000)),
                'debug': os.getenv('DEBUG', 'false').lower() == 'true'
            },
            'logging': {
                'level': os.getenv('LOG_LEVEL', 'INFO'),
                'file': None  # Log to stdout by default
            }
        }
        
        # Load from YAML file if it exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        self._merge_config(config, file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        
        return config
    
    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def is_configured(self) -> bool:
        """Check if the application is properly configured"""
        # Check if config file exists and has required settings
        if not os.path.exists(self.config_file):
            return False
        
        # Check if Home Assistant is configured
        ha_config = self.homeassistant
        if not ha_config.get('base_url') or not ha_config.get('token'):
            return False
        
        return True
    
    def save_setup_config(self, setup_data: Dict[str, Any]):
        """Save configuration from setup process"""
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Merge setup data with current config
        self._merge_config(self._config, setup_data)
        
        # Write to file
        with open(self.config_file, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)
    
    @property
    def tado(self) -> Dict[str, Any]:
        return self._config['tado']
    
    @property
    def homeassistant(self) -> Dict[str, Any]:
        return self._config['homeassistant']
    
    @property
    def web(self) -> Dict[str, Any]:
        return self._config['web']
    
    @property
    def logging(self) -> Dict[str, Any]:
        return self._config['logging']
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation (e.g., 'tado.bridge_ip')"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
