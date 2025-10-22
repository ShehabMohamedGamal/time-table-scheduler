from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from datetime import datetime
from ..csp.variable import Variable
from .solution_validator import ValidationMetrics

@dataclass
class ValidationReport:
    """Detailed validation report"""
    timestamp: str
    validation_metrics: ValidationMetrics
    detailed_violations: List[Dict]
    performance_summary: Dict
    quality_analysis: Dict

class ReportGenerator:
    """Generates detailed reports for solution validation"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist"""
        import os
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_report(self,
                       metrics: ValidationMetrics,
                       variables: List[Variable],
                       solver_stats: Optional[Dict] = None) -> ValidationReport:
        """Generate comprehensive validation report"""
        timestamp = datetime.now().isoformat()
        
        # Analyze constraint violations
        detailed_violations = self._analyze_violations(
            metrics.constraint_violations
        )
        
        # Generate performance summary
        performance_summary = self._generate_performance_summary(
            metrics, solver_stats
        )
        
        # Generate quality analysis
        quality_analysis = self._analyze_solution_quality(
            metrics, variables
        )
        
        return ValidationReport(
            timestamp=timestamp,
            validation_metrics=metrics,
            detailed_violations=detailed_violations,
            performance_summary=performance_summary,
            quality_analysis=quality_analysis
        )
    
    def save_report(self, report: ValidationReport, format: str = 'json'):
        """Save report to file"""
        filename = f"validation_report_{report.timestamp}.{format}"
        filepath = f"{self.output_dir}/{filename}"
        
        if format == 'json':
            self._save_json_report(report, filepath)
        else:
            self._save_text_report(report, filepath)
    
    def _analyze_violations(self, 
                          violations: List[str]
                          ) -> List[Dict]:
        """Group and analyze constraint violations"""
        violation_types = {}
        
        for violation in violations:
            # Extract violation type and details
            if "conflict" in violation.lower():
                type_ = "Resource Conflict"
            elif "requirement" in violation.lower():
                type_ = "Requirement Violation"
            else:
                type_ = "Other Violation"
                
            if type_ not in violation_types:
                violation_types[type_] = []
            violation_types[type_].append(violation)
        
        return [
            {
                "type": type_,
                "count": len(violations),
                "details": violations
            }
            for type_, violations in violation_types.items()
        ]
    
    def _generate_performance_summary(self,
                                   metrics: ValidationMetrics,
                                   solver_stats: Optional[Dict]
                                   ) -> Dict:
        """Generate performance metrics summary"""
        summary = {
            "resource_utilization": metrics.resource_utilization,
            "level_distribution": metrics.level_distribution
        }
        
        if solver_stats:
            summary.update({
                "solver_performance": {
                    "total_time": solver_stats.get('total_time', 0),
                    "attempts": solver_stats.get('attempts', 0),
                    "variables": solver_stats.get('total_variables', 0)
                }
            })
        
        return summary
    
    def _analyze_solution_quality(self,
                                metrics: ValidationMetrics,
                                variables: List[Variable]
                                ) -> Dict:
        """Analyze solution quality metrics"""
        return {
            "overall_score": metrics.quality_score,
            "distribution_metrics": {
                "rooms_utilized": len({v._assigned_room for v in variables}),
                "instructors_utilized": len({v._assigned_instructor for v in variables}),
                "time_slots_used": len({v._assigned_time for v in variables})
            },
            "level_metrics": {
                level: {
                    "courses": stats['total_courses'],
                    "distribution": f"{stats['morning_slots']}/{stats['afternoon_slots']}",
                    "days_spread": stats['days_used']
                }
                for level, stats in metrics.level_distribution.items()
            }
        }
    
    def _save_json_report(self, report: ValidationReport, filepath: str):
        """Save report in JSON format"""
        with open(filepath, 'w') as f:
            json.dump({
                "timestamp": report.timestamp,
                "is_valid": report.validation_metrics.is_valid,
                "violations": report.detailed_violations,
                "performance": report.performance_summary,
                "quality": report.quality_analysis
            }, f, indent=2)
    
    def _save_text_report(self, report: ValidationReport, filepath: str):
        """Save report in human-readable text format"""
        with open(filepath, 'w') as f:
            f.write(f"Validation Report - {report.timestamp}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("Validation Status: ")
            f.write("VALID" if report.validation_metrics.is_valid else "INVALID")
            f.write("\n\n")
            
            if report.detailed_violations:
                f.write("Constraint Violations:\n")
                f.write("-" * 20 + "\n")
                for v in report.detailed_violations:
                    f.write(f"\n{v['type']} ({v['count']}):\n")
                    for detail in v['details']:
                        f.write(f"- {detail}\n")
                f.write("\n")
            
            f.write("Performance Summary:\n")
            f.write("-" * 20 + "\n")
            for metric, value in report.performance_summary.items():
                f.write(f"{metric}: {value}\n")
            f.write("\n")
            
            f.write("Quality Analysis:\n")
            f.write("-" * 20 + "\n")
            f.write(f"Overall Score: {report.quality_analysis['overall_score']:.2f}\n")
            for metric, value in report.quality_analysis['distribution_metrics'].items():
                f.write(f"{metric}: {value}\n")