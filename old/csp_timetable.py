"""
Timetable Management REST API
===============================

A FastAPI-based REST API for managing university timetables with automated
conflict detection and efficiency analysis.

Installation:
    pip install fastapi uvicorn pydantic

Running the API:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

API Documentation:
    Once running, visit http://localhost:8000/docs for interactive API docs

Endpoints:
    GET    /slots              - Retrieve all schedule entries
    GET    /slots/{id}         - Get specific schedule entry
    POST   /slots              - Create new schedule entry
    PUT    /slots/{id}         - Update existing schedule entry
    DELETE /slots/{id}         - Delete schedule entry
    POST   /validate           - Validate entire schedule
    GET    /efficiency         - Get efficiency metrics
    POST   /upload-csv         - Upload and parse CSV file
    GET    /health             - Health check endpoint

Example Usage:
    # Get all slots
    curl http://localhost:8000/slots
    
    # Create a new slot
    curl -X POST http://localhost:8000/slots \
         -H "Content-Type: application/json" \
         -d '{"course_id":"CS101","section_id":"S1","lecture_number":1,
              "day":"Monday","start_time":"09:00","end_time":"10:30",
              "room_id":"Lab1","instructor_id":"I001"}'
    
    # Update a slot
    curl -X PUT http://localhost:8000/slots/1 \
         -H "Content-Type: application/json" \
         -d '{"day":"Tuesday","start_time":"14:00"}'
    
    # Validate schedule
    curl -X POST http://localhost:8000/validate
    
    # Get efficiency metrics
    curl http://localhost:8000/efficiency
"""

from fastapi import FastAPI, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import sqlite3
import logging
import csv
import io
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Timetable Management API",
    description="REST API for university timetable management with conflict detection",
    version="1.0.0"
)

# Database configuration
DATABASE_PATH = "timetable.db"


# ==================== Pydantic Models ====================

class SlotCreate(BaseModel):
    """Model for creating a new schedule slot"""
    course_id: str = Field(..., min_length=1, max_length=50)
    section_id: str = Field(..., min_length=1, max_length=50)
    lecture_number: int = Field(..., ge=1, le=10)
    day: str = Field(..., min_length=1)
    start_time: str = Field(..., regex=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., regex=r"^\d{2}:\d{2}$")
    room_id: str = Field(..., min_length=1, max_length=50)
    instructor_id: str = Field(..., min_length=1, max_length=50)
    
    @validator('day')
    def validate_day(cls, v):
        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        if v not in valid_days:
            raise ValueError(f'Day must be one of: {", ".join(valid_days)}')
        return v
    
    @validator('end_time')
    def validate_times(cls, v, values):
        """Ensure end_time is after start_time"""
        if 'start_time' in values:
            start = datetime.strptime(values['start_time'], '%H:%M')
            end = datetime.strptime(v, '%H:%M')
            if end <= start:
                raise ValueError('end_time must be after start_time')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "course_id": "CS101",
                "section_id": "S1",
                "lecture_number": 1,
                "day": "Monday",
                "start_time": "09:00",
                "end_time": "10:30",
                "room_id": "Lab1",
                "instructor_id": "I001"
            }
        }


class SlotUpdate(BaseModel):
    """Model for updating an existing schedule slot"""
    day: Optional[str] = Field(None, min_length=1)
    start_time: Optional[str] = Field(None, regex=r"^\d{2}:\d{2}$")
    end_time: Optional[str] = Field(None, regex=r"^\d{2}:\d{2}$")
    room_id: Optional[str] = Field(None, min_length=1, max_length=50)
    instructor_id: Optional[str] = Field(None, min_length=1, max_length=50)
    
    @validator('day')
    def validate_day(cls, v):
        if v is not None:
            valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            if v not in valid_days:
                raise ValueError(f'Day must be one of: {", ".join(valid_days)}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "day": "Tuesday",
                "start_time": "14:00",
                "end_time": "15:30"
            }
        }


