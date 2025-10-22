import unittest
from datetime import time
from src.csp.optimization import SolutionOptimizer
from src.csp.variable import Variable, TimeSlot, ResourceRequirements

class TestOptimization(unittest.TestCase):
    def setUp(self):
        self.optimizer = SolutionOptimizer()
        self.requirements = ResourceRequirements(
            room_type="Lecture",
            min_capacity=30
        )
    
    def test_gaps_score(self):
        # Create variables with gaps
        var1 = Variable("CSC111", 1, self.requirements)
        var2 = Variable("CSC112", 1, self.requirements)
        
        # No gap
        var1.assign(
            TimeSlot("Monday", time(9), time(10)),
            "R101",
            "INS1"
        )
        var2.assign(
            TimeSlot("Monday", time(10), time(11)),
            "R102",
            "INS2"
        )
        
        metrics = self.optimizer.score_solution([var1, var2])
        self.assertEqual(metrics.gaps_score, 0)
        
        # 1-hour gap
        var2.assign(
            TimeSlot("Monday", time(11), time(12)),
            "R102",
            "INS2"
        )
        
        metrics = self.optimizer.score_solution([var1, var2])
        self.assertEqual(metrics.gaps_score, 1)
    
    def test_distribution_score(self):
        var1 = Variable("CSC111", 1, self.requirements)
        var2 = Variable("CSC112", 1, self.requirements)
        var3 = Variable("CSC113", 1, self.requirements)
        
        # Even distribution
        var1.assign(
            TimeSlot("Monday", time(9), time(10)),
            "R101",
            "INS1"
        )
        var2.assign(
            TimeSlot("Tuesday", time(9), time(10)),
            "R101",
            "INS1"
        )
        var3.assign(
            TimeSlot("Wednesday", time(9), time(10)),
            "R101",
            "INS1"
        )
        
        metrics = self.optimizer.score_solution([var1, var2, var3])
        self.assertGreater(metrics.distribution_score, 0.8)