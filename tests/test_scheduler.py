import unittest
from datetime import time
from src.generator.scheduler import LevelScheduler
from src.csp.variable import Variable, TimeSlot, ResourceRequirements
from src.csp.domain import Domain, RoomAvailability, InstructorAvailability

class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.domain = Domain(None)  # Mock DB manager
        
        # Add test time slots
        self.domain.time_slots = {
            TimeSlot("Monday", time(9), time(10)),
            TimeSlot("Monday", time(10), time(11)),
            TimeSlot("Monday", time(11), time(12))
        }
        
        # Add test rooms
        self.domain.rooms = {
            "R101": RoomAvailability("R101", "Lecture", 30),
            "R102": RoomAvailability("R102", "Lab", 25)
        }
        
        # Add test instructors
        self.domain.instructors = {
            "INS1": InstructorAvailability("INS1"),
            "INS2": InstructorAvailability("INS2")
        }
        
        self.scheduler = LevelScheduler(self.domain)
    
    def test_level_scheduling(self):
        # Create test variables
        requirements = ResourceRequirements("Lecture", 30)
        variables = [
            Variable("CSC111", 1, requirements),
            Variable("CSC112", 1, requirements)
        ]
        
        # Set domains
        for var in variables:
            times, rooms, instructors = self.domain.get_available_values(
                requirements
            )
            var.set_domain(times, rooms, instructors)
        
        # Schedule level
        result = self.scheduler.schedule_level(1, variables)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.variables)
        self.assertEqual(len(result.variables), 2)
        
        # Check for conflicts
        var1, var2 = result.variables
        self.assertTrue(var1.is_assigned and var2.is_assigned)
        self.assertFalse(var1.conflicts_with(var2))
    
    def test_resource_constraints(self):
        # Create variables that compete for same room
        requirements = ResourceRequirements("Lecture", 30)
        variables = [
            Variable("CSC111", 1, requirements),
            Variable("CSC112", 1, requirements),
            Variable("CSC113", 1, requirements)
        ]
        
        # Limit available rooms to create constraint
        self.domain.rooms = {
            "R101": RoomAvailability("R101", "Lecture", 30)
        }
        
        # Set domains
        for var in variables:
            times, rooms, instructors = self.domain.get_available_values(
                requirements
            )
            var.set_domain(times, rooms, instructors)
        
        # Schedule level
        result = self.scheduler.schedule_level(1, variables)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.variables)
        
        # Check that no room is double-booked
        scheduled_slots = set()
        for var in result.variables:
            self.assertNotIn(
                (var._assigned_room, var._assigned_time),
                scheduled_slots
            )
            scheduled_slots.add((var._assigned_room, var._assigned_time))