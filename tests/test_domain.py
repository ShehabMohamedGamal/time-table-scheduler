import unittest
from datetime import time
import tempfile
import sqlite3
from src.csp.domain import Domain, RoomAvailability, InstructorAvailability
from src.csp.variable import TimeSlot, ResourceRequirements
from src.database.database_manager import DatabaseManager

class TestDomain(unittest.TestCase):
    def setUp(self):
        # Create temporary database with test data
        self.db_file = tempfile.NamedTemporaryFile()
        self.conn = sqlite3.connect(self.db_file.name)
        self.cur = self.conn.cursor()
        
        # Create required tables
        self.cur.executescript('''
            CREATE TABLE timetable (
                id INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                level INTEGER
            );
            
            CREATE TABLE rooms (
                room_id TEXT PRIMARY KEY,
                room_type TEXT NOT NULL,
                room_capacity INTEGER
            );
            
            CREATE TABLE instructors (
                instructor_id TEXT PRIMARY KEY,
                instructor_name TEXT NOT NULL,
                preferred_slots TEXT
            );
        ''')
        
        # Insert test data
        self.cur.execute(
            "INSERT INTO timetable (day, start_time, end_time) VALUES (?, ?, ?)",
            ("Monday", "09:00", "10:30")
        )
        self.cur.execute(
            "INSERT INTO rooms (room_id, room_type, room_capacity) VALUES (?, ?, ?)",
            ("R101", "Lecture", 30)
        )
        self.cur.execute(
            "INSERT INTO instructors (instructor_id, instructor_name, preferred_slots) "
            "VALUES (?, ?, ?)",
            ("INS1", "Dr. Smith", '{"days": ["Monday"], "earliest": "09:00", "latest": "17:00"}')
        )
        
        self.conn.commit()
        self.db_manager = DatabaseManager(self.db_file.name)
        self.domain = Domain(self.db_manager)
        
    def test_load_domain_data(self):
        self.assertEqual(len(self.domain.time_slots), 1)
        self.assertEqual(len(self.domain.rooms), 1)
        self.assertEqual(len(self.domain.instructors), 1)
        
    def test_get_available_values(self):
        requirements = ResourceRequirements(
            room_type="Lecture",
            min_capacity=25
        )
        
        times, rooms, instructors = self.domain.get_available_values(requirements)
        
        self.assertEqual(len(times), 1)
        self.assertEqual(len(rooms), 1)
        self.assertEqual(len(instructors), 1)
        
    def test_availability_updates(self):
        time_slot = next(iter(self.domain.time_slots))
        room_id = "R101"
        instructor_id = "INS1"
        
        self.domain.update_availability(time_slot, room_id, instructor_id)
        
        self.assertNotIn(time_slot, self.domain.rooms[room_id].available_times)
        self.assertNotIn(time_slot, self.domain.instructors[instructor_id].available_times)
        
        self.domain.restore_availability(time_slot, room_id, instructor_id)
        
        self.assertIn(time_slot, self.domain.rooms[room_id].available_times)
        self.assertIn(time_slot, self.domain.instructors[instructor_id].available_times)
        
    def tearDown(self):
        self.conn.close()
        self.db_file.close()