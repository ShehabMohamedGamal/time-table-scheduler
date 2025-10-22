import unittest
from datetime import time
from src.csp.variable import Variable, TimeSlot, ResourceRequirements

class TestVariable(unittest.TestCase):
    def setUp(self):
        self.requirements = ResourceRequirements(
            room_type="Lecture",
            min_capacity=30
        )
        self.variable = Variable(
            course_id="CSC111",
            level=1,
            requirements=self.requirements
        )
        
        # Sample domain values
        self.time_slots = {
            TimeSlot("Monday", time(9), time(10)),
            TimeSlot("Monday", time(10), time(11))
        }
        self.rooms = {"R101", "R102"}
        self.instructors = {"INS1", "INS2"}
        
    def test_assignment(self):
        time_slot = TimeSlot("Monday", time(9), time(10))
        self.variable.assign(time_slot, "R101", "INS1")
        
        self.assertTrue(self.variable.is_assigned)
        
        self.variable.unassign()
        self.assertFalse(self.variable.is_assigned)
        
    def test_domain_operations(self):
        self.variable.set_domain(self.time_slots, self.rooms, self.instructors)
        
        times, rooms, instructors = self.variable.get_domain()
        self.assertEqual(len(times), 2)
        self.assertEqual(len(rooms), 2)
        self.assertEqual(len(instructors), 2)
        
        # Test domain reduction
        remove_time = {TimeSlot("Monday", time(9), time(10))}
        self.variable.reduce_domain(time_slots=remove_time)
        
        times, _, _ = self.variable.get_domain()
        self.assertEqual(len(times), 1)
        
    def test_conflicts(self):
        var1 = Variable("CSC111", 1, self.requirements)
        var2 = Variable("CSC112", 1, self.requirements)
        
        # Same time slot and room
        time_slot = TimeSlot("Monday", time(9), time(10))
        var1.assign(time_slot, "R101", "INS1")
        var2.assign(time_slot, "R101", "INS2")
        
        self.assertTrue(var1.conflicts_with(var2))
        
        # Different time slots
        var2.assign(
            TimeSlot("Monday", time(10), time(11)),
            "R101",
            "INS2"
        )
        self.assertFalse(var1.conflicts_with(var2))
        
    def test_time_slot_overlap(self):
        ts1 = TimeSlot("Monday", time(9), time(11))
        ts2 = TimeSlot("Monday", time(10), time(12))
        ts3 = TimeSlot("Tuesday", time(9), time(11))
        
        self.assertTrue(ts1.overlaps(ts2))
        self.assertFalse(ts1.overlaps(ts3))
