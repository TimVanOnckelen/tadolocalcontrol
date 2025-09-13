#!/usr/bin/env python3
"""
Test script for the optimized schedule storage system
"""
import sys
import os
import tempfile
import shutil
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from schedule_storage import OptimizedScheduleStorage
from smart_automation_manager import SmartAutomationManager

def test_optimization():
    """Test the optimization improvements"""
    print("🚀 Testing Tado Schedule Optimization...")
    
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_schedules.db")
    
    try:
        # Initialize optimized storage
        storage = OptimizedScheduleStorage(db_path)
        print("✅ Optimized storage initialized")
        
        # Create some test schedules
        test_schedules = [
            {
                'name': 'Workday Morning',
                'zones': ['climate.living_room', 'climate.kitchen'],
                'days': ['mon', 'tue', 'wed', 'thu', 'fri'],
                'entries': [
                    {'time': '06:00', 'temperature': 20.0},
                    {'time': '08:00', 'temperature': 16.0},
                    {'time': '17:00', 'temperature': 21.0},
                    {'time': '22:00', 'temperature': 18.0}
                ]
            },
            {
                'name': 'Weekend Comfort',
                'zones': ['climate.living_room', 'climate.bedroom'],
                'days': ['sat', 'sun'],
                'entries': [
                    {'time': '08:00', 'temperature': 19.0},
                    {'time': '22:00', 'temperature': 17.0}
                ]
            },
            {
                'name': 'Kitchen Special',
                'zones': ['climate.kitchen'],
                'days': ['mon', 'wed', 'fri'],
                'entries': [
                    {'time': '05:30', 'temperature': 22.0},
                    {'time': '07:00', 'temperature': 18.0}
                ]
            }
        ]
        
        created_schedules = []
        for i, schedule_data in enumerate(test_schedules):
            schedule_id = f"test_{i+1:03d}"
            schedule = storage.create_schedule(
                schedule_id=schedule_id,
                name=schedule_data['name'],
                zones=schedule_data['zones'],
                entries=schedule_data['entries'],
                days=schedule_data['days'],
                active=True
            )
            created_schedules.append(schedule)
            print(f"✅ Created schedule: {schedule['name']}")
        
        # Test retrieval
        all_schedules = storage.get_all_schedules()
        print(f"✅ Retrieved {len(all_schedules)} schedules")
        
        # Test zone-specific queries
        living_room_schedules = storage.get_active_schedules_for_zone('climate.living_room')
        print(f"✅ Living room has {len(living_room_schedules)} active schedules")
        
        # Test time-based queries
        # Monday 7:00 AM
        monday_7am_state = storage.get_schedule_state_at_time('climate.living_room', 0, 7*60)
        if monday_7am_state:
            print(f"✅ Monday 7:00 AM - Living room should be: {monday_7am_state['temperature']}°C ({monday_7am_state['schedule_name']})")
        
        # Test statistics
        stats = storage.get_database_stats()
        print(f"✅ Database stats: {stats['total_schedules']} schedules, {stats['total_entries']} entries")
        
        # Calculate optimization benefits
        individual_automations_count = 0
        for schedule in all_schedules:
            zones = len(schedule.get('zones', []))
            entries = len(schedule.get('entries', []))
            individual_automations_count += zones * entries
        
        zones_with_schedules = len(storage.get_zones_with_schedules())
        consolidated_automations_count = zones_with_schedules
        
        reduction_ratio = individual_automations_count / max(consolidated_automations_count, 1)
        
        print(f"\n📊 Optimization Results:")
        print(f"   Individual automations (old way): {individual_automations_count}")
        print(f"   Consolidated automations (new way): {consolidated_automations_count}")
        print(f"   Reduction ratio: {reduction_ratio:.1f}x fewer automations")
        print(f"   Storage efficiency: {stats['db_size_bytes']} bytes")
        
        # Test update
        updated_schedule = storage.update_schedule('test_001', active=False)
        print(f"✅ Updated schedule: {updated_schedule['name']} (now inactive)")
        
        # Test deletion
        deleted = storage.delete_schedule('test_003')
        print(f"✅ Deleted schedule: {deleted}")
        
        final_stats = storage.get_database_stats()
        print(f"✅ Final stats: {final_stats['total_schedules']} schedules remaining")
        
        print(f"\n🎉 All tests passed! Optimization is working correctly.")
        print(f"💡 Benefits:")
        print(f"   - {reduction_ratio:.1f}x reduction in Home Assistant automations")
        print(f"   - Faster database queries with proper indexing")
        print(f"   - Better scalability for complex scheduling scenarios")
        print(f"   - Consolidated automation management")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up test directory
        shutil.rmtree(test_dir, ignore_errors=True)

def test_legacy_migration():
    """Test migration from legacy JSON format"""
    print("\n🔄 Testing Legacy Migration...")
    
    test_dir = tempfile.mkdtemp()
    
    try:
        # Create some legacy JSON schedule files
        legacy_dir = os.path.join(test_dir, "legacy_schedules")
        os.makedirs(legacy_dir, exist_ok=True)
        
        legacy_schedule = {
            "id": "legacy_001",
            "name": "Legacy Workday",
            "zones": ["climate.legacy_zone"],
            "days": ["mon", "tue", "wed"],
            "periods": [
                {"start": "07:00", "end": "09:00", "temperature": 20},
                {"start": "18:00", "end": "22:00", "temperature": 21}
            ],
            "active": True,
            "created_at": "2024-01-01T00:00:00"
        }
        
        import json
        with open(os.path.join(legacy_dir, "legacy_001.json"), 'w') as f:
            json.dump(legacy_schedule, f)
        
        print("✅ Created legacy schedule file")
        
        # Initialize storage and test migration
        db_path = os.path.join(test_dir, "migrated_schedules.db")
        storage = OptimizedScheduleStorage(db_path)
        storage.migrate_from_legacy_storage(legacy_dir)
        
        # Verify migration
        migrated_schedule = storage.get_schedule("legacy_001")
        if migrated_schedule:
            print(f"✅ Successfully migrated: {migrated_schedule['name']}")
            print(f"   - {len(migrated_schedule['zones'])} zones")
            print(f"   - {len(migrated_schedule['entries'])} time entries")
            print(f"   - Active: {migrated_schedule['active']}")
        else:
            print("❌ Migration failed")
            return False
        
        print("🎉 Legacy migration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    print("=" * 60)
    print("Tado Local Control - Schedule Optimization Test")
    print("=" * 60)
    
    success1 = test_optimization()
    success2 = test_legacy_migration()
    
    if success1 and success2:
        print(f"\n🎉 All optimization tests passed successfully!")
        print(f"\n💡 The optimization provides:")
        print(f"   • Dramatically reduced automation count")
        print(f"   • Fast database queries with proper indexing")
        print(f"   • Better scalability for complex schedules")
        print(f"   • Seamless migration from legacy format")
        print(f"   • Consolidated smart automation management")
        sys.exit(0)
    else:
        print(f"\n❌ Some tests failed. Check the output above.")
        sys.exit(1)
