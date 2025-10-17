"""
Timetable Management System - Source Package
=============================================

This package contains all core modules for the intelligent timetable
management system.

Modules:
    database: Database operations and schema management
    parser: Data parsing from various formats
    validator: Schedule validation and conflict detection
    manager: High-level slot management operations
    api: REST API endpoints and handlers

Usage:
    from src.database import DatabaseManager
    from src.validator import ScheduleValidator
    from src.manager import SlotManager
    from src.api import APIHandler
    from src.parser import DataParser
"""

__version__ = "1.0.0"
__author__ = "CSIT Department"

# Export main classes for convenient importing
from .database import DatabaseManager
from .parser import DataParser
from .validator import ScheduleValidator
from .manager import SlotManager
from .api import APIHandler

__all__ = [
    "DatabaseManager",
    "DataParser",
    "ScheduleValidator",
    "SlotManager",
    "APIHandler",
]
