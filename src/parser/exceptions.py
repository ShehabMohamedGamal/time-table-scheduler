from typing import Optional, List

class LevelParserError(Exception):
    """Base exception for level parser errors"""
    pass

class InvalidFormatError(LevelParserError):
    """Raised when JSON format is invalid"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        super().__init__(f"Format error{f' in {field}' if field else ''}: {message}")

class MissingCourseError(LevelParserError):
    """Raised when required courses are missing"""
    def __init__(self, courses: List[str], level: Optional[str] = None):
        self.courses = courses
        self.level = level
        courses_str = ", ".join(courses)
        level_str = f" in level {level}" if level else ""
        super().__init__(f"Missing courses{level_str}: {courses_str}")

class ConstraintViolationError(LevelParserError):
    """Raised when course constraints are violated"""
    def __init__(self, constraint: str, details: str):
        self.constraint = constraint
        super().__init__(f"Constraint violation ({constraint}): {details}")