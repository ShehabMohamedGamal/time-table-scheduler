from dataclasses import dataclass
from typing import List, Dict, Optional
from .variable import Variable, TimeSlot

@dataclass
class OptimizationMetrics:
    """Metrics for solution quality"""
    gaps_score: float  # Lower is better
    preference_score: float  # Higher is better
    distribution_score: float  # Higher is better
    total_score: float

class SolutionOptimizer:
    """Handles solution scoring and optimization"""
    
    def __init__(self, max_runtime: float = 300):
        self.max_runtime = max_runtime
        self.best_score: float = float('-inf')
        self.improvement_threshold = 0.1
    
    def score_solution(self, variables: List[Variable]) -> OptimizationMetrics:
        """Calculate quality metrics for a solution"""
        # Calculate gaps between classes
        gaps_score = self._calculate_gaps_score(variables)
        
        # Calculate instructor preference satisfaction
        preference_score = self._calculate_preference_score(variables)
        
        # Calculate time slot distribution
        distribution_score = self._calculate_distribution_score(variables)
        
        # Combine scores with weights
        total_score = (
            -0.4 * gaps_score +  # Minimize gaps
            0.4 * preference_score +  # Maximize preference satisfaction
            0.2 * distribution_score  # Maximize distribution
        )
        
        return OptimizationMetrics(
            gaps_score=gaps_score,
            preference_score=preference_score,
            distribution_score=distribution_score,
            total_score=total_score
        )
    
    def _calculate_gaps_score(self, variables: List[Variable]) -> float:
        """Calculate score based on gaps between classes"""
        gaps = 0.0
        level_slots: Dict[int, List[TimeSlot]] = {}
        
        # Group time slots by level
        for var in variables:
            if not var.is_assigned or var._assigned_time is None:
                continue
            if var.level not in level_slots:
                level_slots[var.level] = []
            level_slots[var.level].append(var._assigned_time)  # Now we know it's not None
        
        # Calculate gaps for each level
        for level_times in level_slots.values():
            sorted_times = sorted(level_times, 
                               key=lambda x: (x.day, x.start_time))
            
            for i in range(len(sorted_times) - 1):
                current = sorted_times[i]
                next_slot = sorted_times[i + 1]
                
                if current.day == next_slot.day:
                    # Calculate gap in minutes
                    gap = (next_slot.start_time.hour * 60 + next_slot.start_time.minute) - \
                          (current.end_time.hour * 60 + current.end_time.minute)
                    if gap > 0:
                        gaps += gap / 60  # Convert to hours
        
        return gaps
    
    def _calculate_preference_score(self, variables: List[Variable]) -> float:
        """Calculate score based on instructor preferences"""
        satisfied_preferences = 0
        total_preferences = 0
        
        for var in variables:
            if not var.is_assigned or var._assigned_time is None:
                continue
            # This would typically check against instructor preferences in the domain
            # Simplified version just checks for reasonable hours
            if (9 <= var._assigned_time.start_time.hour <= 16):
                satisfied_preferences += 1
            total_preferences += 1
        
        return satisfied_preferences / total_preferences if total_preferences > 0 else 0
    
    def _calculate_distribution_score(self, variables: List[Variable]) -> float:
        """Calculate score based on time slot distribution"""
        day_counts: Dict[str, int] = {}
        
        for var in variables:
            if not var.is_assigned or var._assigned_time is None:
                continue
            day = var._assigned_time.day
            day_counts[day] = day_counts.get(day, 0) + 1
        
        if not day_counts:
            return 0
        
        # Calculate standard deviation of counts
        mean = sum(day_counts.values()) / len(day_counts)
        variance = sum((c - mean) ** 2 for c in day_counts.values()) / len(day_counts)
        
        # Convert to score (0-1), where lower variance is better
        return 1 / (1 + variance)