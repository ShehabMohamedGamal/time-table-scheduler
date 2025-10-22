from dataclasses import dataclass
from typing import Optional, Set
from datetime import time

@dataclass
class TimeSlot:
    """Represents a time period in the schedule"""
    day: str
    start_time: time
    end_time: time
    
    def overlaps(self, other: 'TimeSlot') -> bool:
        """Check if this time slot overlaps with another"""
        return (self.day == other.day and
                self.start_time < other.end_time and
                other.start_time < self.end_time)

@dataclass
class ResourceRequirements:
    """Defines required resources for a course"""
    room_type: str
    min_capacity: int
    requires_lab: bool = False
    requires_projector: bool = False

class Variable:
    """Represents a schedulable unit in the timetable CSP"""
    
    def __init__(self, 
                 course_id: str,
                 level: int,
                 requirements: ResourceRequirements):
        self.course_id = course_id
        self.level = level
        self.requirements = requirements
        self._assigned_time: Optional[TimeSlot] = None
        self._assigned_room: Optional[str] = None
        self._assigned_instructor: Optional[str] = None
        self._possible_times: Set[TimeSlot] = set()
        self._possible_rooms: Set[str] = set()
        self._possible_instructors: Set[str] = set()
    
    @property
    def is_assigned(self) -> bool:
        """Check if variable has complete assignment"""
        return all([
            self._assigned_time,
            self._assigned_room,
            self._assigned_instructor
        ])
    
    def assign(self,
               time_slot: TimeSlot,
               room_id: str,
               instructor_id: str) -> None:
        """Assign values to this variable"""
        self._assigned_time = time_slot
        self._assigned_room = room_id
        self._assigned_instructor = instructor_id
    
    def unassign(self) -> None:
        """Clear current assignment"""
        self._assigned_time = None
        self._assigned_room = None
        self._assigned_instructor = None
    
    def set_domain(self,
                  time_slots: Set[TimeSlot],
                  rooms: Set[str],
                  instructors: Set[str]) -> None:
        """Set possible values for this variable"""
        self._possible_times = time_slots
        self._possible_rooms = rooms
        self._possible_instructors = instructors
    
    def get_domain(self) -> tuple[Set[TimeSlot], Set[str], Set[str]]:
        """Get current domain values"""
        return (
            self._possible_times,
            self._possible_rooms,
            self._possible_instructors
        )
    
    def reduce_domain(self,
                     time_slots: Optional[Set[TimeSlot]] = None,
                     rooms: Optional[Set[str]] = None,
                     instructors: Optional[Set[str]] = None) -> None:
        """Remove values from domain"""
        if time_slots:
            self._possible_times -= time_slots
        if rooms:
            self._possible_rooms -= rooms
        if instructors:
            self._possible_instructors -= instructors
    
    def domain_size(self) -> int:
        """Get total size of variable domain"""
        return (len(self._possible_times) *
                len(self._possible_rooms) *
                len(self._possible_instructors))
    
    def conflicts_with(self, other: 'Variable') -> bool:
        """Check if this variable conflicts with another"""
        if not (self.is_assigned and other.is_assigned):
            return False
            
        # Check time slot overlap
        if self._assigned_time and other._assigned_time and self._assigned_time.overlaps(other._assigned_time):
            # Check resource conflicts
            return (self._assigned_room == other._assigned_room or
                   self._assigned_instructor == other._assigned_instructor)
        return False
    
    def clone(self) -> 'Variable':
        """Create a deep copy of this variable"""
        new_var = Variable(
            self.course_id,
            self.level,
            self.requirements
        )
        # Copy assignments
        new_var._assigned_time = self._assigned_time
        new_var._assigned_room = self._assigned_room
        new_var._assigned_instructor = self._assigned_instructor
        
        # Copy domain sets
        new_var._possible_times = self._possible_times.copy()
        new_var._possible_rooms = self._possible_rooms.copy()
        new_var._possible_instructors = self._possible_instructors.copy()
        
        return new_var