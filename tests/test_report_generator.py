import unittest
import tempfile
import os
import json
from datetime import time
from src.validator.report_generator import ReportGenerator
from src.validator.solution_validator import ValidationMetrics
from src.csp.variable import Variable, TimeSlot, ResourceRequirements

class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.report_generator = ReportGenerator(self.temp_dir)
        
        # Create test data
        self.metrics = ValidationMetrics(
            is_valid=True,
            constraint_violations=[],
            quality_score=0.85,
            resource_utilization={'rooms': 0.75, 'instructors': 0.8},
            level_distribution={
                1: {
                    'total_courses': 3,
                    'days_used': 2,
                    'max_per_day': 2,
                    'morning_slots': 2,
                    'afternoon_slots': 1
                }
            }
        )
        
        self.variables = [
            self._create_test_variable("CSC111", 1, "Monday", time(9)),
            self._create_test_variable("CSC112", 1, "Monday", time(11)),
            self._create_test_variable("CSC113", 1, "Tuesday", time(14))
        ]
        
        self.solver_stats = {
            'total_time': 1.5,
            'attempts': 2,
            'total_variables': 3
        }
    
    def test_report_generation(self):
        report = self.report_generator.generate_report(
            self.metrics,
            self.variables,
            self.solver_stats
        )
        
        self.assertIsNotNone(report)
        self.assertTrue(report.validation_metrics.is_valid)
        self.assertEqual(len(report.detailed_violations), 0)
        self.assertIn('solver_performance', report.performance_summary)
        self.assertIn('overall_score', report.quality_analysis)
    
    def test_json_report_saving(self):
        report = self.report_generator.generate_report(
            self.metrics,
            self.variables,
            self.solver_stats
        )
        
        self.report_generator.save_report(report, 'json')
        
        # Check if file exists
        files = os.listdir(self.temp_dir)
        self.assertTrue(any(f.endswith('.json') for f in files))
        
        # Verify JSON content
        json_file = next(f for f in files if f.endswith('.json'))
        with open(os.path.join(self.temp_dir, json_file)) as f:
            data = json.load(f)
            self.assertIn('timestamp', data)
            self.assertIn('is_valid', data)
            self.assertIn('performance', data)
            self.assertIn('quality', data)
    
    def test_text_report_saving(self):
        report = self.report_generator.generate_report(
            self.metrics,
            self.variables,
            self.solver_stats
        )
        
        self.report_generator.save_report(report, 'txt')
        
        # Check if file exists
        files = os.listdir(self.temp_dir)
        self.assertTrue(any(f.endswith('.txt') for f in files))
    
    def _create_test_variable(self, 
                            course_id: str, 
                            level: int,
                            day: str,
                            start: time) -> Variable:
        """Helper to create test variables"""
        var = Variable(
            course_id,
            level,
            ResourceRequirements("Lecture", 30)
        )
        var.assign(
            TimeSlot(day, start, time(start.hour + 1)),
            f"R{level}01",
            f"INS{level}"
        )
        return var
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)