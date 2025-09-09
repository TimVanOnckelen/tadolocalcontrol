import socket
import json
import asyncio
import logging
import netifaces
import threading
import time
from typing import Dict, List, Any, Optional
import requests
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

logger = logging.getLogger(__name__)

class TadoLocalClient:
    """Client for local Tado V3+ communication"""
    
    def __init__(self, config):
        self.config = config
        self.tado_config = config.tado
        self.bridge_ip = self.tado_config.get('bridge_ip')
        self.bridge_port = 80
        self.discovered_devices = {}
        self.zones = {}
        self.schedules = {}
        self._discovery_thread = None
        self._running = False
    
    def start_discovery(self):
        """Start device discovery in background"""
        if not self._discovery_thread or not self._discovery_thread.is_alive():
            self._running = True
            self._discovery_thread = threading.Thread(target=self._discovery_loop)
            self._discovery_thread.daemon = True
            self._discovery_thread.start()
            logger.info("Started Tado device discovery")
    
    def stop_discovery(self):
        """Stop device discovery"""
        self._running = False
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=5)
    
    def _discovery_loop(self):
        """Background discovery loop"""
        while self._running:
            try:
                self._discover_bridge()
                time.sleep(30)  # Discover every 30 seconds
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _discover_bridge(self):
        """Discover Tado bridge on local network"""
        if self.bridge_ip:
            # Use configured IP
            logger.info(f"Testing configured bridge IP: {self.bridge_ip}")
            if self._test_bridge_connection(self.bridge_ip):
                self.discovered_devices[self.bridge_ip] = {
                    'ip': self.bridge_ip,
                    'type': 'bridge',
                    'name': 'Tado Bridge'
                }
                logger.info(f"Verified Tado bridge at configured IP: {self.bridge_ip}")
            else:
                logger.warning(f"Configured bridge IP {self.bridge_ip} is not responding")
            return
        
        # Auto-discovery via multiple methods
        logger.info("Starting Tado bridge auto-discovery...")
        
        # Method 1: mDNS/Bonjour discovery
        bridge_ip = self._discover_via_mdns()
        if bridge_ip:
            logger.info(f"Found Tado bridge via mDNS: {bridge_ip}")
            self.bridge_ip = bridge_ip
            self.discovered_devices[bridge_ip] = {
                'ip': bridge_ip,
                'type': 'bridge',
                'name': 'Tado Bridge'
            }
            return
        
        # Method 2: Network scan
        logger.info("mDNS discovery failed, starting network scan...")
        networks = self._get_local_networks()
        logger.info(f"Scanning networks: {networks}")
        
        for network in networks:
            try:
                bridge_ip = self._scan_network(network)
                if bridge_ip:
                    logger.info(f"Found Tado bridge via network scan: {bridge_ip}")
                    self.bridge_ip = bridge_ip
                    self.discovered_devices[bridge_ip] = {
                        'ip': bridge_ip,
                        'type': 'bridge',
                        'name': 'Tado Bridge'
                    }
                    return
            except Exception as e:
                logger.error(f"Error scanning network {network}: {e}")
        
        logger.warning("No Tado bridge found via auto-discovery")
    
    def _discover_via_mdns(self) -> Optional[str]:
        """Try to discover Tado bridge via mDNS/Bonjour"""
        try:
            import subprocess
            import re
            
            # Try to find Tado devices via Bonjour/mDNS
            result = subprocess.run(
                ['dns-sd', '-B', '_tado._tcp'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output for Tado devices
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'tado' in line.lower():
                        logger.info(f"Found mDNS entry: {line}")
                        # Extract IP if possible
                        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', line)
                        if ip_match:
                            return ip_match.group(1)
            
        except subprocess.TimeoutExpired:
            logger.debug("mDNS discovery timed out")
        except FileNotFoundError:
            logger.debug("dns-sd command not available")
        except Exception as e:
            logger.debug(f"mDNS discovery error: {e}")
        
        # Try alternative mDNS method
        try:
            result = subprocess.run(
                ['avahi-browse', '-r', '_tado._tcp'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'address' in line.lower() and '=' in line:
                        ip_match = re.search(r'\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]', line)
                        if ip_match:
                            return ip_match.group(1)
                            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        except Exception as e:
            logger.debug(f"Alternative mDNS discovery error: {e}")
        
        return None
    
    def _get_local_networks(self) -> List[str]:
        """Get local network ranges to scan"""
        networks = []
        
        try:
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info.get('addr')
                        netmask = addr_info.get('netmask')
                        
                        if ip and netmask and not ip.startswith('127.'):
                            # Calculate network
                            ip_parts = ip.split('.')
                            mask_parts = netmask.split('.')
                            
                            network_parts = []
                            for i in range(4):
                                network_parts.append(str(int(ip_parts[i]) & int(mask_parts[i])))
                            
                            network = '.'.join(network_parts)
                            
                            # For /24 networks, scan the range
                            if netmask == '255.255.255.0':
                                networks.append(f"{network[:-1]}*")
        
        except Exception as e:
            logger.error(f"Error getting networks: {e}")
            # Fallback to common ranges
            networks = ['192.168.1.*', '192.168.0.*', '10.0.0.*']
        
        return networks
    
    def _scan_network(self, network_pattern: str) -> Optional[str]:
        """Scan network for Tado devices"""
        base_ip = network_pattern.replace('*', '')
        logger.info(f"Scanning network range: {base_ip}1-254")
        
        # Scan broader range and prioritize common router/bridge IPs
        priority_ips = [1, 2, 10, 11, 50, 100, 101, 200, 201, 254]
        other_ips = [i for i in range(1, 255) if i not in priority_ips]
        
        # Test priority IPs first
        for i in priority_ips:
            ip = f"{base_ip}{i}"
            logger.debug(f"Testing priority IP: {ip}")
            if self._test_bridge_connection(ip):
                logger.info(f"Found Tado bridge at {ip}")
                return ip
        
        # Test remaining IPs (limit to reasonable range for performance)
        for i in other_ips[:50]:  # Test first 50 remaining IPs
            ip = f"{base_ip}{i}"
            logger.debug(f"Testing IP: {ip}")
            if self._test_bridge_connection(ip):
                logger.info(f"Found Tado bridge at {ip}")
                return ip
        
        return None
    
    def _test_bridge_connection(self, ip: str) -> bool:
        """Test if IP is a Tado bridge"""
        logger.debug(f"Testing connection to {ip}")
        
        # Test multiple endpoints and methods
        test_endpoints = [
            '/api/v1/status',
            '/api/v1/zones',
            '/api/status',
            '/status',
            '/',
            ':80',  # Just test if port 80 is open
        ]
        
        for endpoint in test_endpoints:
            try:
                if endpoint == ':80':
                    # Test if port 80 is open
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((ip, 80))
                    sock.close()
                    if result == 0:
                        logger.debug(f"Port 80 is open on {ip}")
                        # If port is open, try HTTP request
                        continue
                    else:
                        continue
                
                url = f"http://{ip}{endpoint}"
                logger.debug(f"Testing URL: {url}")
                
                response = requests.get(
                    url,
                    timeout=3,
                    headers={
                        'User-Agent': 'TadoLocalControl/1.0',
                        'Accept': 'application/json, text/html, */*'
                    }
                )
                
                logger.debug(f"Response from {url}: {response.status_code}")
                
                if response.status_code == 200:
                    content = response.text.lower()
                    logger.debug(f"Response content preview: {content[:200]}")
                    
                    # Check for Tado-specific indicators
                    tado_indicators = [
                        'tado',
                        'internet bridge',
                        'thermostat',
                        'heating',
                        'zones',
                        'temperature'
                    ]
                    
                    for indicator in tado_indicators:
                        if indicator in content:
                            logger.info(f"Found Tado indicator '{indicator}' at {ip}")
                            return True
                    
                    # Check JSON response for Tado-specific fields
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            keys = str(data.keys()).lower()
                            values = str(data.values()).lower()
                            
                            if any(indicator in keys + values for indicator in tado_indicators):
                                logger.info(f"Found Tado data structure at {ip}")
                                return True
                    except:
                        pass
                
                # Some devices might return other status codes but still be Tado
                elif response.status_code in [401, 403]:
                    logger.info(f"Found device at {ip} (auth required) - might be Tado")
                    # Try to identify from headers or error message
                    if 'tado' in response.text.lower() or 'tado' in str(response.headers).lower():
                        return True
                        
            except requests.exceptions.ConnectTimeout:
                logger.debug(f"Connection timeout to {ip}{endpoint}")
            except requests.exceptions.ConnectionError:
                logger.debug(f"Connection error to {ip}{endpoint}")
            except Exception as e:
                logger.debug(f"Error testing {ip}{endpoint}: {e}")
        
        return False
    
    def discover_devices(self) -> List[Dict[str, Any]]:
        """Get discovered devices"""
        if not self.discovered_devices:
            self._discover_bridge()
        
        devices = []
        for device_data in self.discovered_devices.values():
            devices.append({
                'name': device_data['name'],
                'type': device_data['type'],
                'ip': device_data['ip']
            })
        
        return devices
    
    def get_zones(self) -> List[Dict[str, Any]]:
        """Get all zones from Tado bridge"""
        if not self.bridge_ip:
            self._discover_bridge()
            if not self.bridge_ip:
                raise Exception("No Tado bridge found")
        
        try:
            response = requests.get(
                f"http://{self.bridge_ip}/api/v1/zones",
                timeout=self.tado_config.get('timeout', 10)
            )
            
            if response.status_code == 200:
                zones_data = response.json()
                
                # Process zones data
                zones = []
                for zone_id, zone_info in zones_data.items():
                    zone = {
                        'id': int(zone_id),
                        'name': zone_info.get('name', f'Zone {zone_id}'),
                        'type': zone_info.get('type', 'heating'),
                        'current_temperature': zone_info.get('sensorDataPoints', {}).get('insideTemperature', {}).get('celsius'),
                        'target_temperature': zone_info.get('setting', {}).get('temperature', {}).get('celsius'),
                        'mode': zone_info.get('setting', {}).get('type', 'auto'),
                        'humidity': zone_info.get('sensorDataPoints', {}).get('humidity', {}).get('percentage'),
                        'open_window': zone_info.get('openWindow', False),
                        'overlay': zone_info.get('overlay')
                    }
                    zones.append(zone)
                
                self.zones = {zone['id']: zone for zone in zones}
                return zones
            else:
                raise Exception(f"Failed to get zones: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting zones: {e}")
            raise
    
    def get_zone(self, zone_id: int) -> Dict[str, Any]:
        """Get specific zone details"""
        if zone_id not in self.zones:
            self.get_zones()  # Refresh zones
        
        if zone_id in self.zones:
            return self.zones[zone_id]
        else:
            raise Exception(f"Zone {zone_id} not found")
    
    def set_zone_temperature(self, zone_id: int, temperature: float) -> Dict[str, Any]:
        """Set zone target temperature"""
        if not self.bridge_ip:
            raise Exception("No Tado bridge found")
        
        try:
            payload = {
                "setting": {
                    "type": "HEATING",
                    "power": "ON",
                    "temperature": {
                        "celsius": temperature
                    }
                },
                "termination": {
                    "type": "MANUAL"
                }
            }
            
            response = requests.put(
                f"http://{self.bridge_ip}/api/v1/zones/{zone_id}/overlay",
                json=payload,
                timeout=self.tado_config.get('timeout', 10)
            )
            
            if response.status_code in [200, 204]:
                # Update local cache
                if zone_id in self.zones:
                    self.zones[zone_id]['target_temperature'] = temperature
                
                return {'success': True, 'temperature': temperature}
            else:
                raise Exception(f"Failed to set temperature: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error setting temperature: {e}")
            raise
    
    def set_zone_mode(self, zone_id: int, mode: str) -> Dict[str, Any]:
        """Set zone heating mode"""
        if not self.bridge_ip:
            raise Exception("No Tado bridge found")
        
        try:
            if mode == 'off':
                payload = {
                    "setting": {
                        "type": "HEATING",
                        "power": "OFF"
                    },
                    "termination": {
                        "type": "MANUAL"
                    }
                }
            elif mode == 'auto':
                # Remove overlay to return to schedule
                response = requests.delete(
                    f"http://{self.bridge_ip}/api/v1/zones/{zone_id}/overlay",
                    timeout=self.tado_config.get('timeout', 10)
                )
                
                if response.status_code in [200, 204]:
                    if zone_id in self.zones:
                        self.zones[zone_id]['mode'] = 'auto'
                    return {'success': True, 'mode': 'auto'}
                else:
                    raise Exception(f"Failed to set auto mode: HTTP {response.status_code}")
            else:
                # Manual heating mode
                current_temp = self.zones.get(zone_id, {}).get('target_temperature', 20)
                payload = {
                    "setting": {
                        "type": "HEATING",
                        "power": "ON",
                        "temperature": {
                            "celsius": current_temp
                        }
                    },
                    "termination": {
                        "type": "MANUAL"
                    }
                }
            
            if mode != 'auto':
                response = requests.put(
                    f"http://{self.bridge_ip}/api/v1/zones/{zone_id}/overlay",
                    json=payload,
                    timeout=self.tado_config.get('timeout', 10)
                )
                
                if response.status_code in [200, 204]:
                    if zone_id in self.zones:
                        self.zones[zone_id]['mode'] = mode
                    return {'success': True, 'mode': mode}
                else:
                    raise Exception(f"Failed to set mode: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error setting mode: {e}")
            raise
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get heating schedules"""
        # Placeholder - Tado local API may not support full schedule management
        return []
    
    def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new heating schedule"""
        # Placeholder - Implementation depends on Tado local API capabilities
        raise NotImplementedError("Schedule creation not yet implemented")
    
    def __del__(self):
        """Cleanup on destruction"""
        self.stop_discovery()
