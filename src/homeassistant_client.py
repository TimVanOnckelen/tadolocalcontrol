import requests
import logging
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

class HomeAssistantClient:
    """Client for Home Assistant integration"""
    
    def __init__(self, config):
        self.config = config
        self.ha_config = config.homeassistant
        # Try 'url' first (from YAML), then 'base_url' (from environment/default)
        self.base_url = (self.ha_config.get('url') or self.ha_config.get('base_url', '')).rstrip('/')
        self.token = self.ha_config.get('token')
        self.entity_prefix = self.ha_config.get('entity_prefix', 'tado_local')
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Home Assistant"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Test API endpoint
            response = requests.get(f'{self.base_url}/api/', headers=headers, timeout=10)
            
            if response.status_code == 200:
                api_info = response.json()
                
                # Get entity count
                entities_response = requests.get(f'{self.base_url}/api/states', headers=headers, timeout=10)
                entity_count = len(entities_response.json()) if entities_response.status_code == 200 else 0
                
                # Get HomeKit bridges
                homekit_bridges = self._get_homekit_bridges(headers)
                
                return {
                    'success': True,
                    'version': api_info.get('version', 'Unknown'),
                    'entity_count': entity_count,
                    'homekit_bridges': homekit_bridges
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Connection error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def _get_homekit_bridges(self, headers) -> List[Dict[str, str]]:
        """Get available HomeKit bridges"""
        try:
            import requests
            
            # Get HomeKit integrations
            response = requests.get(f'{self.base_url}/api/config/config_entries', headers=headers)
            
            if response.status_code == 200:
                entries = response.json()
                homekit_entries = [
                    entry for entry in entries 
                    if entry.get('domain') == 'homekit'
                ]
                
                return [
                    {
                        'entity_id': f"homekit.{entry['title'].lower().replace(' ', '_')}",
                        'name': entry['title']
                    }
                    for entry in homekit_entries
                ]
            
        except Exception as e:
            logger.warning(f"Could not get HomeKit bridges: {e}")
        
        return []
    
    def get_tado_entities(self) -> List[Dict[str, Any]]:
        """Get all Tado climate entities from Home Assistant"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Get all states
            response = requests.get(f'{self.base_url}/api/states', headers=headers, timeout=10)
            
            if response.status_code == 200:
                entities = response.json()
                
                # Filter for Tado climate entities
                tado_entities = []
                for entity in entities:
                    entity_id = entity.get('entity_id', '')
                    attributes = entity.get('attributes', {})
                    
                    # Look for Tado-related entities
                    if (entity_id.startswith('climate.') and 
                        ('tado' in entity_id.lower() or 
                         'tado' in attributes.get('friendly_name', '').lower() or
                         'tado' in str(attributes.get('integration', '')).lower())):
                        
                        tado_entities.append({
                            'entity_id': entity_id,
                            'name': attributes.get('friendly_name', entity_id),
                            'current_temperature': attributes.get('current_temperature'),
                            'temperature': attributes.get('temperature'),
                            'hvac_mode': attributes.get('hvac_mode'),
                            'hvac_modes': attributes.get('hvac_modes', []),
                            'min_temp': attributes.get('min_temp', 5),
                            'max_temp': attributes.get('max_temp', 30),
                            'target_temp_step': attributes.get('target_temp_step', 0.5),
                            'state': entity.get('state')
                        })
                
                return tado_entities
            else:
                raise Exception(f"Failed to get entities: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting Tado entities: {e}")
            raise
    
    def get_entity_state(self, entity_id: str) -> Dict[str, Any]:
        """Get current state of a specific entity"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(f'{self.base_url}/api/states/{entity_id}', headers=headers, timeout=10)
            
            if response.status_code == 200:
                entity = response.json()
                attributes = entity.get('attributes', {})
                
                return {
                    'entity_id': entity_id,
                    'name': attributes.get('friendly_name', entity_id),
                    'current_temperature': attributes.get('current_temperature'),
                    'temperature': attributes.get('temperature'),
                    'hvac_mode': attributes.get('hvac_mode'),
                    'hvac_modes': attributes.get('hvac_modes', []),
                    'state': entity.get('state'),
                    'last_changed': entity.get('last_changed'),
                    'last_updated': entity.get('last_updated')
                }
            else:
                raise Exception(f"Failed to get entity state: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting entity state: {e}")
            raise
    
    def set_climate_temperature(self, entity_id: str, temperature: float) -> Dict[str, Any]:
        """Set temperature for a climate entity"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            service_data = {
                'entity_id': entity_id,
                'temperature': temperature
            }
            
            response = requests.post(
                f'{self.base_url}/api/services/climate/set_temperature',
                json=service_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {'success': True, 'temperature': temperature}
            else:
                raise Exception(f"Failed to set temperature: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error setting temperature: {e}")
            raise
    
    def set_climate_mode(self, entity_id: str, mode: str) -> Dict[str, Any]:
        """Set HVAC mode for a climate entity"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            service_data = {
                'entity_id': entity_id,
                'hvac_mode': mode
            }
            
            response = requests.post(
                f'{self.base_url}/api/services/climate/set_hvac_mode',
                json=service_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {'success': True, 'mode': mode}
            else:
                raise Exception(f"Failed to set mode: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error setting mode: {e}")
            raise
    
    def get_tado_automations(self) -> List[Dict[str, Any]]:
        """Get all Tado-related automations from Home Assistant"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Get all states
            response = requests.get(f'{self.base_url}/api/states', headers=headers, timeout=10)
            
            if response.status_code == 200:
                entities = response.json()
                
                # Filter for automation entities related to Tado
                tado_automations = []
                for entity in entities:
                    entity_id = entity.get('entity_id', '')
                    attributes = entity.get('attributes', {})
                    
                    # Look for automation entities related to Tado
                    if (entity_id.startswith('automation.') and 
                        ('tado' in entity_id.lower() or 
                         'tado' in attributes.get('friendly_name', '').lower() or
                         'heating' in entity_id.lower() or
                         'schedule' in entity_id.lower())):
                        
                        tado_automations.append({
                            'entity_id': entity_id,
                            'name': attributes.get('friendly_name', entity_id.replace('automation.', '').replace('_', ' ').title()),
                            'state': entity.get('state'),
                            'description': attributes.get('description', ''),
                            'last_triggered': attributes.get('last_triggered'),
                            'mode': attributes.get('mode', 'single')
                        })
                
                return tado_automations
            else:
                raise Exception(f"Failed to get automations: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting Tado automations: {e}")
            raise

    def _map_tado_mode(self, tado_mode: str) -> str:
        """Map Tado mode to Home Assistant HVAC mode"""
        mode_mapping = {
            'auto': 'auto',
            'heat': 'heat',
            'off': 'off',
            'manual': 'heat'
        }
        return mode_mapping.get(tado_mode.lower(), 'auto')
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get custom Tado schedules from local storage"""
        try:
            return self._load_schedules_from_storage()
        except Exception as e:
            logger.error(f"Error getting schedules: {e}")
            return []
    
    def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new schedule by updating zone automations"""
        try:
            import requests
            import uuid
            import json
            
            # Generate unique ID for schedule
            schedule_id = str(uuid.uuid4())[:8]
            
            # Prepare schedule data
            schedule_data['id'] = schedule_id
            schedule_data['created_at'] = self._get_current_time()
            schedule_data['active'] = True
            
            # Save to storage first
            self._save_schedule_to_storage(schedule_data)
            
            # Update automations for all affected zones
            success = self._update_zone_automations(schedule_data.get('zones', []))
            
            if not success:
                schedule_data['active'] = False
                schedule_data['error'] = 'Failed to create/update Home Assistant automations'
                logger.warning(f"Zone automation update failed for schedule {schedule_id}")
                # Re-save with error status
                self._save_schedule_to_storage(schedule_data)
            else:
                logger.info(f"Successfully updated zone automations for schedule {schedule_id}")
            
            return schedule_data
                
        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            # Even if automation creation fails, save the schedule for manual setup
            schedule_data['id'] = schedule_id if 'schedule_id' in locals() else str(uuid.uuid4())[:8]
            schedule_data['active'] = False
            schedule_data['error'] = str(e)
            self._save_schedule_to_storage(schedule_data)
            return schedule_data
    
    def _update_zone_automations(self, affected_zones: List[str]) -> bool:
        """Update automations for specific zones by combining all schedules"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Get all current schedules
            all_schedules = self._load_schedules_from_storage()
            
            success = True
            for zone_id in affected_zones:
                try:
                    # Get all schedules for this zone
                    zone_schedules = [s for s in all_schedules if zone_id in s.get('zones', [])]
                    
                    if zone_schedules:
                        # Create combined automation for this zone
                        automation_id = f'{self.entity_prefix}_zone_{self._get_zone_name(zone_id)}'
                        automation_config = self._build_zone_automation_config(zone_id, zone_schedules)
                        
                        # Delete existing automation for this zone
                        self._delete_ha_automation(automation_id, headers)
                        
                        # Create new combined automation
                        zone_success = self._create_ha_automation(automation_id, automation_config, headers)
                        if not zone_success:
                            success = False
                            logger.error(f"Failed to create automation for zone {zone_id}")
                        else:
                            logger.info(f"Successfully created combined automation for zone {zone_id}")
                    else:
                        # No schedules for this zone, delete automation if it exists
                        automation_id = f'{self.entity_prefix}_zone_{self._get_zone_name(zone_id)}'
                        self._delete_ha_automation(automation_id, headers)
                        logger.info(f"Removed automation for zone {zone_id} (no schedules)")
                        
                except Exception as e:
                    logger.error(f"Error updating automation for zone {zone_id}: {e}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating zone automations: {e}")
            return False
    
    def _get_zone_name(self, zone_id: str) -> str:
        """Get a clean zone name for automation ID"""
        # Remove 'climate.' prefix and clean up the name
        clean_name = zone_id.replace('climate.', '').replace('tado_', '').replace('smart_radiator_thermostat_', '')
        # Remove non-alphanumeric characters except underscores
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '', clean_name)
        return clean_name.lower()
    
    def _build_zone_automation_config(self, zone_id: str, zone_schedules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build Home Assistant automation configuration for a single zone combining all schedules"""
        zone_name = self._get_zone_display_name(zone_id)
        automation_name = f"Tado Zone: {zone_name}"
        
        # Get away/home configuration
        away_home_config = self.ha_config.get('away_home', {})
        away_home_enabled = away_home_config.get('enabled', False)
        away_entity_id = away_home_config.get('entity_id')
        home_state = away_home_config.get('home_state', 'home')
        away_temperature = away_home_config.get('away_temperature', 16.0)
        away_mode = away_home_config.get('away_mode', 'auto')
        
        # Collect all triggers from all schedules for this zone
        triggers = []
        trigger_id = 0
        
        for schedule in zone_schedules:
            if not schedule.get('active', True):
                continue  # Skip inactive schedules
                
            schedule_name = schedule.get('name', f'Schedule {schedule.get("id", "Unknown")}')
            schedule_days = schedule.get('days', [])
            
            # Handle both 'entries' and 'periods' for backward compatibility
            entries = schedule.get('entries', schedule.get('periods', []))
            
            for i, entry in enumerate(entries):
                time_str = entry.get('time', entry.get('start', '08:00'))
                temperature = entry.get('temperature', 20.0)
                
                # Trigger for entry time
                triggers.append({
                    'platform': 'time',
                    'at': time_str,
                    'id': f'schedule_{schedule.get("id")}_{i}_start',
                    'variables': {
                        'schedule_id': schedule.get('id'),
                        'schedule_name': schedule_name,
                        'entry_index': i,
                        'action_type': 'start',
                        'temperature': temperature,
                        'days': schedule_days
                    }
                })
        
        # Add trigger for away/home state changes if enabled
        if away_home_enabled and away_entity_id:
            triggers.append({
                'platform': 'state',
                'entity_id': away_entity_id,
                'id': 'away_home_change',
                'variables': {
                    'action_type': 'away_home_change'
                }
            })
        
        # Build the main action with day checking and away/home logic
        actions = [
            {
                'choose': [
                    # Handle scheduled time triggers
                    {
                        'conditions': [
                            {
                                'condition': 'template',
                                'value_template': "{{ trigger.id.endswith('_start') }}"
                            },
                            {
                                'condition': 'template',
                                'value_template': "{{ now().strftime('%a').lower() in trigger.variables.days }}"
                            }
                        ] + ([
                            {
                                'condition': 'state',
                                'entity_id': away_entity_id,
                                'state': home_state
                            }
                        ] if away_home_enabled and away_entity_id else []),
                        'sequence': [
                            {
                                'choose': [
                                    {
                                        'conditions': [
                                            {
                                                'condition': 'template',
                                                'value_template': "{{ trigger.variables.temperature == 'off' }}"
                                            }
                                        ],
                                        'sequence': [
                                            {
                                                'service': 'climate.set_hvac_mode',
                                                'target': {'entity_id': zone_id},
                                                'data': {'hvac_mode': 'off'}
                                            },
                                            {
                                                'service': 'logbook.log',
                                                'data': {
                                                    'name': 'Tado Scheduler',
                                                    'message': "Turned off heating for {{ trigger.variables.schedule_name }}"
                                                }
                                            }
                                        ]
                                    }
                                ],
                                'default': [
                                    {
                                        'service': 'climate.set_temperature',
                                        'target': {'entity_id': zone_id},
                                        'data': {'temperature': "{{ trigger.variables.temperature }}"}
                                    },
                                    {
                                        'service': 'climate.set_hvac_mode',
                                        'target': {'entity_id': zone_id},
                                        'data': {'hvac_mode': 'heat'}
                                    },
                                    {
                                        'service': 'logbook.log',
                                        'data': {
                                            'name': 'Tado Scheduler',
                                            'message': "Started heating {{ trigger.variables.schedule_name }} for {{ trigger.variables.temperature }}°C"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ] + ([
                    # Handle away/home state changes
                    {
                        'conditions': [
                            {
                                'condition': 'template',
                                'value_template': "{{ trigger.id == 'away_home_change' }}"
                            }
                        ],
                        'sequence': [
                            {
                                'choose': [
                                    # When going away
                                    {
                                        'conditions': [
                                            {
                                                'condition': 'template',
                                                'value_template': f"{{{{ trigger.to_state.state != '{home_state}' }}}}"
                                            }
                                        ],
                                        'sequence': [
                                            {
                                                'service': 'climate.set_temperature',
                                                'target': {'entity_id': zone_id},
                                                'data': {'temperature': away_temperature}
                                            },
                                            {
                                                'service': 'climate.set_hvac_mode',
                                                'target': {'entity_id': zone_id},
                                                'data': {'hvac_mode': away_mode}
                                            },
                                            {
                                                'service': 'logbook.log',
                                                'data': {
                                                    'name': 'Tado Scheduler',
                                                    'message': f"Set away mode for {zone_name} - {away_temperature}°C"
                                                }
                                            }
                                        ]
                                    }
                                ],
                                'default': [
                                    # When coming home - don't automatically set temperature, let schedules handle it
                                    {
                                        'service': 'logbook.log',
                                        'data': {
                                            'name': 'Tado Scheduler',
                                            'message': f"Welcome home! {zone_name} will follow scheduled temperatures."
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ] if away_home_enabled and away_entity_id else []),
                'default': []
            }
        ]
        
        return {
            'id': f'{self.entity_prefix}_zone_{self._get_zone_name(zone_id)}',
            'alias': automation_name,
            'description': f'Combined heating schedules for {zone_name} - Auto created by Tado Local Control' + 
                          (' (with away/home automation)' if away_home_enabled else ''),
            'trigger': triggers,
            'condition': [],  # All conditions are handled in the actions
            'action': actions,
            'mode': 'queued',
            'max': 20,
            'labels': ['auto_created', 'tado_local_control']
        }
    
    def _get_zone_display_name(self, zone_id: str) -> str:
        """Get a friendly display name for a zone"""
        # Try to get the zone from our zones list first
        zone = next((z for z in getattr(self, '_cached_zones', []) if z.get('entity_id') == zone_id), None)
        if zone:
            return zone.get('friendly_name', zone.get('name', zone_id))
        
        # Fallback to cleaning up the entity ID
        return zone_id.replace('climate.', '').replace('_', ' ').title()
    
    def _create_ha_automation(self, automation_id: str, automation_config: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """Create automation in Home Assistant using the REST API"""
        try:
            import requests
            
            # Method 1: Try using the automation.create service
            service_data = {
                'alias': automation_config['alias'],
                'trigger': automation_config['trigger'],
                'condition': automation_config.get('condition', []),
                'action': automation_config['action'],
                'mode': automation_config.get('mode', 'single'),
                'description': automation_config.get('description', '')
            }
            
            create_response = requests.post(
                f'{self.base_url}/api/services/automation/create',
                json=service_data,
                headers=headers,
                timeout=10
            )
            
            if create_response.status_code == 200:
                logger.info(f"Created automation using automation.create service")
                return True
            else:
                logger.error(f"Create service failed: {create_response.status_code}")
                logger.error(f"Create service response: {create_response.text}")
            
            # Method 2: Try using config API without labels (for compatibility)
            config_data = automation_config.copy()
            if 'labels' in config_data:
                del config_data['labels']  # Remove labels for compatibility
            
            config_response = requests.post(
                f'{self.base_url}/api/config/automation/config/{automation_id}',
                json=config_data,
                headers=headers,
                timeout=10
            )
            
            if config_response.status_code in [200, 201]:
                # Reload automations to make them active
                reload_response = requests.post(
                    f'{self.base_url}/api/services/automation/reload',
                    json={},
                    headers=headers,
                    timeout=10
                )
                
                if reload_response.status_code == 200:
                    logger.info(f"Created automation using config API and reloaded")
                    return True
                else:
                    logger.error(f"Reload failed: {reload_response.status_code}")
                    logger.error(f"Reload response: {reload_response.text}")
            else:
                logger.error(f"Config API failed: {config_response.status_code}")
                logger.error(f"Config API response: {config_response.text}")
            
            logger.error(f"All automation creation methods failed. Config API response: {config_response.status_code}, Create service response: {create_response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating Home Assistant automation: {e}")
            return False
        """Create automation in Home Assistant using the REST API"""
        try:
            import requests
            
            # Method 1: Try using the automation service
            service_data = {
                'alias': automation_config['alias'],
                'trigger': automation_config['trigger'],
                'condition': automation_config.get('condition', []),
                'action': automation_config['action'],
                'mode': automation_config.get('mode', 'single'),
                'description': automation_config.get('description', '')
            }
            
            # Create automation using the automation.create service (if available)
            create_response = requests.post(
                f'{self.base_url}/api/services/automation/create',
                json=service_data,
                headers=headers,
                timeout=10
            )
            
            if create_response.status_code == 200:
                logger.info(f"Created automation using automation.create service")
                return True
            
            # Method 2: Try using config API (newer HA versions)
            config_response = requests.post(
                f'{self.base_url}/api/config/automation/config/{automation_id}',
                json=automation_config,
                headers=headers,
                timeout=10
            )
            
            if config_response.status_code in [200, 201]:
                # Reload automations to make them active
                reload_response = requests.post(
                    f'{self.base_url}/api/services/automation/reload',
                    json={},
                    headers=headers,
                    timeout=10
                )
                
                if reload_response.status_code == 200:
                    logger.info(f"Created automation using config API and reloaded")
                    return True
            
            # Method 3: Use the generic automation service call
            generic_service_data = {
                'entity_id': f'automation.{automation_id}',
                **service_data
            }
            
            generic_response = requests.post(
                f'{self.base_url}/api/services/automation/turn_on',
                json=generic_service_data,
                headers=headers,
                timeout=10
            )
            
            if generic_response.status_code == 200:
                logger.info(f"Created automation using generic service")
                return True
            
            logger.error(f"All automation creation methods failed. Last response: {config_response.status_code}, {config_response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating Home Assistant automation: {e}")
            return False
    
    def _build_automation_config(self, schedule_id: str, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build Home Assistant automation configuration"""
        automation_name = f"Tado Schedule: {schedule_data.get('name', 'Unnamed')}"
        
        # Build triggers for each time period start and end
        triggers = []
        trigger_id = 0
        
        for i, period in enumerate(schedule_data.get('periods', [])):
            # Trigger for period start
            triggers.append({
                'platform': 'time',
                'at': period['start'],
                'id': f'period_{i}_start',
                'variables': {
                    'period_index': i,
                    'action_type': 'start',
                    'temperature': period['temperature']
                }
            })
            
            # Trigger for period end (set to a lower temperature or off)
            triggers.append({
                'platform': 'time',
                'at': period['end'],
                'id': f'period_{i}_end',
                'variables': {
                    'period_index': i,
                    'action_type': 'end',
                    'temperature': 16  # Default end temperature
                }
            })
        
        # Build conditions for days of the week
        day_conditions = []
        if schedule_data.get('days'):
            # Convert day abbreviations to Home Assistant format
            ha_days = []
            day_mapping = {
                'mon': 'mon', 'tue': 'tue', 'wed': 'wed', 'thu': 'thu',
                'fri': 'fri', 'sat': 'sat', 'sun': 'sun'
            }
            
            for day in schedule_data.get('days', []):
                if day in day_mapping:
                    ha_days.append(day_mapping[day])
            
            if ha_days:
                day_conditions.append({
                    'condition': 'time',
                    'weekday': ha_days
                })
        
        # Build actions
        actions = []
        
        # First, add a condition to check if the schedule is for start or end
        actions.append({
            'choose': [
                {
                    'conditions': [
                        {
                            'condition': 'template',
                            'value_template': "{{ trigger.id.endswith('_start') }}"
                        }
                    ],
                    'sequence': self._build_temperature_actions(schedule_data.get('zones', []), 'start')
                },
                {
                    'conditions': [
                        {
                            'condition': 'template',
                            'value_template': "{{ trigger.id.endswith('_end') }}"
                        }
                    ],
                    'sequence': self._build_temperature_actions(schedule_data.get('zones', []), 'end')
                }
            ],
            'default': []
        })
        
        return {
            'id': f'{self.entity_prefix}_schedule_{schedule_id}',
            'alias': automation_name,
            'description': f'Automated heating schedule created by Tado Local Control - {schedule_id}',
            'trigger': triggers,
            'condition': day_conditions,
            'action': actions,
            'mode': 'queued',
            'max': 10
        }
    
    def _build_temperature_actions(self, zones: List[str], action_type: str) -> List[Dict[str, Any]]:
        """Build temperature setting actions for zones"""
        actions = []
        
        for zone_entity in zones:
            if action_type == 'start':
                # Set the scheduled temperature
                actions.append({
                    'service': 'climate.set_temperature',
                    'target': {
                        'entity_id': zone_entity
                    },
                    'data': {
                        'temperature': "{{ trigger.variables.temperature }}"
                    }
                })
                
                # Also set the mode to heat
                actions.append({
                    'service': 'climate.set_hvac_mode',
                    'target': {
                        'entity_id': zone_entity
                    },
                    'data': {
                        'hvac_mode': 'heat'
                    }
                })
            else:  # action_type == 'end'
                # Set a lower temperature or turn off
                actions.append({
                    'service': 'climate.set_temperature',
                    'target': {
                        'entity_id': zone_entity
                    },
                    'data': {
                        'temperature': 16  # Default comfort temperature
                    }
                })
                
                # Optionally set to eco mode or auto
                actions.append({
                    'service': 'climate.set_hvac_mode',
                    'target': {
                        'entity_id': zone_entity
                    },
                    'data': {
                        'hvac_mode': 'auto'
                    }
                })
        
        return actions
    
    def _get_current_time(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _save_schedule_to_storage(self, schedule_data: Dict[str, Any]):
        """Save schedule to persistent storage (file-based for now)"""
        try:
            import os
            import json
            
            # Create schedules directory if it doesn't exist
            schedules_dir = os.path.join('config', 'schedules')
            os.makedirs(schedules_dir, exist_ok=True)
            
            # Save schedule to individual file
            schedule_file = os.path.join(schedules_dir, f"{schedule_data['id']}.json")
            with open(schedule_file, 'w') as f:
                json.dump(schedule_data, f, indent=2)
                
            logger.info(f"Schedule saved to {schedule_file}")
            
        except Exception as e:
            logger.error(f"Error saving schedule to storage: {e}")
    
    def _load_schedules_from_storage(self) -> List[Dict[str, Any]]:
        """Load schedules from persistent storage"""
        try:
            import os
            import json
            
            schedules_dir = os.path.join('config', 'schedules')
            if not os.path.exists(schedules_dir):
                return []
            
            schedules = []
            for filename in os.listdir(schedules_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(schedules_dir, filename), 'r') as f:
                            schedule = json.load(f)
                            schedules.append(schedule)
                    except Exception as e:
                        logger.error(f"Error loading schedule from {filename}: {e}")
            
            return schedules
            
        except Exception as e:
            logger.error(f"Error loading schedules from storage: {e}")
            return []
    
    def update_schedule(self, schedule_id: str, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing schedule"""
        try:
            # Get the old schedule to see which zones were affected
            old_schedules = self._load_schedules_from_storage()
            old_schedule = next((s for s in old_schedules if s.get('id') == schedule_id), None)
            old_zones = old_schedule.get('zones', []) if old_schedule else []
            
            # Add ID and timestamp to data
            schedule_data['id'] = schedule_id
            schedule_data['updated_at'] = self._get_current_time()
            
            # Save updated schedule
            self._save_schedule_to_storage(schedule_data)
            
            # Determine all zones that need automation updates
            new_zones = schedule_data.get('zones', [])
            affected_zones = list(set(old_zones + new_zones))
            
            # Update automations for all affected zones
            success = self._update_zone_automations(affected_zones)
            
            schedule_data['active'] = success
            
            if not success:
                schedule_data['error'] = 'Failed to update Home Assistant automations'
                logger.warning(f"Zone automation update failed for schedule {schedule_id}")
            else:
                logger.info(f"Successfully updated zone automations for schedule {schedule_id}")
            
            # Re-save with status
            self._save_schedule_to_storage(schedule_data)
            
            return schedule_data
            
        except Exception as e:
            logger.error(f"Error updating schedule: {e}")
            raise
    
    def delete_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Delete a schedule"""
        try:
            import os
            
            # Get the schedule to see which zones were affected
            old_schedules = self._load_schedules_from_storage()
            old_schedule = next((s for s in old_schedules if s.get('id') == schedule_id), None)
            affected_zones = old_schedule.get('zones', []) if old_schedule else []
            
            # Delete schedule file
            schedule_file = os.path.join('config', 'schedules', f"{schedule_id}.json")
            if os.path.exists(schedule_file):
                os.remove(schedule_file)
                logger.info(f"Deleted schedule file: {schedule_file}")
            
            # Update automations for affected zones
            automation_updated = self._update_zone_automations(affected_zones)
            
            if automation_updated:
                logger.info(f"Successfully updated zone automations after deleting schedule {schedule_id}")
            else:
                logger.warning(f"Failed to update zone automations after deleting schedule {schedule_id}")
            
            return {
                'success': True, 
                'message': f'Schedule {schedule_id} deleted',
                'automation_updated': automation_updated
            }
            
        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            raise
    
    def _delete_ha_automation(self, automation_id: str, headers: Dict[str, str]) -> bool:
        """Delete automation from Home Assistant"""
        try:
            import requests
            
            # Method 1: Try using automation.remove service
            remove_response = requests.post(
                f'{self.base_url}/api/services/automation/remove',
                json={'entity_id': f'automation.{automation_id}'},
                headers=headers,
                timeout=10
            )
            
            if remove_response.status_code == 200:
                logger.info(f"Deleted automation using automation.remove service")
                return True
            
            # Method 2: Try using config API
            config_response = requests.delete(
                f'{self.base_url}/api/config/automation/config/{automation_id}',
                headers=headers,
                timeout=10
            )
            
            if config_response.status_code in [200, 204]:
                # Reload automations
                reload_response = requests.post(
                    f'{self.base_url}/api/services/automation/reload',
                    json={},
                    headers=headers,
                    timeout=10
                )
                
                if reload_response.status_code == 200:
                    logger.info(f"Deleted automation using config API and reloaded")
                    return True
            
            # Method 3: Try turning off the automation
            turn_off_response = requests.post(
                f'{self.base_url}/api/services/automation/turn_off',
                json={'entity_id': f'automation.{automation_id}'},
                headers=headers,
                timeout=10
            )
            
            if turn_off_response.status_code == 200:
                logger.info(f"Turned off automation (deletion not supported)")
                return True
            
            logger.error(f"All automation deletion methods failed. Last response: {config_response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting Home Assistant automation: {e}")
            return False
    
    def get_tado_automations(self) -> List[Dict[str, Any]]:
        """Get Tado-related automations from Home Assistant"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Get all automations
            response = requests.get(f'{self.base_url}/api/states', headers=headers, timeout=10)
            
            if response.status_code == 200:
                entities = response.json()
                
                # Filter for Tado zone automations
                automations = []
                for entity in entities:
                    entity_id = entity.get('entity_id', '')
                    if (entity_id.startswith('automation.') and 
                        self.entity_prefix in entity_id and 
                        ('zone' in entity_id or 'schedule' in entity_id)):
                        
                        automation_data = {
                            'entity_id': entity_id,
                            'name': entity.get('attributes', {}).get('friendly_name', entity_id),
                            'state': entity.get('state', 'unknown'),
                            'description': entity.get('attributes', {}).get('description', ''),
                            'last_triggered': entity.get('attributes', {}).get('last_triggered'),
                            'mode': entity.get('attributes', {}).get('mode', 'single'),
                            'labels': entity.get('attributes', {}).get('labels', [])
                        }
                        automations.append(automation_data)
                
                return automations
            else:
                logger.error(f"Failed to fetch automations: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting automations: {e}")
            return []
    
    def activate_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Activate a schedule by enabling the zone automations"""
        try:
            # Get the schedule to find its zones
            schedules = self._load_schedules_from_storage()
            schedule = next((s for s in schedules if s.get('id') == schedule_id), None)
            
            if not schedule:
                return {'success': False, 'error': 'Schedule not found'}
            
            # Mark schedule as active and save
            schedule['active'] = True
            self._save_schedule_to_storage(schedule)
            
            # Update automations for the zones
            success = self._update_zone_automations(schedule.get('zones', []))
            
            if success:
                logger.info(f"Activated schedule {schedule_id}")
                return {'success': True, 'message': f'Schedule {schedule_id} activated'}
            else:
                return {'success': False, 'error': 'Failed to update zone automations'}
                
        except Exception as e:
            logger.error(f"Error activating schedule: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_away_home_entities(self) -> List[Dict[str, Any]]:
        """Get possible away/home entities from Home Assistant"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Get all states
            response = requests.get(f'{self.base_url}/api/states', headers=headers, timeout=10)
            
            if response.status_code == 200:
                entities = response.json()
                
                # Filter for entities that could represent away/home state
                away_home_entities = []
                for entity in entities:
                    entity_id = entity.get('entity_id', '')
                    attributes = entity.get('attributes', {})
                    state = entity.get('state', '')
                    
                    # Look for entities that might represent home/away state
                    if (
                        # Person entities (person.name)
                        entity_id.startswith('person.') or
                        # Device tracker entities
                        entity_id.startswith('device_tracker.') or
                        # Group entities (like group.all_persons)
                        (entity_id.startswith('group.') and ('person' in entity_id or 'home' in entity_id)) or
                        # Binary sensor entities for presence
                        (entity_id.startswith('binary_sensor.') and 
                         ('presence' in entity_id or 'occupancy' in entity_id or 'home' in entity_id)) or
                        # Input boolean for manual away/home control
                        entity_id.startswith('input_boolean.') or
                        # Zone entities
                        entity_id.startswith('zone.')
                    ):
                        away_home_entities.append({
                            'entity_id': entity_id,
                            'name': attributes.get('friendly_name', entity_id),
                            'state': state,
                            'device_class': attributes.get('device_class'),
                            'possible_states': self._get_possible_states(entity),
                            'entity_type': entity_id.split('.')[0]
                        })
                
                return away_home_entities
            else:
                raise Exception(f"Failed to get entities: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting away/home entities: {e}")
            raise
    
    def _get_possible_states(self, entity: Dict[str, Any]) -> List[str]:
        """Get possible states for an entity"""
        entity_id = entity.get('entity_id', '')
        state = entity.get('state', '')
        
        # Common state patterns
        if entity_id.startswith('person.') or entity_id.startswith('device_tracker.'):
            return ['home', 'not_home', 'away']
        elif entity_id.startswith('binary_sensor.'):
            return ['on', 'off']
        elif entity_id.startswith('input_boolean.'):
            return ['on', 'off']
        elif entity_id.startswith('group.'):
            return ['home', 'not_home']
        else:
            # Return current state as possible state
            return [state] if state else ['unknown']
    
    def get_away_home_state(self) -> Dict[str, Any]:
        """Get current away/home state"""
        try:
            away_home_config = self.ha_config.get('away_home', {})
            
            if not away_home_config.get('enabled') or not away_home_config.get('entity_id'):
                return {
                    'enabled': False,
                    'state': None,
                    'is_home': True  # Default to home if not configured
                }
            
            entity_id = away_home_config['entity_id']
            entity_state = self.get_entity_state(entity_id)
            
            current_state = entity_state.get('state')
            home_state = away_home_config.get('home_state', 'home')
            away_state = away_home_config.get('away_state', 'not_home')
            
            is_home = current_state == home_state
            
            return {
                'enabled': True,
                'entity_id': entity_id,
                'state': current_state,
                'is_home': is_home,
                'home_state': home_state,
                'away_state': away_state,
                'away_temperature': away_home_config.get('away_temperature', 16.0),
                'away_mode': away_home_config.get('away_mode', 'auto')
            }
            
        except Exception as e:
            logger.error(f"Error getting away/home state: {e}")
            return {
                'enabled': False,
                'state': None,
                'is_home': True,
                'error': str(e)
            }
    
    def set_away_home_state(self, state: str) -> Dict[str, Any]:
        """Set away/home state"""
        try:
            away_home_config = self.ha_config.get('away_home', {})
            
            if not away_home_config.get('enabled') or not away_home_config.get('entity_id'):
                return {'success': False, 'error': 'Away/home functionality not configured'}
            
            entity_id = away_home_config['entity_id']
            
            # Determine the service to call based on entity type
            if entity_id.startswith('input_boolean.'):
                # For input_boolean, use turn_on/turn_off
                service = 'input_boolean.turn_on' if state == 'on' else 'input_boolean.turn_off'
                service_data = {'entity_id': entity_id}
            elif entity_id.startswith('person.') or entity_id.startswith('device_tracker.'):
                # For person/device_tracker, use device_tracker.see service
                service = 'device_tracker.see'
                service_data = {
                    'dev_id': entity_id.split('.')[1],
                    'location_name': state
                }
            else:
                # Generic approach - try to set state
                return {'success': False, 'error': f'Unsupported entity type for setting state: {entity_id}'}
            
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{self.base_url}/api/services/{service.replace(".", "/")}',
                json=service_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {'success': True, 'state': state}
            else:
                raise Exception(f"Failed to set state: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error setting away/home state: {e}")
            return {'success': False, 'error': str(e)}
    
    def apply_away_mode_to_zones(self, zones: List[str]) -> Dict[str, Any]:
        """Apply away mode settings to specified zones"""
        try:
            away_home_config = self.ha_config.get('away_home', {})
            
            if not away_home_config.get('enabled'):
                return {'success': False, 'error': 'Away/home functionality not enabled'}
            
            away_temperature = away_home_config.get('away_temperature', 16.0)
            away_mode = away_home_config.get('away_mode', 'auto')
            
            results = []
            
            for zone_id in zones:
                try:
                    # Set temperature
                    temp_result = self.set_climate_temperature(zone_id, away_temperature)
                    
                    # Set mode
                    mode_result = self.set_climate_mode(zone_id, away_mode)
                    
                    results.append({
                        'zone': zone_id,
                        'temperature_success': temp_result.get('success', False),
                        'mode_success': mode_result.get('success', False)
                    })
                    
                except Exception as e:
                    logger.error(f"Error applying away mode to zone {zone_id}: {e}")
                    results.append({
                        'zone': zone_id,
                        'temperature_success': False,
                        'mode_success': False,
                        'error': str(e)
                    })
            
            success_count = sum(1 for r in results if r.get('temperature_success') and r.get('mode_success'))
            
            return {
                'success': True,
                'applied_zones': success_count,
                'total_zones': len(zones),
                'results': results,
                'away_temperature': away_temperature,
                'away_mode': away_mode
            }
            
        except Exception as e:
            logger.error(f"Error applying away mode: {e}")
            return {'success': False, 'error': str(e)}
    
    def deactivate_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Deactivate a schedule by updating the zone automations"""
        try:
            # Get the schedule to find its zones
            schedules = self._load_schedules_from_storage()
            schedule = next((s for s in schedules if s.get('id') == schedule_id), None)
            
            if not schedule:
                return {'success': False, 'error': 'Schedule not found'}
            
            # Mark schedule as inactive and save
            schedule['active'] = False
            self._save_schedule_to_storage(schedule)
            
            # Update automations for the zones
            success = self._update_zone_automations(schedule.get('zones', []))
            
            if success:
                logger.info(f"Deactivated schedule {schedule_id}")
                return {'success': True, 'message': f'Schedule {schedule_id} deactivated'}
            else:
                return {'success': False, 'error': 'Failed to update zone automations'}
                
        except Exception as e:
            logger.error(f"Error deactivating schedule: {e}")
            return {'success': False, 'error': str(e)}