class ValidationResponse(BaseModel):
    """Model for validation response"""
    is_valid: bool
    conflicts: List[Dict[str, str]]
    warnings: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "is_valid": False,
                "conflicts": [
                    {
                        "type": "instructor_conflict",
                        "message": "Instructor I001 already assigned to CS102 (Section S2) at Monday 09:00",
                        "schedule_id": "5"
                    }
                ],
                "warnings": [
                    "Room Lab1 idle for 3.0 hours on Monday between 10:30 and 13:30"
                ]
            }
        }


class EfficiencyMetrics(BaseModel):
    """Model for efficiency metrics response"""
    overall_efficiency: float = Field(..., ge=0, le=100)
    room_utilization: Dict[str, float]
    instructor_utilization: Dict[str, float]
    total_gaps: int
    warnings: List[str]
    
    class Config:
        schema_extra = {
            "example": {
                "overall_efficiency": 78.5,
                "room_utilization": {
                    "Lab1": 65.0,
                    "Room101": 82.3
                },
                "instructor_utilization": {
                    "I001": 70.0,
                    "I002": 85.5
                },
                "total_gaps": 5,
                "warnings": [
                    "Room Lab1 idle for 3.0 hours on Monday",
                    "Section S1 has 2.5 hour gap on Tuesday"
                ]
            }
        }


# ==================== Database Utilities ====================

