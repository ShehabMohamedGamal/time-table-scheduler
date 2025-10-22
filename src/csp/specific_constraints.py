from typing import List, Set, Dict
from .constraints import Constraint, ConstraintViolation
from .variable import Variable, TimeSlot
from .domain import Domain

class ResourceConflictConstraint(Constraint):
    """Prevents double-booking of resources (rooms and instructors)"""
    
    def check(self, variables: List[Variable], domain: Domain) -> List[ConstraintViolation]:
        violations = []
        resource_usage: Dict[str, Dict[TimeSlot, Variable]] = {
            'rooms': {},
            'instructors': {}
        }
        
        for var in variables:
            if not var.is_assigned or var._assigned_time is None:
                continue
                
            # Check room conflicts
            if var._assigned_room:
                for slot, other_var in resource_usage['rooms'].items():
                    if slot.overlaps(var._assigned_time) and other_var._assigned_room == var._assigned_room:
                        violations.append(ConstraintViolation(
                            constraint_type="room_conflict",
                            description=f"Room {var._assigned_room} double-booked",
                            variables=[var, other_var],
                            severity=1.0
                        ))
                resource_usage['rooms'][var._assigned_time] = var
            
            # Check instructor conflicts
            if var._assigned_instructor:
                for slot, other_var in resource_usage['instructors'].items():
                    if slot.overlaps(var._assigned_time) and other_var._assigned_instructor == var._assigned_instructor:
                        violations.append(ConstraintViolation(
                            constraint_type="instructor_conflict",
                            description=f"Instructor {var._assigned_instructor} double-booked",
                            variables=[var, other_var],
                            severity=1.0
                        ))
                resource_usage['instructors'][var._assigned_time] = var
                
        return violations
    
    def propagate(self, variable: Variable, domain: Domain) -> bool:
        """Remove conflicting time slots from domain"""
        if not variable.is_assigned or variable._assigned_time is None:
            return True
            
        # Now we know _assigned_time is not None
        domain.update_availability(
            variable._assigned_time,
            variable._assigned_room,
            variable._assigned_instructor
        )
        return True

class TimeConflictConstraint(Constraint):
    """Ensures no time conflicts within same level"""
    
    def check(self, variables: List[Variable], domain: Domain) -> List[ConstraintViolation]:
        violations = []
        level_slots: Dict[int, Dict[TimeSlot, Variable]] = {}
        
        for var in variables:
            if not var.is_assigned or var._assigned_time is None:
                continue
                
            if var.level not in level_slots:
                level_slots[var.level] = {}
                
            for slot, other_var in level_slots[var.level].items():
                if slot.overlaps(var._assigned_time):
                    violations.append(ConstraintViolation(
                        constraint_type="time_conflict",
                        description=f"Time conflict in level {var.level}",
                        variables=[var, other_var],
                        severity=1.0
                    ))
            level_slots[var.level][var._assigned_time] = var
            
        return violations
    
    def propagate(self, variable: Variable, domain: Domain) -> bool:
        return True  # Time conflicts handled by resource conflict propagation

class LevelRequirementConstraint(Constraint):
    """Enforces level-specific scheduling requirements"""
    
    MAX_DAILY_HOURS = 6  # Maximum hours per day for each level
    
    def check(self, variables: List[Variable], domain: Domain) -> List[ConstraintViolation]:
        violations = []
        level_hours: Dict[int, Dict[str, float]] = {}  # level -> day -> hours
        
        for var in variables:
            if not var.is_assigned or var._assigned_time is None:  # Add None check
                continue
                
            if var.level not in level_hours:
                level_hours[var.level] = {}
                
            day = var._assigned_time.day
            if day not in level_hours[var.level]:
                level_hours[var.level][day] = 0
                
            # Calculate hours for this slot
            start = var._assigned_time.start_time
            end = var._assigned_time.end_time
            hours = (end.hour - start.hour) + (end.minute - start.minute) / 60
            
            level_hours[var.level][day] += hours
            
            if level_hours[var.level][day] > self.MAX_DAILY_HOURS:
                violations.append(ConstraintViolation(
                    constraint_type="max_hours_exceeded",
                    description=f"Level {var.level} exceeds {self.MAX_DAILY_HOURS} hours on {day}",
                    variables=[var],
                    severity=0.8  # Soft constraint
                ))
                
        return violations
    
    def propagate(self, variable: Variable, domain: Domain) -> bool:
        return True  # No specific propagation needed