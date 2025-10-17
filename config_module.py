"""
Configuration Module
====================
Centralized configuration for the timetable management system.
"""

from typing import List
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    db_path: str = "timetable.db"
    row_factory_enabled: bool = True


@dataclass
class APIConfig:
    """API configuration settings"""
    title: str = "Timetable Management API"
    description: str = "REST API for university timetable management with conflict detection"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class ScheduleConfig:
    """Schedule validation and business logic configuration"""
    valid_days: List[str] = None
    working_hours_per_day: int = 10
    working_days_per_week: int = 5
    min_gap_warning_hours: float = 2.0
    time_format: str = "%H:%M"
    
    def __post_init__(self):
        if self.valid_days is None:
            self.valid_days = [
                'Monday', 'Tuesday', 'Wednesday', 
                'Thursday', 'Friday', 'Saturday', 'Sunday'
            ]
    
    @property
    def total_available_hours(self) -> int:
        """Calculate total available hours per week"""
        return self.working_days_per_week * self.working_hours_per_day


# Global configuration instances
db_config = DatabaseConfig()
api_config = APIConfig()
schedule_config = ScheduleConfig()


# Constants
TIME_SLOT_REGEX = r"^\d{2}:\d{2}$"
MAX_LECTURE_NUMBER = 10
MIN_STRING_LENGTH = 1
MAX_STRING_LENGTH = 50