@contextmanager
def get_db_connection():
    """
    Context manager for database connections
    Ensures proper connection handling and cleanup
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        conn.close()


def initialize_database():
    """
    Initialize database schema if not exists
    Creates all necessary tables for timetable management
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create Courses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                credits INTEGER NOT NULL,
                course_type TEXT NOT NULL
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
                room_type TEXT NOT NULL,
                capacity INTEGER NOT NULL
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
                semester INTEGER NOT NULL,
                student_count INTEGER NOT NULL
            )
        """)
        
        # Create Schedule table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                section_id TEXT NOT NULL,
                lecture_number INTEGER NOT NULL,
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
        
        logger.info("Database initialized successfully")


# ==================== Validation Functions ====================

def validate_slot_conflicts(conn: sqlite3.Connection, schedule_id: Optional[int],
                           day: str, start_time: str, end_time: str,
                           room_id: str, instructor_id: str, section_id: str) -> List[Dict]:
    """
    Validate schedule slot for conflicts
    
    Returns:
        List of conflict dictionaries
    """
    conflicts = []
    cursor = conn.cursor()
    
    # Exclude current schedule_id if updating
    exclude_clause = "AND schedule_id != ?" if schedule_id else ""
    exclude_params = (schedule_id,) if schedule_id else ()
    
    # Check instructor conflicts
    cursor.execute(f"""
        SELECT s.schedule_id, s.course_id, c.course_name, s.section_id 
        FROM schedule s
        JOIN courses c ON s.course_id = c.course_id
        WHERE s.instructor_id = ? 
        AND s.day = ? 
        AND s.start_time < ?
        AND s.end_time > ?
        {exclude_clause}
    """, (instructor_id, day, end_time, start_time) + exclude_params)
    
    for row in cursor.fetchall():
        conflicts.append({
            "type": "instructor_conflict",
            "schedule_id": str(row[0]),
            "message": (f"Instructor {instructor_id} already assigned to "
                       f"{row[2]} (Section {row[3]}) at {day} {start_time}")
        })
    
    # Check room conflicts
    cursor.execute(f"""
        SELECT s.schedule_id, s.course_id, c.course_name, s.section_id
        FROM schedule s
        JOIN courses c ON s.course_id = c.course_id
        WHERE s.room_id = ? 
        AND s.day = ? 
        AND s.start_time < ?
        AND s.end_time > ?
        {exclude_clause}
    """, (room_id, day, end_time, start_time) + exclude_params)
    
    for row in cursor.fetchall():
        conflicts.append({
            "type": "room_conflict",
            "schedule_id": str(row[0]),
            "message": (f"Room {room_id} already booked for "
                       f"{row[2]} (Section {row[3]}) at {day} {start_time}")
        })
    
    # Check section conflicts
    cursor.execute(f"""
        SELECT s.schedule_id, s.course_id, c.course_name
        FROM schedule s
        JOIN courses c ON s.course_id = c.course_id
        WHERE s.section_id = ? 
        AND s.day = ? 
        AND s.start_time < ?
        AND s.end_time > ?
        {exclude_clause}
    """, (section_id, day, end_time, start_time) + exclude_params)
    
    for row in cursor.fetchall():
        conflicts.append({
            "type": "section_conflict",
            "schedule_id": str(row[0]),
            "message": (f"Section {section_id} already has {row[2]} "
                       f"scheduled at {day} {start_time}")
        })
    
    return conflicts


def calculate_efficiency_metrics(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Calculate comprehensive efficiency metrics for the schedule
    
    Returns:
        Dictionary with efficiency metrics
    """
    cursor = conn.cursor()
    warnings = []
    
    # Get all schedule entries
    cursor.execute("""
        SELECT schedule_id, room_id, instructor_id, section_id, 
               day, start_time, end_time
        FROM schedule
        ORDER BY day, start_time
    """)
    
    schedule_entries = cursor.fetchall()
    
    # Calculate room utilization
    room_schedule = {}
    for entry in schedule_entries:
        _, room_id, _, _, day, start_time, end_time = entry
        key = (room_id, day)
        
        if key not in room_schedule:
            room_schedule[key] = []
        
        start = datetime.strptime(start_time, '%H:%M')
        end = datetime.strptime(end_time, '%H:%M')
        duration = (end - start).seconds / 3600
        room_schedule[key].append((start_time, end_time, duration))
    
    # Calculate gaps and utilization for rooms
    room_utilization = {}
    total_gaps = 0
    
    for (room_id, day), sessions in room_schedule.items():
        sessions.sort()
        
        # Calculate total usage time
        total_usage = sum(s[2] for s in sessions)
        
        # Assume working day is 8am-6pm (10 hours)
        room_utilization[room_id] = room_utilization.get(room_id, 0) + total_usage
        
        # Check for gaps
        for i in range(len(sessions) - 1):
            end_current = datetime.strptime(sessions[i][1], '%H:%M')
            start_next = datetime.strptime(sessions[i+1][0], '%H:%M')
            gap_hours = (start_next - end_current).seconds / 3600
            
            if gap_hours >= 2:
                total_gaps += 1
                warnings.append(
                    f"Room {room_id} idle for {gap_hours:.1f} hours on {day} "
                    f"between {sessions[i][1]} and {sessions[i+1][0]}"
                )
    
    # Calculate instructor utilization
    instructor_schedule = {}
    for entry in schedule_entries:
        _, _, instructor_id, _, day, start_time, end_time = entry
        
        if instructor_id not in instructor_schedule:
            instructor_schedule[instructor_id] = 0
        
        start = datetime.strptime(start_time, '%H:%M')
        end = datetime.strptime(end_time, '%H:%M')
        duration = (end - start).seconds / 3600
        instructor_schedule[instructor_id] += duration
    
    # Get total available hours (5 working days × 10 hours)
    total_available_hours = 50
    
    # Calculate percentages
    room_utilization_pct = {
        room_id: round((hours / total_available_hours) * 100, 1)
        for room_id, hours in room_utilization.items()
    }
    
    instructor_utilization_pct = {
        instructor_id: round((hours / total_available_hours) * 100, 1)
        for instructor_id, hours in instructor_schedule.items()
    }
    
    # Calculate overall efficiency
    avg_room_util = sum(room_utilization_pct.values()) / len(room_utilization_pct) if room_utilization_pct else 0
    avg_instr_util = sum(instructor_utilization_pct.values()) / len(instructor_utilization_pct) if instructor_utilization_pct else 0
    overall_efficiency = round((avg_room_util + avg_instr_util) / 2, 1)
    
    return {
        "overall_efficiency": overall_efficiency,
        "room_utilization": room_utilization_pct,
        "instructor_utilization": instructor_utilization_pct,
        "total_gaps": total_gaps,
        "warnings": warnings
    }


