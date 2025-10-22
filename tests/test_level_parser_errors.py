import unittest
from src.parser.level_parser import LevelParser
from src.parser.exceptions import (
    InvalidFormatError,
    MissingCourseError,
    ConstraintViolationError
)
import tempfile
import json
import sqlite3

class TestLevelParserErrors(unittest.TestCase):
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
        
        # Add some valid courses
        valid_courses = [
            ("CSC111", "Intro to Programming", 3.0, "Lecture"),
            ("MTH111", "Calculus I", 3.0, "Lecture")
        ]
        self.cur.executemany(
            "INSERT INTO courses VALUES (?, ?, ?, ?)",
            valid_courses
        )
        self.conn.commit()
        
        self.levels_file = tempfile.NamedTemporaryFile(mode='w+')

    def test_invalid_json_format(self):
        self.levels_file.write("{invalid json")
        self.levels_file.flush()
        
        parser = LevelParser(self.db_file.name, self.levels_file.name)
        with self.assertRaises(InvalidFormatError):
            parser.load_levels()

    def test_invalid_level_key(self):
        json.dump({"invalid_level": []}, self.levels_file)
        self.levels_file.flush()
        
        parser = LevelParser(self.db_file.name, self.levels_file.name)
        with self.assertRaises(InvalidFormatError):
            parser.load_levels()

    def test_missing_courses(self):
        json.dump({
            "level_1": ["CSC111", "INVALID101"]
        }, self.levels_file)
        self.levels_file.flush()
        
        parser = LevelParser(self.db_file.name, self.levels_file.name)
        parser.load_levels()
        with self.assertRaises(MissingCourseError):
            parser.validate()

    def test_invalid_elective_group(self):
        json.dump({
            "level_1": ["CSC111", ["MTH111"]]  # Single course in elective group
        }, self.levels_file)
        self.levels_file.flush()
        
        parser = LevelParser(self.db_file.name, self.levels_file.name)
        with self.assertRaises(ConstraintViolationError):
            parser.load_levels()

    def tearDown(self):
        self.conn.close()
        self.db_file.close()
        self.levels_file.close()