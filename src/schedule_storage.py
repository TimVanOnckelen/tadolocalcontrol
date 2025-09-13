import sqlite3
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, time
import os

logger = logging.getLogger(__name__)

class OptimizedScheduleStorage:
    """Optimized schedule storage using SQLite for better performance and scalability"""
    
    def __init__(self, db_path: str = "config/schedules.db"):
        self.db_path = db_path
        self.ensure_directory()
        self.init_database()
    
    def ensure_directory(self):
        """Ensure the config directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """Initialize the SQLite database with optimized schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schedules (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT  -- JSON for additional data
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schedule_zones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id TEXT NOT NULL,
                        zone_id TEXT NOT NULL,
                        FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
                        UNIQUE(schedule_id, zone_id)
                    )
                """)
                
                # Add new table for room-based schedules
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schedule_rooms (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id TEXT NOT NULL,
                        room_name TEXT NOT NULL,
                        area_id TEXT,
                        FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
                        UNIQUE(schedule_id, room_name)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schedule_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        schedule_id TEXT NOT NULL,
                        day_of_week INTEGER NOT NULL,  -- 0=Monday, 6=Sunday
                        time_minutes INTEGER NOT NULL, -- Minutes since midnight
                        temperature REAL,
                        action TEXT DEFAULT 'heat',    -- 'heat', 'off', 'auto'
                        FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
                    )
                """)
                
                # Create optimized indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_zones ON schedule_zones(zone_id, schedule_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_rooms ON schedule_rooms(room_name, schedule_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_entries_time ON schedule_entries(day_of_week, time_minutes)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_schedule_entries_schedule ON schedule_entries(schedule_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_active_schedules ON schedules(active)")
                
                logger.info("Schedule database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing schedule database: {e}")
            raise
    
    def migrate_from_legacy_storage(self, legacy_schedules_dir: str = "config/schedules"):
        """Migrate existing JSON schedules to the new database format"""
        if not os.path.exists(legacy_schedules_dir):
            logger.info("No legacy schedules directory found, skipping migration")
            return
        
        try:
            migrated_count = 0
            for filename in os.listdir(legacy_schedules_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(legacy_schedules_dir, filename), 'r') as f:
                            legacy_schedule = json.load(f)
                        
                        # Convert legacy format to new format
                        self._migrate_single_schedule(legacy_schedule)
                        migrated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error migrating schedule from {filename}: {e}")
            
            logger.info(f"Migrated {migrated_count} schedules from legacy format")
            
        except Exception as e:
            logger.error(f"Error during migration: {e}")
    
    def _migrate_single_schedule(self, legacy_schedule: Dict[str, Any]):
        """Migrate a single legacy schedule to the new format"""
        schedule_id = legacy_schedule.get('id')
        if not schedule_id:
            return
        
        # Check if already migrated
        if self.get_schedule(schedule_id):
            return
        
        # Create schedule entry
        metadata = {
            'legacy_migrated': True,
            'original_created_at': legacy_schedule.get('created_at'),
            'error': legacy_schedule.get('error')
        }
        
        self.create_schedule(
            schedule_id=schedule_id,
            name=legacy_schedule.get('name', 'Migrated Schedule'),
            zones=legacy_schedule.get('zones', []),
            entries=self._convert_legacy_periods(legacy_schedule),
            days=legacy_schedule.get('days', []),
            active=legacy_schedule.get('active', True),
            metadata=metadata
        )
    
    def _convert_legacy_periods(self, legacy_schedule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert legacy periods/entries format to new format"""
        entries = []
        
        # Handle both 'periods' and 'entries' for backward compatibility
        periods = legacy_schedule.get('periods', legacy_schedule.get('entries', []))
        
        for period in periods:
            # Legacy format used 'start'/'end' or just 'time'
            time_str = period.get('time', period.get('start', '08:00'))
            temperature = period.get('temperature', 20.0)
            
            entries.append({
                'time': time_str,
                'temperature': temperature,
                'action': 'off' if str(temperature).lower() == 'off' else 'heat'
            })
        
        return entries
    
    def create_schedule(self, schedule_id: str, name: str, zones: List[str] = None, 
                       rooms: List[str] = None, entries: List[Dict[str, Any]] = None, 
                       days: List[str] = None, active: bool = True, 
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new schedule with optimized storage - supports both zones and rooms"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert schedule
                conn.execute("""
                    INSERT OR REPLACE INTO schedules (id, name, active, metadata)
                    VALUES (?, ?, ?, ?)
                """, (schedule_id, name, active, json.dumps(metadata or {})))
                
                # Clear existing zones, rooms, and entries
                conn.execute("DELETE FROM schedule_zones WHERE schedule_id = ?", (schedule_id,))
                conn.execute("DELETE FROM schedule_rooms WHERE schedule_id = ?", (schedule_id,))
                conn.execute("DELETE FROM schedule_entries WHERE schedule_id = ?", (schedule_id,))
                
                # Insert zones (for backward compatibility)
                if zones:
                    for zone_id in zones:
                        conn.execute("""
                            INSERT INTO schedule_zones (schedule_id, zone_id)
                            VALUES (?, ?)
                        """, (schedule_id, zone_id))
                
                # Insert rooms (new room-based approach)
                if rooms:
                    for room_name in rooms:
                        # Extract area_id if it's in format "room_name|area_id"
                        area_id = None
                        if '|' in room_name:
                            room_name, area_id = room_name.split('|', 1)
                        
                        conn.execute("""
                            INSERT INTO schedule_rooms (schedule_id, room_name, area_id)
                            VALUES (?, ?, ?)
                        """, (schedule_id, room_name, area_id))
                
                # Insert entries for each day
                if entries and days:
                    day_mapping = {
                        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 
                        'fri': 4, 'sat': 5, 'sun': 6
                    }
                    
                    for day_abbr in days:
                        day_num = day_mapping.get(day_abbr.lower())
                        if day_num is None:
                            continue
                        
                        for entry in entries:
                            time_str = entry.get('time', '08:00')
                            time_minutes = self._time_str_to_minutes(time_str)
                            temperature = entry.get('temperature', 20.0)
                            action = entry.get('action', 'heat')
                            
                            if str(temperature).lower() == 'off':
                                action = 'off'
                                temperature = None
                            
                            conn.execute("""
                                INSERT INTO schedule_entries 
                                (schedule_id, day_of_week, time_minutes, temperature, action)
                                VALUES (?, ?, ?, ?, ?)
                            """, (schedule_id, day_num, time_minutes, temperature, action))
                
                # Explicitly commit the transaction
                conn.commit()
                
                target_type = "rooms" if rooms else "zones"
                target_count = len(rooms or zones or [])
                logger.info(f"Created schedule {schedule_id} with {target_count} {target_type} and {len(entries or [])} entries")
                result = self.get_schedule(schedule_id)
                if result is None:
                    logger.error(f"get_schedule returned None immediately after creation for {schedule_id}")
                return result
                
        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get schedule info
                schedule_row = conn.execute("""
                    SELECT * FROM schedules WHERE id = ?
                """, (schedule_id,)).fetchone()
                
                if not schedule_row:
                    return None
                
                # Get zones (for backward compatibility)
                zones = [row[0] for row in conn.execute("""
                    SELECT zone_id FROM schedule_zones WHERE schedule_id = ?
                """, (schedule_id,)).fetchall()]
                
                # Get rooms (new room-based approach)
                rooms = []
                room_rows = conn.execute("""
                    SELECT room_name, area_id FROM schedule_rooms WHERE schedule_id = ?
                """, (schedule_id,)).fetchall()
                
                for room_row in room_rows:
                    room_name = room_row[0]
                    area_id = room_row[1]
                    if area_id:
                        rooms.append(f"{room_name}|{area_id}")
                    else:
                        rooms.append(room_name)
                
                # Get entries grouped by day
                entries_rows = conn.execute("""
                    SELECT day_of_week, time_minutes, temperature, action
                    FROM schedule_entries 
                    WHERE schedule_id = ?
                    ORDER BY day_of_week, time_minutes
                """, (schedule_id,)).fetchall()
                
                # Group entries by day and convert to legacy format
                day_names = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                days = []
                periods = []
                
                for row in entries_rows:
                    day_name = day_names[row[0]]
                    if day_name not in days:
                        days.append(day_name)
                    
                    time_str = self._minutes_to_time_str(row[1])
                    temperature = row[2] if row[2] is not None else 'off'
                    
                    periods.append({
                        'time': time_str,
                        'temperature': temperature,
                        'action': row[3]
                    })
                
                metadata = json.loads(schedule_row['metadata']) if schedule_row['metadata'] else {}
                
                result = {
                    'id': schedule_row['id'],
                    'name': schedule_row['name'],
                    'active': bool(schedule_row['active']),
                    'zones': zones,  # For backward compatibility
                    'rooms': rooms,  # New room-based approach
                    'days': days,
                    'periods': periods,
                    'entries': periods,  # For backward compatibility
                    'created_at': schedule_row['created_at'],
                    'updated_at': schedule_row['updated_at'] if 'updated_at' in schedule_row.keys() else schedule_row['created_at'],
                    **metadata
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting schedule {schedule_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                schedule_rows = conn.execute("""
                    SELECT id FROM schedules ORDER BY created_at DESC
                """).fetchall()
                
                schedules = []
                for row in schedule_rows:
                    schedule = self.get_schedule(row[0])
                    if schedule:
                        schedules.append(schedule)
                
                return schedules
                
        except Exception as e:
            logger.error(f"Error getting all schedules: {e}")
            return []
    
    def get_active_schedules_for_zone(self, zone_id: str) -> List[Dict[str, Any]]:
        """Get all active schedules for a specific zone"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                schedule_ids = [row[0] for row in conn.execute("""
                    SELECT DISTINCT sz.schedule_id
                    FROM schedule_zones sz
                    JOIN schedules s ON sz.schedule_id = s.id
                    WHERE sz.zone_id = ? AND s.active = 1
                """, (zone_id,)).fetchall()]
                
                schedules = []
                for schedule_id in schedule_ids:
                    schedule = self.get_schedule(schedule_id)
                    if schedule:
                        schedules.append(schedule)
                
                return schedules
                
        except Exception as e:
            logger.error(f"Error getting schedules for zone {zone_id}: {e}")
            return []
    
    def get_active_schedules_for_room(self, room_name: str) -> List[Dict[str, Any]]:
        """Get all active schedules for a specific room"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                schedule_ids = [row[0] for row in conn.execute("""
                    SELECT DISTINCT sr.schedule_id
                    FROM schedule_rooms sr
                    JOIN schedules s ON sr.schedule_id = s.id
                    WHERE sr.room_name = ? AND s.active = 1
                """, (room_name,)).fetchall()]
                
                schedules = []
                for schedule_id in schedule_ids:
                    schedule = self.get_schedule(schedule_id)
                    if schedule:
                        schedules.append(schedule)
                
                return schedules
                
        except Exception as e:
            logger.error(f"Error getting schedules for room {room_name}: {e}")
            return []
    
    def get_zones_for_room_schedules(self, room_name: str, ha_client=None) -> List[str]:
        """Get all zone entity IDs that belong to a room (for automation creation)"""
        try:
            if not ha_client:
                return []
            
            # Get room information from Home Assistant
            rooms = ha_client.get_rooms_with_tado_devices()
            
            # Find the matching room
            matching_room = None
            for room in rooms:
                if room['name'] == room_name:
                    matching_room = room
                    break
            
            if not matching_room:
                logger.warning(f"Room '{room_name}' not found in Home Assistant")
                return []
            
            # Extract entity IDs from the room's devices
            zone_ids = []
            for device in matching_room.get('devices', []):
                entity_id = device.get('entity_id')
                if entity_id:
                    zone_ids.append(entity_id)
            
            logger.info(f"Room '{room_name}' contains {len(zone_ids)} zones: {zone_ids}")
            return zone_ids
            
        except Exception as e:
            logger.error(f"Error getting zones for room {room_name}: {e}")
            return []
    
    def get_schedule_state_at_time(self, zone_id: str, day_of_week: int, 
                                  time_minutes: int) -> Optional[Dict[str, Any]]:
        """Get what a zone should be doing at a specific time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Find the most recent entry before or at the specified time
                entry = conn.execute("""
                    SELECT se.temperature, se.action, s.name as schedule_name
                    FROM schedule_entries se
                    JOIN schedule_zones sz ON se.schedule_id = sz.schedule_id
                    JOIN schedules s ON se.schedule_id = s.id
                    WHERE sz.zone_id = ? 
                      AND se.day_of_week = ?
                      AND se.time_minutes <= ?
                      AND s.active = 1
                    ORDER BY se.time_minutes DESC
                    LIMIT 1
                """, (zone_id, day_of_week, time_minutes)).fetchone()
                
                if entry:
                    return {
                        'temperature': entry[0],
                        'action': entry[1],
                        'schedule_name': entry[2]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting schedule state: {e}")
            return None
    
    def update_schedule(self, schedule_id: str, **updates) -> Dict[str, Any]:
        """Update an existing schedule"""
        try:
            current_schedule = self.get_schedule(schedule_id)
            if not current_schedule:
                raise ValueError(f"Schedule {schedule_id} not found")
            
            # Handle full update
            if 'zones' in updates and 'entries' in updates and 'days' in updates:
                return self.create_schedule(
                    schedule_id=schedule_id,
                    name=updates.get('name', current_schedule['name']),
                    zones=updates['zones'],
                    entries=updates['entries'],
                    days=updates['days'],
                    active=updates.get('active', current_schedule['active']),
                    metadata=updates.get('metadata', {})
                )
            
            # Handle partial updates
            with sqlite3.connect(self.db_path) as conn:
                if 'name' in updates or 'active' in updates:
                    conn.execute("""
                        UPDATE schedules 
                        SET name = COALESCE(?, name),
                            active = COALESCE(?, active),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (updates.get('name'), updates.get('active'), schedule_id))
                
                return self.get_schedule(schedule_id)
                
        except Exception as e:
            logger.error(f"Error updating schedule {schedule_id}: {e}")
            raise
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule and all its related data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Delete will cascade to zones and entries due to foreign key constraints
                cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
                deleted = cursor.rowcount > 0
                
                if deleted:
                    logger.info(f"Deleted schedule {schedule_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting schedule {schedule_id}: {e}")
            return False
    
    def get_zones_with_schedules(self) -> List[str]:
        """Get all zones that have active schedules"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                zones = [row[0] for row in conn.execute("""
                    SELECT DISTINCT sz.zone_id
                    FROM schedule_zones sz
                    JOIN schedules s ON sz.schedule_id = s.id
                    WHERE s.active = 1
                """).fetchall()]
                
                return zones
                
        except Exception as e:
            logger.error(f"Error getting zones with schedules: {e}")
            return []
    
    def _time_str_to_minutes(self, time_str: str) -> int:
        """Convert time string (HH:MM) to minutes since midnight"""
        try:
            hours, minutes = map(int, time_str.split(':'))
            return hours * 60 + minutes
        except:
            return 0
    
    def _minutes_to_time_str(self, minutes: int) -> str:
        """Convert minutes since midnight to time string (HH:MM)"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for monitoring"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}
                
                # Count records
                stats['total_schedules'] = conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0]
                stats['active_schedules'] = conn.execute("SELECT COUNT(*) FROM schedules WHERE active = 1").fetchone()[0]
                stats['total_zones'] = conn.execute("SELECT COUNT(DISTINCT zone_id) FROM schedule_zones").fetchone()[0]
                stats['total_entries'] = conn.execute("SELECT COUNT(*) FROM schedule_entries").fetchone()[0]
                
                # Database size
                stats['db_size_bytes'] = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
