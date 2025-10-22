from .exceptions import InvalidFormatError, MissingCourseError, ConstraintViolationError
import json
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Union, Optional, Set
from dataclasses import dataclass
from enum import Enum
import sqlite3

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class CourseType(Enum):
    REQUIRED = "required"
    ELECTIVE = "elective"

@dataclass
class CourseGroup:
    """Represents a group of optional courses"""
    courses: List[Union[str, 'CourseGroup']]
    type: CourseType = CourseType.ELECTIVE
    max_concurrent: int = 2  # Maximum concurrent courses from elective group

class ValidationRule:
    """Base class for validation rules"""
    def validate(self, parser: 'LevelParser') -> List[str]:
        raise NotImplementedError

class CourseExistenceRule(ValidationRule):
    """Validates all courses exist in database"""
    def validate(self, parser: 'LevelParser') -> List[str]:
        errors = []
        with sqlite3.connect(parser.db_path) as conn:
            cur = conn.cursor()
            for level, courses in parser.levels.items():
                for course in parser._flatten_courses(courses):
                    cur.execute("SELECT 1 FROM courses WHERE course_id = ?", (course,))
                    if not cur.fetchone():
                        errors.append(f"Course {course} in level {level} not found in database")
        return errors

class LevelConsistencyRule(ValidationRule):
    """Validates level consistency (prerequisites, no duplicates)"""
    def validate(self, parser: 'LevelParser') -> List[str]:
        errors = []
        all_courses: Set[str] = set()
        
        for level, courses in parser.levels.items():
            level_courses = set(parser._flatten_courses(courses))
            
            # Check for duplicates within level
            if len(level_courses) != len(parser._flatten_courses(courses)):
                errors.append(f"Duplicate courses found in level {level}")
            
            # Check for duplicates across levels
            duplicates = all_courses.intersection(level_courses)
            if duplicates:
                errors.append(f"Courses {duplicates} appear in multiple levels")
                
            all_courses.update(level_courses)
        return errors

class ElectiveGroupRule(ValidationRule):
    """Validates elective group constraints"""
    def validate(self, parser: 'LevelParser') -> List[str]:
        errors = []
        
        def validate_group(group: CourseGroup, level: str) -> None:
            if group.type == CourseType.ELECTIVE:
                if len(group.courses) < group.max_concurrent:
                    errors.append(
                        f"Elective group in level {level} has fewer options "
                        f"({len(group.courses)}) than max concurrent ({group.max_concurrent})"
                    )
        
        for level, courses in parser.levels.items():
            for item in courses:
                if isinstance(item, CourseGroup):
                    validate_group(item, level)
        
        return errors

class LevelParser:
    """Parses and validates course levels from JSON against database"""
    
    def __init__(self, db_path: str, levels_path: str):
        self.db_path = db_path
        self.levels_path = levels_path
        self.levels: Dict[str, List[Union[str, CourseGroup]]] = {}
        self.validation_rules: List[ValidationRule] = [
            CourseExistenceRule(),
            LevelConsistencyRule(),
            ElectiveGroupRule()
        ]

    def load_levels(self) -> None:
        """Load and parse levels.json file with error handling"""
        try:
            with open(self.levels_path) as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                raise InvalidFormatError("Root element must be an object")
            
            # Validate expected level format (level_1, level_2, etc)
            for level in data:
                if not level.startswith("level_"):
                    raise InvalidFormatError(f"Invalid level key: {level}", "level_name")
                
                if not isinstance(data[level], list):
                    raise InvalidFormatError(
                        f"Level {level} must contain a list of courses",
                        level
                    )
            
            self.levels = {
                level: self._parse_course_list(courses) 
                for level, courses in data.items()
            }
            
        except JSONDecodeError as e:
            raise InvalidFormatError(f"Invalid JSON format: {str(e)}")
        except FileNotFoundError:
            raise InvalidFormatError(f"Levels file not found: {self.levels_path}")

    def _parse_course_list(self, 
                          courses: List[Any], 
                          current_level: Optional[str] = None
                          ) -> List[Union[str, CourseGroup]]:
        """Parse course list with validation"""
        parsed = []
        
        for item in courses:
            if isinstance(item, str):
                if not self._is_valid_course_id(item):
                    raise InvalidFormatError(
                        f"Invalid course ID format: {item}",
                        current_level
                    )
                parsed.append(item)
            elif isinstance(item, list):
                # Validate elective group
                if len(item) < 2:
                    raise ConstraintViolationError(
                        "elective_group_size",
                        f"Elective group must have at least 2 options, got {len(item)}"
                    )
                parsed.append(CourseGroup(
                    courses=self._parse_course_list(item, current_level)
                ))
            else:
                raise InvalidFormatError(
                    f"Invalid course entry type: {type(item).__name__}",
                    current_level
                )
        
        return parsed

    def _is_valid_course_id(self, course_id: str) -> bool:
        """Validate course ID format"""
        # Example: Matches format like CSC111, MTH212, etc.
        import re
        return bool(re.match(r'^[A-Z]{2,3}\d{3}$', course_id))

    def validate(self, raise_errors: bool = True) -> List[str]:
        """Run all validation with error handling"""
        errors = []
        
        try:
            # Check database connection first
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                
                # Collect all course IDs from levels
                all_courses = set(self._flatten_courses(
                    [c for courses in self.levels.values() for c in courses]
                ))
                
                # Check existence in database
                missing_courses = []
                for course in all_courses:
                    cur.execute(
                        "SELECT 1 FROM courses WHERE course_id = ?", 
                        (course,)
                    )
                    if not cur.fetchone():
                        missing_courses.append(course)
                
                if missing_courses:
                    error = MissingCourseError(missing_courses)
                    if raise_errors:
                        raise error
                    errors.append(str(error))
                
                # Run other validation rules
                for rule in self.validation_rules:
                    try:
                        rule_errors = rule.validate(self)
                        errors.extend(rule_errors)
                    except Exception as e:
                        errors.append(f"Validation error in {rule.__class__.__name__}: {str(e)}")
                
        except sqlite3.Error as e:
            error = f"Database error: {str(e)}"
            if raise_errors:
                raise ConstraintViolationError("database", error)
            errors.append(error)
            
        if errors and raise_errors:
            raise ConstraintViolationError("validation", "; ".join(errors))
            
        return errors
    
    def get_level_courses(self, level: str) -> Optional[List[Union[str, CourseGroup]]]:
        """Get parsed courses for a specific level"""
        return self.levels.get(level)