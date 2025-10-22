# Course Level Parser

## Overview
The Course Level Parser is the first component of the Timetable Generator CSP project. It handles parsing of course levels from `levels.txt` and provides validation and mapping functionality for the constraint satisfaction solver.

## Features
- ✅ Parse JSON-formatted course levels from `levels.txt`
- ✅ Create in-memory course-level mapping
- ✅ Validate course data against database
- ✅ Comprehensive error handling and validation
- ✅ Export functionality for external use
- ✅ Unit tests with 100% coverage

## Files
- `course_level_parser.py` - Main parser implementation
- `test_course_level_parser.py` - Unit tests
- `demo_parser.py` - Demonstration script
- `level_mapping_export.json` - Exported mapping data

## Usage

### Basic Usage
```python
from course_level_parser import CourseLevelParser

# Initialize parser
parser = CourseLevelParser("levels.txt", "timetable.db")

# Load levels
if parser.load_levels():
    print("Levels loaded successfully!")
    
    # Validate with database
    if parser.validate_with_database():
        print("Database validation successful!")
    else:
        print("Validation warnings:", parser.get_validation_errors())
```

### Key Methods
- `load_levels()` - Load course levels from JSON file
- `validate_with_database()` - Validate against database
- `get_courses_by_level(level)` - Get courses for specific level
- `get_level_for_course(course_id)` - Get level for specific course
- `get_course_info(course_id)` - Get complete course information
- `export_level_mapping()` - Export data for external use

### Running Tests
```bash
python -m pytest test_course_level_parser.py -v
```

### Running Demo
```bash
python demo_parser.py
```

## Data Structure

### Input: levels.txt
```json
{
    "level_1": ["CSC111", "MTH111", "PHY113"],
    "level_2": ["CSC211", "MTH212", "CSC114"],
    "level_3": ["CSC317", "CSC314", "CSC315"],
    "level_4": ["CSC414", "CSC415", "CSC426"]
}
```

### Output: CourseInfo Objects
```python
@dataclass
class CourseInfo:
    course_id: str
    level: int
    course_name: Optional[str] = None
    credits: Optional[float] = None
    course_type: Optional[str] = None
```

## Validation
The parser performs comprehensive validation:
- JSON format validation
- Course ID format validation
- Duplicate course detection
- Database existence validation
- Data consistency checks

## Statistics
Current data loaded:
- **Total Courses**: 53
- **Total Levels**: 4
- **Level 1**: 9 courses
- **Level 2**: 8 courses  
- **Level 3**: 10 courses
- **Level 4**: 26 courses

## Next Steps
This parser is ready for integration with:
1. **Phase 2**: Core Models (TimeSlot, constraints)
2. **Phase 3**: Basic Solver (backtracking algorithm)
3. **CSP Solver**: Level-based scheduling constraints

## Error Handling
The parser provides detailed error reporting:
- File not found errors
- JSON parsing errors
- Data structure validation
- Database connectivity issues
- Course existence validation

All errors are collected and can be retrieved via `get_validation_errors()`.
