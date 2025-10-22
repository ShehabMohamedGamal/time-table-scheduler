import unittest
from src.parser.level_parser import LevelParser, CourseGroup, CourseType
import tempfile
import json
import sqlite3

class TestLevelParser(unittest.TestCase):
    def setUp(self):
        # Create temporary database
        self.db_file = tempfile.NamedTemporaryFile()
        self.conn = sqlite3.connect(self.db_file.name)
        self.cur = self.conn.cursor()
        self.cur.execute('''CREATE TABLE courses 
                           (course_id TEXT PRIMARY KEY, 
                            course_name TEXT, 
                            credits REAL, 
                            course_type TEXT)''')
        
        # Create temporary levels.json
        self.levels_file = tempfile.NamedTemporaryFile(mode='w+')
        self.test_levels = {
            "level_1": [
                "CSC111",
                ["LRA104", "LRA103", "LRA105"]  # Elective group
            ]
        }
        json.dump(self.test_levels, self.levels_file)
        self.levels_file.flush()
        
        # Initialize parser
        self.parser = LevelParser(self.db_file.name, self.levels_file.name)

    def test_elective_group_validation(self):
        # Add test courses to DB
        courses = ["CSC111", "LRA104", "LRA103", "LRA105"]
        for course in courses:
            self.cur.execute("INSERT INTO courses VALUES (?, ?, ?, ?)",
                           (course, f"Test {course}", 3.0, "Lecture"))
        self.conn.commit()
        
        self.parser.load_levels()
        errors = self.parser.validate()
        self.assertEqual(len(errors), 0, f"Unexpected validation errors: {errors}")

    def test_invalid_elective_group(self):
        # Test with insufficient elective options
        invalid_levels = {
            "level_1": [
                "CSC111",
                ["LRA104"]  # Only one elective option
            ]
        }
        with tempfile.NamedTemporaryFile(mode='w+') as f:
            json.dump(invalid_levels, f)
            f.flush()
            parser = LevelParser(self.db_file.name, f.name)
            parser.load_levels()
            errors = parser.validate()
            self.assertTrue(any("fewer options" in err for err in errors))

    def tearDown(self):
        self.conn.close()
        self.db_file.close()
        self.levels_file.close()