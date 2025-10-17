"""
Database Manager Module
========================
Handles all database operations including connection management,
schema initialization, and CRUD operations.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from config import db_config


logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database operations for timetable management.
    
    Responsibilities:
    - Database connection management
    - Schema initialization and migration
    - CRUD operations for all entities
    - Transaction management
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. Defaults to config.
        """
        self.db_path = db_path or db_config.db_path
        self._initialized = False
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Ensures proper connection handling and cleanup.
        
        Yields:
            sqlite3.Connection: Database connection object
        """
        conn = sqlite3.connect(self.db_path)
        if db_config.row_factory_enabled:
            conn.row_factory = sqlite3.Row
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {str(e)}")
            raise
        finally:
            conn.close()
    
    def initialize_schema(self) -> None:
        """
        Initialize database schema if not exists.
        Creates all necessary tables for timetable management.
        """
        if self._initialized:
            return
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create Courses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    credits INTEGER NOT NULL,
                    course_type TEXT NOT NULL CHECK(course_type IN ('Lecture', 'Lab'))
                )
            """)
            
            # Create Instructors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instructors (
                    instructor_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    preferred_slots TEXT,
                    qualified_courses TEXT
                )
            """)
            
            # Create Rooms table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id TEXT PRIMARY KEY,
                    room_type TEXT NOT NULL CHECK(room_type IN ('Lab', 'Lecture')),
                    capacity INTEGER NOT NULL CHECK(capacity > 0)
                )
            """)
            
            # Create TimeSlots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS time_slots (
                    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    day TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    UNIQUE(day, start_time, end_time)
                )
            """)
            
            # Create Sections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sections (
                    section_id TEXT PRIMARY KEY,
                    semester INTEGER NOT NULL CHECK(semester > 0),
                    student_count INTEGER NOT NULL CHECK(student_count > 0)
                )
            """)
            
            # Create Schedule table with proper constraints
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule (
                    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    lecture_number INTEGER NOT NULL CHECK(lecture_number > 0),
                    day TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    instructor_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (course_id) REFERENCES courses(course_id),
                    FOREIGN KEY (section_id) REFERENCES sections(section_id),
                    FOREIGN KEY (room_id) REFERENCES rooms(room_id),
                    FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id),
                    UNIQUE(course_id, section_id, lecture_number)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_schedule_instructor 
                ON schedule(instructor_id, day, start_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_schedule_room 
                ON schedule(room_id, day, start_time)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_schedule_section 
                ON schedule(section_id, day, start_time)
            """)
            
            self._initialized = True
            logger.info("Database schema initialized successfully")
    
    # ==================== Schedule CRUD Operations ====================
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """
        Retrieve all schedule entries with joined details.
        
        Returns:
            List of schedule dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.schedule_id, s.course_id, c.course_name, s.section_id, 
                       s.lecture_number, s.day, s.start_time, s.end_time, 
                       s.room_id, r.room_type, s.instructor_id, i.name as instructor_name,
                       s.created_at, s.updated_at
                FROM schedule s
                JOIN courses c ON s.course_id = c.course_id
                JOIN rooms r ON s.room_id = r.room_id
                JOIN instructors i ON s.instructor_id = i.instructor_id
                ORDER BY s.day, s.start_time
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_schedule_by_id(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific schedule entry by ID.
        
        Args:
            schedule_id: Schedule entry ID
            
        Returns:
            Schedule dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.schedule_id, s.course_id, c.course_name, s.section_id, 
                       s.lecture_number, s.day, s.start_time, s.end_time, 
                       s.room_id, s.instructor_id, i.name as instructor_name
                FROM schedule s
                JOIN courses c ON s.course_id = c.course_id
                JOIN instructors i ON s.instructor_id = i.instructor_id
                WHERE s.schedule_id = ?
            """, (schedule_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_schedule(self, course_id: str, section_id: str, lecture_number: int,
                       day: str, start_time: str, end_time: str,
                       room_id: str, instructor_id: str) -> int:
        """
        Create a new schedule entry.
        
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
            ID of created schedule entry
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule 
                (course_id, section_id, lecture_number, day, start_time, 
                 end_time, room_id, instructor_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (course_id, section_id, lecture_number, day, start_time,
                  end_time, room_id, instructor_id))
            
            return cursor.lastrowid
    
    def update_schedule(self, schedule_id: int, **kwargs) -> bool:
        """
        Update an existing schedule entry.
        
        Args:
            schedule_id: Schedule entry ID
            **kwargs: Fields to update (day, start_time, end_time, room_id, instructor_id)
            
        Returns:
            True if update successful, False if entry not found
        """
        allowed_fields = {'day', 'start_time', 'end_time', 'room_id', 'instructor_id'}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
        
        if not update_fields:
            return False
        
        set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
        set_clause += ", updated_at = CURRENT_TIMESTAMP"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE schedule
                SET {set_clause}
                WHERE schedule_id = ?
            """, (*update_fields.values(), schedule_id))
            
            return cursor.rowcount > 0
    
    def delete_schedule(self, schedule_id: int) -> bool:
        """
        Delete a schedule entry.
        
        Args:
            schedule_id: Schedule entry ID
            
        Returns:
            True if deletion successful, False if entry not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedule WHERE schedule_id = ?", (schedule_id,))
            return cursor.rowcount > 0
    
    def get_schedule_raw(self, schedule_id: int) -> Optional[Tuple]:
        """
        Get raw schedule data for validation.
        
        Args:
            schedule_id: Schedule entry ID
            
        Returns:
            Tuple of (course_id, section_id, day, start_time, end_time, room_id, instructor_id)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT course_id, section_id, day, start_time, end_time, 
                       room_id, instructor_id
                FROM schedule
                WHERE schedule_id = ?
            """, (schedule_id,))
            
            return cursor.fetchone()
    
    # ==================== Conflict Detection Queries ====================
    
    def get_instructor_conflicts(self, instructor_id: str, day: str, 
                                start_time: str, end_time: str,
                                exclude_schedule_id: Optional[int] = None) -> List[Dict]:
        """
        Check for instructor scheduling conflicts.
        
        Args:
            instructor_id: Instructor identifier
            day: Day of week
            start_time: Start time
            end_time: End time
            exclude_schedule_id: Schedule ID to exclude from check
            
        Returns:
            List of conflicting schedule entries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            exclude_clause = "AND schedule_id != ?" if exclude_schedule_id else ""
            params = (instructor_id, day, end_time, start_time)
            if exclude_schedule_id:
                params += (exclude_schedule_id,)
            
            cursor.execute(f"""
                SELECT s.schedule_id, s.course_id, c.course_name, s.section_id,
                       s.start_time, s.end_time
                FROM schedule s
                JOIN courses c ON s.course_id = c.course_id
                WHERE s.instructor_id = ? 
                AND s.day = ? 
                AND s.start_time < ?
                AND s.end_time > ?
                {exclude_clause}
            """, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_room_conflicts(self, room_id: str, day: str,
                          start_time: str, end_time: str,
                          exclude_schedule_id: Optional[int] = None) -> List[Dict]:
        """
        Check for room scheduling conflicts.
        
        Args:
            room_id: Room identifier
            day: Day of week
            start_time: Start time
            end_time: End time
            exclude_schedule_id: Schedule ID to exclude from check
            
        Returns:
            List of conflicting schedule entries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            exclude_clause = "AND schedule_id != ?" if exclude_schedule_id else ""
            params = (room_id, day, end_time, start_time)
            if exclude_schedule_id:
                params += (exclude_schedule_id,)
            
            cursor.execute(f"""
                SELECT s.schedule_id, s.course_id, c.course_name, s.section_id,
                       s.start_time, s.end_time
                FROM schedule s
                JOIN courses c ON s.course_id = c.course_id
                WHERE s.room_id = ? 
                AND s.day = ? 
                AND s.start_time < ?
                AND s.end_time > ?
                {exclude_clause}
            """, params)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_section_conflicts(self, section_id: str, day: str,
                             start_time: str, end_time: str,
                             exclude_schedule_id: Optional[int] = None) -> List[Dict]:
        """
        Check for section scheduling conflicts.
        
        Args:
            section_id: Section identifier
            day: Day of week
            start_time: Start time
            end_time: End time
            exclude_schedule_id: Schedule ID to exclude from check
            
        Returns:
            List of conflicting schedule entries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            exclude_clause = "AND schedule_id != ?" if exclude_schedule_id else ""
            params = (section_id, day, end_time, start_time)
            if exclude_schedule_id:
                params += (exclude_schedule_id,)
            
            cursor.execute(f"""
                SELECT s.schedule_id, s.course_id, c.course_name,
                       s.start_time, s.end_time
                FROM schedule s
                JOIN courses c ON s.course_id = c.course_id
                WHERE s.section_id = ? 
                AND s.day = ? 
                AND s.start_time < ?
                AND s.end_time > ?
                {exclude_clause}
            """, params)
            
            return [dict(row) for row in cursor.fetchall()]
