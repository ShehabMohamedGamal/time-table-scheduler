import unittest
from datetime import time
from src.csp.specific_constraints import (
    ResourceConflictConstraint,
    TimeConflictConstraint,
    LevelRequirementConstraint
)
from src.csp.variable import Variable, TimeSlot, ResourceRequirements
from src.csp.domain import Domain

class TestSpecificConstraints(unittest.TestCase):
    def setUp(self):
        self.requirements = ResourceRequirements(
            room_type="Lecture",
            min_capacity=30
        )
        
        # Create test variables
        self.var1 = Variable("CSC111", 1, self.requirements)
        self.var2 = Variable("CSC112", 1, self.requirements)
        
        # Create test time slots
        self.morning_slot = TimeSlot("Monday", time(9), time(10))
        self.overlapping_slot = TimeSlot("Monday", time(9, 30), time(10, 30))
        self.afternoon_slot = TimeSlot("Monday", time(14), time(15))
        
    def test_resource_conflict_constraint(self):
        constraint = ResourceConflictConstraint()
        
        # Test room conflict
        self.var1.assign(self.morning_slot, "R101", "INS1")
        self.var2.assign(self.overlapping_slot, "R101", "INS2")
        
        violations = constraint.check([self.var1, self.var2])
        self.assertTrue(any(v.constraint_type == "room_conflict" 
                          for v in violations))
        
        # Test instructor conflict
        self.var2.assign(self.overlapping_slot, "R102", "INS1")
        violations = constraint.check([self.var1, self.var2])
        self.assertTrue(any(v.constraint_type == "instructor_conflict" 
                          for v in violations))
        
    def test_time_conflict_constraint(self):
        constraint = TimeConflictConstraint()
        
        # Test same level time conflict
        self.var1.assign(self.morning_slot, "R101", "INS1")
        self.var2.assign(self.overlapping_slot, "R102", "INS2")
        
        violations = constraint.check([self.var1, self.var2])
        self.assertTrue(any(v.constraint_type == "time_conflict" 
                          for v in violations))
        
        # Test different level (should be allowed)
        self.var2 = Variable("CSC112", 2, self.requirements)
        self.var2.assign(self.overlapping_slot, "R102", "INS2")
        
        violations = constraint.check([self.var1, self.var2])
        self.assertFalse(any(v.constraint_type == "time_conflict" 
                           for v in violations))
        
    def test_level_requirement_constraint(self):
        constraint = LevelRequirementConstraint()
        
        # Create multiple slots for same day
        slots = [
            TimeSlot("Monday", time(9), time(11)),   # 2 hours
            TimeSlot("Monday", time(11), time(13)),  # 2 hours
            TimeSlot("Monday", time(14), time(17))   # 3 hours
        ]
        
        variables = []
        for i, slot in enumerate(slots):
            var = Variable(f"CSC11{i}", 1, self.requirements)
            var.assign(slot, f"R10{i}", f"INS{i}")
            variables.append(var)
        
        violations = constraint.check(variables)
        self.assertTrue(any(v.constraint_type == "max_hours_exceeded" 
                          for v in violations))