# ==================== API Endpoints ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    initialize_database()
    logger.info("API started successfully")


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint
    Returns API status and database connectivity
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )


@app.get("/slots", tags=["Slots"])
async def get_all_slots() -> List[Dict]:
    """
    Retrieve all schedule slots from the database
    
    Returns:
        List of schedule entries with full details
    """
    try:
        with get_db_connection() as conn:
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
            
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            slots = []
            for row in rows:
                slots.append({
                    "schedule_id": row[0],
                    "course_id": row[1],
                    "course_name": row[2],
                    "section_id": row[3],
                    "lecture_number": row[4],
                    "day": row[5],
                    "start_time": row[6],
                    "end_time": row[7],
                    "room_id": row[8],
                    "room_type": row[9],
                    "instructor_id": row[10],
                    "instructor_name": row[11],
                    "created_at": row[12],
                    "updated_at": row[13]
                })
            
            logger.info(f"Retrieved {len(slots)} schedule slots")
            return slots
    
    except Exception as e:
        logger.error(f"Error retrieving slots: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedule slots"
        )


@app.get("/slots/{schedule_id}", tags=["Slots"])
async def get_slot(schedule_id: int) -> Dict:
    """
    Retrieve a specific schedule slot by ID
    
    Args:
        schedule_id: ID of the schedule entry
    
    Returns:
        Schedule entry details
    """
    try:
        with get_db_connection() as conn:
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
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Schedule slot {schedule_id} not found"
                )
            
            return {
                "schedule_id": row[0],
                "course_id": row[1],
                "course_name": row[2],
                "section_id": row[3],
                "lecture_number": row[4],
                "day": row[5],
                "start_time": row[6],
                "end_time": row[7],
                "room_id": row[8],
                "instructor_id": row[9],
                "instructor_name": row[10]
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving slot {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedule slot"
        )


@app.post("/slots", status_code=status.HTTP_201_CREATED, tags=["Slots"])
async def create_slot(slot: SlotCreate) -> Dict:
    """
    Create a new schedule slot
    
    Validates the slot for conflicts before inserting
    
    Args:
        slot: Schedule slot data
    
    Returns:
        Created schedule entry with assigned ID
    """
    try:
        with get_db_connection() as conn:
            # Validate for conflicts
            conflicts = validate_slot_conflicts(
                conn, None, slot.day, slot.start_time, slot.end_time,
                slot.room_id, slot.instructor_id, slot.section_id
            )
            
            if conflicts:
                logger.warning(f"Slot creation failed: conflicts detected")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Schedule conflicts detected",
                        "conflicts": conflicts
                    }
                )
            
            # Insert the slot
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedule 
                (course_id, section_id, lecture_number, day, start_time, 
                 end_time, room_id, instructor_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (slot.course_id, slot.section_id, slot.lecture_number,
                  slot.day, slot.start_time, slot.end_time,
                  slot.room_id, slot.instructor_id))
            
            schedule_id = cursor.lastrowid
            
            logger.info(f"Created schedule slot {schedule_id}")
            
            return {
                "schedule_id": schedule_id,
                "message": "Schedule slot created successfully",
                **slot.dict()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating slot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule slot"
        )


