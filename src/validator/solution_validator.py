from dataclasses import dataclass
from typing import Dict, List, Set
from ..csp.variable import Variable, TimeSlot
from ..csp.constraints import ConstraintManager
from ..csp.optimization import OptimizationMetrics, SolutionOptimizer

@dataclass
class ValidationMetrics:
    """Detailed validation metrics for a solution"""
    is_valid: bool
    constraint_violations: List[str]
    quality_score: float
    resource_utilization: Dict[str, float]
    level_distribution: Dict[int, Dict[str, int]]

class SolutionValidator:
    """Validates and analyzes timetable solutions"""
    
    def __init__(self, constraint_manager: ConstraintManager):
        self.constraint_manager = constraint_manager
        self.optimizer = SolutionOptimizer()
    
    def validate_solution(self, 
                         timetable: Dict[int, List[Variable]]
                         ) -> ValidationMetrics:
        """Validate complete timetable solution"""
        # Collect all variables
        all_variables = [
            var for level_vars in timetable.values()
            for var in level_vars
        ]
        
        # Check constraint violations
        violations = self.constraint_manager.check_assignment(all_variables)
        violation_msgs = [v.description for v in violations]
        
        # Get solution quality metrics
        quality_metrics = self.optimizer.score_solution(all_variables)
        
        # Calculate resource utilization
        resource_usage = self._calculate_resource_usage(all_variables)
        
        # Analyze level distribution
        level_dist = self._analyze_level_distribution(timetable)
        
        return ValidationMetrics(
            is_valid=len(violations) == 0,
            constraint_violations=violation_msgs,
            quality_score=quality_metrics.total_score,
            resource_utilization=resource_usage,
            level_distribution=level_dist
        )
    
    def _calculate_resource_usage(self, 
                                variables: List[Variable]
                                ) -> Dict[str, float]:
        """Calculate resource utilization percentages"""
        total_slots = len({var._assigned_time for var in variables})
        
        # Room usage
        room_usage: Dict[str, Set[TimeSlot]] = {}
        for var in variables:
            if var._assigned_room not in room_usage:
                room_usage[var._assigned_room] = set()
            room_usage[var._assigned_room].add(var._assigned_time)
        
        # Instructor usage
        instructor_usage: Dict[str, Set[TimeSlot]] = {}
        for var in variables:
            if var._assigned_instructor not in instructor_usage:
                instructor_usage[var._assigned_instructor] = set()
            instructor_usage[var._assigned_instructor].add(var._assigned_time)
        
        # Calculate percentages
        return {
            'rooms': sum(len(slots) for slots in room_usage.values()) / 
                    (len(room_usage) * total_slots) if room_usage else 0,
            'instructors': sum(len(slots) for slots in instructor_usage.values()) / 
                         (len(instructor_usage) * total_slots) if instructor_usage else 0
        }
    
    def _analyze_level_distribution(self, 
                                  timetable: Dict[int, List[Variable]]
                                  ) -> Dict[int, Dict[str, int]]:
        """Analyze course distribution across days for each level"""
        distribution = {}
        
        for level, variables in timetable.items():
            day_counts = {}
            time_ranges = {'morning': 0, 'afternoon': 0}
            
            for var in variables:
                # Count by day
                day = var._assigned_time.day
                day_counts[day] = day_counts.get(day, 0) + 1
                
                # Count by time range
                hour = var._assigned_time.start_time.hour
                if 8 <= hour < 12:
                    time_ranges['morning'] += 1
                else:
                    time_ranges['afternoon'] += 1
            
            distribution[level] = {
                'total_courses': len(variables),
                'days_used': len(day_counts),
                'max_per_day': max(day_counts.values()) if day_counts else 0,
                'morning_slots': time_ranges['morning'],
                'afternoon_slots': time_ranges['afternoon']
            }
        
        return distribution