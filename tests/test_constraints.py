import unittest
from datetime import time
from src.csp.constraints import (
    ConstraintManager,
    ConstraintViolation,
    NoOverlapConstraint,
    RoomTypeConstraint
)
from src.csp.variable import Variable, TimeSlot, ResourceRequirements
from src.csp.domain import Domain, RoomAvailability

class TestConstraints(unittest.TestCase):
    def setUp(self):
        self.constraint_manager = ConstraintManager()
        
        # Create test variables
        self.requirements = ResourceRequirements(
            room_type="Lecture",
            min_capacity=30
        )
        
        self.var1 = Variable("CSC111", 1, self.requirements)
        self.var2 = Variable("CSC112", 1, self.requirements)
        
        # Create test time slots
        self.time1 = TimeSlot("Monday", time(9), time(10))
        self.time2 = TimeSlot("Monday", time(9, 30), time(10, 30))
        self.time3 = TimeSlot("Monday", time(10), time(11))
        
    def test_no_overlap_constraint(self):
        # Assign overlapping time slots
        self.var1.assign(self.time1, "R101", "INS1")
        self.var2.assign(self.time2, "R101", "INS2")
        
        violations = self.constraint_manager.check_assignment([self.var1, self.var2])
        self.assertTrue(any(v.constraint_type == "resource_overlap" 
                          for v in violations))
        
        # Assign non-overlapping time slots
        self.var2.assign(self.time3, "R101", "INS2")
        violations = self.constraint_manager.check_assignment([self.var1, self.var2])
        self.assertFalse(any(v.constraint_type == "resource_overlap" 
                           for v in violations))
        
    def test_room_type_constraint(self):
        # Create domain with test rooms
        domain = Domain(None)  # Mock DB manager
        domain.rooms = {
            "R101": RoomAvailability("R101", "Lecture", 30),
            "R102": RoomAvailability("R102", "Lab", 30)
        }
        
        # Assign incompatible room
        self.var1.assign(self.time1, "R102", "INS1")
        violations = RoomTypeConstraint().check([self.var1])
        self.assertTrue(any(v.constraint_type == "room_type_mismatch" 
                          for v in violations))
        
        # Assign compatible room
        self.var1.assign(self.time1, "R101", "INS1")
        violations = RoomTypeConstraint().check([self.var1])
        self.assertFalse(any(v.constraint_type == "room_type_mismatch" 
                           for v in violations))

    def test_constraint_propagation(self):
        domain = Domain(None)  # Mock DB manager
        domain.rooms = {
            "R101": RoomAvailability("R101", "Lecture", 30)
        }
        domain.time_slots = {self.time1, self.time2, self.time3}
        
        self.var1.assign(self.time1, "R101", "INS1")
        success = self.constraint_manager.propagate_constraints(self.var1, domain)
        
        self.assertTrue(success)
        self.assertNotIn(self.time1, domain.rooms["R101"].available_times)