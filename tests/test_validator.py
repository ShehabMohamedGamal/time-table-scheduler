import unittest
from datetime import time
from src.validator.solution_validator import SolutionValidator
from src.csp.variable import Variable, TimeSlot, ResourceRequirements
from src.csp.constraints import ConstraintManager

class TestSolutionValidator(unittest.TestCase):
    def setUp(self):
        self.constraint_manager = ConstraintManager()
        self.validator = SolutionValidator(self.constraint_manager)
        self.requirements = ResourceRequirements(
            room_type="Lecture",
            min_capacity=30
        )
    
    def test_valid_solution(self):
        # Create a valid timetable
        timetable = {
            1: [  # Level 1
                self._create_assigned_variable(
                    "CSC111", 1,
                    TimeSlot("Monday", time(9), time(10)),
                    "R101", "INS1"
                ),
                self._create_assigned_variable(
                    "CSC112", 1,
                    TimeSlot("Monday", time(10), time(11)),
                    "R102", "INS2"
                )
            ],
            2: [  # Level 2
                self._create_assigned_variable(
                    "CSC211", 2,
                    TimeSlot("Monday", time(9), time(10)),
                    "R103", "INS3"
                )
            ]
        }
        
        metrics = self.validator.validate_solution(timetable)
        
        self.assertTrue(metrics.is_valid)
        self.assertEqual(len(metrics.constraint_violations), 0)
        self.assertGreater(metrics.quality_score, 0)
        
        # Check level distribution
        self.assertEqual(metrics.level_distribution[1]['total_courses'], 2)
        self.assertEqual(metrics.level_distribution[2]['total_courses'], 1)
    
    def test_invalid_solution(self):
        # Create timetable with conflicts
        timetable = {
            1: [
                self._create_assigned_variable(
                    "CSC111", 1,
                    TimeSlot("Monday", time(9), time(10)),
                    "R101", "INS1"
                ),
                self._create_assigned_variable(
                    "CSC112", 1,
                    TimeSlot("Monday", time(9), time(10)),  # Same time!
                    "R101", "INS1"  # Same room and instructor!
                )
            ]
        }
        
        metrics = self.validator.validate_solution(timetable)
        
        self.assertFalse(metrics.is_valid)
        self.assertGreater(len(metrics.constraint_violations), 0)
    
    def test_resource_utilization(self):
        # Create timetable with known resource usage
        timetable = {
            1: [
                self._create_assigned_variable(
                    "CSC111", 1,
                    TimeSlot("Monday", time(9), time(10)),
                    "R101", "INS1"
                ),
                self._create_assigned_variable(
                    "CSC112", 1,
                    TimeSlot("Monday", time(10), time(11)),
                    "R101", "INS1"  # Same room and instructor
                )
            ]
        }
        
        metrics = self.validator.validate_solution(timetable)
        
        # Check utilization (2 slots used out of 2 total = 100%)
        self.assertEqual(metrics.resource_utilization['rooms'], 1.0)
        self.assertEqual(metrics.resource_utilization['instructors'], 1.0)
    
    def _create_assigned_variable(self, 
                                course_id: str,
                                level: int,
                                time_slot: TimeSlot,
                                room: str,
                                instructor: str) -> Variable:
        """Helper to create and assign variables"""
        var = Variable(course_id, level, self.requirements)
        var.assign(time_slot, room, instructor)
        return var