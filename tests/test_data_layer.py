import unittest
import tempfile
import sqlite3
import json
from src.parser.level_parser import LevelParser
from src.database.database_manager import DatabaseManager
from src.database.validators import SchemaValidator, RelationshipValidator

class TestDataLayer(unittest.TestCase):
    def setUp(self):
        # Create temporary database
        self.db_file = tempfile.NamedTemporaryFile()
        self.setup_test_database()
        
        # Create temporary levels.json
        self.levels_file = tempfile.NamedTemporaryFile(mode='w+')
        self.setup_test_levels()
        
        # Initialize components
        self.db_manager = DatabaseManager(self.db_file.name)
        self.level_parser = LevelParser(self.db_file.name, self.levels_file.name)
        self.schema_validator = SchemaValidator(self.db_file.name)
    
    def setup_test_database(self):
        """Create test database schema and data"""
        conn = sqlite3.connect(self.db_file.name)
        cur = conn.cursor()
        
        # Create tables
        cur.executescript('''
            CREATE TABLE courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                course_type TEXT NOT NULL,
                min_capacity INTEGER,
                requires_lab INTEGER DEFAULT 0,
                requires_projector INTEGER DEFAULT 0
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
            
            CREATE TABLE timetable (
                id INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                room_id TEXT,
                course_id TEXT,
                instructor_id TEXT,
                FOREIGN KEY(room_id) REFERENCES rooms(room_id),
                FOREIGN KEY(course_id) REFERENCES courses(course_id),
                FOREIGN KEY(instructor_id) REFERENCES instructors(instructor_id)
            );
        ''')
        
        # Insert test data
        cur.executemany(
            "INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("CSC111", "Intro to Programming", "Lecture", 30, 0, 1),
                ("CSC112", "Data Structures", "Lab", 25, 1, 1),
                ("MTH101", "Calculus I", "Lecture", 40, 0, 0)
            ]
        )
        
        cur.executemany(
            "INSERT INTO rooms VALUES (?, ?, ?)",
            [
                ("R101", "Lecture", 50),
                ("R102", "Lab", 30),
                ("R103", "Lecture", 40)
            ]
        )
        
        cur.executemany(
            "INSERT INTO instructors VALUES (?, ?, ?)",
            [
                ("INS1", "Dr. Smith", '{"days": ["Monday", "Wednesday"]}'),
                ("INS2", "Dr. Jones", '{"days": ["Tuesday", "Thursday"]}')
            ]
        )
        
        conn.commit()
        conn.close()
    
    def setup_test_levels(self):
        """Create test levels.json data"""
        levels_data = {
            "level_1": [
                "CSC111",
                ["MTH101"]  # Elective group
            ],
            "level_2": [
                "CSC112"
            ]
        }
        json.dump(levels_data, self.levels_file)
        self.levels_file.flush()
    
    def test_level_parser(self):
        """Test level parser functionality"""
        self.level_parser.load_levels()
        
        # Test level loading
        self.assertEqual(len(self.level_parser.levels), 2)
        self.assertIn("level_1", self.level_parser.levels)
        
        # Test course validation
        errors = self.level_parser.validate_against_db()
        self.assertEqual(len(errors), 0)
        
        # Test elective group handling
        level1_courses = self.level_parser.levels["level_1"]
        self.assertTrue(any(isinstance(c, list) for c in level1_courses))
    
    def test_database_operations(self):
        """Test database CRUD operations"""
        # Test Create
        result = self.db_manager.create_record(
            "courses",
            {
                "course_id": "PHY101",
                "course_name": "Physics I",
                "course_type": "Lecture",
                "min_capacity": 35
            }
        )
        self.assertTrue(result.success)
        
        # Test Read
        result = self.db_manager.read_records(
            "courses",
            {"course_id": "PHY101"}
        )
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        
        # Test Update
        result = self.db_manager.update_record(
            "courses",
            {"min_capacity": 40},
            {"course_id": "PHY101"}
        )
        self.assertTrue(result.success)
        
        # Test Delete
        result = self.db_manager.delete_record(
            "courses",
            {"course_id": "PHY101"}
        )
        self.assertTrue(result.success)
    
    def test_schema_validation(self):
        """Test database schema validation"""
        validation = self.schema_validator.validate_schema()
        
        self.assertTrue(validation.is_valid)
        self.assertEqual(len(validation.errors), 0)
        
        # Test relationship validation
        relationship_validator = RelationshipValidator(self.db_file.name)
        validation = relationship_validator.validate_relationships()
        self.assertTrue(validation.is_valid)
    
    def test_transaction_handling(self):
        """Test transaction management"""
        # Test successful transaction
        queries = [
            ("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?)",
             ("TEST101", "Test Course", "Lecture", 30, 0, 0)),
            ("UPDATE rooms SET room_capacity = ? WHERE room_id = ?",
             (60, "R101"))
        ]
        
        result = self.db_manager.transaction(queries)
        self.assertTrue(result.success)
        
        # Test transaction rollback
        invalid_queries = [
            ("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?)",
             ("TEST102", "Test Course 2", "Lecture", 30, 0, 0)),
            ("INSERT INTO rooms VALUES (?, ?, ?)",
             ("R101", "Lecture", 40))  # Duplicate key - should fail
        ]
        
        result = self.db_manager.transaction(invalid_queries)
        self.assertFalse(result.success)
        
        # Verify rollback
        result = self.db_manager.read_records(
            "courses",
            {"course_id": "TEST102"}
        )
        self.assertEqual(len(result.data), 0)
    
    def tearDown(self):
        self.db_file.close()
        self.levels_file.close()