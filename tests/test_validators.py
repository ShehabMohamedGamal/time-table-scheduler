import unittest
import tempfile
import sqlite3
from src.database.validators import SchemaValidator, RelationshipValidator

class TestValidators(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile()
        self.conn = sqlite3.connect(self.db_file.name)
        self.cur = self.conn.cursor()
        
        # Create test tables
        self.cur.execute('''
            CREATE TABLE courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                credits REAL NOT NULL,
                course_type TEXT NOT NULL
            )
        ''')
        self.cur.execute('''
            CREATE TABLE timetable (
                id INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                level INTEGER,
                room_id TEXT,
                course_id TEXT,
                instructor_id TEXT
            )
        ''')
        self.conn.commit()
        
        self.schema_validator = SchemaValidator(self.db_file.name)
        self.relationship_validator = RelationshipValidator(self.db_file.name)

    def test_schema_validation(self):
        result = self.schema_validator.validate_schema()
        self.assertFalse(result.is_valid)  # Missing required tables
        self.assertTrue(any("Missing required table" in err 
                          for err in result.errors))

    def test_relationship_validation(self):
        # Insert test data with invalid foreign key
        self.cur.execute(
            "INSERT INTO timetable (day, start_time, end_time, room_id) "
            "VALUES (?, ?, ?, ?)",
            ("Monday", "09:00", "10:30", "INVALID_ROOM")
        )
        self.conn.commit()
        
        result = self.relationship_validator.validate_relationships()
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Invalid room_id" in err 
                          for err in result.errors))

    def tearDown(self):
        self.conn.close()
        self.db_file.close()