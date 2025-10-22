from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from ..csp.variable import Variable, TimeSlot, ResourceRequirements
from ..csp.domain import Domain
from ..csp.optimization import OptimizationMetrics

@dataclass
class SchedulingResult:
    """Result of scheduling attempt"""
    success: bool
    variables: Optional[List[Variable]] = None
    metrics: Optional[OptimizationMetrics] = None
    error: Optional[str] = None

class LevelScheduler:
    """Handles level-based course scheduling"""
    
    def __init__(self, domain: Domain):
        self.domain = domain
        self.scheduled_resources: Dict[str, Set[Tuple[str, TimeSlot]]] = {
            'rooms': set(),
            'instructors': set()
        }
    
    def schedule_level(self, 
                      level: int, 
                      variables: List[Variable],
                      max_attempts: int = 3) -> SchedulingResult:
        """Schedule all courses for a specific level"""
        try:
            # Sort variables by constraints (most constrained first)
            sorted_vars = self._sort_by_constraints(variables)
            
            # Try multiple scheduling attempts
            for attempt in range(max_attempts):
                # Reset resource tracking
                self._reset_resources()
                
                # Try to schedule each variable
                success = True
                for var in sorted_vars:
                    if not self._schedule_variable(var):
                        success = False
                        break
                
                if success:
                    return SchedulingResult(
                        success=True,
                        variables=sorted_vars
                    )
                
                # Reset assignments for next attempt
                for var in sorted_vars:
                    var.unassign()
            
            return SchedulingResult(
                success=False,
                error=f"Failed to schedule level {level} after {max_attempts} attempts"
            )
            
        except Exception as e:
            return SchedulingResult(
                success=False,
                error=f"Scheduling error: {str(e)}"
            )
    
    def _sort_by_constraints(self, variables: List[Variable]) -> List[Variable]:
        """Sort variables by number of constraints (descending)"""
        return sorted(
            variables,
            key=lambda v: (
                -len(v.requirements.room_type),  # More specific room type first
                -v.requirements.min_capacity,    # Larger capacity requirements first
                -len(v._possible_times)         # Fewer time slots first
            )
        )
    
    def _schedule_variable(self, variable: Variable) -> bool:
        """Attempt to schedule a single variable"""
        times, rooms, instructors = variable.get_domain()
        
        # Filter available resources
        available_times = times - self._get_level_conflicts(variable.level)
        available_rooms = self._filter_available_rooms(
            rooms, variable.requirements
        )
        available_instructors = self._filter_available_instructors(instructors)
        
        # Try each combination
        for time in available_times:
            for room in available_rooms:
                if self._is_resource_available('rooms', room, time):
                    for instructor in available_instructors:
                        if self._is_resource_available('instructors', instructor, time):
                            # Try assignment
                            variable.assign(time, room, instructor)
                            
                            # Update resource tracking
                            self._mark_resource_used('rooms', room, time)
                            self._mark_resource_used('instructors', instructor, time)
                            
                            return True
        
        return False
    
    def _reset_resources(self):
        """Reset resource tracking"""
        self.scheduled_resources: Dict[str, Set[Tuple[str, TimeSlot]]] =  {
            'rooms': set(),
            'instructors': set()
        }
    
    def _get_level_conflicts(self, level: int) -> Set[TimeSlot]:
        """Get time slots already used by level"""
        # This would typically check against existing schedules
        return set()
    
    def _filter_available_rooms(self, 
                              rooms: Set[str], 
                              requirements: 'ResourceRequirements') -> Set[str]:
        """Filter rooms based on requirements"""
        return {
            room for room in rooms
            if self.domain.rooms[room].room_type == requirements.room_type
            and self.domain.rooms[room].capacity >= requirements.min_capacity
        }
    
    def _filter_available_instructors(self, 
                                    instructors: Set[str]) -> Set[str]:
        """Filter instructors based on availability"""
        return {
            i for i in instructors
            if self.domain.instructors[i].max_hours_per_day > 0
        }
    
    def _is_resource_available(self, 
                             resource_type: str,
                             resource_id: str,
                             time_slot: TimeSlot) -> bool:
        """Check if a resource is available at given time"""
        return (resource_id, time_slot) not in self.scheduled_resources[resource_type]
    
    def _mark_resource_used(self,
                          resource_type: str,
                          resource_id: str,
                          time_slot: TimeSlot):
        """Mark a resource as used for a time slot"""
        self.scheduled_resources[resource_type].add((resource_id, time_slot))