"""
Data Parser Module
==================
Handles parsing and preprocessing of timetable data from various sources.
"""

import csv
import io
import logging
from typing import List, Dict, Any, BinaryIO
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ParsedScheduleEntry:
    """Represents a parsed schedule entry"""
    course_id: str
    section_id: str
    lecture_number: int
    day: str
    start_time: str
    end_time: str
    room_id: str
    instructor_id: str


class DataParser:
    """
    Handles parsing of timetable data from CSV and other formats.
    
    Responsibilities:
    - CSV file parsing
    - Data validation and cleaning
    - Format conversion
    - Error handling for malformed data
    """
    
    def __init__(self):
        """Initialize the data parser."""
        self.required_fields = {
            'course_id', 'section_id', 'lecture_number', 'day',
            'start_time', 'end_time', 'room_id', 'instructor_id'
        }
    
    def parse_csv_file(self, file_content: bytes) -> List[ParsedScheduleEntry]:
        """
        Parse CSV file content into schedule entries.
        
        Args:
            file_content: Binary content of CSV file
            
        Returns:
            List of parsed schedule entries
            
        Raises:
            ValueError: If CSV format is invalid or required fields are missing
        """
        try:
            # Decode bytes to string
            content_str = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content_str))
            
            # Validate headers
            headers = set(csv_reader.fieldnames or [])
            self._validate_headers(headers)
            
            # Parse rows
            entries = []
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    entry = self._parse_row(row, row_num)
                    entries.append(entry)
                except ValueError as e:
                    logger.warning(f"Skipping row {row_num}: {str(e)}")
                    continue
            
            logger.info(f"Successfully parsed {len(entries)} schedule entries")
            return entries
            
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid file encoding. Expected UTF-8: {str(e)}")
        except csv.Error as e:
            raise ValueError(f"CSV parsing error: {str(e)}")
    
    def _validate_headers(self, headers: set) -> None:
        """
        Validate that CSV contains all required headers.
        
        Args:
            headers: Set of header names from CSV
            
        Raises:
            ValueError: If required headers are missing
        """
        # Normalize headers (strip whitespace, lowercase)
        normalized_headers = {h.strip().lower() for h in headers}
        required_normalized = {f.lower() for f in self.required_fields}
        
        missing = required_normalized - normalized_headers
        if missing:
            raise ValueError(
                f"Missing required CSV columns: {', '.join(sorted(missing))}"
            )
    
    def _parse_row(self, row: Dict[str, str], row_num: int) -> ParsedScheduleEntry:
        """
        Parse a single CSV row into a schedule entry.
        
        Args:
            row: Dictionary of row data
            row_num: Row number for error reporting
            
        Returns:
            ParsedScheduleEntry object
            
        Raises:
            ValueError: If row data is invalid
        """
        # Normalize keys (strip whitespace)
        normalized_row = {k.strip(): v.strip() for k, v in row.items()}
        
        try:
            # Extract and validate fields
            course_id = self._validate_string_field(
                normalized_row.get('course_id', ''), 'course_id'
            )
            section_id = self._validate_string_field(
                normalized_row.get('section_id', ''), 'section_id'
            )
            lecture_number = self._validate_lecture_number(
                normalized_row.get('lecture_number', '')
            )
            day = self._validate_day(normalized_row.get('day', ''))
            start_time = self._validate_time(
                normalized_row.get('start_time', ''), 'start_time'
            )
            end_time = self._validate_time(
                normalized_row.get('end_time', ''), 'end_time'
            )
            room_id = self._validate_string_field(
                normalized_row.get('room_id', ''), 'room_id'
            )
            instructor_id = self._validate_string_field(
                normalized_row.get('instructor_id', ''), 'instructor_id'
            )
            
            # Validate time ordering
            if end_time <= start_time:
                raise ValueError("end_time must be after start_time")
            
            return ParsedScheduleEntry(
                course_id=course_id,
                section_id=section_id,
                lecture_number=lecture_number,
                day=day,
                start_time=start_time,
                end_time=end_time,
                room_id=room_id,
                instructor_id=instructor_id
            )
            
        except ValueError as e:
            raise ValueError(f"Row {row_num}: {str(e)}")
    
    def _validate_string_field(self, value: str, field_name: str) -> str:
        """
        Validate a string field.
        
        Args:
            value: Field value
            field_name: Name of field for error reporting
            
        Returns:
            Validated string
            
        Raises:
            ValueError: If validation fails
        """
        if not value or not value.strip():
            raise ValueError(f"{field_name} cannot be empty")
        
        cleaned = value.strip()
        if len(cleaned) > 50:
            raise ValueError(f"{field_name} exceeds maximum length of 50 characters")
        
        return cleaned
    
    def _validate_lecture_number(self, value: str) -> int:
        """
        Validate and convert lecture number.
        
        Args:
            value: Lecture number as string
            
        Returns:
            Validated lecture number
            
        Raises:
            ValueError: If validation fails
        """
        try:
            num = int(value)
            if num < 1 or num > 10:
                raise ValueError("lecture_number must be between 1 and 10")
            return num
        except (ValueError, TypeError):
            raise ValueError(f"lecture_number must be a valid integer: '{value}'")
    
    def _validate_day(self, value: str) -> str:
        """
        Validate day of week.
        
        Args:
            value: Day name
            
        Returns:
            Validated day name
            
        Raises:
            ValueError: If day is invalid
        """
        valid_days = {
            'Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday'
        }
        
        cleaned = value.strip().title()
        if cleaned not in valid_days:
            raise ValueError(
                f"day must be one of: {', '.join(valid_days)}"
            )
        
        return cleaned
    
    def _validate_time(self, value: str, field_name: str) -> str:
        """
        Validate time format (HH:MM).
        
        Args:
            value: Time string
            field_name: Field name for error reporting
            
        Returns:
            Validated time string
            
        Raises:
            ValueError: If time format is invalid
        """
        import re
        
        cleaned = value.strip()
        if not re.match(r'^\d{2}:\d{2}$', cleaned):
            raise ValueError(
                f"{field_name} must be in HH:MM format (e.g., '09:00')"
            )
        
        # Validate hour and minute ranges
        try:
            hour, minute = map(int, cleaned.split(':'))
            if hour < 0 or hour > 23:
                raise ValueError(f"{field_name} hour must be between 00 and 23")
            if minute < 0 or minute > 59:
                raise ValueError(f"{field_name} minute must be between 00 and 59")
        except ValueError as e:
            raise ValueError(f"Invalid time format for {field_name}: {str(e)}")
        
        return cleaned
    
    def entries_to_dict_list(self, entries: List[ParsedScheduleEntry]) -> List[Dict[str, Any]]:
        """
        Convert parsed entries to dictionary format for database insertion.
        
        Args:
            entries: List of parsed schedule entries
            
        Returns:
            List of dictionaries
        """
        return [
            {
                'course_id': e.course_id,
                'section_id': e.section_id,
                'lecture_number': e.lecture_number,
                'day': e.day,
                'start_time': e.start_time,
                'end_time': e.end_time,
                'room_id': e.room_id,
                'instructor_id': e.instructor_id
            }
            for e in entries
        ]
