"""
Slot Manager Module
===================
Manages schedule slot operations with integrated validation.
"""

import logging
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


class SlotManager:
    """
    Manages schedule slot creation, updates, and deletion with validation.
    
    Responsibilities:
    - Coordinate between database and validator
    - Handle slot CRUD operations with automatic validation
    - Provide high-level slot management interface
    - Transaction management for complex operations
    """
    
    def __init__(self, db_manager, validator):
        """
        Initialize slot manager with dependencies.
        
        Args:
            db_manager: DatabaseManager instance
            validator: ScheduleValidator instance
        """
        self.db = db_manager
        self.validator = validator
    
    def create_slot(self, course_id: str, section_id: str, lecture_number: int,
                   day: str, start_time: str, end_time: str,
                   room_id: str, instructor_id: str) -> Dict[str, Any]:
        """
        Create a new schedule slot with validation.
        
        Args:
            course_id: Course identifier
            section_id: Section identifier
            lecture_number: Lecture number (1-10)
            day: Day of week
            start_time: Start time (HH:MM)
            end_time: End time (HH:MM)
            room_id: Room identifier
            instructor_id: Instructor identifier
            
        Returns:
            Dictionary with creation result and assigned schedule_id
            
        Raises:
            ValueError: If validation fails or conflicts exist
        """
        # Validate the slot
        is_valid, conflicts = self.validator.validate_slot(
            day, start_time, end_time, room_id, instructor_id, section_id
        )
        
        if not is_valid:
            logger.warning(f"Slot creation failed: conflicts detected")
            raise ValueError({
                "message": "Schedule conflicts detected",
                "conflicts": conflicts
            })
        
        # Create the slot
        try:
            schedule_id = self.db.create_schedule(
                course_id, section_id, lecture_number,
                day, start_time, end_time, room_id, instructor_id
            )
            
            logger.info(f"Created schedule slot {schedule_id}")
            
            return {
                "schedule_id": schedule_id,
                "message": "Schedule slot created successfully",
                "course_id": course_id,
                "section_id": section_id,
                "lecture_number": lecture_number,
                "day": day,
                "start_time": start_time,
                "end_time": end_time,
                "room_id": room_id,
                "instructor_id": instructor_id
            }
        except Exception as e:
            logger.error(f"Failed to create slot: {str(e)}")
            raise ValueError(f"Database error: {str(e)}")
    
    def update_slot(self, schedule_id: int, **updates) -> Dict[str, Any]:
        """
        Update an existing schedule slot with validation.
        
        Args:
            schedule_id: ID of schedule entry to update
            **updates: Fields to update (day, start_time, end_time, room_id, instructor_id)
            
        Returns:
            Dictionary with update result
            
        Raises:
            ValueError: If slot not found, validation fails, or conflicts exist
        """
        # Get current slot data
        current = self.db.get_schedule_raw(schedule_id)
        
        if not current:
            raise ValueError(f"Schedule slot {schedule_id} not found")
        
        # Build updated values
        course_id, section_id, day, start_time, end_time, room_id, instructor_id = current
        
        new_day = updates.get('day', day)
        new_start = updates.get('start_time', start_time)
        new_end = updates.get('end_time', end_time)
        new_room = updates.get('room_id', room_id)
        new_instructor = updates.get('instructor_id', instructor_id)
        
        # Validate the updated slot
        is_valid, conflicts = self.validator.validate_slot(
            new_day, new_start, new_end, new_room, new_instructor,
            section_id, schedule_id
        )
        
        if not is_valid:
            logger.warning(f"Slot update failed: conflicts detected")
            raise ValueError({
                "message": "Schedule conflicts detected",
                "conflicts": conflicts
            })
        
        # Perform update
        try:
            success = self.db.update_schedule(
                schedule_id,
                day=new_day,
                start_time=new_start,
                end_time=new_end,
                room_id=new_room,
                instructor_id=new_instructor
            )
            
            if not success:
                raise ValueError(f"Failed to update schedule slot {schedule_id}")
            
            logger.info(f"Updated schedule slot {schedule_id}")
            
            return {
                "schedule_id": schedule_id,
                "message": "Schedule slot updated successfully",
                "updated_fields": {k: v for k, v in updates.items() if v is not None}
            }
        except Exception as e:
            logger.error(f"Failed to update slot {schedule_id}: {str(e)}")
            raise ValueError(f"Database error: {str(e)}")
    
    def delete_slot(self, schedule_id: int) -> Dict[str, Any]:
        """
        Delete a schedule slot.
        
        Args:
            schedule_id: ID of schedule entry to delete
            
        Returns:
            Dictionary with deletion confirmation
            
        Raises:
            ValueError: If slot not found
        """
        success = self.db.delete_schedule(schedule_id)
        
        if not success:
            raise ValueError(f"Schedule slot {schedule_id} not found")
        
        logger.info(f"Deleted schedule slot {schedule_id}")
        
        return {
            "message": f"Schedule slot {schedule_id} deleted successfully",
            "schedule_id": schedule_id
        }
    
    def get_slot(self, schedule_id: int) -> Dict[str, Any]:
        """
        Retrieve a specific schedule slot.
        
        Args:
            schedule_id: ID of schedule entry
            
        Returns:
            Schedule slot data
            
        Raises:
            ValueError: If slot not found
        """
        slot = self.db.get_schedule_by_id(schedule_id)
        
        if not slot:
            raise ValueError(f"Schedule slot {schedule_id} not found")
        
        return slot
    
    def get_all_slots(self) -> List[Dict[str, Any]]:
        """
        Retrieve all schedule slots.
        
        Returns:
            List of all schedule entries
        """
        return self.db.get_all_schedules()
    
    def bulk_create_slots(self, slots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple schedule slots in a transaction.
        
        Args:
            slots: List of slot dictionaries with required fields
            
        Returns:
            Dictionary with creation results
        """
        created = []
        failed = []
        
        for i, slot_data in enumerate(slots):
            try:
                result = self.create_slot(**slot_data)
                created.append(result['schedule_id'])
            except ValueError as e:
                failed.append({
                    "index": i,
                    "data": slot_data,
                    "error": str(e)
                })
                logger.warning(f"Failed to create slot {i}: {str(e)}")
        
        return {
            "total": len(slots),
            "created": len(created),
            "failed": len(failed),
            "created_ids": created,
            "failures": failed
        }
