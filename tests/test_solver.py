import unittest
from datetime import time
from src.csp.solver import Solver
from src.csp.constraints import ConstraintManager
from src.csp.variable import Variable, TimeSlot, ResourceRequirements
from src.csp.domain import Domain, RoomAvailability, InstructorAvailability

class TestSolver(unittest.TestCase):
    def setUp(self):
        self.constraint_manager = ConstraintManager()
        
        # Create test domain
        self.domain = Domain(None)  # Mock DB manager
        self.domain.time_slots = {
            TimeSlot("Monday", time(9), time(10)),
            TimeSlot("Monday", time(10), time(11)),
            TimeSlot("Monday", time(11), time(12))
        }
        self.domain.rooms = {
            "R101": RoomAvailability("R101", "Lecture", 30),
            "R102": RoomAvailability("R102", "Lecture", 30)
        }
        self.domain.instructors = {
            "INS1": InstructorAvailability("INS1"),
            "INS2": InstructorAvailability("INS2")
        }
        
        self.solver = Solver(self.constraint_manager, self.domain)
        
    def test_simple_solution(self):
        # Create two variables that need different time slots
        requirements = ResourceRequirements("Lecture", 30)
        var1 = Variable("CSC111", 1, requirements)
        var2 = Variable("CSC112", 1, requirements)
        
        # Set domains
        for var in [var1, var2]:
            times, rooms, instructors = self.domain.get_available_values(requirements)
            var.set_domain(times, rooms, instructors)
        
        solutions = self.solver.solve([var1, var2])
        
        self.assertEqual(len(solutions), 1)
        solution = solutions[0]
        
        # Check that solution is valid
        self.assertTrue(all(v.is_assigned for v in solution))
        self.assertFalse(solution[0].conflicts_with(solution[1]))
        
    def test_no_solution(self):
        # Create a scenario with no valid solution
        requirements = ResourceRequirements("Lab", 30)  # No Lab rooms in domain
        var = Variable("CSC111", 1, requirements)
        times, rooms, instructors = self.domain.get_available_values(requirements)
        var.set_domain(times, rooms, instructors)
        
        solutions = self.solver.solve([var])
        self.assertEqual(len(solutions), 0)
        
    def test_forward_checking(self):
        requirements = ResourceRequirements("Lecture", 30)
        variables = [
            Variable(f"CSC11{i}", 1, requirements)
            for i in range(3)
        ]
        
        # Set domains
        for var in variables:
            times, rooms, instructors = self.domain.get_available_values(requirements)
            var.set_domain(times, rooms, instructors)
        
        solutions = self.solver.solve(variables)
        
        self.assertTrue(len(solutions) > 0)
        self.assertTrue(self.solver.stats.backtracks > 0)
        
    def test_ac3(self):
        requirements = ResourceRequirements("Lecture", 30)
        var1 = Variable("CSC111", 1, requirements)
        var2 = Variable("CSC112", 1, requirements)
        
        # Set domains
        for var in [var1, var2]:
            times, rooms, instructors = self.domain.get_available_values(requirements)
            var.set_domain(times, rooms, instructors)
        
        # Apply AC-3
        success = self.solver.ac3([var1, var2])
        self.assertTrue(success)
        self.assertTrue(var1.domain_size() > 0)
        self.assertTrue(var2.domain_size() > 0)