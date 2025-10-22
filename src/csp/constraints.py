from abc import ABC, abstractmethod
from typing import List, Set, Dict, Optional
from dataclasses import dataclass
from .variable import Variable, TimeSlot
from .domain import Domain

@dataclass
class ConstraintViolation:
    """Represents a constraint violation"""
    constraint_type: str
    description: str
    variables: List[Variable]
    severity: float  # 0-1, where 1 is a hard constraint violation

class Constraint(ABC):
    """Base class for all constraints"""
    
    @abstractmethod
    def check(self, variables: List[Variable], domain: Domain) -> List[ConstraintViolation]:
        """Check if constraint is satisfied"""
        pass
    
    @abstractmethod
    def propagate(self, variable: Variable, domain: Domain) -> bool:
        """Propagate constraint effects to domain"""
        pass

class NoOverlapConstraint(Constraint):
    """Ensures no resource conflicts"""
    
    def check(self, variables: List[Variable], domain: Domain) -> List[ConstraintViolation]:
        violations = []
        for i, var1 in enumerate(variables):
            for var2 in variables[i+1:]:
                if var1.conflicts_with(var2):
                    violations.append(ConstraintViolation(
                        constraint_type="resource_overlap",
                        description=f"Resource conflict between {var1.course_id} and {var2.course_id}",
                        variables=[var1, var2],
                        severity=1.0
                    ))
        return violations
    
    def propagate(self, variable: Variable, domain: Domain) -> bool:
        """Remove conflicting time slots from domain"""
        if not variable.is_assigned or variable._assigned_time is None:
            return True
            
        domain.update_availability(
            variable._assigned_time,  # Now we know it's not None
            variable._assigned_room,
            variable._assigned_instructor
        )
        return True

class RoomTypeConstraint(Constraint):
    """Ensures room type matches course requirements"""
    
    def check(self, variables: List[Variable], domain: Domain) -> List[ConstraintViolation]:
        violations = []
        for var in variables:
            if var.is_assigned and var._assigned_room:
                room = domain.rooms.get(var._assigned_room)
                if room and room.room_type != var.requirements.room_type:
                    violations.append(ConstraintViolation(
                        constraint_type="room_type_mismatch",
                        description=f"Room type mismatch for {var.course_id}",
                        variables=[var],
                        severity=1.0
                    ))
        return violations
    
    def propagate(self, variable: Variable, domain: Domain) -> bool:
        """Remove incompatible rooms from domain"""
        times, rooms, instructors = variable.get_domain()
        compatible_rooms = {
            room_id for room_id in rooms
            if domain.rooms[room_id].room_type == variable.requirements.room_type
        }
        variable.reduce_domain(rooms=rooms - compatible_rooms)
        return len(compatible_rooms) > 0

class LevelConstraint(Constraint):
    """Ensures level-appropriate scheduling"""
    
    def check(self, variables: List[Variable], domain: Domain) -> List[ConstraintViolation]:
        violations = []
        level_times: Dict[int, Set[TimeSlot]] = {}
        
        for var in variables:
            if var.is_assigned and var._assigned_time:  # Add None check
                if var.level not in level_times:
                    level_times[var.level] = set()
                
                # Check for overlapping times within same level
                if any(var._assigned_time.overlaps(t) for t in level_times[var.level]):
                    violations.append(ConstraintViolation(
                        constraint_type="level_time_conflict",
                        description=f"Time conflict in level {var.level}",
                        variables=[var],
                        severity=1.0
                    ))
                level_times[var.level].add(var._assigned_time)
        
        return violations
    
    def propagate(self, variable: Variable, domain: Domain) -> bool:
        """No specific propagation needed for level constraint"""
        return True

class ConstraintManager:
    """Manages and evaluates scheduling constraints"""
    
    def __init__(self, domain: Domain):
        self.domain = domain
        self.hard_constraints: List[Constraint] = [
            NoOverlapConstraint(),
            RoomTypeConstraint(),
            LevelConstraint()
        ]
        self.soft_constraints: List[Constraint] = []
        
    def check_assignment(self, variables: List[Variable]) -> List[ConstraintViolation]:
        """Check all constraints for given assignment"""
        violations = []
        
        # Check hard constraints
        for constraint in self.hard_constraints:
            violations.extend(constraint.check(variables, self.domain))
        
        # Check soft constraints
        for constraint in self.soft_constraints:
            violations.extend(constraint.check(variables, self.domain))
            
        return violations
    
    def propagate_constraints(self, 
                            variable: Variable, 
                            domain: Domain) -> bool:
        """Propagate all constraints for given variable"""
        for constraint in self.hard_constraints:
            if not constraint.propagate(variable, domain):
                return False
        return True
    
    def get_violation_score(self, violations: List[ConstraintViolation]) -> float:
        """Calculate overall violation score"""
        if any(v.severity == 1.0 for v in violations):
            return float('inf')
        return sum(v.severity for v in violations)