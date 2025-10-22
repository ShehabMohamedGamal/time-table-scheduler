import unittest
from datetime import time
from src.csp.variable import Variable, TimeSlot, ResourceRequirements
from src.csp.domain import Domain
from src.csp.constraints import ConstraintManager
from src.csp.solver import Solver

class TestCSPEngine(unittest.TestCase):
    def setUp(self):
        """Set up test environment with sample data"""
        # Initialize domain
        self.domain = Domain(None)  # Mock DB connection
        
        # Add test time slots
        self.domain.time_slots = {
            TimeSlot("Monday", time(9), time(10)),
            TimeSlot("Monday", time(10), time(11)),
            TimeSlot("Tuesday", time(9), time(10))
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
        
        self.constraint_manager = ConstraintManager()
        self.solver = Solver(self.constraint_manager, self.domain)

class TestConstraints(TestCSPEngine):
    """Test constraint validation and propagation"""
    
    def test_resource_conflict_constraint(self):
        """Test resource conflict detection"""
        var1 = self._create_test_variable("CSC111", 1)
        var2 = self._create_test_variable("CSC112", 1)
        
        # Assign same room and time
        time_slot = TimeSlot("Monday", time(9), time(10))
        var1.assign(time_slot, "R101", "INS1")
        var2.assign(time_slot, "R101", "INS2")
        
        violations = self.constraint_manager.check_assignment([var1, var2])
        self.assertTrue(any(v.severity == 1.0 for v in violations))
    
    def test_level_constraint(self):
        """Test level-based scheduling constraints"""
        var1 = self._create_test_variable("CSC111", 1)
        var2 = self._create_test_variable("CSC112", 1)
        var3 = self._create_test_variable("CSC211", 2)
        
        # Same time slot for same level
        time_slot = TimeSlot("Monday", time(9), time(10))
        var1.assign(time_slot, "R101", "INS1")
        var2.assign(time_slot, "R102", "INS2")
        
        violations = self.constraint_manager.check_assignment([var1, var2])
        self.assertTrue(any(v.constraint_type == "level_time_conflict" 
                          for v in violations))
        
        # Same time slot different levels (should be allowed)
        var2.unassign()
        var3.assign(time_slot, "R102", "INS2")
        violations = self.constraint_manager.check_assignment([var1, var3])
        self.assertFalse(any(v.constraint_type == "level_time_conflict" 
                            for v in violations))

class TestDomain(TestCSPEngine):
    """Test domain management and filtering"""
    
    def test_domain_filtering(self):
        """Test domain reduction and restoration"""
        var = self._create_test_variable("CSC111", 1)
        initial_domain = var.get_domain()
        
        # Reduce domain
        time_slot = TimeSlot("Monday", time(9), time(10))
        var.reduce_domain(time_slots={time_slot})
        
        reduced_domain = var.get_domain()
        self.assertLess(len(reduced_domain[0]), len(initial_domain[0]))
        
        # Test domain restoration
        self.domain._restore_domains([var])
        restored_domain = var.get_domain()
        self.assertEqual(len(restored_domain[0]), len(initial_domain[0]))
    
    def test_resource_availability(self):
        """Test resource availability tracking"""
        var = self._create_test_variable("CSC111", 1)
        time_slot = TimeSlot("Monday", time(9), time(10))
        
        # Mark resource as used
        self.domain.update_availability(time_slot, "R101", "INS1")
        
        # Verify resource is unavailable
        times, rooms, instructors = var.get_domain()
        self.assertNotIn(time_slot, times)

class TestSolver(TestCSPEngine):
    """Test solver functionality"""
    
    def test_simple_solution(self):
        """Test solving simple scheduling problem"""
        variables = [
            self._create_test_variable("CSC111", 1),
            self._create_test_variable("CSC112", 1)
        ]
        
        solutions = self.solver.solve(variables)
        
        self.assertTrue(len(solutions) > 0)
        solution = solutions[0]
        
        # Verify solution validity
        self.assertTrue(all(v.is_assigned for v in solution))
        self.assertFalse(solution[0].conflicts_with(solution[1]))
    
    def test_forward_checking(self):
        """Test forward checking mechanism"""
        variables = [
            self._create_test_variable("CSC111", 1),
            self._create_test_variable("CSC112", 1),
            self._create_test_variable("CSC113", 1)
        ]
        
        # Assign first variable
        variables[0].assign(
            TimeSlot("Monday", time(9), time(10)),
            "R101",
            "INS1"
        )
        
        # Verify domain reduction in other variables
        success = self.solver._forward_check(variables[1:])
        self.assertTrue(success)
        
        # Verify domains were reduced
        times1, _, _ = variables[1].get_domain()
        self.assertNotIn(TimeSlot("Monday", time(9), time(10)), times1)
    
    def test_ac3_consistency(self):
        """Test AC-3 arc consistency"""
        variables = [
            self._create_test_variable("CSC111", 1),
            self._create_test_variable("CSC112", 1)
        ]
        
        # Apply AC-3
        success = self.solver.ac3(variables)
        self.assertTrue(success)
        
        # Verify domains are still valid
        for var in variables:
            times, rooms, instructors = var.get_domain()
            self.assertTrue(len(times) > 0)
            self.assertTrue(len(rooms) > 0)
            self.assertTrue(len(instructors) > 0)
    
    def _create_test_variable(self, course_id: str, level: int) -> Variable:
        """Helper method to create test variables"""
        requirements = ResourceRequirements("Lecture", 30)
        var = Variable(course_id, level, requirements)
        times, rooms, instructors = self.domain.get_available_values(requirements)
        var.set_domain(times, rooms, instructors)
        return var