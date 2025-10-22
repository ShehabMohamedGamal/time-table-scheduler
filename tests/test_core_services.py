import unittest
import tempfile
import sqlite3
import json
from datetime import time
from src.generator.timetable_generator import TimetableGenerator, GeneratorResult
from src.validator.solution_validator import SolutionValidator
from src.csp.variable import TimeSlot, ResourceRequirements

class TestCoreServices(unittest.TestCase):
    def setUp(self):
        """Set up test environment with sample data"""
        # Create temporary database
        self.db_file = tempfile.NamedTemporaryFile()
        self.setup_test_database()
        
        # Create temporary levels file
        self.levels_file = tempfile.NamedTemporaryFile(mode='w+')
        self.setup_test_levels()
        
        # Initialize components
        self.generator = TimetableGenerator(self.db_file.name, self.levels_file.name)
        self.validator = SolutionValidator(self.generator.constraint_manager)
    
    def setup_test_database(self):
        """Create test database with sample data"""
        conn = sqlite3.connect(self.db_file.name)
        cur = conn.cursor()
        
        # Create schema
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
        ''')
        
        # Insert test data
        cur.executemany("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?)", [
            ("CSC111", "Programming 1", "Lecture", 30, 0, 1),
            ("CSC112", "Programming 2", "Lab", 25, 1, 1),
            ("MTH101", "Math 1", "Lecture", 40, 0, 0)
        ])
        
        cur.executemany("INSERT INTO rooms VALUES (?, ?, ?)", [
            ("R101", "Lecture", 50),
            ("R102", "Lab", 30),
            ("R103", "Lecture", 40)
        ])
        
        cur.executemany("INSERT INTO instructors VALUES (?, ?, ?)", [
            ("INS1", "Dr. Smith", '{"days": ["Monday", "Wednesday"]}'),
            ("INS2", "Dr. Jones", '{"days": ["Tuesday", "Thursday"]}')
        ])
        
        conn.commit()
        conn.close()
    
    def setup_test_levels(self):
        """Create test levels configuration"""
        levels_data = {
            "level_1": ["CSC111", "MTH101"],
            "level_2": ["CSC112"]
        }
        json.dump(levels_data, self.levels_file)
        self.levels_file.flush()

class TestTimetableGenerator(TestCoreServices):
    """Test timetable generation functionality"""
    
    def test_successful_generation(self):
        """Test successful timetable generation"""
        result = self.generator.generate()
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.timetable)
        self.assertTrue(len(result.timetable) == 2)  # Two levels
        
        # Verify level assignments
        self.assertTrue(all(var.is_assigned 
                          for vars in result.timetable.values() 
                          for var in vars))
    
    def test_generation_with_constraints(self):
        """Test generation with specific constraints"""
        # Add a constraint that makes scheduling impossible
        def impossible_constraint(variables):
            return False
        
        self.generator.constraint_manager.add_constraint(impossible_constraint)
        result = self.generator.generate()
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
    
    def test_resource_allocation(self):
        """Test proper resource allocation"""
        result = self.generator.generate()
        
        if result.success:
            # Check room types match course requirements
            for level_vars in result.timetable.values():
                for var in level_vars:
                    room_type = self.generator.domain.rooms[var._assigned_room].room_type
                    self.assertEqual(room_type, var.requirements.room_type)

class TestSolutionValidator(TestCoreServices):
    """Test solution validation functionality"""
    
    def test_valid_solution(self):
        """Test validation of valid solution"""
        # Generate a valid solution
        result = self.generator.generate()
        
        if result.success:
            validation = self.validator.validate_solution(result.timetable)
            
            self.assertTrue(validation.is_valid)
            self.assertEqual(len(validation.constraint_violations), 0)
            self.assertGreater(validation.quality_score, 0)
    
    def test_invalid_solution(self):
        """Test validation of invalid solution"""
        # Create an invalid timetable with conflicts
        result = self.generator.generate()
        
        if result.success:
            # Introduce a conflict
            vars_level1 = result.timetable[1]
            if len(vars_level1) >= 2:
                # Assign same time slot to two courses
                vars_level1[1]._assigned_time = vars_level1[0]._assigned_time
                vars_level1[1]._assigned_room = vars_level1[0]._assigned_room
                
                validation = self.validator.validate_solution(result.timetable)
                self.assertFalse(validation.is_valid)
                self.assertGreater(len(validation.constraint_violations), 0)

class TestIntegration(TestCoreServices):
    """Test integration between components"""
    
    def test_end_to_end_flow(self):
        """Test complete flow from generation to validation"""
        # Generate timetable
        gen_result = self.generator.generate()
        self.assertTrue(gen_result.success)
        
        # Validate solution
        validation = self.validator.validate_solution(gen_result.timetable)
        self.assertTrue(validation.is_valid)
        
        # Generate report
        from src.validator.report_generator import ReportGenerator
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = ReportGenerator(tmpdir)
            report = reporter.generate_report(
                validation,
                [v for vars in gen_result.timetable.values() for v in vars],
                gen_result.stats
            )
            
            self.assertIsNotNone(report)
            reporter.save_report(report)
    
    def test_error_handling(self):
        """Test error handling across components"""
        # Test with invalid levels file
        with tempfile.NamedTemporaryFile(mode='w+') as bad_file:
            bad_file.write("invalid json")
            bad_file.flush()
            
            bad_generator = TimetableGenerator(self.db_file.name, bad_file.name)
            result = bad_generator.generate()
            
            self.assertFalse(result.success)
            self.assertIsNotNone(result.error)
    
    def tearDown(self):
        self.db_file.close()
        self.levels_file.close()