import unittest
import tempfile
import sqlite3
import json
from src.generator.timetable_generator import TimetableGenerator

class TestTimetableGenerator(unittest.TestCase):
    def setUp(self):
        # Create temporary database
        self.db_file = tempfile.NamedTemporaryFile()
        self.conn = sqlite3.connect(self.db_file.name)
        self.cur = self.conn.cursor()
        
        # Create required tables
        self.cur.executescript('''
            CREATE TABLE courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT,
                course_type TEXT,
                min_capacity INTEGER,
                requires_lab INTEGER,
                requires_projector INTEGER
            );
            
            CREATE TABLE rooms (
                room_id TEXT PRIMARY KEY,
                room_type TEXT,
                room_capacity INTEGER
            );
            
            CREATE TABLE instructors (
                instructor_id TEXT PRIMARY KEY,
                instructor_name TEXT
            );
        ''')
        
        # Insert test data
        self.cur.executemany(
            "INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("CSC111", "Intro CS", "Lecture", 30, 0, 1),
                ("CSC112", "Programming", "Lab", 25, 1, 1)
            ]
        )
        
        self.cur.executemany(
            "INSERT INTO rooms VALUES (?, ?, ?)",
            [
                ("R101", "Lecture", 40),
                ("R102", "Lab", 30)
            ]
        )
        
        self.cur.executemany(
            "INSERT INTO instructors VALUES (?, ?)",
            [
                ("INS1", "Dr. Smith"),
                ("INS2", "Dr. Jones")
            ]
        )
        
        self.conn.commit()
        
        # Create temporary levels file
        self.levels_file = tempfile.NamedTemporaryFile(mode='w+')
        json.dump({
            "level_1": ["CSC111"],
            "level_2": ["CSC112"]
        }, self.levels_file)
        self.levels_file.flush()
        
        self.generator = TimetableGenerator(
            self.db_file.name,
            self.levels_file.name
        )
    
    def test_successful_generation(self):
        result = self.generator.generate()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.timetable)
        self.assertIsNotNone(result.stats)
        
        # Check if all levels are scheduled
        self.assertEqual(len(result.timetable), 2)  # Two levels
        
        # Check if courses are assigned
        level1 = result.timetable[1]
        self.assertEqual(len(level1), 1)  # One course in level 1
        self.assertEqual(level1[0].course_id, "CSC111")
        
    def test_invalid_level_data(self):
        # Create invalid levels file
        with tempfile.NamedTemporaryFile(mode='w+') as invalid_file:
            json.dump({
                "level_1": ["INVALID101"]
            }, invalid_file)
            invalid_file.flush()
            
            generator = TimetableGenerator(
                self.db_file.name,
                invalid_file.name
            )
            result = generator.generate()
            
            self.assertFalse(result.success)
            self.assertIn("validation failed", result.error)
    
    def tearDown(self):
        self.conn.close()
        self.db_file.close()
        self.levels_file.close()