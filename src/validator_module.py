"""
Schedule Validator Module
==========================
Handles validation of schedules for conflicts and efficiency analysis.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from config import schedule_config


logger = logging.getLogger(__name__)


class ScheduleValidator:
    """
    Validates schedules for conflicts and analyzes efficiency.
    
    Responsibilities:
    - Detect hard constraint violations (instructor, room, section conflicts)
    - Identify soft constraint violations (gaps, inefficiencies)
    - Calculate utilization metrics
    - Generate warnings and recommendations
    """
    
    def __init__(self, db_manager):
        """
        Initialize validator with database manager.
        
        Args:
            db_manager: DatabaseManager instance for querying conflicts
        """
        self.db = db_manager
        self.config = schedule_config
    
    def validate_slot(self, day: str, start_time: str, end_time: str,
                     room_id: str, instructor_id: str, section_id: str,
                     schedule_id: Optional[int] = None) -> Tuple[bool, List[Dict]]:
        """
        Validate a single schedule slot for conflicts.
        
        Args:
            day: Day of week
            start_time: Start time (HH:MM)
            end_time: End time (HH:MM)
            room_id: Room identifier
            instructor_id: Instructor identifier
            section_id: Section identifier
            schedule_id: ID to exclude from validation (for updates)
            
        Returns:
            Tuple of (is_valid, conflicts_list)
        """
        conflicts = []
        
        # Validate time ordering
        try:
            start_dt = datetime.strptime(start_time, self.config.time_format)
            end_dt = datetime.strptime(end_time, self.config.time_format)
            
            if end_dt <= start_dt:
                conflicts.append({
                    "type": "time_validation",
                    "message": "End time must be after start time"
                })
                return False, conflicts
        except ValueError as e:
            conflicts.append({
                "type": "time_validation",
                "message": f"Invalid time format: {str(e)}"
            })
            return False, conflicts
        
        # Check instructor conflicts
        instructor_conflicts = self.db.get_instructor_conflicts(
            instructor_id, day, start_time, end_time, schedule_id
        )
        for conflict in instructor_conflicts:
            conflicts.append({
                "type": "instructor_conflict",
                "schedule_id": str(conflict['schedule_id']),
                "message": (
                    f"Instructor {instructor_id} already assigned to "
                    f"{conflict['course_name']} (Section {conflict['section_id']}) "
                    f"at {day} {start_time}"
                )
            })
        
        # Check room conflicts
        room_conflicts = self.db.get_room_conflicts(
            room_id, day, start_time, end_time, schedule_id
        )
        for conflict in room_conflicts:
            conflicts.append({
                "type": "room_conflict",
                "schedule_id": str(conflict['schedule_id']),
                "message": (
                    f"Room {room_id} already booked for "
                    f"{conflict['course_name']} (Section {conflict['section_id']}) "
                    f"at {day} {start_time}"
                )
            })
        
        # Check section conflicts
        section_conflicts = self.db.get_section_conflicts(
            section_id, day, start_time, end_time, schedule_id
        )
        for conflict in section_conflicts:
            conflicts.append({
                "type": "section_conflict",
                "schedule_id": str(conflict['schedule_id']),
                "message": (
                    f"Section {section_id} already has {conflict['course_name']} "
                    f"scheduled at {day} {start_time}"
                )
            })
        
        is_valid = len(conflicts) == 0
        return is_valid, conflicts
    
    def validate_entire_schedule(self) -> Dict[str, Any]:
        """
        Validate the entire schedule for all conflicts.
        
        Returns:
            Dictionary with validation results including conflicts and warnings
        """
        all_conflicts = []
        schedules = self.db.get_all_schedules()
        
        # Check each schedule entry for conflicts
        for schedule in schedules:
            is_valid, conflicts = self.validate_slot(
                schedule['day'],
                schedule['start_time'],
                schedule['end_time'],
                schedule['room_id'],
                schedule['instructor_id'],
                schedule['section_id'],
                schedule['schedule_id']
            )
            
            all_conflicts.extend(conflicts)
        
        # Get efficiency warnings
        efficiency_data = self.calculate_efficiency_metrics()
        
        return {
            "is_valid": len(all_conflicts) == 0,
            "conflicts": all_conflicts,
            "warnings": efficiency_data.get("warnings", [])
        }
    
    def calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive efficiency metrics for the schedule.
        
        Returns:
            Dictionary with efficiency metrics and warnings
        """
        schedules = self.db.get_all_schedules()
        
        if not schedules:
            return {
                "overall_efficiency": 0.0,
                "room_utilization": {},
                "instructor_utilization": {},
                "total_gaps": 0,
                "warnings": ["No schedule entries found"]
            }
        
        # Organize schedules by resource and day
        room_schedule = defaultdict(list)
        instructor_schedule = defaultdict(float)
        section_schedule = defaultdict(list)
        
        for entry in schedules:
            # Room scheduling by day
            key = (entry['room_id'], entry['day'])
            start_dt = datetime.strptime(entry['start_time'], self.config.time_format)
            end_dt = datetime.strptime(entry['end_time'], self.config.time_format)
            duration = (end_dt - start_dt).seconds / 3600
            
            room_schedule[key].append({
                'start': entry['start_time'],
                'end': entry['end_time'],
                'duration': duration
            })
            
            # Instructor total hours
            instructor_schedule[entry['instructor_id']] += duration
            
            # Section scheduling by day
            section_key = (entry['section_id'], entry['day'])
            section_schedule[section_key].append({
                'start': entry['start_time'],
                'end': entry['end_time']
            })
        
        # Calculate room utilization and gaps
        room_utilization = defaultdict(float)
        room_gaps = []
        
        for (room_id, day), sessions in room_schedule.items():
            # Sort sessions by start time
            sessions.sort(key=lambda x: x['start'])
            
            # Sum total usage time
            total_usage = sum(s['duration'] for s in sessions)
            room_utilization[room_id] += total_usage
            
            # Detect gaps between sessions
            for i in range(len(sessions) - 1):
                end_current = datetime.strptime(sessions[i]['end'], self.config.time_format)
                start_next = datetime.strptime(sessions[i+1]['start'], self.config.time_format)
                gap_hours = (start_next - end_current).seconds / 3600
                
                if gap_hours >= self.config.min_gap_warning_hours:
                    room_gaps.append(
                        f"Room {room_id} idle for {gap_hours:.1f} hours on {day} "
                        f"between {sessions[i]['end']} and {sessions[i+1]['start']}"
                    )
        
        # Calculate section gaps (student experience)
        section_gaps = []
        for (section_id, day), sessions in section_schedule.items():
            sessions.sort(key=lambda x: x['start'])
            
            for i in range(len(sessions) - 1):
                end_current = datetime.strptime(sessions[i]['end'], self.config.time_format)
                start_next = datetime.strptime(sessions[i+1]['start'], self.config.time_format)
                gap_hours = (start_next - end_current).seconds / 3600
                
                if gap_hours >= self.config.min_gap_warning_hours:
                    section_gaps.append(
                        f"Section {section_id} has {gap_hours:.1f} hour gap on {day} "
                        f"between {sessions[i]['end']} and {sessions[i+1]['start']}"
                    )
        
        # Calculate utilization percentages
        total_available = self.config.total_available_hours
        
        room_util_pct = {
            room_id: round((hours / total_available) * 100, 1)
            for room_id, hours in room_utilization.items()
        }
        
        instructor_util_pct = {
            instructor_id: round((hours / total_available) * 100, 1)
            for instructor_id, hours in instructor_schedule.items()
        }
        
        # Calculate overall efficiency
        avg_room = sum(room_util_pct.values()) / len(room_util_pct) if room_util_pct else 0
        avg_instructor = sum(instructor_util_pct.values()) / len(instructor_util_pct) if instructor_util_pct else 0
        overall = round((avg_room + avg_instructor) / 2, 1)
        
        # Compile warnings
        warnings = room_gaps + section_gaps
        
        # Add utilization warnings
        for room_id, util in room_util_pct.items():
            if util < 30:
                warnings.append(f"Room {room_id} is underutilized at {util}%")
        
        for instructor_id, util in instructor_util_pct.items():
            if util < 30:
                warnings.append(f"Instructor {instructor_id} is underutilized at {util}%")
            elif util > 90:
                warnings.append(f"Instructor {instructor_id} may be overloaded at {util}%")
        
        return {
            "overall_efficiency": overall,
            "room_utilization": room_util_pct,
            "instructor_utilization": instructor_util_pct,
            "total_gaps": len(room_gaps),
            "warnings": warnings
        }
    
    def check_soft_constraints(self) -> List[str]:
        """
        Check soft constraints and return recommendations.
        
        Returns:
            List of soft constraint violation warnings
        """
        warnings = []
        schedules = self.db.get_all_schedules()
        
        # Check for early morning classes (before 8 AM)
        for entry in schedules:
            hour = int(entry['start_time'].split(':')[0])
            if hour < 8:
                warnings.append(
                    f"Early morning class: {entry['course_name']} at "
                    f"{entry['day']} {entry['start_time']}"
                )
        
        # Check for late evening classes (after 6 PM)
        for entry in schedules:
            hour = int(entry['start_time'].split(':')[0])
            if hour >= 18:
                warnings.append(
                    f"Late evening class: {entry['course_name']} at "
                    f"{entry['day']} {entry['start_time']}"
                )
        
        return warnings