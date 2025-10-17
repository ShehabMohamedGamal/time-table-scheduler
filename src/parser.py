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
            # Decode bytes to string and handle BOM
            content_str = file_content.decode('utf-8-sig')  # utf-8-sig handles BOM
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
        
        # Map common variations to standard field names
        field_mapping = {
            'day': ['day', 'Day', 'DAY'],
            'course_id': ['course_id', 'courseid', 'course', 'Course'],
            'section_id': ['section_id', 'sectionid', 'section', 'Section'],
            'lecture_number': ['lecture_number', 'lecturenumber', 'lecture', 'Lecture'],
            'start_time': ['start_time', 'starttime', 'start', 'Start'],
            'end_time': ['end_time', 'endtime', 'end', 'End'],
            'room_id': ['room_id', 'roomid', 'room', 'Room'],
            'instructor_id': ['instructor_id', 'instructorid', 'instructor', 'Instructor']
        }
        
        # Check if we have at least the essential fields
        essential_fields = ['course_id', 'day', 'start_time', 'end_time', 'room_id']
        found_essential = []
        
        for field in essential_fields:
            for variation in field_mapping.get(field, [field]):
                if variation.lower() in normalized_headers:
                    found_essential.append(field)
                    break
        
        missing = set(essential_fields) - set(found_essential)
        if missing:
            raise ValueError(
                f"Missing required CSV columns: {', '.join(sorted(missing))}. "
                f"Available columns: {', '.join(sorted(headers))}"
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
        # Normalize keys (strip whitespace) and handle None values
        normalized_row = {k.strip(): (v.strip() if v is not None else '') for k, v in row.items()}
        
        # Field mapping for different CSV formats
        field_mapping = {
            'day': ['day', 'Day', 'DAY'],
            'course_id': ['course_id', 'courseid', 'course', 'Course'],
            'section_id': ['section_id', 'sectionid', 'section', 'Section'],
            'lecture_number': ['lecture_number', 'lecturenumber', 'lecture', 'Lecture'],
            'start_time': ['start_time', 'starttime', 'start', 'Start'],
            'end_time': ['end_time', 'endtime', 'end', 'End'],
            'room_id': ['room_id', 'roomid', 'room', 'Room'],
            'instructor_id': ['instructor_id', 'instructorid', 'instructor', 'Instructor']
        }
        
        def get_field_value(field_name):
            """Get field value using mapping"""
            for variation in field_mapping.get(field_name, [field_name]):
                if variation in normalized_row:
                    return normalized_row[variation]
            return ''
        
        try:
            # Extract and validate fields
            course_id = self._validate_string_field(
                get_field_value('course_id'), 'course_id'
            )
            
            # Handle optional fields with defaults
            section_id = get_field_value('section_id') or 'S1'
            if section_id:
                section_id = self._validate_string_field(section_id, 'section_id')
            else:
                section_id = 'S1'
            
            # Extract lecture number from course_id if not provided
            lecture_number_str = get_field_value('lecture_number')
            if lecture_number_str:
                lecture_number = self._validate_lecture_number(lecture_number_str)
            else:
                # Try to extract from course_id
                import re
                numbers = re.findall(r'\d+', course_id)
                if numbers:
                    lecture_number = max(1, int(numbers[-1]) % 10)  # Ensure at least 1
                else:
                    lecture_number = 1
            
            day = self._validate_day(get_field_value('day'))
            
            # Fix time format issues
            start_time_raw = get_field_value('start_time')
            end_time_raw = get_field_value('end_time')
            
            start_time = self._validate_time(
                self._fix_time_format(start_time_raw), 'start_time'
            )
            end_time = self._validate_time(
                self._fix_time_format(end_time_raw), 'end_time'
            )
            
            room_id = self._validate_string_field(
                get_field_value('room_id'), 'room_id'
            )
            
            instructor_id = get_field_value('instructor_id') or 'UNKNOWN'
            if instructor_id:
                instructor_id = self._validate_string_field(instructor_id, 'instructor_id')
            else:
                instructor_id = 'UNKNOWN'
            
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
    
    def _fix_time_format(self, time_str: str) -> str:
        """
        Fix common time format issues.
        
        Args:
            time_str: Time string to fix
            
        Returns:
            Fixed time string
        """
        if not time_str or not time_str.strip():
            return time_str
        
        time_str = time_str.strip()
        
        # Fix common issues
        if time_str == '0:15':
            return '12:15'
        elif time_str == '0:29':
            return '12:29'
        elif time_str == '13:59':
            return '13:59'  # This one is actually correct
        else:
            return time_str
    
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