@app.put("/slots/{schedule_id}", tags=["Slots"])
async def update_slot(schedule_id: int, slot_update: SlotUpdate) -> Dict:
    """
    Update an existing schedule slot
    
    Only provided fields will be updated
    Validates updated slot for conflicts
    
    Args:
        schedule_id: ID of the schedule entry to update
        slot_update: Fields to update
    
    Returns:
        Updated schedule entry
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current slot
            cursor.execute("""
                SELECT course_id, section_id, day, start_time, end_time, 
                       room_id, instructor_id
                FROM schedule
                WHERE schedule_id = ?
            """, (schedule_id,))
            
            current = cursor.fetchone()
            
            if not current:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Schedule slot {schedule_id} not found"
                )
            
            # Build updated values
            course_id, section_id, day, start_time, end_time, room_id, instructor_id = current
            
            new_day = slot_update.day if slot_update.day else day
            new_start = slot_update.start_time if slot_update.start_time else start_time
            new_end = slot_update.end_time if slot_update.end_time else end_time
            new_room = slot_update.room_id if slot_update.room_id else room_id
            new_instructor = slot_update.instructor_id if slot_update.instructor_id else instructor_id
            
            # Validate time consistency if both are being updated
            if slot_update.start_time and slot_update.end_time:
                start_dt = datetime.strptime(new_start, '%H:%M')
                end_dt = datetime.strptime(new_end, '%H:%M')
                if end_dt <= start_dt:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="end_time must be after start_time"
                    )
            
            # Validate for conflicts
            conflicts = validate_slot_conflicts(
                conn, schedule_id, new_day, new_start, new_end,
                new_room, new_instructor, section_id
            )
            
            if conflicts:
                logger.warning(f"Slot update failed: conflicts detected")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Schedule conflicts detected",
                        "conflicts": conflicts
                    }
                )
            
            # Update the slot
            cursor.execute("""
                UPDATE schedule
                SET day = ?, start_time = ?, end_time = ?, 
                    room_id = ?, instructor_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE schedule_id = ?
            """, (new_day, new_start, new_end, new_room, new_instructor, schedule_id))
            
            logger.info(f"Updated schedule slot {schedule_id}")
            
            return {
                "schedule_id": schedule_id,
                "message": "Schedule slot updated successfully",
                "updated_fields": {
                    k: v for k, v in slot_update.dict().items() if v is not None
                }
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating slot {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule slot"
        )


@app.delete("/slots/{schedule_id}", tags=["Slots"])
async def delete_slot(schedule_id: int) -> Dict:
    """
    Delete a schedule slot
    
    Args:
        schedule_id: ID of the schedule entry to delete
    
    Returns:
        Confirmation message
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if slot exists
            cursor.execute("SELECT 1 FROM schedule WHERE schedule_id = ?", (schedule_id,))
            
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Schedule slot {schedule_id} not found"
                )
            
            # Delete the slot
            cursor.execute("DELETE FROM schedule WHERE schedule_id = ?", (schedule_id,))
            
            logger.info(f"Deleted schedule slot {schedule_id}")
            
            return {
                "message": f"Schedule slot {schedule_id} deleted successfully",
                "schedule_id": schedule_id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting slot {schedule_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete schedule slot"
        )


@app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
async def validate_schedule() -> ValidationResponse:
    """
    Validate the entire schedule for conflicts and inefficiencies
    
    Checks:
    - Instructor conflicts
    - Room conflicts
    - Section conflicts
    - Efficiency issues (gaps, underutilization)
    
    Returns:
        Validation results with conflicts and warnings
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all schedule entries
            cursor.execute("""
                SELECT schedule_id, course_id, section_id, day, start_time, 
                       end_time, room_id, instructor_id
                FROM schedule
            """)
            
            entries = cursor.fetchall()
            all_conflicts = []
            
            # Validate each entry against all others
            for entry in entries:
                schedule_id, course_id, section_id, day, start_time, end_time, room_id, instructor_id = entry
                
                conflicts = validate_slot_conflicts(
                    conn, schedule_id, day, start_time, end_time,
                    room_id, instructor_id, section_id
                )
                
                all_conflicts.extend(conflicts)
            
            # Get efficiency warnings
            metrics = calculate_efficiency_metrics(conn)
            
            is_valid = len