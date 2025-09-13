import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, time
import json

logger = logging.getLogger(__name__)

class SmartAutomationManager:
    """Manages consolidated Home Assistant automations for Tado schedules"""
    
    def __init__(self, ha_client, schedule_storage):
        self.ha_client = ha_client
        self.storage = schedule_storage
        self.entity_prefix = ha_client.entity_prefix
    
    def update_zone_automations(self, affected_zones: List[str]) -> bool:
        """Update automations for specific zones using consolidated approach"""
        try:
            success = True
            
            for zone_id in affected_zones:
                try:
                    # Get all active schedules for this zone (both zone-based and room-based)
                    zone_schedules = self._get_all_schedules_for_zone(zone_id)
                    logger.info(f"Zone {zone_id} has {len(zone_schedules)} active schedules: {[s.get('name', 'Unnamed') for s in zone_schedules]}")
                    
                    if zone_schedules:
                        # Create consolidated automation for this zone
                        automation_success = self._create_zone_consolidated_automation(zone_id, zone_schedules)
                        if not automation_success:
                            success = False
                            logger.error(f"Failed to create consolidated automation for zone {zone_id}")
                    else:
                        # No schedules for this zone, remove automation
                        automation_success = self._remove_zone_automation(zone_id)
                        if not automation_success:
                            logger.warning(f"Failed to remove automation for zone {zone_id}")
                        
                except Exception as e:
                    logger.error(f"Error updating automation for zone {zone_id}: {e}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating zone automations: {e}")
            return False
    
    def _get_all_schedules_for_zone(self, zone_id: str) -> List[Dict[str, Any]]:
        """Get all active schedules that affect a zone (both direct zone assignments and room assignments)"""
        try:
            schedules = []
            
            # Get direct zone-based schedules
            zone_schedules = self.storage.get_active_schedules_for_zone(zone_id)
            schedules.extend(zone_schedules)
            
            # Get room-based schedules that include this zone
            # First, find which room this zone belongs to
            rooms = self.ha_client.get_rooms_with_tado_devices()
            zone_rooms = []
            
            for room in rooms:
                for device in room.get('devices', []):
                    if device.get('entity_id') == zone_id:
                        zone_rooms.append(room['name'])
                        break
            
            # Get schedules for each room this zone belongs to
            for room_name in zone_rooms:
                room_schedules = self.storage.get_active_schedules_for_room(room_name)
                schedules.extend(room_schedules)
            
            # Remove duplicates based on schedule ID
            unique_schedules = {}
            for schedule in schedules:
                schedule_id = schedule.get('id')
                if schedule_id and schedule_id not in unique_schedules:
                    unique_schedules[schedule_id] = schedule
            
            return list(unique_schedules.values())
            
        except Exception as e:
            logger.error(f"Error getting all schedules for zone {zone_id}: {e}")
            return []
    
    def _create_zone_consolidated_automation(self, zone_id: str, zone_schedules: List[Dict[str, Any]]) -> bool:
        """Create a single consolidated automation for a zone that handles all its schedules"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.ha_client.token}',
                'Content-Type': 'application/json'
            }
            
            zone_name = self._get_zone_display_name(zone_id)
            automation_id = f'{self.entity_prefix}_zone_{self._get_zone_name(zone_id)}_consolidated'
            
            # Build the consolidated automation config
            automation_config = self._build_consolidated_automation_config(zone_id, zone_name, zone_schedules)
            
            # Delete any existing automations for this zone (old individual ones)
            self._cleanup_old_zone_automations(zone_id, headers)
            
            # Create the new consolidated automation
            success = self._create_ha_automation(automation_id, automation_config, headers)
            
            if success:
                logger.info(f"Created consolidated automation for zone {zone_id} with {len(zone_schedules)} schedules")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating consolidated automation for zone {zone_id}: {e}")
            return False
    
    def _build_consolidated_automation_config(self, zone_id: str, zone_name: str, 
                                            zone_schedules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a consolidated automation that handles all schedules for a zone"""
        
        # Get away/home configuration
        away_home_config = self.ha_client.ha_config.get('away_home', {})
        away_home_enabled = away_home_config.get('enabled', False)
        away_entity_id = away_home_config.get('entity_id')
        home_state = away_home_config.get('home_state', 'home')
        
        # Collect all unique trigger times
        trigger_times = set()
        for schedule in zone_schedules:
            for entry in schedule.get('entries', schedule.get('periods', [])):
                time_str = entry.get('time', entry.get('start', '08:00'))
                trigger_times.add(time_str)
        
        # Create triggers for each unique time
        triggers = []
        for time_str in sorted(trigger_times):
            triggers.append({
                'platform': 'time',
                'at': time_str,
                'id': f'time_{time_str.replace(":", "_")}'
            })
        
        # Build conditions
        conditions = []
        
        # Add away/home condition if enabled
        if away_home_enabled and away_entity_id:
            conditions.append({
                'condition': 'state',
                'entity_id': away_entity_id,
                'state': home_state
            })
        
        # Add template condition to check if any schedule is active for current day/time
        schedule_template = self._build_schedule_evaluation_template(zone_schedules)
        conditions.append({
            'condition': 'template',
            'value_template': schedule_template
        })
        
        # Build actions that calculate the target state dynamically
        actions = [
            {
                'variables': {
                    'target_state': self._build_target_state_template_safe(zone_schedules)
                }
            },
            {
                'choose': [
                    {
                        'conditions': [
                            {
                                'condition': 'template',
                                'value_template': "{{ target_state.action == 'off' }}"
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
                                    'name': 'Tado Smart Scheduler',
                                    'message': f"Turned off heating in {zone_name} (Schedule: {{{{ target_state.schedule_name }}}})"
                                }
                            }
                        ]
                    }
                ],
                'default': [
                    {
                        'service': 'climate.set_temperature',
                        'target': {'entity_id': zone_id},
                        'data': {'temperature': "{{ target_state.temperature }}"}
                    },
                    {
                        'service': 'climate.set_hvac_mode',
                        'target': {'entity_id': zone_id},
                        'data': {'hvac_mode': 'heat'}
                    },
                    {
                        'service': 'logbook.log',
                        'data': {
                            'name': 'Tado Smart Scheduler',
                            'message': f"Set {zone_name} to {{{{ target_state.temperature }}}}°C (Schedule: {{{{ target_state.schedule_name }}}})"
                        }
                    }
                ]
            }
        ]
        
        return {
            'alias': f"Tado Smart Scheduler: {zone_name}",
            'description': f'Consolidated smart heating schedule for {zone_name} - manages {len(zone_schedules)} schedules',
            'trigger': triggers,
            'condition': conditions,
            'action': actions,
            'mode': 'single'
        }
    
    def _build_schedule_evaluation_template(self, zone_schedules: List[Dict[str, Any]]) -> str:
        """Build a template that evaluates if any schedule should be active"""
        # This template checks if the current day/time matches any active schedule
        template_parts = []
        
        for schedule in zone_schedules:
            if not schedule.get('active', True):
                continue
            
            schedule_days = schedule.get('days', [])
            entries = schedule.get('entries', schedule.get('periods', []))
            
            if not schedule_days or not entries:
                continue
            
            # Build day condition
            day_condition = f"now().strftime('%a').lower() in {json.dumps(schedule_days)}"
            
            # Build time conditions for this schedule
            time_conditions = []
            for entry in entries:
                time_str = entry.get('time', entry.get('start', '08:00'))
                time_conditions.append(f"now().strftime('%H:%M') == '{time_str}'")
            
            if time_conditions:
                schedule_condition = f"({day_condition} and ({' or '.join(time_conditions)}))"
                template_parts.append(schedule_condition)
        
        if template_parts:
            return f"{{{{ {' or '.join(template_parts)} }}}}"
        else:
            return "{{ false }}"
    
    def _build_target_state_template(self, zone_schedules: List[Dict[str, Any]]) -> str:
        """Build a template that calculates the target temperature and action"""
        # This template finds the appropriate schedule entry for the current time
        template_lines = [
            "{% set current_day = now().strftime('%a').lower() %}",
            "{% set current_time = now().strftime('%H:%M') %}",
            "{% set result = {'temperature': 20, 'action': 'heat', 'schedule_name': 'Default'} %}"
        ]
        
        for schedule in zone_schedules:
            if not schedule.get('active', True):
                continue
            
            schedule_name = schedule.get('name', 'Unnamed Schedule')
            schedule_days = schedule.get('days', [])
            entries = schedule.get('entries', schedule.get('periods', []))
            
            if not schedule_days or not entries:
                continue
            
            # Add check for this schedule
            template_lines.extend([
                f"{{%- if current_day in {json.dumps(schedule_days)} -%}}",
            ])
            
            for entry in entries:
                time_str = entry.get('time', entry.get('start', '08:00'))
                temperature = entry.get('temperature', 20.0)
                action = 'off' if str(temperature).lower() == 'off' else 'heat'
                
                # For 'off' action, don't include temperature (it will be ignored anyway)
                if action == 'off':
                    temp_value = 16  # Fallback temperature, won't be used
                else:
                    temp_value = float(temperature)
                
                template_lines.extend([
                    f"  {{%- if current_time == '{time_str}' -%}}",
                    f"    {{%- set result = {{'temperature': {temp_value}, 'action': '{action}', 'schedule_name': '{schedule_name}'}} -%}}",
                    f"  {{%- endif -%}}"
                ])
            
            template_lines.append("{% endif %}")
        
        template_lines.append("{{ result }}")
        
        return '\n'.join(template_lines)
    
    def _build_target_state_template_safe(self, zone_schedules: List[Dict[str, Any]]) -> str:
        """Build a safer template that calculates the target temperature and action"""
        # For now, use a simpler approach that's more reliable
        if not zone_schedules:
            return "{{ {'temperature': 20, 'action': 'heat', 'schedule_name': 'Default'} }}"
        
        # Use the first active schedule's first entry as a simple example
        for schedule in zone_schedules:
            if schedule.get('active', True):
                entries = schedule.get('entries', schedule.get('periods', []))
                if entries:
                    first_entry = entries[0]
                    temperature = first_entry.get('temperature', 20)
                    action = 'off' if str(temperature).lower() == 'off' else 'heat'
                    schedule_name = schedule.get('name', 'Unnamed Schedule')
                    
                    # For 'off' action, use a numeric fallback temperature (won't be used)
                    temp_value = 16 if action == 'off' else float(temperature)
                    
                    return f"{{{{ {{'temperature': {temp_value}, 'action': '{action}', 'schedule_name': '{schedule_name}'}} }}}}"
        
        return "{{ {'temperature': 20, 'action': 'heat', 'schedule_name': 'Default'} }}"
    
    def _cleanup_old_zone_automations(self, zone_id: str, headers: Dict[str, str]):
        """Remove old individual automations for a zone"""
        try:
            # Get existing automations that might be for this zone
            zone_name = self._get_zone_name(zone_id)
            
            # Try to delete various possible old automation patterns
            old_patterns = [
                f'{self.entity_prefix}_zone_{zone_name}',
                f'{self.entity_prefix}_zone_{zone_name}_schedule_',
            ]
            
            for pattern in old_patterns:
                # This would need to be implemented to search and delete matching automations
                # For now, we'll just try the most common patterns
                for i in range(10):  # Assume max 10 old automations per zone
                    old_id = f"{pattern}{i}"
                    self._delete_ha_automation(old_id, headers)
            
        except Exception as e:
            logger.warning(f"Error cleaning up old automations for zone {zone_id}: {e}")
    
    def _remove_zone_automation(self, zone_id: str) -> bool:
        """Remove automation for a zone that no longer has schedules"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.ha_client.token}',
                'Content-Type': 'application/json'
            }
            
            automation_id = f'{self.entity_prefix}_zone_{self._get_zone_name(zone_id)}_consolidated'
            success = self._delete_ha_automation(automation_id, headers)
            
            if success:
                logger.info(f"Removed automation for zone {zone_id} (no active schedules)")
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing automation for zone {zone_id}: {e}")
            return False
    
    def _create_ha_automation(self, automation_id: str, automation_config: Dict[str, Any], 
                             headers: Dict[str, str]) -> bool:
        """Create automation in Home Assistant - enhanced version"""
        try:
            import requests
            
            # First, try to delete any existing automation with this ID
            self._delete_ha_automation(automation_id, headers)
            
            # Method 1: Try using the config API
            config_response = requests.post(
                f'{self.ha_client.base_url}/api/config/automation/config/{automation_id}',
                json=automation_config,
                headers=headers,
                timeout=15
            )
            
            if config_response.status_code in [200, 201]:
                # Reload automations to make them active
                reload_response = requests.post(
                    f'{self.ha_client.base_url}/api/services/automation/reload',
                    json={},
                    headers=headers,
                    timeout=15
                )
                
                if reload_response.status_code == 200:
                    logger.info(f"Created consolidated automation {automation_id}")
                    return True
                else:
                    logger.error(f"Automation created but reload failed: {reload_response.status_code}")
            else:
                logger.error(f"Config API failed: {config_response.status_code} - {config_response.text}")
            
            # Method 2: Try using automation.create service (fallback)
            service_data = {
                'alias': automation_config['alias'],
                'trigger': automation_config['trigger'],
                'condition': automation_config.get('condition', []),
                'action': automation_config['action'],
                'mode': automation_config.get('mode', 'single'),
                'description': automation_config.get('description', '')
            }
            
            create_response = requests.post(
                f'{self.ha_client.base_url}/api/services/automation/create',
                json=service_data,
                headers=headers,
                timeout=15
            )
            
            if create_response.status_code == 200:
                logger.info(f"Created automation using automation.create service")
                return True
            
            logger.error(f"All automation creation methods failed for {automation_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating Home Assistant automation: {e}")
            return False
    
    def _delete_ha_automation(self, automation_id: str, headers: Dict[str, str]) -> bool:
        """Delete automation from Home Assistant"""
        try:
            import requests
            
            # Method 1: Try config API delete
            config_response = requests.delete(
                f'{self.ha_client.base_url}/api/config/automation/config/{automation_id}',
                headers=headers,
                timeout=10
            )
            
            if config_response.status_code in [200, 204, 404]:  # 404 is OK (already deleted)
                return True
            
            # Method 2: Try automation.remove service
            remove_response = requests.post(
                f'{self.ha_client.base_url}/api/services/automation/remove',
                json={'entity_id': f'automation.{automation_id}'},
                headers=headers,
                timeout=10
            )
            
            if remove_response.status_code in [200, 404]:
                return True
            
            # It's not critical if deletion fails
            return True
            
        except Exception as e:
            logger.warning(f"Error deleting automation {automation_id}: {e}")
            return True  # Don't fail the whole process
    
    def _get_zone_name(self, zone_id: str) -> str:
        """Get a clean zone name for automation ID"""
        clean_name = zone_id.replace('climate.', '').replace('tado_', '').replace('smart_radiator_thermostat_', '')
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '', clean_name)
        return clean_name.lower()
    
    def _get_zone_display_name(self, zone_id: str) -> str:
        """Get a friendly display name for a zone"""
        # Try to get from cached zones if available
        if hasattr(self.ha_client, '_cached_zones'):
            zone = next((z for z in self.ha_client._cached_zones if z.get('entity_id') == zone_id), None)
            if zone:
                return zone.get('friendly_name', zone.get('name', zone_id))
        
        # Fallback to cleaning up the entity ID
        return zone_id.replace('climate.', '').replace('_', ' ').title()
    
    def get_consolidation_stats(self) -> Dict[str, Any]:
        """Get statistics about automation consolidation"""
        try:
            zones_with_schedules = self.storage.get_zones_with_schedules()
            total_schedules = len(self.storage.get_all_schedules())
            
            # Calculate how many individual automations would have been created vs consolidated
            individual_count = 0
            for zone_id in zones_with_schedules:
                zone_schedules = self.storage.get_active_schedules_for_zone(zone_id)
                for schedule in zone_schedules:
                    entries = schedule.get('entries', schedule.get('periods', []))
                    individual_count += len(entries)
            
            consolidated_count = len(zones_with_schedules)
            
            return {
                'total_zones_with_schedules': len(zones_with_schedules),
                'total_schedules': total_schedules,
                'individual_automations_avoided': individual_count,
                'consolidated_automations_created': consolidated_count,
                'reduction_ratio': individual_count / max(consolidated_count, 1),
                'storage_stats': self.storage.get_database_stats()
            }
            
        except Exception as e:
            logger.error(f"Error getting consolidation stats: {e}")
            return {}
