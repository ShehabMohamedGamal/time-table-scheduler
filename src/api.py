"""
API Handler Module
==================
FastAPI REST API endpoints for timetable management.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from config import api_config, TIME_SLOT_REGEX, MAX_LECTURE_NUMBER


logger = logging.getLogger(__name__)


# ==================== Pydantic Models ====================

class SlotCreate(BaseModel):
    """Model for creating a new schedule slot"""
    course_id: str = Field(..., min_length=1, max_length=50)
    section_id: str = Field(..., min_length=1, max_length=50)
    lecture_number: int = Field(..., ge=1, le=MAX_LECTURE_NUMBER)
    day: str = Field(..., min_length=1)
    start_time: str = Field(..., pattern=TIME_SLOT_REGEX)
    end_time: str = Field(..., pattern=TIME_SLOT_REGEX)
    room_id: str = Field(..., min_length=1, max_length=50)
    instructor_id: str = Field(..., min_length=1, max_length=50)
    
    @validator('day')
    def validate_day(cls, v):
        from config import schedule_config
        if v not in schedule_config.valid_days:
            raise ValueError(f'Day must be one of: {", ".join(schedule_config.valid_days)}')
        return v
    
    @validator('end_time')
    def validate_times(cls, v, values):
        if 'start_time' in values:
            from datetime import datetime
            start = datetime.strptime(values['start_time'], '%H:%M')
            end = datetime.strptime(v, '%H:%M')
            if end <= start:
                raise ValueError('end_time must be after start_time')
        return v
    
    class Config:
        json_schema_extra = {
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
    start_time: Optional[str] = Field(None, pattern=TIME_SLOT_REGEX)
    end_time: Optional[str] = Field(None, pattern=TIME_SLOT_REGEX)
    room_id: Optional[str] = Field(None, min_length=1, max_length=50)
    instructor_id: Optional[str] = Field(None, min_length=1, max_length=50)
    
    @validator('day')
    def validate_day(cls, v):
        if v is not None:
            from config import schedule_config
            if v not in schedule_config.valid_days:
                raise ValueError(f'Day must be one of: {", ".join(schedule_config.valid_days)}')
        return v
    
    class Config:
        json_schema_extra = {
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


class EfficiencyMetrics(BaseModel):
    """Model for efficiency metrics response"""
    overall_efficiency: float = Field(..., ge=0, le=100)
    room_utilization: Dict[str, float]
    instructor_utilization: Dict[str, float]
    total_gaps: int
    warnings: List[str]


# ==================== API Handler Class ====================

class APIHandler:
    """
    FastAPI application handler for timetable management.
    
    Responsibilities:
    - Expose REST API endpoints
    - Handle HTTP requests and responses
    - Coordinate between slot manager, validator, and parser
    - Error handling and response formatting
    """
    
    def __init__(self, slot_manager, validator, parser):
        """
        Initialize API handler with dependencies.
        
        Args:
            slot_manager: SlotManager instance
            validator: ScheduleValidator instance
            parser: DataParser instance
        """
        self.slot_manager = slot_manager
        self.validator = validator
        self.parser = parser
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title=api_config.title,
            description=api_config.description,
            version=api_config.version
        )
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register all API routes"""
        
        @self.app.get("/health", tags=["System"])
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/slots", tags=["Slots"])
        async def get_all_slots() -> List[Dict]:
            """Retrieve all schedule slots"""
            try:
                slots = self.slot_manager.get_all_slots()
                logger.info(f"Retrieved {len(slots)} schedule slots")
                return slots
            except Exception as e:
                logger.error(f"Error retrieving slots: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve schedule slots"
                )
        
        @self.app.get("/slots/{schedule_id}", tags=["Slots"])
        async def get_slot(schedule_id: int) -> Dict:
            """Retrieve a specific schedule slot by ID"""
            try:
                slot = self.slot_manager.get_slot(schedule_id)
                return slot
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"Error retrieving slot {schedule_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve schedule slot"
                )
        
        @self.app.post("/slots", status_code=status.HTTP_201_CREATED, tags=["Slots"])
        async def create_slot(slot: SlotCreate) -> Dict:
            """Create a new schedule slot with validation"""
            try:
                result = self.slot_manager.create_slot(
                    slot.course_id, slot.section_id, slot.lecture_number,
                    slot.day, slot.start_time, slot.end_time,
                    slot.room_id, slot.instructor_id
                )
                return result
            except ValueError as e:
                error_data = eval(str(e)) if isinstance(str(e), str) and '{' in str(e) else {"message": str(e)}
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error_data
                )
            except Exception as e:
                logger.error(f"Error creating slot: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create schedule slot"
                )
        
        @self.app.put("/slots/{schedule_id}", tags=["Slots"])
        async def update_slot(schedule_id: int, slot_update: SlotUpdate) -> Dict:
            """Update an existing schedule slot"""
            try:
                updates = {k: v for k, v in slot_update.dict().items() if v is not None}
                result = self.slot_manager.update_slot(schedule_id, **updates)
                return result
            except ValueError as e:
                error_data = eval(str(e)) if isinstance(str(e), str) and '{' in str(e) else {"message": str(e)}
                status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_409_CONFLICT
                raise HTTPException(status_code=status_code, detail=error_data)
            except Exception as e:
                logger.error(f"Error updating slot {schedule_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update schedule slot"
                )
        
        @self.app.delete("/slots/{schedule_id}", tags=["Slots"])
        async def delete_slot(schedule_id: int) -> Dict:
            """Delete a schedule slot"""
            try:
                result = self.slot_manager.delete_slot(schedule_id)
                return result
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"Error deleting slot {schedule_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete schedule slot"
                )
        
        @self.app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
        async def validate_schedule() -> ValidationResponse:
            """Validate the entire schedule for conflicts"""
            try:
                result = self.validator.validate_entire_schedule()
                return ValidationResponse(**result)
            except Exception as e:
                logger.error(f"Error validating schedule: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to validate schedule"
                )
        
        @self.app.get("/efficiency", response_model=EfficiencyMetrics, tags=["Analytics"])
        async def get_efficiency() -> EfficiencyMetrics:
            """Get efficiency metrics for the schedule"""
            try:
                metrics = self.validator.calculate_efficiency_metrics()
                return EfficiencyMetrics(**metrics)
            except Exception as e:
                logger.error(f"Error calculating efficiency: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to calculate efficiency metrics"
                )
        
        @self.app.post("/upload-csv", tags=["Data Import"])
        async def upload_csv(request: Request) -> Dict:
            """Upload and parse CSV file to create schedule entries"""
            try:
                # Read raw content from request body
                content = await request.body()
                
                # Parse CSV
                entries = self.parser.parse_csv_file(content)
                
                # Convert to dict format
                slot_dicts = self.parser.entries_to_dict_list(entries)
                
                # Bulk create slots
                result = self.slot_manager.bulk_create_slots(slot_dicts)
                
                return {
                    "message": "CSV processed successfully",
                    "filename": "uploaded_file.csv",  # Default filename since we can't get it from multipart
                    **result
                }
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            except Exception as e:
                logger.error(f"Error processing CSV: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process CSV file"
                )
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance"""
        return self.app
