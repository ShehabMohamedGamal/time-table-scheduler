from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional
from datetime import time
from .variable import TimeSlot, ResourceRequirements

@dataclass
class RoomAvailability:
    """Tracks room availability and constraints"""
    room_id: str
    room_type: str
    capacity: int
    available_times: List[TimeSlot] = field(default_factory=list)
    features: Dict[str, bool] = field(default_factory=dict)

@dataclass
class InstructorAvailability:
    """Tracks instructor availability and preferences"""
    instructor_id: str
    max_hours_per_day: int = 6
    preferred_times: List[TimeSlot] = field(default_factory=list)
    available_times: List[TimeSlot] = field(default_factory=list)

class Domain:
    """Manages available values for CSP variables"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.time_slots: List[TimeSlot] = list()
        self.rooms: Dict[str, RoomAvailability] = {}
        self.instructors: Dict[str, InstructorAvailability] = {}
        self._load_domain_data()
    
    def _load_domain_data(self) -> None:
        """Load all domain data from database"""
        # Load time slots
        result = self.db_manager.read_records('timetable', {'level': None})
        if result.success and result.data:
            for row in result.data:
                self.time_slots.append(TimeSlot(
                    day=row[1],  # day
                    start_time=time.fromisoformat(row[2]),  # start_time
                    end_time=time.fromisoformat(row[3])     # end_time
                ))
        
        # Load rooms
        result = self.db_manager.read_records('rooms')
        if result.success and result.data:
            for row in result.data:
                self.rooms[row[0]] = RoomAvailability(
                    room_id=row[0],
                    room_type=row[1],
                    capacity=row[2],
                    available_times=self.time_slots.copy()
                )
        
        # Load instructors
        result = self.db_manager.read_records('instructors')
        if result.success and result.data:
            for row in result.data:
                preferred_slots = []
                if row[2]:  # preferred_slots column
                    # Assuming preferred slots are stored as JSON
                    import json
                    prefs = json.loads(row[2])
                    preferred_slots = [
                        ts for ts in self.time_slots
                        if self._matches_preference(ts, prefs)
                    ]
                
                self.instructors[row[0]] = InstructorAvailability(
                    instructor_id=row[0],
                    available_times=self.time_slots.copy(),
                    preferred_times=preferred_slots
                )
    
    def _matches_preference(self, time_slot: TimeSlot, prefs: Dict) -> bool:
        """Check if time slot matches instructor preferences"""
        return (time_slot.day in prefs.get('days', []) and
                time_slot.start_time >= time.fromisoformat(prefs.get('earliest', '08:00')) and
                time_slot.end_time <= time.fromisoformat(prefs.get('latest', '18:00')))
    
    def get_available_values(self, 
                           requirements: ResourceRequirements
                           ) -> tuple[Set[TimeSlot], Set[str], Set[str]]:
        """Get available values matching requirements"""
        # Convert time_slots list to set
        available_times = set(self.time_slots)  # Convert List to Set
        
        # Filter rooms by type and capacity
        suitable_rooms = {
            room_id
            for room_id, room in self.rooms.items()
            if (room.room_type == requirements.room_type and
                room.capacity >= requirements.min_capacity and
                (not requirements.requires_lab or room.features.get('lab')) and
                (not requirements.requires_projector or room.features.get('projector')))
        }
        
        # Get qualified instructors (this would typically use a qualification table)
        qualified_instructors = set(self.instructors.keys())  # Simplified for now
        
        return (available_times, suitable_rooms, qualified_instructors)
    
    def update_availability(self,
                          time_slot: TimeSlot,
                          room_id: Optional[str] = None,
                          instructor_id: Optional[str] = None) -> None:
        """Mark resources as unavailable for given time slot"""
        if room_id and room_id in self.rooms:
            try:
                self.rooms[room_id].available_times.remove(time_slot)
            except ValueError:
                pass
            
    def restore_availability(self,
                             time_slot: TimeSlot,
                             room_id: Optional[str] = None,
                             instructor_id: Optional[str] = None) -> None:
        """Restore resource availability for given time slot"""
        if room_id and room_id in self.rooms:
            if time_slot not in self.rooms[room_id].available_times:
                self.rooms[room_id].available_times.append(time_slot)

        if instructor_id and instructor_id in self.instructors:
            if time_slot not in self.instructors[instructor_id].available_times:
                self.instructors[instructor_id].available_times.append(time_slot)